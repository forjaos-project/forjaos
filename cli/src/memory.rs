use serde_json::Value;
use std::io::{self, Read};
use std::process::{Command, Stdio};
use zbus::{Connection, Proxy};

const BUS_NAME: &str = "org.forjaos.Memory";
const OBJECT_PATH: &str = "/org/forjaos/Memory";
const INTERFACE: &str = "org.forjaos.Memory";

async fn proxy(connection: &Connection) -> Result<Proxy<'_>, zbus::Error> {
    Proxy::new(connection, BUS_NAME, OBJECT_PATH, INTERFACE).await
}

async fn call_search(query: &str, limit: u32) -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy.call("Search", &(query, limit)).await
}

async fn call_timeline(days: u32, limit: u32) -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy.call("Timeline", &(days, limit)).await
}

async fn call_rebuild() -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy.call("Rebuild", &()).await
}

async fn call_remember(note: &str) -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy.call("Remember", &note).await
}

async fn call_collectors() -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy.call("Collectors", &()).await
}

async fn call_set_collector(source: &str, enabled: bool) -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy.call("SetCollector", &(source, enabled)).await
}

async fn call_set_retention(source: &str, days: u32) -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy.call("SetRetention", &(source, days)).await
}

async fn call_purge() -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy.call("Purge", &()).await
}

async fn call_collect_event(
    source: &str,
    detail: &str,
    cwd: &str,
    exit_code: i32,
    duration_ms: u64,
) -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy
        .call(
            "CollectEvent",
            &(source, detail, cwd, exit_code, duration_ms),
        )
        .await
}

async fn call_register_git_repository(path: &str) -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy.call("RegisterGitRepository", &path).await
}

async fn call_unregister_git_repository(path: &str) -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy.call("UnregisterGitRepository", &path).await
}

async fn call_scan_git_repositories() -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = proxy(&connection).await?;
    proxy.call("ScanGitRepositories", &()).await
}

fn unavailable(json: bool, error: &zbus::Error) -> i32 {
    if json {
        println!("{}", serde_json::json!({"status":"memd_unavailable"}));
    } else {
        eprintln!("forja memory: memd indisponível; verifique memd.service ({error}).");
    }
    1
}

