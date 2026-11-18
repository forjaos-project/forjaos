use crate::policy::Action;
use serde_json::Value;
use std::path::Path;
use std::process::Output;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::io::AsyncReadExt;
use tokio::process::Command;
use tokio::time::{timeout, Duration};
use zbus::{Connection, Proxy};

const MEMORY_BUS: &str = "org.forjaos.Memory";
const MEMORY_PATH: &str = "/org/forjaos/Memory";
const MEMORY_INTERFACE: &str = "org.forjaos.Memory";
const ACTION_TIMEOUT: Duration = Duration::from_secs(58);
const PROCESS_TIMEOUT: Duration = Duration::from_secs(55);
const AGENT_TIMEOUT: Duration = Duration::from_secs(600);
const MAX_AGENT_SUMMARY: usize = 12_000;

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
    let action_timeout = if matches!(&action, Action::CodeDelegate { .. }) {
        AGENT_TIMEOUT + Duration::from_secs(10)
    } else {
        ACTION_TIMEOUT
    };
    timeout(action_timeout, execute_inner(action))
        .await
        .map_err(|_| {
            "A ação excedeu o limite de execução; o HERO voltou ao estado ocioso.".to_string()
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
            if !allowed_project(&cwd) {
                return Err("O projeto não está cadastrado nem em uma raiz Git permitida.".into());
            }
            output_text(run_output(Command::new("code").args(["--reuse-window"]).arg(cwd)).await?)
        }
        Action::OpenApp(app) => {
            if !valid_desktop_id(&app) {
                return Err("Identificador de aplicativo inválido.".into());
            }
            output_text(run_output(Command::new("gtk-launch").arg(app)).await?)
        }
        Action::ServiceList => output_text(
            run_output(Command::new("systemctl").args([
                "--user",
                "list-units",
                "--type=service",
                "--state=running",
                "--no-pager",
            ]))
            .await?,
        ),
        Action::ServiceStatus(service) => {
            if !valid_unit_name(&service) {
                return Err("Nome de serviço inválido.".into());
            }
            output_text(
                run_output(Command::new("systemctl").args([
                    "--user",
                    "status",
                    "--no-pager",
                    &service,
                ]))
                .await?,
            )
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
        Action::CodeDelegate { agent, cwd, task } => {
            let (program, args) = agent_invocation(&agent, &task)?;
            if !allowed_project(&cwd) {
                return Err(
                    "O projeto não está cadastrado nem em uma raiz de desenvolvimento permitida."
                        .into(),
                );
            }
            run_managed_agent(program, &args, &cwd).await
        }
    }
}

async fn run_managed_agent(program: &str, args: &[&str], cwd: &Path) -> Result<String, String> {
    let pipe_path = temporary_task_pipe()?;
    create_task_pipe(&pipe_path)?;
    const RUNNER: &str = r#"fifo="$1"; shift; exec 3>"$fifo"; "$@" 2>&1 | tee -a "$fifo"; code=${PIPESTATUS[0]}; printf '\n[HERO_EXIT_STATUS=%s]\n' "$code" >&3; exit "$code""#;
    let mut terminal = Command::new("konsole")
        .current_dir(cwd)
        .args([
            "--separate",
            "--hold",
            "-e",
            "bash",
            "-c",
            RUNNER,
            "hero-task",
        ])
        .arg(&pipe_path)
        .arg(program)
        .args(args)
        .spawn()
        .map_err(|error| {
            let _ = std::fs::remove_file(&pipe_path);
            format!("Não foi possível abrir o terminal gerenciado: {error}")
        })?;
    let reader_path = pipe_path.clone();
    let reader = tokio::task::spawn_blocking(move || {
        std::fs::OpenOptions::new().read(true).open(reader_path)
    });
    let mut reader = match timeout(Duration::from_secs(20), reader).await {
        Ok(Ok(Ok(reader))) => tokio::fs::File::from_std(reader),
        Ok(Ok(Err(error))) => {
            let _ = terminal.start_kill();
            let _ = terminal.wait().await;
            let _ = std::fs::remove_file(&pipe_path);
            return Err(format!("Não foi possível ler a saída da tarefa: {error}"));
        }
        Ok(Err(error)) => {
            let _ = terminal.start_kill();
            let _ = terminal.wait().await;
            let _ = std::fs::remove_file(&pipe_path);
            return Err(format!("Falha ao abrir o fluxo da tarefa: {error}"));
        }
        Err(_) => {
            let _ = terminal.start_kill();
            let _ = terminal.wait().await;
            let _ = std::fs::remove_file(&pipe_path);
            return Err("O agente não conectou ao fluxo de saída em 20 segundos.".into());
        }
    };
    let mut captured = Vec::new();
    let status = timeout(AGENT_TIMEOUT, async {
        let mut buffer = [0u8; 4096];
        loop {
            let size = reader
                .read(&mut buffer)
                .await
                .map_err(|error| error.to_string())?;
            if size == 0 {
                break;
            }
            capture_tail(&mut captured, &buffer[..size]);
        }
        Ok::<(), String>(())
    })
    .await;
    drop(reader);
    let _ = std::fs::remove_file(&pipe_path);
    let result = match status {
        Ok(Ok(())) => {
            let text = String::from_utf8_lossy(&captured);
            let exit_code = terminal_exit_code(&text);
            let summary = summarize_output(&captured);
            match exit_code {
                Some(0) => Ok(format!(
                    "{program} concluiu com código 0 no projeto {}. Resumo da saída final:\n{summary}",
                    cwd.display()
                )),
                Some(code) => Err(format!(
                    "{program} terminou com código {code} no projeto {}. Resumo da saída final:\n{summary}",
                    cwd.display()
                )),
                None => Err(format!(
                    "O terminal encerrou antes de confirmar a conclusão de {program}. Saída final:\n{summary}"
                )),
            }
        }
        Ok(Err(error)) => Err(format!("Falha ao aguardar {program}: {error}")),
        Err(_) => {
            let _ = terminal.start_kill();
            let _ = terminal.wait().await;
            Err(format!(
                "{program} excedeu o limite de 10 minutos e foi interrompido."
            ))
        }
    };
    result
}

