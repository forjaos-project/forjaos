use serde_json::Value;
use std::path::Path;
use std::process::{Command, Output};
use std::time::{SystemTime, UNIX_EPOCH};

fn forja(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_forja"))
        .args(args)
        .env(
            "HOME",
            std::env::temp_dir().join(format!("forja-cli-contract-{}", std::process::id())),
        )
        .output()
        .expect("execute forja")
}

fn forja_in_home(args: &[&str], home: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_forja"))
        .args(args)
        .env("HOME", home)
        .output()
        .expect("execute forja")
}

fn stdout(output: &Output) -> String {
    String::from_utf8(output.stdout.clone()).expect("UTF-8 stdout")
}

#[test]
fn every_cli_leaf_has_help_in_both_languages() {
    let leaves: &[&[&str]] = &[
        &["ai"],
        &["memory", "search"],
        &["memory", "timeline"],
        &["memory", "rebuild"],
        &["memory", "remember"],
        &["memory", "viewer"],
        &["memory", "mcp"],
        &["memory", "collectors", "status"],
        &["memory", "collectors", "enable"],
        &["memory", "collectors", "disable"],
        &["memory", "retention"],
        &["memory", "purge"],
        &["memory", "collect"],
        &["memory", "hook", "install"],
        &["memory", "git", "register"],
        &["memory", "git", "unregister"],
        &["memory", "git", "scan"],
        &["memory", "graph"],
        &["mascot", "status"],
        &["mascot", "name"],
        &["mascot", "voice"],
        &["mascot", "voices", "list"],
        &["mascot", "voices", "download"],
        &["mascot", "train"],
        &["keys", "set"],
        &["keys", "ssh-add"],
        &["keys", "env"],
        &["setup"],
        &["doctor"],
        &["install", "unity"],
        &["install", "escudo"],
        &["install", "claude-code"],
        &["install", "homebrew"],
        &["install", "devcontainers"],
        &["install", "vscode-devcontainers"],
        &["box", "create"],
        &["docker", "install"],
        &["docker", "setup-rootless"],
        &["game-mode", "on"],
        &["game-mode", "off"],
        &["game-mode", "status"],
        &["up"],
        &["down"],
        &["logs"],
        &["completions"],
        &["report"],
        &["update"],
        &["rollback"],
    ];
    for leaf in leaves {
        for (language, usage) in [("pt-br", "Uso:"), ("en", "Usage:")] {
            let mut args = vec!["--lang", language];
            args.extend_from_slice(leaf);
            args.push("--help");
            let output = forja(&args);
            assert!(output.status.success(), "{args:?}: {}", stdout(&output));
            assert!(
                stdout(&output).contains(usage),
                "{args:?}: {}",
                stdout(&output)
            );
        }
    }
}

#[test]
fn safe_json_paths_emit_one_object_with_status() {
    for args in [
        &["mascot", "status", "--json"][..],
        &["mascot", "train", "?", "--json"],
        &["mascot", "voices", "list", "--json"],
        &["memory", "collectors", "status", "--json"],
        &["memory", "search", "abc", "--json"],
        &["memory", "timeline", "--json"],
        &["keys", "env", "--json"],
        &["ai", "", "--json"],
        &["install", "unity", "--json"],
        &["install", "claude-code", "--json"],
        &["install", "homebrew", "--json"],
        &["install", "devcontainers", "--json"],
        &["install", "vscode-devcontainers", "--json"],
        &["docker", "install", "--json"],
        &["update", "--json"],
        &["rollback", "--json"],
        &["install", "escudo", "--json"],
    ] {
        let output = forja(args);
        let raw = stdout(&output);
        let value: Value = serde_json::from_str(raw.trim()).expect("one JSON object");
        assert!(value.is_object(), "{args:?}: {raw}");
        assert!(value["status"].is_string(), "{args:?}: {raw}");
        if args[0] == "mascot" && args[1] == "status" {
            assert_eq!(value["status"], "ok");
            assert_eq!(value["name"], "Guará");
        }
        if args[0] == "update" || args[0] == "rollback" {
            assert_eq!(value["status"], "confirmation_required");
            assert!(!output.status.success());
        }
        if args[0] == "install" && args[1] != "escudo" || args[0] == "docker" {
            assert_eq!(value["status"], "confirmation_required");
            assert!(!output.status.success());
        }
        if args[0] == "install" && args[1] == "escudo" {
            assert_eq!(value["status"], "unavailable");
            assert!(!output.status.success());
        }
    }
}

