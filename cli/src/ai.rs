use serde_json::Value;
use std::io::{self, IsTerminal, Write};
use zbus::{Connection, Proxy};

const BUS_NAME: &str = "org.forjaos.Hero";
const OBJECT_PATH: &str = "/org/forjaos/Hero";
const INTERFACE: &str = "org.forjaos.Hero";

fn terminal_safe(text: &str) -> String {
    text.chars()
        .filter(|character| !character.is_control() || matches!(character, '\n' | '\t'))
        .collect()
}

async fn request(query: &str, cwd: &str, snapshot: &str) -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = Proxy::new(&connection, BUS_NAME, OBJECT_PATH, INTERFACE).await?;
    proxy.call("AskText", &(query, cwd, snapshot)).await
}

async fn confirm(id: &str, approved: bool) -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = Proxy::new(&connection, BUS_NAME, OBJECT_PATH, INTERFACE).await?;
    proxy.call("ConfirmAction", &(id, approved)).await
}

fn print_reply(reply: &Value, json: bool) {
    if json {
        println!("{reply}");
    } else {
        println!(
            "Rota: {}",
            reply["route"].as_str().unwrap_or("desconhecida")
        );
        if let Some(context) = reply["context"].as_str() {
            println!("Contexto: {}", terminal_safe(context));
        }
        if let Some(tier) = reply["tier"].as_str() {
            println!("Tier: {tier}");
        }
        println!(
            "{}",
            terminal_safe(reply["answer"].as_str().unwrap_or("Sem resposta do HERO."))
        );
    }
}

fn status_code(reply: &Value) -> i32 {
    match reply["status"].as_str().unwrap_or("") {
        "ok" => 0,
        "confirmation_required" => 3,
        "invalid_query" | "blocked" | "cancelled" => 2,
        _ => 1,
    }
}

fn unavailable(json: bool) -> i32 {
    if json {
        println!("{}", serde_json::json!({"status":"hero_unavailable"}));
    } else {
        eprintln!("forja ai: HERO indisponível; verifique herod.service na sessão do usuário.");
    }
    1
}

fn parse_reply(raw: &str, json: bool) -> Result<Value, i32> {
    serde_json::from_str(raw).map_err(|_| {
        if json {
            println!("{}", serde_json::json!({"status":"invalid_hero_response"}));
        } else {
            eprintln!("forja ai: resposta inválida do HERO.");
        }
        1
    })
}

pub fn run(query: Option<&str>, confirmation: Option<&str>, json: bool) -> i32 {
    if let Some(id) = confirmation {
        return match zbus::block_on(confirm(id, true)) {
            Ok(raw) => match parse_reply(&raw, json) {
                Ok(reply) => {
                    print_reply(&reply, json);
                    status_code(&reply)
                }
                Err(code) => code,
            },
            Err(_) => unavailable(json),
        };
    }

    let Some(query) = query else { return 2 };
    let cwd = std::env::current_dir()
        .map(|path| path.to_string_lossy().to_string())
        .unwrap_or_default();
    let raw = match zbus::block_on(request(query, &cwd, "{}")) {
        Ok(raw) => raw,
        Err(_) => return unavailable(json),
    };
    let mut reply = match parse_reply(&raw, json) {
        Ok(reply) => reply,
        Err(code) => return code,
    };

    if reply["status"] == "confirmation_required" {
        let id = reply["confirmation_id"].as_str().unwrap_or("").to_string();
        if id.is_empty() {
            print_reply(&reply, json);
            return 1;
        }
        if json {
            print_reply(&reply, true);
            return 3;
        }
        if !io::stdin().is_terminal() {
            println!("Ação pendente. Confirme com: forja ai --confirm {id}");
            print_reply(&reply, false);
            return 3;
        }
        println!(
            "Rota: {}",
            reply["route"].as_str().unwrap_or("desconhecida")
        );
        println!(
            "Contexto: {}",
            terminal_safe(reply["context"].as_str().unwrap_or("nenhum"))
        );
        println!("{}", terminal_safe(reply["answer"].as_str().unwrap_or("")));
        print!("Executar? [s/N] ");
        let _ = io::stdout().flush();
        let mut answer = String::new();
        if io::stdin().read_line(&mut answer).is_err() {
            return 1;
        }
        let approved = matches!(answer.trim().to_lowercase().as_str(), "s" | "sim");
        let raw = match zbus::block_on(confirm(&id, approved)) {
            Ok(raw) => raw,
            Err(_) => return unavailable(false),
        };
        reply = match parse_reply(&raw, false) {
            Ok(reply) => reply,
            Err(code) => return code,
        };
    }

    print_reply(&reply, false);
    status_code(&reply)
}
