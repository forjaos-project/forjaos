use std::process::Stdio;
use std::time::Duration;
use tokio::process::Command;
use tokio::time::timeout;

pub async fn run(program: &str, args: &[&str]) -> Result<String, String> {
    let mut command = Command::new(program);
    command.args(args).stdin(Stdio::null()).kill_on_drop(true);
    let output = timeout(Duration::from_secs(15), command.output())
        .await
        .map_err(|_| "tempo limite excedido".to_string())?
        .map_err(|_| format!("{program} indisponível"))?;
    let stdout = String::from_utf8_lossy(&output.stdout)
        .chars()
        .filter(|character| !character.is_control() || matches!(character, '\n' | '\t'))
        .take(16_000)
        .collect::<String>();
    if output.status.success() {
        Ok(if stdout.trim().is_empty() {
            "concluído".to_string()
        } else {
            stdout.trim().to_string()
        })
    } else {
        Err("comando não concluiu; confira a disponibilidade do serviço".to_string())
    }
}

pub async fn run_input(program: &str, args: &[&str], input: &str) -> Result<String, String> {
    use tokio::io::AsyncWriteExt;
    let mut command = Command::new(program);
    command
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .kill_on_drop(true);
    let mut child = command
        .spawn()
        .map_err(|_| format!("{program} indisponível"))?;
    let mut stdin = child
        .stdin
        .take()
        .ok_or_else(|| format!("{program} indisponível"))?;
    stdin
        .write_all(input.as_bytes())
        .await
        .map_err(|_| format!("{program} indisponível"))?;
    drop(stdin);
    let output = timeout(Duration::from_secs(15), child.wait_with_output())
        .await
        .map_err(|_| "tempo limite excedido".to_string())?
        .map_err(|_| format!("{program} indisponível"))?;
    if output.status.success() {
        Ok("concluído".to_string())
    } else {
        Err("comando não concluiu".to_string())
    }
}

pub fn valid_atom(value: &str, maximum: usize) -> bool {
    !value.is_empty()
        && value.len() <= maximum
        && value.as_bytes()[0].is_ascii_alphanumeric()
        && value
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || "@_.:+-".contains(character))
}

pub fn home() -> Option<std::path::PathBuf> {
    std::env::var_os("HOME").map(std::path::PathBuf::from)
}
