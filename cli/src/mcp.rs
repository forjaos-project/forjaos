use serde_json::json;
use std::path::Path;
use std::process::{Command, Output};

struct Server {
    name: &'static str,
    executable: &'static str,
    args: &'static [&'static str],
}

const SERVERS: &[Server] = &[
    Server {
        name: "hero-system",
        executable: "/usr/libexec/forjaos/hero-system",
        args: &["--mcp"],
    },
    Server {
        name: "hero-desktop",
        executable: "/usr/libexec/forjaos/hero-desktop",
        args: &["--mcp"],
    },
    Server {
        name: "hero-dev",
        executable: "/usr/libexec/forjaos/hero-dev",
        args: &["--mcp"],
    },
    Server {
        name: "hero-memory",
        executable: "/usr/libexec/forjaos/memd",
        args: &["--mcp"],
    },
];

struct Client<'a> {
    name: &'static str,
    executable: &'a str,
}

const CLIENTS: &[Client] = &[
    Client {
        name: "claude-code",
        executable: "claude",
    },
    Client {
        name: "codex",
        executable: "codex",
    },
    Client {
        name: "hermes",
        executable: "hermes",
    },
];

fn command_exists(command: &str) -> bool {
    std::env::var_os("PATH")
        .into_iter()
        .flat_map(|paths| std::env::split_paths(&paths).collect::<Vec<_>>())
        .map(|path| path.join(command))
        .any(|path| path.is_file())
}

fn invoke(program: &str, args: &[&str]) -> Result<Output, String> {
    Command::new(program)
        .args(args)
        .output()
        .map_err(|error| error.to_string())
}

fn contains_server(output: &Output, name: &str) -> bool {
    let text = format!(
        "{}\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    text.lines().any(|line| {
        line.split(|ch: char| !ch.is_ascii_alphanumeric() && ch != '-')
            .any(|word| word == name)
    })
}

fn already_registered(client: &Client, server: &Server) -> Result<bool, String> {
    let output = match client.name {
        "claude-code" => invoke(client.executable, &["mcp", "get", server.name])?,
        "codex" | "hermes" => {
            invoke(client.executable, &["mcp", "list"]).map_err(|error| error.to_string())?
        }
        _ => return Err("cliente MCP desconhecido".to_string()),
    };
    if !output.status.success() {
        if client.name == "claude-code" {
            return Ok(false);
        }
        return Err(String::from_utf8_lossy(&output.stderr).trim().to_string());
    }
    Ok(contains_server(&output, server.name))
}

fn register_with(client: &Client, server: &Server) -> Result<(), String> {
    let mut args = match client.name {
        "claude-code" => vec!["mcp", "add", "--scope", "user", server.name, "--"],
        "codex" => vec!["mcp", "add", server.name, "--"],
        "hermes" => vec!["mcp", "add", server.name, "--command", server.executable],
        _ => return Err("cliente MCP desconhecido".to_string()),
    };
    if client.name != "hermes" {
        args.push(server.executable);
        args.extend(server.args.iter().copied());
    } else {
        args.push("--args=--mcp");
    }
    let output = invoke(client.executable, &args)?;
    if output.status.success() {
        Ok(())
    } else {
        let message = String::from_utf8_lossy(&output.stderr).trim().to_string();
        Err(if message.is_empty() {
            format!("processo encerrou com {}", output.status)
        } else {
            message
        })
    }
}

pub fn register(json_output: bool, english: bool) -> i32 {
    let installed_servers = SERVERS
        .iter()
        .filter(|server| {
            let path = Path::new(server.executable);
            path.is_file()
        })
        .collect::<Vec<_>>();
    let missing_servers = SERVERS
        .iter()
        .filter(|server| {
            !installed_servers
                .iter()
                .any(|installed| installed.name == server.name)
        })
        .map(|server| server.name)
        .collect::<Vec<_>>();
    let mut results = Vec::new();
    let mut failures = Vec::new();

    for client in CLIENTS {
        if !command_exists(client.executable) {
            results.push(json!({"client":client.name,"status":"unavailable"}));
            continue;
        }
        for server in &installed_servers {
            match already_registered(client, server) {
                Ok(true) => results.push(json!({"client":client.name,"server":server.name,"status":"already_registered"})),
                Ok(false) => match register_with(client, server) {
                    Ok(()) => results.push(json!({"client":client.name,"server":server.name,"status":"registered"})),
                    Err(error) => {
                        failures.push(format!("{} / {}: {}", client.name, server.name, error));
                        results.push(json!({"client":client.name,"server":server.name,"status":"error","error":error}));
                    }
                },
                Err(error) => {
                    failures.push(format!("{} / {}: {}", client.name, server.name, error));
                    results.push(json!({"client":client.name,"server":server.name,"status":"error","error":error}));
                }
            }
        }
    }

    let status = if failures.is_empty() { "ok" } else { "error" };
    if json_output {
        println!(
            "{}",
            json!({
                "command":"mcp register",
                "status":status,
                "servers_unavailable":missing_servers,
                "results":results,
                "exit_code":if failures.is_empty() { 0 } else { 1 }
            })
        );
    } else {
        for result in &results {
            let client = result["client"].as_str().unwrap_or("?");
            let server = result["server"].as_str();
            let result_status = result["status"].as_str().unwrap_or("?");
            let description = match (english, result_status) {
                (true, "registered") => "registered",
                (true, "already_registered") => "already registered",
                (true, "unavailable") => "client unavailable",
                (true, _) => "registration failed",
                (false, "registered") => "registrado",
                (false, "already_registered") => "já registrado",
                (false, "unavailable") => "cliente indisponível",
                (false, _) => "falha no registro",
            };
            if let Some(server) = server {
                println!("{client} / {server}: {description}");
            } else {
                println!("{client}: {description}");
            }
        }
        if !missing_servers.is_empty() {
            let label = if english {
                "MCP servers not installed"
            } else {
                "Servidores MCP não instalados"
            };
            println!("{label}: {}", missing_servers.join(", "));
        }
        for failure in &failures {
            eprintln!("forja mcp register: {failure}");
        }
    }
    if failures.is_empty() {
        0
    } else {
        1
    }
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    use std::fs;
    use std::os::unix::fs::PermissionsExt;

    #[test]
    fn memory_registration_uses_stdio_and_is_detected_for_every_client() {
        let root = std::env::temp_dir().join(format!("forja-mcp-register-{}", std::process::id()));
        fs::create_dir_all(&root).unwrap();
        let executable = root.join("client");
        fs::write(
            &executable,
            "#!/bin/sh\ncase \"$2\" in\n add) case \"$*\" in\n *hero-memory*--mcp*) exit 0;;\n *) exit 1;;\n esac;;\n get|list) echo hero-memory;;\n *) exit 1;;\nesac\n",
        ).unwrap();
        fs::set_permissions(&executable, fs::Permissions::from_mode(0o700)).unwrap();
        let memory = SERVERS
            .iter()
            .find(|server| server.name == "hero-memory")
            .unwrap();
        assert_eq!(memory.executable, "/usr/libexec/forjaos/memd");
        assert_eq!(memory.args, ["--mcp"]);
        for name in ["claude-code", "codex", "hermes"] {
            let client = Client {
                name,
                executable: executable.to_str().unwrap(),
            };
            register_with(&client, memory).unwrap();
            assert!(already_registered(&client, memory).unwrap());
        }
        fs::remove_file(executable).unwrap();
        fs::remove_dir(root).unwrap();
    }
}
