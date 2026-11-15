#![cfg(unix)]

use serde_json::Value;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::time::{SystemTime, UNIX_EPOCH};

fn fake_command(bin: &Path, name: &str, exit_code: i32) {
    let path = bin.join(name);
    fs::write(&path, format!("#!/bin/sh\nexit {exit_code}\n")).expect("write fake command");
    fs::set_permissions(path, fs::Permissions::from_mode(0o755)).expect("make fake executable");
}

fn run(home: &Path, bin: &Path, args: &[&str]) -> Output {
    let path = std::env::join_paths([bin, Path::new("/usr/bin"), Path::new("/bin")])
        .expect("isolated PATH");
    Command::new(env!("CARGO_BIN_EXE_forja"))
        .args(args)
        .current_dir(home)
        .env("HOME", home)
        .env("PATH", path)
        .output()
        .expect("run forja")
}

fn json(output: &Output) -> Value {
    serde_json::from_slice(&output.stdout).expect("one JSON result")
}

#[test]
fn development_commands_delegate_to_isolated_fake_backends() {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let home: PathBuf = std::env::temp_dir().join(format!("forja-dev-{nonce}"));
    let bin = home.join("bin");
    fs::create_dir_all(&bin).expect("create fake bin");
    for name in [
        "distrobox",
        "podman",
        "rpm-ostree",
        "sudo",
        "dockerd-rootless-setuptool.sh",
        "systemctl",
        "ssh-add",
    ] {
        fake_command(&bin, name, 0);
    }

    let box_result = run(&home, &bin, &["box", "create", "ubuntu", "--json"]);
    assert!(box_result.status.success());
    assert_eq!(json(&box_result)["status"], "created");
    let invalid = run(
        &home,
        &bin,
        &["box", "create", "fedora", "--name", "bad name", "--json"],
    );
    assert!(!invalid.status.success());
    assert_eq!(json(&invalid)["status"], "error");

    let docker = run(&home, &bin, &["docker", "install", "--yes", "--json"]);
    assert!(docker.status.success());
    assert_eq!(json(&docker)["status"], "reboot_required");
    let rootless = run(&home, &bin, &["docker", "setup-rootless", "--json"]);
    assert!(rootless.status.success());
    assert_eq!(json(&rootless)["status"], "rootless_ready");
    let keys = run(&home, &bin, &["keys", "ssh-add", "--json"]);
    assert!(keys.status.success());
    assert_eq!(json(&keys)["ssh_agent"], "ready");

    let missing_compose = run(&home, &bin, &["up", "--json"]);
    assert_eq!(json(&missing_compose)["status"], "compose_file_not_found");
    fs::write(home.join("compose.yaml"), "services: {}\n").expect("compose fixture");
    for action in ["up", "down", "logs"] {
        let result = run(&home, &bin, &[action, "--json"]);
        assert!(
            result.status.success(),
            "{action}: {}",
            String::from_utf8_lossy(&result.stdout)
        );
        assert_eq!(json(&result)["status"], "ok");
    }

    for action in ["update", "rollback"] {
        let result = run(&home, &bin, &[action, "--yes", "--json"]);
        assert!(
            result.status.success(),
            "{action}: {}",
            String::from_utf8_lossy(&result.stdout)
        );
        assert_eq!(json(&result)["status"], "ok");
    }

    fake_command(&bin, "sudo", 9);
    let failure = run(&home, &bin, &["docker", "install", "--yes", "--json"]);
    assert_eq!(json(&failure)["stage"], "repository");
    assert_eq!(failure.status.code(), Some(9));

    fake_command(&bin, "podman", 9);
    let compose_failure = run(&home, &bin, &["up", "--json"]);
    assert_eq!(json(&compose_failure)["status"], "error");
    assert_eq!(compose_failure.status.code(), Some(9));

    fake_command(&bin, "distrobox", 9);
    let box_failure = run(&home, &bin, &["box", "create", "arch", "--json"]);
    assert_eq!(json(&box_failure)["status"], "error");
    assert_eq!(box_failure.status.code(), Some(9));

    fake_command(&bin, "systemctl", 9);
    let rootless_failure = run(&home, &bin, &["docker", "setup-rootless", "--json"]);
    assert_eq!(json(&rootless_failure)["stage"], "user_service");
    assert_eq!(rootless_failure.status.code(), Some(9));

    fs::remove_dir_all(home).expect("remove isolated fixture");
}