fn terminal_exit_code(text: &str) -> Option<i32> {
    text.lines().rev().find_map(|line| {
        line.strip_prefix("[HERO_EXIT_STATUS=")?
            .strip_suffix(']')?
            .parse::<i32>()
            .ok()
    })
}

fn capture_tail(captured: &mut Vec<u8>, chunk: &[u8]) {
    captured.extend_from_slice(chunk);
    if captured.len() > MAX_AGENT_SUMMARY {
        let start = captured.len() - MAX_AGENT_SUMMARY;
        captured.drain(..start);
    }
}

fn summarize_output(output: &[u8]) -> String {
    let text = String::from_utf8_lossy(output);
    let mut lines = text
        .lines()
        .filter(|line| !line.starts_with("[HERO_EXIT_STATUS="))
        .rev()
        .take(60)
        .collect::<Vec<_>>();
    lines.reverse();
    let summary = lines
        .join("\n")
        .chars()
        .filter(|character| !character.is_control() || matches!(character, '\n' | '\t'))
        .collect::<String>();
    if summary.trim().is_empty() {
        "O agente não retornou texto.".into()
    } else {
        summary
    }
}

fn temporary_task_pipe() -> Result<std::path::PathBuf, String> {
    let runtime = std::env::var_os("XDG_RUNTIME_DIR")
        .map(std::path::PathBuf::from)
        .ok_or_else(|| "XDG_RUNTIME_DIR não está disponível.".to_string())?;
    let dir = runtime.join("forjaos");
    std::fs::create_dir_all(&dir).map_err(|error| error.to_string())?;
    let metadata = std::fs::symlink_metadata(&dir).map_err(|error| error.to_string())?;
    if !metadata.is_dir() || metadata.file_type().is_symlink() {
        return Err("O diretório de runtime HERO não é seguro.".into());
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o700))
            .map_err(|error| error.to_string())?;
    }
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| error.to_string())?
        .as_nanos();
    Ok(dir.join(format!("hero-task-{}-{stamp}.pipe", std::process::id())))
}

fn create_task_pipe(path: &Path) -> Result<(), String> {
    let output = std::process::Command::new("mkfifo")
        .args(["-m", "600", "--"])
        .arg(path)
        .output()
        .map_err(|error| format!("Não foi possível criar o canal temporário: {error}"))?;
    if output.status.success() {
        Ok(())
    } else {
        let detail = String::from_utf8_lossy(&output.stderr).trim().to_string();
        Err(if detail.is_empty() {
            "Não foi possível criar o canal temporário.".into()
        } else {
            detail
        })
    }
}

