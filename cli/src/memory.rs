use serde_json::Value;
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

fn unavailable(json: bool, error: &zbus::Error) -> i32 {
    if json {
        println!("{}", serde_json::json!({"status":"memd_unavailable"}));
    } else {
        eprintln!("forja memory: memd indisponível; verifique memd.service ({error}).");
    }
    1
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
