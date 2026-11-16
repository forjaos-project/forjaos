use crate::common;
use rmcp::{
    handler::server::router::tool::ToolRouter, handler::server::wrapper::Parameters, tool,
    tool_router,
};
use schemars::JsonSchema;
use serde::Deserialize;
use std::fs;

pub struct SystemServer {
    #[allow(dead_code)]
    tool_router: ToolRouter<Self>,
}

impl Default for SystemServer {
    fn default() -> Self {
        Self {
            tool_router: Self::tool_router(),
        }
    }
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct ServiceArgs {
    #[schemars(length(max = 128))]
    service: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct JournalArgs {
    #[schemars(range(min = 1, max = 100))]
    lines: u8,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct ToggleArgs {
    enabled: bool,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct VpnArgs {
    #[schemars(length(max = 128))]
    name: String,
    enabled: bool,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct ModelArgs {
    #[schemars(length(max = 128))]
    model: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct PackageArgs {
    #[schemars(length(max = 64))]
    package: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct PowerArgs {
    #[schemars(extend("enum" = ["power-saver", "balanced", "performance"]))]
    profile: String,
}

#[tool_router(server_handler)]
impl SystemServer {
    #[tool(
        name = "services.list",
        description = "Tier: livre. Lista serviços systemd do usuário.",
        annotations(read_only_hint = true)
    )]
    async fn services_list(&self) -> String {
        common::run(
            "systemctl",
            &[
                "--user",
                "list-units",
                "--type=service",
                "--all",
                "--no-pager",
                "--plain",
            ],
        )
        .await
        .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "services.status",
        description = "Tier: livre. Consulta um serviço systemd do usuário.",
        annotations(read_only_hint = true)
    )]
    async fn services_status(&self, Parameters(args): Parameters<ServiceArgs>) -> String {
        if !common::valid_atom(&args.service, 128) {
            return "nome de serviço inválido".to_string();
        }
        common::run(
            "systemctl",
            &[
                "--user",
                "show",
                "--property=ActiveState,SubState,UnitFileState",
                &args.service,
            ],
        )
        .await
        .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "services.restart",
        description = "Tier: alterar. Reinicia serviço do usuário; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn services_restart(&self, Parameters(args): Parameters<ServiceArgs>) -> String {
        if !common::valid_atom(&args.service, 128) {
            return "nome de serviço inválido".to_string();
        }
        common::run("systemctl", &["--user", "restart", &args.service])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "journal.query",
        description = "Tier: livre. Consulta somente eventos de erro do journald.",
        annotations(read_only_hint = true)
    )]
    async fn journal_query(&self, Parameters(args): Parameters<JournalArgs>) -> String {
        common::run(
            "journalctl",
            &[
                "--user",
                "-p",
                "err",
                "-n",
                &args.lines.to_string(),
                "--no-pager",
                "-o",
                "short-iso",
            ],
        )
        .await
        .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "firewall.status",
        description = "Tier: livre. Consulta o estado do firewalld.",
        annotations(read_only_hint = true)
    )]
    async fn firewall_status(&self) -> String {
        common::run("firewall-cmd", &["--state"])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "firewall.toggle_zone",
        description = "Tier: bloqueado. Alteração de zona do firewall não é permitida pelo HERO.",
        annotations(destructive_hint = true)
    )]
    async fn firewall_toggle_zone(&self) -> String {
        "bloqueado pela política de segurança; nenhuma alteração foi feita".to_string()
    }

    #[tool(
        name = "gpu.status",
        description = "Tier: livre. Consulta uso, memória e temperatura de GPU NVIDIA.",
        annotations(read_only_hint = true)
    )]
    async fn gpu_status(&self) -> String {
        common::run(
            "nvidia-smi",
            &[
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader",
            ],
        )
        .await
        .unwrap_or_else(|_| "dados de GPU indisponíveis".to_string())
    }

    #[tool(
        name = "cpu.status",
        description = "Tier: livre. Consulta carga do processador.",
        annotations(read_only_hint = true)
    )]
    async fn cpu_status(&self) -> String {
        fs::read_to_string("/proc/loadavg")
            .map(|value| value.trim().to_string())
            .unwrap_or_else(|_| "dados de CPU indisponíveis".to_string())
    }

    #[tool(
        name = "mem.status",
        description = "Tier: livre. Consulta memória do sistema.",
        annotations(read_only_hint = true)
    )]
    async fn mem_status(&self) -> String {
        common::run("free", &["-b"])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "disk.status",
        description = "Tier: livre. Consulta espaço dos sistemas de arquivos.",
        annotations(read_only_hint = true)
    )]
    async fn disk_status(&self) -> String {
        common::run(
            "df",
            &["-h", "--output=source,size,used,avail,pcent,target"],
        )
        .await
        .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "thermal.status",
        description = "Tier: livre. Consulta sensores térmicos disponíveis.",
        annotations(read_only_hint = true)
    )]
    async fn thermal_status(&self) -> String {
        let mut entries = Vec::new();
        if let Ok(zones) = fs::read_dir("/sys/class/thermal") {
            for zone in zones.flatten().filter(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .starts_with("thermal_zone")
            }) {
                if let Ok(value) = fs::read_to_string(zone.path().join("temp")) {
                    entries.push(format!(
                        "{}: {} m°C",
                        zone.file_name().to_string_lossy(),
                        value.trim()
                    ));
                }
            }
        }
        if entries.is_empty() {
            "nenhum sensor térmico disponível".to_string()
        } else {
            entries.join("\n")
        }
    }

    #[tool(
        name = "network.status",
        description = "Tier: livre. Consulta conectividade e rádio de rede.",
        annotations(read_only_hint = true)
    )]
    async fn network_status(&self) -> String {
        common::run(
            "nmcli",
            &[
                "-t",
                "-f",
                "DEVICE,TYPE,STATE,CONNECTION",
                "device",
                "status",
            ],
        )
        .await
        .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "wifi.toggle",
        description = "Tier: alterar. Liga ou desliga Wi-Fi; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn wifi_toggle(&self, Parameters(args): Parameters<ToggleArgs>) -> String {
        let state = if args.enabled { "on" } else { "off" };
        common::run("nmcli", &["radio", "wifi", state])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "bluetooth.toggle",
        description = "Tier: alterar. Liga ou desliga Bluetooth; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn bluetooth_toggle(&self, Parameters(args): Parameters<ToggleArgs>) -> String {
        let state = if args.enabled { "unblock" } else { "block" };
        common::run("rfkill", &[state, "bluetooth"])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "vpn.toggle",
        description = "Tier: alterar. Liga ou desliga uma conexão VPN; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn vpn_toggle(&self, Parameters(args): Parameters<VpnArgs>) -> String {
        if args.name.len() > 128 || args.name.chars().any(char::is_control) {
            return "nome de VPN inválido".to_string();
        }
        let action = if args.enabled { "up" } else { "down" };
        common::run("nmcli", &["connection", action, "id", &args.name])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "system.update",
        description = "Tier: alterar. Enfileira atualização bootc; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn system_update(&self) -> String {
        common::run("forja", &["update"])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "system.rollback",
        description = "Tier: alterar. Agenda rollback bootc; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn system_rollback(&self) -> String {
        common::run("forja", &["rollback"])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "ollama.models",
        description = "Tier: livre. Lista modelos locais do Ollama.",
        annotations(read_only_hint = true)
    )]
    async fn ollama_models(&self) -> String {
        common::run("ollama", &["list"])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "ollama.load",
        description = "Tier: alterar. Carrega um modelo local; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn ollama_load(&self, Parameters(args): Parameters<ModelArgs>) -> String {
        if !common::valid_atom(&args.model, 128) {
            return "identificador de modelo inválido".to_string();
        }
        let body =
            serde_json::json!({"model":args.model,"prompt":"","stream":false,"keep_alive":"5m"})
                .to_string();
        common::run(
            "curl",
            &[
                "--silent",
                "--show-error",
                "--fail",
                "--max-time",
                "15",
                "-H",
                "Content-Type: application/json",
                "-d",
                &body,
                "http://127.0.0.1:11434/api/generate",
            ],
        )
        .await
        .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "ollama.unload",
        description = "Tier: alterar. Descarrega um modelo local; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn ollama_unload(&self, Parameters(args): Parameters<ModelArgs>) -> String {
        if !common::valid_atom(&args.model, 128) {
            return "identificador de modelo inválido".to_string();
        }
        let body =
            serde_json::json!({"model":args.model,"prompt":"","stream":false,"keep_alive":0})
                .to_string();
        common::run(
            "curl",
            &[
                "--silent",
                "--show-error",
                "--fail",
                "--max-time",
                "15",
                "-H",
                "Content-Type: application/json",
                "-d",
                &body,
                "http://127.0.0.1:11434/api/generate",
            ],
        )
        .await
        .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "packages.install",
        description = "Tier: alterar. Instala pacote RPM; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn packages_install(&self, Parameters(args): Parameters<PackageArgs>) -> String {
        if !common::valid_atom(&args.package, 64) {
            return "nome de pacote inválido".to_string();
        }
        common::run("rpm-ostree", &["install", "--idempotent", &args.package])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "power.profile",
        description = "Tier: alterar. Altera perfil de energia; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn power_profile(&self, Parameters(args): Parameters<PowerArgs>) -> String {
        if !["power-saver", "balanced", "performance"].contains(&args.profile.as_str()) {
            return "perfil de energia inválido".to_string();
        }
        common::run("powerprofilesctl", &["set", &args.profile])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "game_mode.toggle",
        description = "Tier: alterar. Ativa ou desativa Modo Jogo; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn game_mode_toggle(&self, Parameters(args): Parameters<ToggleArgs>) -> String {
        let action = if args.enabled { "start" } else { "stop" };
        common::run("systemctl", &["--user", action, "hero-game.target"])
            .await
            .unwrap_or_else(|error| error)
    }
}