async fn system_status() -> Result<String, String> {
    let checks: [(&str, &str, &[&str]); 9] = [
        (
            "Journald — erros das últimas 24 h",
            "journalctl",
            &[
                "--since",
                "24 hours ago",
                "--priority=err",
                "--no-pager",
                "--lines=50",
            ],
        ),
        (
            "GPU",
            "nvidia-smi",
            &[
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader",
            ],
        ),
        ("Carga e tempo ativo", "uptime", &[]),
        ("Memória", "free", &["-h"]),
        ("Rede", "nmcli", &["general", "status"]),
        ("Firewall", "firewall-cmd", &["--state"]),
        ("Auditd", "systemctl", &["is-active", "auditd"]),
        ("Portas TCP em escuta", "ss", &["-tlnp"]),
        (
            "Disco",
            "df",
            &["-h", "--output=source,fstype,size,used,avail,pcent,target"],
        ),
    ];
    let mut details = Vec::with_capacity(checks.len() + 2);
    details.push(format!("CPU:\n{}", cpu_usage().await));
    for (label, program, args) in checks {
        let result = match run_output(Command::new(program).args(args)).await {
            Ok(output) if output.status.success() => {
                let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if stdout.is_empty() {
                    "sem dados retornados".to_string()
                } else {
                    stdout
                }
            }
            Ok(output) => {
                let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
                if stderr.is_empty() {
                    format!("indisponível ({})", output.status)
                } else {
                    format!("indisponível: {stderr}")
                }
            }
            Err(error) => format!("indisponível: {error}"),
        };
        details.push(format!("{label}:\n{result}"));
    }
    let thermal = match run_output(Command::new("sensors").arg("-A")).await {
        Ok(output) if output.status.success() => {
            let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if stdout.is_empty() {
                "sem dados retornados".to_string()
            } else {
                stdout
            }
        }
        Ok(output) => {
            let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
            if stderr.is_empty() {
                format!("indisponível ({})", output.status)
            } else {
                format!("indisponível: {stderr}")
            }
        }
        Err(error) => format!("indisponível: {error}"),
    };
    details.push(format!("Temperatura:\n{thermal}"));
    Ok(system_status_report(&details))
}

fn system_status_report(details: &[String]) -> String {
    let unavailable = details
        .iter()
        .filter_map(|detail| {
            let (label, value) = detail.split_once(':')?;
            value.contains("indisponível").then_some(label.trim())
        })
        .collect::<Vec<_>>();
    let journal = details
        .iter()
        .find(|detail| detail.starts_with("Journald"))
        .map(String::as_str)
        .unwrap_or_default();
    let journal_summary = if journal.contains("sem dados retornados") {
        "o journald não listou erros nas últimas 24 horas"
    } else if journal.contains("indisponível") {
        "o journald não pôde ser consultado"
    } else {
        "o journald listou erros para revisão"
    };
    let source_summary = if unavailable.is_empty() {
        "As fontes locais consultadas responderam.".to_string()
    } else {
        format!("Fontes indisponíveis: {}.", unavailable.join(", "))
    };
    format!(
        "Resumo do diagnóstico: {journal_summary}. {source_summary}\nAção sugerida: revise os erros listados e verifique as fontes indisponíveis antes de alterar o sistema; nenhuma mudança foi feita.\n\n{}",
        details.join("\n\n")
    )
}

fn agent_invocation<'a>(
    agent: &str,
    task: &'a str,
) -> Result<(&'static str, Vec<&'a str>), String> {
    match agent {
        "claude-code" => Ok(("claude", vec!["--print", task])),
        "codex" => Ok((
            "codex",
            vec![
                "exec",
                "--sandbox",
                "workspace-write",
                "--ask-for-approval",
                "on-request",
                task,
            ],
        )),
        "hermes" => Ok(("hermes", vec!["chat", "-q", task])),
        _ => Err("Agente de código não permitido.".into()),
    }
}

async fn cpu_usage() -> String {
    let Ok(before) = tokio::fs::read_to_string("/proc/stat").await else {
        return "indisponível: /proc/stat não foi lido".into();
    };
    tokio::time::sleep(Duration::from_millis(200)).await;
    let Ok(after) = tokio::fs::read_to_string("/proc/stat").await else {
        return "indisponível: /proc/stat não foi lido".into();
    };
    let Some((before_total, before_idle)) = cpu_counters(&before) else {
        return "indisponível: contadores de CPU inválidos".into();
    };
    let Some((after_total, after_idle)) = cpu_counters(&after) else {
        return "indisponível: contadores de CPU inválidos".into();
    };
    let total = after_total.saturating_sub(before_total);
    let idle = after_idle.saturating_sub(before_idle);
    if total == 0 {
        "indisponível: intervalo sem amostras".into()
    } else {
        let used = total.saturating_sub(idle) as f64 * 100.0 / total as f64;
        format!("{used:.1}% de uso médio em 200 ms")
    }
}

