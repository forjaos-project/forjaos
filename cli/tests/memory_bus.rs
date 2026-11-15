#![cfg(unix)]

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use zbus::blocking::connection::Builder;
use zbus::interface;

struct FakeMemory;

#[interface(name = "org.forjaos.Memory")]
impl FakeMemory {
    fn search(&self, query: &str, limit: u32) -> String {
        if query == "invalid-response" {
            return "not-json".into();
        }
        json!([{"title":query,"path":"/tmp/note","excerpt":"example","limit":limit}]).to_string()
    }

    fn timeline(&self, days: u32, limit: u32) -> String {
        json!([{"title":"Today","path":"/tmp/note","modified_at":42,"days":days,"limit":limit}])
            .to_string()
    }

    fn rebuild(&self) -> String {
        json!({"status":"ok","indexed":2,"semantic_search":false}).to_string()
    }

    fn remember(&self, note: &str) -> String {
        json!({"status":"ok","path":"/tmp/note","note":note}).to_string()
    }

    fn collectors(&self) -> String {
        json!([{"source":"shell","enabled":true,"retention_days":30,"available":true}]).to_string()
    }

    fn set_collector(&self, source: &str, enabled: bool) -> String {
        json!({"status":"ok","source":source,"enabled":enabled}).to_string()
    }

    fn set_retention(&self, source: &str, days: u32) -> String {
        json!({"status":"ok","source":source,"retention_days":days}).to_string()
    }

    fn purge(&self) -> String {
        json!({"status":"ok","removed":2}).to_string()
    }

    fn graph_repository(&self, path: &str) -> String {
        json!({"status":"ok","path":path,"nodes":2,"links":1}).to_string()
    }

    fn register_git_repository(&self, path: &str) -> String {
        json!({"status":"ok","path":path}).to_string()
    }

    fn unregister_git_repository(&self, path: &str) -> String {
        json!({"status":"ok","path":path}).to_string()
    }

    fn scan_git_repositories(&self) -> String {
        json!({"status":"ok","scanned":1}).to_string()
    }

    fn collect_event(
        &self,
        source: &str,
        detail: &str,
        cwd: &str,
        exit_code: i32,
        duration_ms: u64,
    ) -> String {
        json!({"status":"ok","source":source,"detail":detail,"cwd":cwd,"exit_code":exit_code,"duration_ms":duration_ms}).to_string()
    }
}

struct PrivateBus(Child);

