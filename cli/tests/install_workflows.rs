#![cfg(unix)]

use serde_json::Value;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::Path;
use std::process::{Command, Output};
use std::time::{SystemTime, UNIX_EPOCH};

fn run(home: &Path, args: &[&str]) -> Output {
    let path = std::env::join_paths([home.join("bin"), "/usr/bin".into(), "/bin".into()])
        .expect("isolated PATH");
    Command::new(env!("CARGO_BIN_EXE_forja"))
        .args(args)
        .env("HOME", home)
        .env("PATH", path)
        .output()
        .expect("run forja")
}

fn json(output: &Output) -> Value {
    serde_json::from_slice(&output.stdout).expect("one JSON result")
}

#[test]
fn user_installers_use_fake_downloads_inside_isolated_home() {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let home = std::env::temp_dir().join(format!("forja-install-{nonce}"));
    let bin = home.join("bin");
    fs::create_dir_all(&bin).expect("create fake bin");
    let curl = bin.join("curl");
    fs::write(
        &curl,
        "#!/bin/sh\nout=''\nprev=''\nfor arg in \"$@\"; do\n  if [ \"$prev\" = '--output' ]; then out=\"$arg\"; fi\n  prev=\"$arg\"\ndone\nif [ -n \"$out\" ]; then printf '\\177ELF' > \"$out\"; else printf 'exit 0\\n'; fi\n",
    )
    .expect("write fake curl");
    fs::set_permissions(&curl, fs::Permissions::from_mode(0o755))
        .expect("make fake curl executable");

    let unity = run(&home, &["install", "unity", "--yes", "--json"]);
    assert!(
        unity.status.success(),
        "{}",
        String::from_utf8_lossy(&unity.stdout)
    );
    assert_eq!(json(&unity)["status"], "installed");
    assert!(home
        .join(".local/opt/forja/unityhub/UnityHub.AppImage")
        .is_file());
    assert!(home
        .join(".local/share/applications/unityhub.desktop")
        .is_file());

    let claude = run(&home, &["install", "claude-code", "--yes", "--json"]);
    assert!(
        claude.status.success(),
        "{}",
        String::from_utf8_lossy(&claude.stdout)
    );
    assert_eq!(json(&claude)["status"], "installed");

    fs::write(&curl, "#!/bin/sh\nexit 9\n").expect("write failing fake curl");
    let failed = run(&home, &["install", "unity", "--yes", "--json"]);
    assert!(!failed.status.success());
    assert_eq!(json(&failed)["status"], "error");

    fs::remove_dir_all(home).expect("remove isolated fixture");
}
