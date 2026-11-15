use serde_json::Value;
use std::process::{Command, Output};

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
        &["update", "--json"],
        &["rollback", "--json"],
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
