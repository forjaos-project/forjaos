//! `forja doctor` (FR-036): lista cada verificação com ✓ / ! / ✗; código de saída 1 se algo crítico falha.
use serde::Serialize;
use std::io::IsTerminal;
use std::process::Command;

#[derive(Clone, Copy, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
enum Status {
    Ok,
    Warn,
    Fail,
}

#[derive(Serialize)]
struct Check {
    name: &'static str,
    status: Status,
    detail: String,
    critical: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    hint: Option<String>,
}

fn run_cmd(program: &str, args: &[&str]) -> Option<String> {
    let out = Command::new(program).args(args).output().ok()?;
    out.status.success().then(|| String::from_utf8_lossy(&out.stdout).trim().to_string())
}

fn first_line(text: &str) -> String {
    text.lines().next().unwrap_or("").trim().to_string()
}

fn check(name: &'static str, status: Status, detail: impl Into<String>, critical: bool, hint: Option<&str>) -> Check {
    Check { name, status, detail: detail.into(), critical, hint: hint.map(str::to_string) }
}

/// Ferramenta presente: Ok com a versão, ou `missing` (aviso, ou falha se crítica) com a dica de instalação.
fn tool(name: &'static str, program: &str, args: &[&str], critical: bool, hint: &str) -> Check {
    match run_cmd(program, args) {
        Some(version) => check(name, Status::Ok, first_line(&version), critical, None),
        None => check(name, if critical { Status::Fail } else { Status::Warn }, "não encontrado", critical, Some(hint)),
    }
}

fn kernel() -> Check {
    check("Kernel", Status::Ok, run_cmd("uname", &["-r"]).unwrap_or_else(|| "desconhecido".into()), false, None)
}

fn zram() -> Check {
    if std::path::Path::new("/sys/block/zram0").exists() {
        check("zram", Status::Ok, "ativo", false, None)
    } else {
        check("zram", Status::Warn, "zram0 ausente", false, None)
    }
}

fn gpu() -> (Check, Check) {
    let query = run_cmd("nvidia-smi", &["--query-gpu=name,driver_version", "--format=csv,noheader"]);
    let gpu = match &query {
        Some(line) => check("GPU", Status::Ok, first_line(line), false, None),
        None => check("GPU", Status::Warn, "driver NVIDIA não detectado", false, None),
    };
    let cuda = run_cmd("nvidia-smi", &[])
        .and_then(|text| text.split("CUDA Version:").nth(1).map(|v| v.split_whitespace().next().unwrap_or("").to_string()))
        .map(|v| check("CUDA", Status::Ok, v, false, None))
        .unwrap_or_else(|| check("CUDA", Status::Warn, "indisponível", false, None));
    (gpu, cuda)
}

fn git_auth() -> Check {
    let helper = run_cmd("git", &["config", "--global", "credential.helper"]).unwrap_or_default();
    if helper.contains("libsecret") || helper.contains("manager") {
        check("Git auth", Status::Ok, helper, false, None)
    } else {
        check("Git auth", Status::Warn, "sem credential helper do sistema", false, Some("gh auth login"))
    }
}

fn ollama() -> Check {
    match run_cmd("ollama", &["--version"]) {
        None => check("Ollama", Status::Warn, "não encontrado", false, Some("forja setup --profile ia")),
        Some(version) => {
            let model = run_cmd("ollama", &["ps"])
                .and_then(|text| text.lines().nth(1).and_then(|l| l.split_whitespace().next().map(str::to_string)));
            let detail = match model {
                Some(m) => format!("{} · modelo carregado: {m}", first_line(&version)),
                None => format!("{} · nenhum modelo carregado", first_line(&version)),
            };
            check("Ollama", Status::Ok, detail, false, None)
        }
    }
}

fn keys() -> Check {
    match run_cmd("secret-tool", &["search", "--all", "service", "forja"]) {
        Some(text) => {
            let count = text.lines().filter(|l| l.starts_with("[/")).count();
            check("Chaves de API", if count > 0 { Status::Ok } else { Status::Warn }, format!("{count} no KWallet"), false, (count == 0).then_some("forja keys set anthropic"))
        }
        None => check("Chaves de API", Status::Warn, "secret-tool indisponível", false, None),
    }
}

