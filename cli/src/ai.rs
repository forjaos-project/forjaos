use serde_json::Value;
use zbus::{Connection, Proxy};

const BUS_NAME: &str = "org.forjaos.Hero";
const OBJECT_PATH: &str = "/org/forjaos/Hero";
const INTERFACE: &str = "org.forjaos.Hero";

fn terminal_safe(text: &str) -> String {
    text.chars()
        .filter(|character| !character.is_control() || matches!(character, '\n' | '\t'))
        .collect()
}

async fn request(query: &str) -> Result<String, zbus::Error> {
    let connection = Connection::session().await?;
    let proxy = Proxy::new(&connection, BUS_NAME, OBJECT_PATH, INTERFACE).await?;
    proxy.call("AskText", &query).await
}

fn result_code(status: &str) -> i32 {
    match status {
        "ok" => 0,
        "invalid_query" | "route_unavailable" => 2,
        _ => 1,
    }
}

pub fn run(query: &str, json: bool) -> i32 {
    let response = zbus::block_on(request(query));
    let Ok(response) = response else {
        if json {
            println!("{}", serde_json::json!({"status":"hero_unavailable"}));
        } else {
            eprintln!("forja ai: HERO indisponível; verifique herod.service na sessão do usuário.");
        }
        return 1;
    };
    let Ok(reply) = serde_json::from_str::<Value>(&response) else {
        if json {
            println!("{}", serde_json::json!({"status":"invalid_hero_response"}));
        } else {
            eprintln!("forja ai: resposta do HERO inválida.");
        }
        return 1;
    };

    let status = reply["status"].as_str().unwrap_or("invalid_hero_response");
    if json {
        println!("{}", reply);
    } else {
        println!(
            "Rota: {}",
            reply["route"].as_str().unwrap_or("desconhecida")
        );
        println!(
            "Contexto: {}",
            reply["context"].as_str().unwrap_or("nenhum")
        );
        println!(
            "{}",
            terminal_safe(reply["answer"].as_str().unwrap_or("Sem resposta do HERO."))
        );
    }
    result_code(status)
}
