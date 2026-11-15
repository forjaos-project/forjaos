use crate::policy::Action;
use serde_json::Value;
use std::path::Path;
use std::process::Output;
use tokio::process::Command;
use tokio::time::{timeout, Duration};
use zbus::{Connection, Proxy};

const MEMORY_BUS: &str = "org.forjaos.Memory";
const MEMORY_PATH: &str = "/org/forjaos/Memory";
const MEMORY_INTERFACE: &str = "org.forjaos.Memory";
const ACTION_TIMEOUT: Duration = Duration::from_secs(58);
const PROCESS_TIMEOUT: Duration = Duration::from_secs(55);

async fn run_output(command: &mut Command) -> Result<Output, String> {
    command.kill_on_drop(true);
    timeout(PROCESS_TIMEOUT, command.output())
        .await
        .map_err(|_| "O processo excedeu o limite de 55 segundos e foi interrompido.".to_string())?
        .map_err(|error| error.to_string())
}

fn output_text(output: Output) -> Result<String, String> {
    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
    if output.status.success() {
        Ok(if stdout.is_empty() { stderr } else { stdout })
    } else {
        let detail = if stderr.is_empty() { stdout } else { stderr };
        Err(if detail.is_empty() {
            format!("processo terminou com {}", output.status)
        } else {
            detail
        })
    }
}

fn require_project(cwd: &Path) -> Result<(), String> {
    if !cwd.is_dir() {
        return Err("O diretório do projeto não está disponível.".into());
    }
    if ![
        "compose.yaml",
        "compose.yml",
        "docker-compose.yml",
        "docker-compose.yaml",
    ]
    .iter()
    .any(|name| cwd.join(name).is_file())
    {
        return Err("Não encontrei um arquivo Compose no diretório atual.".into());
    }
    Ok(())
}

async fn memory_call(method: &str, payload: &str) -> Result<String, String> {
    let connection = Connection::session()
        .await
        .map_err(|error| error.to_string())?;
    let proxy = Proxy::new(&connection, MEMORY_BUS, MEMORY_PATH, MEMORY_INTERFACE)
        .await
        .map_err(|error| error.to_string())?;
    let call = async {
        if method == "Search" {
            proxy.call::<_, _, String>(method, &(payload, 5u32)).await
        } else {
            proxy.call::<_, _, String>(method, &payload).await
        }
    };
    let raw: String = timeout(PROCESS_TIMEOUT, call)
        .await
        .map_err(|_| "A Memória não respondeu em 55 segundos.".to_string())?
        .map_err(|error| error.to_string())?;
    let value = serde_json::from_str::<Value>(&raw).map_err(|error| error.to_string())?;
    serde_json::to_string(&value).map_err(|error| error.to_string())
}

pub async fn record_hero_action(tool: &str, succeeded: bool, cwd: &str) {
    let detail = format!(
        "tool={tool}; approved=true; result={}",
        if succeeded { "ok" } else { "failed" }
    );
    let _ = timeout(Duration::from_secs(2), async {
        let Ok(connection) = Connection::session().await else {
            return;
        };
        let Ok(proxy) = Proxy::new(&connection, MEMORY_BUS, MEMORY_PATH, MEMORY_INTERFACE).await
        else {
            return;
        };
        let _ = proxy
            .call::<_, _, String>(
                "CollectEvent",
                &(
                    "hero",
                    detail.as_str(),
                    cwd,
                    if succeeded { 0i32 } else { 1i32 },
                    0u64,
                ),
            )
            .await;
    })
    .await;
}

pub async fn execute(action: Action) -> Result<String, String> {
    timeout(ACTION_TIMEOUT, execute_inner(action))
        .await
        .map_err(|_| {
            "A ação excedeu o limite de 58 segundos; o HERO voltou ao estado ocioso.".to_string()
        })?
}