fn unity_hub() -> Check {
    let home = std::env::var("HOME").unwrap_or_default();
    if std::path::Path::new(&format!("{home}/.local/share/applications/unityhub.desktop")).exists() {
        check("Unity Hub", Status::Ok, "instalado", false, None)
    } else {
        check("Unity Hub", Status::Warn, "não instalado", false, Some("forja install unity"))
    }
}

fn daemon(name: &'static str, unit: &str) -> Check {
    let active = run_cmd("systemctl", &["--user", "is-active", unit]).is_some_and(|s| s == "active");
    if active {
        let pid = run_cmd("systemctl", &["--user", "show", "-p", "MainPID", "--value", unit]).unwrap_or_default();
        check(name, Status::Ok, format!("PID {pid}"), false, None)
    } else {
        check(name, Status::Warn, "inativo", false, None)
    }
}

fn firewall() -> Check {
    let active = run_cmd("systemctl", &["is-active", "firewalld"]).is_some_and(|s| s == "active");
    if active {
        check("Firewall", Status::Ok, "firewalld ativo", true, None)
    } else {
        check("Firewall", Status::Fail, "firewalld inativo", true, Some("sudo systemctl enable --now firewalld"))
    }
}

fn open_ports() -> Check {
    let exposed = run_cmd("ss", &["-tlnH"]).map(|text| {
        text.lines()
            .filter(|l| {
                let local = l.split_whitespace().nth(3).unwrap_or("");
                !(local.starts_with("127.") || local.starts_with("[::1]") || local.starts_with("::1"))
            })
            .count()
    });
    match exposed {
        Some(0) => check("Portas abertas", Status::Ok, "0", true, None),
        Some(n) => check("Portas abertas", Status::Fail, n.to_string(), true, Some("ss -tlnp")),
        None => check("Portas abertas", Status::Warn, "ss indisponível", true, None),
    }
}

fn collect() -> Vec<Check> {
    let (gpu, cuda) = gpu();
    vec![
        kernel(),
        zram(),
        gpu,
        cuda,
        tool("Docker", "docker", &["--version"], true, "forja setup"),
        tool("Podman", "podman", &["--version"], true, "forja setup"),
        git_auth(),
        ollama(),
        keys(),
        unity_hub(),
        tool("Claude Code", "claude", &["--version"], false, "forja install claude-code"),
        tool("Codex", "codex", &["--version"], false, "forja setup --profile ia"),
        tool("Hermes", "hermes", &["--version"], false, "forja setup --profile ia"),
        daemon("herod", "herod.service"),
        daemon("memd", "memd.service"),
        firewall(),
        open_ports(),
    ]
}

struct Palette {
    on: bool,
}

impl Palette {
    // Valores da paleta escura (brand/palette.json: success, warning, danger, accent-cyan) em RGB decimal.
    fn paint(&self, rgb: (u8, u8, u8), text: &str) -> String {
        if self.on { format!("\x1b[38;2;{};{};{}m{text}\x1b[0m", rgb.0, rgb.1, rgb.2) } else { text.to_string() }
    }
    fn chip(&self, text: &str) -> String {
        if self.on { format!("\x1b[48;2;22;27;38m\x1b[38;2;0;229;255m {text} \x1b[0m") } else { format!("`{text}`") }
    }
}

pub fn run(json: bool) -> i32 {
    let checks = collect();
    let critical_failure = checks.iter().any(|c| c.critical && c.status == Status::Fail);
    if json {
        println!("{}", serde_json::to_string_pretty(&checks).expect("serialize checks"));
        return i32::from(critical_failure);
    }
    let p = Palette { on: std::io::stdout().is_terminal() && std::env::var_os("NO_COLOR").is_none() };
    let (green, amber, red) = ((16, 185, 129), (245, 158, 11), (244, 63, 94));
    for c in &checks {
        let (mark, color) = match c.status {
            Status::Ok => ("✓", green),
            Status::Warn => ("!", amber),
            Status::Fail => ("✗", red),
        };
        println!("{} {:<16} {}", p.paint(color, mark), c.name, c.detail);
    }
    let count = |s: Status| checks.iter().filter(|c| c.status == s).count();
    println!("\n{} ok · {} avisos · {} falhas", count(Status::Ok), count(Status::Warn), count(Status::Fail));
    if let Some(hint) = checks.iter().find_map(|c| (c.status != Status::Ok).then(|| c.hint.as_deref()).flatten()) {
        println!("Sugestão: {}", p.chip(hint));
    }
    i32::from(critical_failure)
}
