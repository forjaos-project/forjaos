use crate::policy::Action;
use serde_json::Value;
use std::path::Path;
use std::process::{Command, Output};
use zbus::{Connection, Proxy};

const MEMORY_BUS: &str = "org.forjaos.Memory";
const MEMORY_PATH: &str = "/org/forjaos/Memory";
const MEMORY_INTERFACE: &str = "org.forjaos.Memory";

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
    let raw: String = if method == "Search" {
        proxy
            .call(method, &(payload, 5u32))
            .await
            .map_err(|error| error.to_string())?
    } else {
        proxy
            .call(method, &payload)
            .await
            .map_err(|error| error.to_string())?
    };
    let value = serde_json::from_str::<Value>(&raw).map_err(|error| error.to_string())?;
    Ok(serde_json::to_string(&value).map_err(|error| error.to_string())?)
}

pub async fn execute(action: Action) -> Result<String, String> {
    match action {
        Action::GameMode(enabled) => {
            let operation = if enabled { "start" } else { "stop" };
            output_text(
                Command::new("systemctl")
                    .args(["--user", operation, "hero-game.target"])
                    .output()
                    .map_err(|error| error.to_string())?,
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
            output_text(command.output().map_err(|error| error.to_string())?)
        }
        Action::GitStatus(cwd) => output_text(
            Command::new("git")
                .current_dir(cwd)
                .args(["status", "--short", "--branch"])
                .output()
                .map_err(|error| error.to_string())?,
        ),
        Action::GpuStatus => output_text(
            Command::new("nvidia-smi")
                .args([
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader",
                ])
                .output()
                .map_err(|error| error.to_string())?,
        ),
        Action::OpenUrl(url) => {
            let output = Command::new("xdg-open")
                .arg(url)
                .output()
                .map_err(|error| error.to_string())?;
            output_text(output)
        }
        Action::MemorySearch(query) => memory_call("Search", &query).await,
        Action::Remember(note) => memory_call("Remember", &note).await,
        Action::Update => output_text(
            Command::new("forja")
                .args(["update", "--yes"])
                .output()
                .map_err(|error| error.to_string())?,
        ),
        Action::Rollback => output_text(
            Command::new("forja")
                .args(["rollback", "--yes"])
                .output()
                .map_err(|error| error.to_string())?,
        ),
        Action::RestartUserService(unit) => output_text(
            Command::new("systemctl")
                .args(["--user", "restart", &unit])
                .output()
                .map_err(|error| error.to_string())?,
        ),
    }
}