async fn execute_inner(action: Action) -> Result<String, String> {
    match action {
        Action::GameMode(enabled) => {
            let operation = if enabled { "start" } else { "stop" };
            output_text(
                run_output(Command::new("systemctl").args([
                    "--user",
                    operation,
                    "hero-game.target",
                ]))
                .await?,
            )
        }
        Action::Compose { up, cwd } => {
            require_project(&cwd)?;
            let mut command = Command::new("podman");
            command.current_dir(cwd).arg("compose");
            if up {
                command.args(["up", "-d"]);
            } else {
                command.arg("down");
            }
            output_text(run_output(&mut command).await?)
        }
        Action::ComposeLogs(cwd) => {
            require_project(&cwd)?;
            output_text(
                run_output(
                    Command::new("podman")
                        .current_dir(cwd)
                        .args(["compose", "logs", "--tail", "50"]),
                )
                .await?,
            )
        }
        Action::GitStatus(cwd) => output_text(
            run_output(
                Command::new("git")
                    .current_dir(cwd)
                    .args(["status", "--short", "--branch"]),
            )
            .await?,
        ),
        Action::GpuStatus => output_text(
            run_output(Command::new("nvidia-smi").args([
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader",
            ]))
            .await?,
        ),
        Action::SystemStatus => system_status().await,
        Action::OpenProject(cwd) => {
            if !cwd.is_dir() {
                return Err("O diretório do projeto não está disponível.".into());
            }
            output_text(run_output(Command::new("code").args(["--reuse-window"]).arg(cwd)).await?)
        }
        Action::OpenUrl(url) => {
            let output = run_output(Command::new("xdg-open").arg(url)).await?;
            output_text(output)
        }
        Action::Wifi(enabled) => {
            let state = if enabled { "on" } else { "off" };
            output_text(run_output(Command::new("nmcli").args(["radio", "wifi", state])).await?)
        }
        Action::Bluetooth(enabled) => {
            let state = if enabled { "on" } else { "off" };
            output_text(run_output(Command::new("bluetoothctl").args(["power", state])).await?)
        }
        Action::Vpn { enabled, name } => vpn(enabled, &name).await,
        Action::RunTests(cwd) => {
            let (program, args): (&str, &[&str]) =
                if cwd.join("justfile").is_file() || cwd.join("Justfile").is_file() {
                    ("just", &["test"])
                } else if cwd.join("Cargo.toml").is_file() {
                    ("cargo", &["test", "--locked"])
                } else {
                    return Err(
                        "Não encontrei justfile ou Cargo.toml; nenhum teste foi executado.".into(),
                    );
                };
            output_text(run_output(Command::new(program).current_dir(cwd).args(args)).await?)
        }
        Action::MemorySearch(query) => memory_call("Search", &query).await,
        Action::Remember(note) => memory_call("Remember", &note).await,
        Action::Update => {
            output_text(run_output(Command::new("forja").args(["update", "--yes"])).await?)
        }
        Action::Rollback => {
            output_text(run_output(Command::new("forja").args(["rollback", "--yes"])).await?)
        }
        Action::RestartUserService(unit) => output_text(
            run_output(Command::new("systemctl").args(["--user", "restart", &unit])).await?,
        ),
    }
}

async fn system_status() -> Result<String, String> {
    let mut details = Vec::new();
    for (program, args) in [
        ("uptime", vec!["--pretty"]),
        ("free", vec!["-h"]),
        ("nmcli", vec!["general", "status"]),
    ] {
        let output = run_output(Command::new(program).args(args))
            .await
            .map_err(|error| format!("{program}: {error}"))?;
        if output.status.success() {
            let text = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !text.is_empty() {
                details.push(text);
            }
        }
    }
    if details.is_empty() {
        Err("Nenhum dado de saúde do sistema está disponível.".into())
    } else {
        Ok(details.join("\n"))
    }
}

async fn vpn(enabled: bool, name: &str) -> Result<String, String> {
    let output =
        run_output(Command::new("nmcli").args(["-t", "-f", "NAME,TYPE", "connection", "show"]))
            .await?;
    if !output.status.success() {
        return output_text(output);
    }
    let connections = String::from_utf8_lossy(&output.stdout);
    let matching = connections.lines().find_map(|line| {
        let (candidate, kind) = line.split_once(':')?;
        (candidate.eq_ignore_ascii_case(name) && kind.to_ascii_lowercase().contains("vpn"))
            .then_some(candidate)
    });
    let Some(connection_name) = matching else {
        return Err("Não encontrei uma conexão VPN com esse nome.".into());
    };
    let operation = if enabled { "up" } else { "down" };
    output_text(
        run_output(Command::new("nmcli").args([
            "--wait",
            "10",
            "connection",
            operation,
            "id",
            connection_name,
        ]))
        .await?,
    )
}