fn cpu_counters(source: &str) -> Option<(u64, u64)> {
    let line = source.lines().next()?;
    let mut fields = line.split_whitespace();
    if fields.next()? != "cpu" {
        return None;
    }
    let values = fields
        .map(str::parse::<u64>)
        .collect::<Result<Vec<_>, _>>()
        .ok()?;
    if values.len() < 5 {
        return None;
    }
    let total = values.iter().copied().sum();
    let idle = values[3].saturating_add(values[4]);
    Some((total, idle))
}

fn allowed_project(path: &Path) -> bool {
    let Ok(path) = path.canonicalize() else {
        return false;
    };
    if !path.is_dir() || !path.join(".git").exists() {
        return false;
    }
    let Some(home) = std::env::var_os("HOME").map(std::path::PathBuf::from) else {
        return false;
    };
    let in_standard_root = ["proj", "dev", "code"].iter().any(|name| {
        home.join(name)
            .canonicalize()
            .ok()
            .is_some_and(|root| path.starts_with(root))
    });
    if in_standard_root {
        return true;
    }

    #[derive(serde::Deserialize)]
    #[serde(deny_unknown_fields)]
    struct ProjectsConfig {
        #[serde(default)]
        projects: Vec<Project>,
    }
    #[derive(serde::Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Project {
        name: String,
        path: std::path::PathBuf,
    }
    let config = home.join(".config/hero/projects.toml");
    let Ok(source) = std::fs::read_to_string(config) else {
        return false;
    };
    let Ok(config) = toml::from_str::<ProjectsConfig>(&source) else {
        return false;
    };
    config.projects.into_iter().any(|project| {
        if project.name.is_empty() {
            return false;
        }
        let configured = if project.path.is_absolute() {
            project.path
        } else {
            home.join(project.path)
        };
        configured
            .canonicalize()
            .ok()
            .is_some_and(|configured| path == configured)
    })
}

fn valid_unit_name(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || "@_-.:".contains(character))
}

fn valid_desktop_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 255
        && value
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || "._-".contains(character))
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

#[cfg(test)]
mod tests {
    use super::{
        agent_invocation, allowed_project, capture_tail, cpu_counters, cpu_usage, execute,
        output_text, require_project, summarize_output, system_status_report, terminal_exit_code,
        valid_desktop_id, valid_unit_name,
    };
    use crate::policy::Action;
    use crate::test_support::TestHome;
    use std::fs;
    use std::path::PathBuf;
    use std::process::{ExitStatus, Output};
    use std::time::{SystemTime, UNIX_EPOCH};

    fn unique_dir(name: &str) -> PathBuf {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock after epoch")
            .as_nanos();
        let dir = std::env::temp_dir().join(format!("hero-{name}-{}-{stamp}", std::process::id()));
        fs::create_dir_all(&dir).expect("create test directory");
        dir
    }

    #[test]
    fn cpu_counters_include_idle_and_iowait() {
        assert_eq!(
            cpu_counters("cpu 10 2 3 40 5 6 7 8\ncpu0 1 0 0 4 0 0 0 0"),
            Some((81, 45))
        );
        assert_eq!(cpu_counters("cpu 1 2 3"), None);
        assert_eq!(cpu_counters("invalid"), None);
    }

    #[test]
    fn agent_summary_omits_internal_exit_marker() {
        let summary = summarize_output(b"Build finished\n[HERO_EXIT_STATUS=0]\n");
        assert_eq!(summary, "Build finished");
    }

    #[test]
    fn terminal_status_uses_final_marker_after_agent_output() {
        assert_eq!(
            terminal_exit_code("[HERO_EXIT_STATUS=0]\nfailed\n[HERO_EXIT_STATUS=7]\n"),
            Some(7)
        );
    }

    #[test]
    fn agent_invocation_has_explicit_sandbox_and_approval_arguments() {
        assert_eq!(
            agent_invocation("claude-code", "revise"),
            Ok(("claude", vec!["--print", "revise"]))
        );
        assert_eq!(
            agent_invocation("codex", "revise"),
            Ok((
                "codex",
                vec![
                    "exec",
                    "--sandbox",
                    "workspace-write",
                    "--ask-for-approval",
                    "on-request",
                    "revise"
                ]
            ))
        );
        assert_eq!(
            agent_invocation("hermes", "revise"),
            Ok(("hermes", vec!["chat", "-q", "revise"]))
        );
        assert_eq!(
            agent_invocation("unknown", "revise"),
            Err("Agente de código não permitido.".into())
        );
    }

