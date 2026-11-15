use serde_json::json;
use std::process::Command;

const PROVIDERS: &[(&str, &str)] = &[
    ("anthropic", "ANTHROPIC_API_KEY"),
    ("openai", "OPENAI_API_KEY"),
    ("openrouter", "OPENROUTER_API_KEY"),
    ("nous", "NOUS_API_KEY"),
];

pub fn env(shell: &str, json_output: bool) -> i32 {
    if !matches!(shell, "bash" | "zsh" | "fish") {
        return failure(json_output, "shell_not_supported");
    }
    let mut configured = Vec::new();
    let mut exports = Vec::new();
    for (provider, variable) in PROVIDERS {
        match read_secret(provider) {
            Ok(Some(secret)) => {
                configured.push(*provider);
                let value = match shell {
                    "fish" => fish_quote(&secret),
                    _ => posix_quote(&secret),
                };
                exports.push(match shell {
                    "fish" => format!("set -gx {variable} {value};"),
                    _ => format!("export {variable}={value}"),
                });
            }
            Ok(None) => {}
            Err(_) => return failure(json_output, "secret_service_unavailable"),
        }
    }

    if json_output {
        println!(
            "{}",
            json!({
                "command":"keys env",
                "status":"ok",
                "shell":shell,
                "providers":configured
            })
        );
    } else if !exports.is_empty() {
        println!("{}", exports.join("\n"));
    }
    0
}

fn read_secret(provider: &str) -> Result<Option<String>, ()> {
    let result = Command::new("secret-tool")
        .args(["lookup", "application", "forjaos", "provider", provider])
        .output()
        .map_err(|_| ())?;
    if !result.status.success() {
        return if result.status.code() == Some(1) && result.stderr.is_empty() {
            Ok(None)
        } else {
            Err(())
        };
    }
    let mut secret = String::from_utf8(result.stdout).map_err(|_| ())?;
    if secret.ends_with('\n') {
        secret.pop();
    }
    if secret.is_empty() || secret.chars().any(|character| character.is_control()) {
        return Err(());
    }
    Ok(Some(secret))
}

fn posix_quote(value: &str) -> String {
    format!("'{}'", value.replace('\'', "'\\''"))
}

fn fish_quote(value: &str) -> String {
    let escaped = value.replace('\\', "\\\\").replace('\'', "\\'");
    format!("'{escaped}'")
}

fn failure(json_output: bool, code: &str) -> i32 {
    if json_output {
        println!(
            "{}",
            json!({"command":"keys env", "status":"error", "error":code})
        );
    } else {
        eprintln!("forja keys env: não foi possível consultar o KWallet/Secret Service.");
    }
    1
}