fn configure_window_collector(enabled: bool) -> Result<bool, String> {
    let output = Command::new("kwriteconfig6")
        .args([
            "--file",
            "kwinrc",
            "--group",
            "Plugins",
            "--key",
            "forja-memory-windowEnabled",
            if enabled { "true" } else { "false" },
        ])
        .output()
        .map_err(|error| format!("kwriteconfig6: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "kwriteconfig6: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    for program in ["qdbus6", "qdbus"] {
        match Command::new(program)
            .args(["org.kde.KWin", "/KWin", "reconfigure"])
            .status()
        {
            Ok(status) if status.success() => return Ok(true),
            Ok(_) => continue,
            Err(_) => continue,
        }
    }
    Ok(false)
}

fn parse_reply(raw: String, json: bool) -> Result<Value, i32> {
    serde_json::from_str(&raw).map_err(|_| {
        if json {
            println!("{}", serde_json::json!({"status":"invalid_memd_response"}));
        } else {
            eprintln!("forja memory: resposta inválida de memd.");
        }
        1
    })
}

fn terminal_safe(text: &str) -> String {
    text.chars()
        .filter(|character| !character.is_control() || matches!(character, '\n' | '\t'))
        .collect()
}

pub fn search(query: &str, limit: u32, json: bool) -> i32 {
    match zbus::block_on(call_search(query, limit)) {
        Ok(raw) => match parse_reply(raw, json) {
            Ok(value) => {
                if json {
                    println!("{value}");
                } else if let Some(hits) = value.as_array() {
                    for hit in hits {
                        println!(
                            "{}\n  {}\n  {}",
                            terminal_safe(hit["title"].as_str().unwrap_or("Nota")),
                            terminal_safe(hit["path"].as_str().unwrap_or("")),
                            terminal_safe(hit["excerpt"].as_str().unwrap_or(""))
                        );
                    }
                    if hits.is_empty() {
                        println!("Nenhum resultado.");
                    }
                }
                0
            }
            Err(code) => code,
        },
        Err(error) => unavailable(json, &error),
    }
}

pub fn timeline(days: u32, limit: u32, json: bool) -> i32 {
    match zbus::block_on(call_timeline(days, limit)) {
        Ok(raw) => match parse_reply(raw, json) {
            Ok(value) => {
                if json {
                    println!("{value}");
                } else if let Some(entries) = value.as_array() {
                    for entry in entries {
                        println!(
                            "{} · {}\n  {}",
                            entry["modified_at"].as_i64().unwrap_or_default(),
                            terminal_safe(entry["title"].as_str().unwrap_or("Nota")),
                            terminal_safe(entry["path"].as_str().unwrap_or(""))
                        );
                    }
                    if entries.is_empty() {
                        println!("Nenhuma atividade no período.");
                    }
                }
                0
            }
            Err(code) => code,
        },
        Err(error) => unavailable(json, &error),
    }
}

pub fn rebuild(json: bool) -> i32 {
    match zbus::block_on(call_rebuild()) {
        Ok(raw) => match parse_reply(raw, json) {
            Ok(value) => {
                if json {
                    println!("{value}");
                } else {
                    let search = if value["semantic_search"].as_bool().unwrap_or(false) {
                        "FTS5 e busca semântica local"
                    } else {
                        "FTS5; modelo nomic-embed-text ausente"
                    };
                    println!(
                        "Índice reconstruído: {} notas ({search}).",
                        value["indexed"].as_u64().unwrap_or_default(),
                    );
                }
                0
            }
            Err(code) => code,
        },
        Err(error) => unavailable(json, &error),
    }
}

pub fn remember(note: &str, json: bool) -> i32 {
    match zbus::block_on(call_remember(note)) {
        Ok(raw) => match parse_reply(raw, json) {
            Ok(value) => {
                if json {
                    println!("{value}");
                } else {
                    println!(
                        "Nota salva em {}.",
                        terminal_safe(value["path"].as_str().unwrap_or(""))
                    );
                }
                0
            }
            Err(code) => code,
        },
        Err(error) => unavailable(json, &error),
    }
}

pub fn collectors_status(json: bool) -> i32 {
    match zbus::block_on(call_collectors()) {
        Ok(raw) => match parse_reply(raw, json) {
            Ok(value) => {
                if json {
                    println!("{value}");
                } else if let Some(collectors) = value.as_array() {
                    for collector in collectors {
                        println!(
                            "{} · {} · {} dias · {}",
                            collector["source"].as_str().unwrap_or("?"),
                            if collector["enabled"].as_bool().unwrap_or(false) {
                                "ativo"
                            } else {
                                "inativo"
                            },
                            collector["retention_days"].as_u64().unwrap_or(0),
                            if collector["available"].as_bool().unwrap_or(false) {
                                "disponível"
                            } else {
                                "indisponível"
                            }
                        );
                    }
                }
                0
            }
            Err(code) => code,
        },
        Err(error) => unavailable(json, &error),
    }
}

pub fn set_collector(source: &str, enabled: bool, json: bool) -> i32 {
    match zbus::block_on(call_set_collector(source, enabled)) {
        Ok(raw) => match parse_reply(raw, json) {
            Ok(mut value) => {
                if source == "windows" {
                    match configure_window_collector(enabled) {
                        Ok(reloaded) => {
                            value["active_session_reloaded"] = serde_json::json!(reloaded)
                        }
                        Err(error) => {
                            let _ = zbus::block_on(call_set_collector(source, !enabled));
                            if json {
                                println!(
                                    "{}",
                                    serde_json::json!({"status":"kwin_configuration_failed"})
                                );
                            } else {
                                eprintln!("forja memory windows: {error}");
                            }
                            return 1;
                        }
                    }
                }
                if json {
                    println!("{value}");
                } else {
                    if source == "windows"
                        && !value["active_session_reloaded"].as_bool().unwrap_or(false)
                    {
                        println!(
                            "Coletor {source}: {} para a próxima sessão do KWin.",
                            if enabled { "ativado" } else { "desativado" }
                        );
                    } else {
                        println!(
                            "Coletor {source}: {}.",
                            if enabled { "ativado" } else { "desativado" }
                        );
                    }
                }
                0
            }
            Err(code) => code,
        },
        Err(error) => unavailable(json, &error),
    }
}

pub fn set_retention(source: &str, days: u32, json: bool) -> i32 {
    match zbus::block_on(call_set_retention(source, days)) {
        Ok(raw) => match parse_reply(raw, json) {
            Ok(value) => {
                if json {
                    println!("{value}");
                } else {
                    println!(
                        "Retenção de {source}: {}.",
                        if days == 0 {
                            "indefinida".into()
                        } else {
                            format!("{days} dias")
                        }
                    );
                }
                0
            }
            Err(code) => code,
        },
        Err(error) => unavailable(json, &error),
    }
}

pub fn purge(json: bool) -> i32 {
    match zbus::block_on(call_purge()) {
        Ok(raw) => match parse_reply(raw, json) {
            Ok(value) => {
                if json {
                    println!("{value}");
                } else {
                    println!(
                        "Eventos removidos pela retenção: {}.",
                        value["removed"].as_u64().unwrap_or(0)
                    );
                }
                0
            }
            Err(code) => code,
        },
        Err(error) => unavailable(json, &error),
    }
}

pub fn collect(source: &str, exit_code: i32, duration_ms: u64) -> i32 {
    let detail = if source == "shell" {
        let mut detail = String::new();
        if io::stdin()
            .take((64 * 1024 + 1) as u64)
            .read_to_string(&mut detail)
            .is_err()
            || detail.len() > 64 * 1024
        {
            eprintln!("forja memory collect: entrada acima de 64 KiB ou leitura inválida.");
            return 2;
        }
        detail
    } else {
        let output = match Command::new("git")
            .args(["log", "-1", "--format=%H%x09%s"])
            .output()
        {
            Ok(output) if output.status.success() => output,
            Ok(_) => {
                eprintln!("forja memory collect: não foi possível ler o último commit Git.");
                return 2;
            }
            Err(error) => {
                eprintln!("forja memory collect: {error}");
                return 2;
            }
        };
        String::from_utf8_lossy(&output.stdout).trim().to_string()
    };
    let cwd = std::env::current_dir()
        .map(|path| path.to_string_lossy().to_string())
        .unwrap_or_default();
    match zbus::block_on(call_collect_event(
        source,
        &detail,
        &cwd,
        exit_code,
        duration_ms,
    )) {
        Ok(_) => 0,
        Err(error) => {
            eprintln!("forja memory collect: {error}");
            1
        }
    }
}

pub fn install_git_hook(json: bool) -> i32 {
    let root = match Command::new("git")
        .args(["rev-parse", "--show-toplevel"])
        .output()
    {
        Ok(output) if output.status.success() => {
            std::path::PathBuf::from(String::from_utf8_lossy(&output.stdout).trim())
        }
        _ => {
            if json {
                println!(
                    "{}",
                    serde_json::json!({"command":"memory hook install", "status":"not_a_repository"})
                );
            } else {
                eprintln!("forja memory hook: execute dentro de um repositório Git.");
            }
            return 2;
        }
    };
    if Command::new("git")
        .current_dir(&root)
        .args(["config", "--get", "core.hooksPath"])
        .output()
        .is_ok_and(|output| output.status.success())
    {
        if json {
            println!(
                "{}",
                serde_json::json!({"command":"memory hook install", "status":"custom_hooks_path_preserved"})
            );
        } else {
            eprintln!("forja memory hook: core.hooksPath já está configurado; nenhuma alteração foi feita.");
        }
        return 2;
    }
    let hook_path = match Command::new("git")
        .current_dir(&root)
        .args(["rev-parse", "--git-path", "hooks/post-commit"])
        .output()
    {
        Ok(output) if output.status.success() => {
            let path = std::path::PathBuf::from(String::from_utf8_lossy(&output.stdout).trim());
            if path.is_absolute() {
                path
            } else {
                root.join(path)
            }
        }
        Ok(_) => {
            eprintln!("forja memory hook: Git não informou o caminho do hook.");
            return 1;
        }
        Err(error) => {
            eprintln!("forja memory hook: {error}");
            return 1;
        }
    };
    let Some(parent) = hook_path.parent() else {
        eprintln!("forja memory hook: caminho de hook inválido.");
        return 1;
    };
    if let Err(error) = std::fs::create_dir_all(parent) {
        eprintln!("forja memory hook: {error}");
        return 1;
    }
    let mut file = match std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&hook_path)
    {
        Ok(file) => file,
        Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {
            if json {
                println!(
                    "{}",
                    serde_json::json!({"command":"memory hook install", "status":"existing_hook_preserved"})
                );
            } else {
                eprintln!(
                    "forja memory hook: hook existente preservado em {}.",
                    hook_path.display()
                );
            }
            return 2;
        }
        Err(error) => {
            eprintln!("forja memory hook: {error}");
            return 1;
        }
    };
    use std::io::Write;
    if let Err(error) = file
        .write_all(b"#!/bin/sh\n/usr/bin/forja memory collect git >/dev/null 2>&1 || true\n")
        .and_then(|()| file.sync_all())
    {
        let _ = std::fs::remove_file(&hook_path);
        eprintln!("forja memory hook: {error}");
        return 1;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if let Err(error) =
            std::fs::set_permissions(&hook_path, std::fs::Permissions::from_mode(0o755))
        {
            let _ = std::fs::remove_file(&hook_path);
            eprintln!("forja memory hook: {error}");
            return 1;
        }
    }
    if json {
        println!(
            "{}",
            serde_json::json!({"command":"memory hook install", "status":"installed"})
        );
    } else {
        println!("Hook post-commit instalado em {}.", hook_path.display());
    }
    0
}

pub fn register_git_repository(path: &str, json: bool) -> i32 {
    let path = match std::fs::canonicalize(path) {
        Ok(path) => path.to_string_lossy().to_string(),
        Err(error) => {
            if json {
                println!(
                    "{}",
                    serde_json::json!({"status":"invalid_repository_path"})
                );
            } else {
                eprintln!("forja memory git register: {error}");
            }
            return 2;
        }
    };
    match zbus::block_on(call_register_git_repository(&path)) {
        Ok(raw) => match parse_reply(raw, json) {
            Ok(value) => {
                if json {
                    println!("{value}");
                } else {
                    println!(
                        "Repositório {} para varredura diária.",
                        if value["registered"].as_bool().unwrap_or(false) {
                            "registrado"
                        } else {
                            "já estava registrado"
                        }
                    );
                }
                0
            }
            Err(code) => code,
        },
        Err(error) => unavailable(json, &error),
    }
}

pub fn unregister_git_repository(path: &str, json: bool) -> i32 {
    let path = match std::fs::canonicalize(path) {
        Ok(path) => path.to_string_lossy().to_string(),
        Err(_) if std::path::Path::new(path).is_absolute() => path.to_string(),
        Err(error) => {
            if json {
                println!(
                    "{}",
                    serde_json::json!({"status":"invalid_repository_path"})
                );
            } else {
                eprintln!("forja memory git unregister: {error}");
            }
            return 2;
        }
    };
    match zbus::block_on(call_unregister_git_repository(&path)) {
        Ok(raw) => match parse_reply(raw, json) {
            Ok(value) => {
                if json {
                    println!("{value}");
                } else if value["unregistered"].as_bool().unwrap_or(false) {
                    println!("Repositório removido da varredura diária.");
                } else {
                    println!("Repositório não estava registrado.");
                }
                0
            }
            Err(code) => code,
        },
        Err(error) => unavailable(json, &error),
    }
}

pub fn scan_git_repositories(json: bool) -> i32 {
    match zbus::block_on(call_scan_git_repositories()) {
        Ok(raw) => match parse_reply(raw, json) {
            Ok(value) => {
                let failed = value["status"] == "partial";
                if json {
                    println!("{value}");
                } else {
                    println!(
                        "Varredura Git: {} commits em {} repositórios; {} falhas.",
                        value["commits_recorded"].as_u64().unwrap_or(0),
                        value["repositories"].as_u64().unwrap_or(0),
                        value["errors"].as_array().map_or(0, Vec::len)
                    );
                }
                if failed {
                    1
                } else {
                    0
                }
            }
            Err(code) => code,
        },
        Err(error) => unavailable(json, &error),
    }
}

pub fn viewer(json: bool) -> i32 {
    let result = Command::new("/usr/bin/python3")
        .args(["/usr/share/forjaos/memory-viewer/viewer.py"])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn();
    match result {
        Ok(_) => {
            if json {
                println!(
                    "{}",
                    serde_json::json!({"command":"memory viewer", "status":"started"})
                );
            } else {
                println!("Visualizador da Memória aberto.");
            }
            0
        }
        Err(error) => {
            if json {
                println!(
                    "{}",
                    serde_json::json!({"command":"memory viewer", "status":"error"})
                );
            } else {
                eprintln!("forja memory viewer: {error}");
            }
            1
        }
    }
}

pub fn mcp() -> i32 {
    match Command::new("/usr/libexec/forjaos/memd")
        .arg("--mcp")
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()
    {
        Ok(status) => status.code().unwrap_or(1),
        Err(error) => {
            eprintln!("forja memory mcp: {error}");
            1
        }
    }
}