    #[test]
    fn summaries_keep_only_the_tail_and_filter_control_characters() {
        let mut captured = b"old\n".to_vec();
        capture_tail(&mut captured, &vec![b'x'; super::MAX_AGENT_SUMMARY]);
        assert_eq!(captured.len(), super::MAX_AGENT_SUMMARY);
        let summary = summarize_output(b"one\x07\ntwo\n[HERO_EXIT_STATUS=1]\n");
        assert_eq!(summary, "one\ntwo");
    }

    #[test]
    fn health_report_names_missing_sources_and_never_claims_a_change() {
        let report = system_status_report(&[
            "Journald — erros das últimas 24 h:\nsem dados retornados".into(),
            "GPU:\nindisponível: comando ausente".into(),
        ]);
        assert!(report.contains("journald não listou erros"));
        assert!(report.contains("Fontes indisponíveis: GPU"));
        assert!(report.contains("nenhuma mudança foi feita"));

        let report = system_status_report(&["Journald:\nindisponível".into()]);
        assert!(report.contains("journald não pôde ser consultado"));
    }

    #[test]
    fn validates_apps_services_and_compose_project_requirements() {
        assert!(valid_unit_name("podman.service"));
        assert!(!valid_unit_name("podman; reboot"));
        assert!(valid_desktop_id("org.kde.konsole"));
        assert!(!valid_desktop_id("org.kde.konsole;id"));

        let dir = unique_dir("compose");
        assert!(require_project(&dir).is_err());
        fs::write(dir.join("compose.yaml"), "services: {}\n").expect("write compose file");
        assert!(require_project(&dir).is_ok());
        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn output_text_selects_stdout_or_stderr_from_process_status() {
        #[cfg(unix)]
        use std::os::unix::process::ExitStatusExt;
        #[cfg(windows)]
        use std::os::windows::process::ExitStatusExt;

        let success = Output {
            status: ExitStatus::from_raw(0),
            stdout: b"  result  \n".to_vec(),
            stderr: b"warning".to_vec(),
        };
        assert_eq!(output_text(success), Ok("result".into()));

        let failure = Output {
            status: ExitStatus::from_raw(1 << 8),
            stdout: b"partial".to_vec(),
            stderr: b"failed".to_vec(),
        };
        assert_eq!(output_text(failure), Err("failed".into()));
    }

    #[test]
    fn project_allowlist_accepts_registered_git_repositories_only() {
        let home = TestHome::new();
        let registered = home.register_project("registered");
        assert!(allowed_project(&registered));

        let external = unique_dir("external-project");
        fs::create_dir_all(external.join(".git")).expect("create external git marker");
        assert!(!allowed_project(&external));
        fs::remove_dir_all(external).expect("remove external project");
    }

    #[tokio::test]
    async fn execution_rejects_invalid_or_unscoped_requests_before_launching_tools() {
        let home = TestHome::new();
        let external = unique_dir("unscoped");
        assert!(execute(Action::OpenApp("bad;launch".into())).await.is_err());
        assert!(execute(Action::ServiceStatus("service;restart".into()))
            .await
            .is_err());
        assert!(execute(Action::OpenProject(external.clone()))
            .await
            .is_err());
        assert!(execute(Action::Compose {
            up: true,
            cwd: external.clone(),
        })
        .await
        .is_err());
        assert!(execute(Action::ComposeLogs(external.clone()))
            .await
            .is_err());
        assert!(execute(Action::RunTests(external.clone())).await.is_err());
        assert!(execute(Action::CodeDelegate {
            agent: "unknown".into(),
            cwd: external.clone(),
            task: "inspect".into(),
        })
        .await
        .is_err());
        assert!(execute(Action::CodeDelegate {
            agent: "codex".into(),
            cwd: external.clone(),
            task: "inspect".into(),
        })
        .await
        .is_err());
        fs::remove_dir_all(external).expect("remove unscoped project");
        drop(home);
    }

    #[tokio::test]
    async fn cpu_usage_returns_a_read_only_status_string() {
        let status = cpu_usage().await;
        assert!(status.contains("indisponível") || status.contains("% de uso médio em 200 ms"));
    }
}