impl Drop for PrivateBus {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

#[test]
fn memory_commands_use_private_session_bus() {
    if Command::new("dbus-daemon")
        .arg("--version")
        .output()
        .is_err()
    {
        return;
    }
    let mut child = Command::new("dbus-daemon")
        .args(["--session", "--nofork", "--print-address=1"])
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .expect("start private D-Bus");
    let mut address = String::new();
    BufReader::new(child.stdout.take().expect("D-Bus stdout"))
        .read_line(&mut address)
        .expect("read D-Bus address");
    let address = address.trim();
    assert!(!address.is_empty(), "private D-Bus has no address");
    let _bus = PrivateBus(child);
    let _service = Builder::address(address)
        .expect("D-Bus address")
        .name("org.forjaos.Memory")
        .expect("claim fake service name")
        .serve_at("/org/forjaos/Memory", FakeMemory)
        .expect("serve fake memory")
        .build()
        .expect("connect fake memory");

    let cases: &[&[&str]] = &[
        &["search", "needle", "--json"],
        &["timeline", "--json"],
        &["rebuild", "--json"],
        &["remember", "note", "--json"],
        &["collectors", "status", "--json"],
        &["collectors", "enable", "shell", "--json"],
        &["collectors", "disable", "shell", "--json"],
        &["retention", "shell", "30", "--json"],
        &["purge", "--json"],
        &["graph", ".", "--json"],
        &["git", "register", ".", "--json"],
        &["git", "unregister", ".", "--json"],
        &["git", "scan", "--json"],
    ];
    for args in cases {
        let output = Command::new(env!("CARGO_BIN_EXE_forja"))
            .arg("memory")
            .args(*args)
            .env("DBUS_SESSION_BUS_ADDRESS", address)
            .output()
            .expect("run forja memory");
        assert!(
            output.status.success(),
            "{args:?}: {}",
            String::from_utf8_lossy(&output.stdout)
        );
        let value: Value = serde_json::from_slice(&output.stdout).expect("memory JSON");
        assert!(value.is_object() || value.is_array(), "{args:?}: {value}");
    }

    let readable: &[&[&str]] = &[
        &["search", "needle"],
        &["timeline"],
        &["rebuild"],
        &["remember", "note"],
        &["collectors", "status"],
        &["collectors", "enable", "shell"],
        &["retention", "shell", "30"],
        &["purge"],
        &["graph", "."],
        &["git", "register", "."],
        &["git", "unregister", "."],
        &["git", "scan"],
    ];
    for args in readable {
        let output = Command::new(env!("CARGO_BIN_EXE_forja"))
            .arg("memory")
            .args(*args)
            .env("DBUS_SESSION_BUS_ADDRESS", address)
            .output()
            .expect("run readable memory command");
        assert!(
            output.status.success(),
            "{args:?}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(!output.stdout.is_empty(), "{args:?}: no readable output");
    }

    let mut collect = Command::new(env!("CARGO_BIN_EXE_forja"))
        .args([
            "memory",
            "collect",
            "shell",
            "--exit-code",
            "7",
            "--duration-ms",
            "42",
            "--json",
        ])
        .env("DBUS_SESSION_BUS_ADDRESS", address)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("run shell collector");
    collect
        .stdin
        .take()
        .expect("collector stdin")
        .write_all(b"echo hello\n")
        .expect("write shell event");
    let output = collect.wait_with_output().expect("collector output");
    assert!(output.status.success());
    let value: Value = serde_json::from_slice(&output.stdout).expect("collector JSON");
    assert_eq!(value["detail"], "echo hello\n");
    assert_eq!(value["exit_code"], 7);

    let malformed = Command::new(env!("CARGO_BIN_EXE_forja"))
        .args(["memory", "search", "invalid-response", "--json"])
        .env("DBUS_SESSION_BUS_ADDRESS", address)
        .output()
        .expect("run malformed response case");
    assert!(!malformed.status.success());
    let value: Value = serde_json::from_slice(&malformed.stdout).expect("malformed response JSON");
    assert_eq!(value["status"], "invalid_memd_response");
}

#[test]
fn git_hook_installer_preserves_existing_hook_in_temporary_repository() {
    if Command::new("git").arg("--version").output().is_err() {
        return;
    }
    let repo = std::env::temp_dir().join(format!("forja-hook-{}", std::process::id()));
    std::fs::create_dir_all(&repo).expect("create temporary repo");
    let init = Command::new("git")
        .args(["init", "--quiet"])
        .current_dir(&repo)
        .status()
        .expect("git init");
    assert!(init.success());
    let install = || {
        Command::new(env!("CARGO_BIN_EXE_forja"))
            .args(["memory", "hook", "install", "--json"])
            .current_dir(&repo)
            .output()
            .expect("run hook installer")
    };
    let first = install();
    assert!(first.status.success());
    let value: Value = serde_json::from_slice(&first.stdout).expect("hook JSON");
    assert_eq!(value["status"], "installed");
    let hook = repo.join(".git/hooks/post-commit");
    assert!(std::fs::read_to_string(&hook)
        .expect("installed hook")
        .contains("forja memory collect git"));
    let second = install();
    let value: Value = serde_json::from_slice(&second.stdout).expect("existing hook JSON");
    assert_eq!(value["status"], "existing_hook_preserved");
    std::fs::remove_dir_all(repo).expect("remove temporary repo");
}