#[test]
fn completion_scripts_exist_for_three_shells() {
    for shell in ["bash", "zsh", "fish"] {
        let output = forja(&["completions", shell]);
        assert!(output.status.success(), "{shell}");
        let script = stdout(&output);
        assert!(script.len() > 1000, "{shell}: empty completion script");
        assert!(script.contains("forja"), "{shell}: wrong command name");

        let json_output = forja(&["completions", shell, "--json"]);
        assert!(
            json_output.status.success(),
            "{shell}: JSON completion failed"
        );
        let value: Value = serde_json::from_slice(&json_output.stdout).expect("JSON completion");
        assert_eq!(value["status"], "ok");
        assert_eq!(value["shell"], shell);
        assert_eq!(value["script"], script);
    }
}

#[test]
fn game_mode_status_is_json_even_without_backend() {
    let output = forja(&["game-mode", "status", "--json"]);
    let value: Value = serde_json::from_slice(&output.stdout).expect("game mode JSON");
    assert!(value.get("game_mode").is_some() || value["status"] == "error");
}

#[test]
fn mascot_name_persists_in_isolated_home_and_training_reports_missing_backend() {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let home = std::env::temp_dir().join(format!("forja-mascot-{nonce}"));
    std::fs::create_dir_all(&home).expect("create isolated home");

    let set = forja_in_home(&["mascot", "name", "Guará", "--json"], &home);
    assert!(set.status.success(), "{}", stdout(&set));
    let value: Value = serde_json::from_slice(&set.stdout).expect("name JSON");
    assert_eq!(value["name"], "Guará");

    let status = forja_in_home(&["mascot", "status", "--json"], &home);
    let value: Value = serde_json::from_slice(&status.stdout).expect("status JSON");
    assert_eq!(value["name"], "Guará");
    assert_eq!(value["wakeword"], "not_installed");

    let invalid = forja_in_home(&["mascot", "name", "?", "--json"], &home);
    assert!(!invalid.status.success());
    let value: Value = serde_json::from_slice(&invalid.stdout).expect("invalid name JSON");
    assert_eq!(value["status"], "error");

    let unavailable = forja_in_home(&["mascot", "voice", "missing", "--json"], &home);
    assert!(!unavailable.status.success());
    let value: Value = serde_json::from_slice(&unavailable.stdout).expect("voice JSON");
    assert_eq!(value["status"], "error");

    let voices = home.join(".local/share/hero/voices");
    std::fs::create_dir_all(&voices).expect("create voice fixture");
    std::fs::write(voices.join("fixture.onnx"), b"model").expect("voice fixture model");
    std::fs::write(voices.join("fixture.onnx.json"), b"{}").expect("voice fixture config");
    let selected = forja_in_home(&["mascot", "voice", "fixture", "--json"], &home);
    assert!(selected.status.success());
    assert_eq!(
        serde_json::from_slice::<Value>(&selected.stdout).expect("selected voice JSON")["voice"],
        "fixture"
    );
    let status = forja_in_home(&["mascot", "status", "--json"], &home);
    let value: Value = serde_json::from_slice(&status.stdout).expect("voice status JSON");
    assert_eq!(value["voice_status"], "installed");
    let readable = forja_in_home(&["mascot", "status"], &home);
    assert!(stdout(&readable).contains("fixture (installed)"));
    let catalog = forja_in_home(&["mascot", "voices", "list"], &home);
    assert!(stdout(&catalog).contains("pt_BR-cadu-medium"));
    let unknown = forja_in_home(
        &["mascot", "voices", "download", "unknown", "--json"],
        &home,
    );
    assert!(!unknown.status.success());
    assert_eq!(
        serde_json::from_slice::<Value>(&unknown.stdout).expect("unknown voice JSON")["status"],
        "error"
    );

    let train = forja_in_home(&["mascot", "train", "sol", "--json"], &home);
    assert!(!train.status.success());
    let value: Value = serde_json::from_slice(&train.stdout).expect("train JSON");
    assert!(value["error"]
        .as_str()
        .unwrap_or_default()
        .contains("falsos positivos"));
    let long_name = forja_in_home(&["mascot", "train", "Aurora", "--json"], &home);
    assert!(!long_name.status.success());
    let value: Value = serde_json::from_slice(&long_name.stdout).expect("missing trainer JSON");
    assert!(value["error"]
        .as_str()
        .unwrap_or_default()
        .contains("não está instalado"));

    std::fs::remove_dir_all(home).expect("remove isolated home");
}

#[test]
fn diagnostics_return_structured_checks_and_readable_report() {
    for command in ["doctor", "report"] {
        let output = forja(&[command, "--json"]);
        let checks: Value = serde_json::from_slice(&output.stdout).expect("diagnostic JSON");
        let checks = checks.as_array().expect("diagnostic array");
        assert!(!checks.is_empty(), "{command}: no checks");
        for check in checks {
            assert!(check["name"].is_string());
            assert!(check["status"].is_string());
            assert!(check["detail"].is_string());
            assert!(check["critical"].is_boolean());
        }
    }
    let report = forja(&["report"]);
    assert!(report.status.success());
    assert!(stdout(&report).contains("Relatório de diagnóstico ForjaOS"));
}
