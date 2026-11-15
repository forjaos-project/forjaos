use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum Tier {
    #[serde(rename = "livre")]
    Free,
    #[serde(rename = "alterar")]
    Alter,
    #[serde(rename = "bloqueado")]
    Blocked,
}

impl Tier {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Free => "livre",
            Self::Alter => "alterar",
            Self::Blocked => "bloqueado",
        }
    }

    fn from_str(value: &str) -> Option<Self> {
        Some(match value {
            "livre" => Self::Free,
            "alterar" => Self::Alter,
            "bloqueado" => Self::Blocked,
            _ => return None,
        })
    }
}

#[derive(Clone)]
pub enum Action {
    GameMode(bool),
    Compose { up: bool, cwd: PathBuf },
    ComposeLogs(PathBuf),
    GitStatus(PathBuf),
    GpuStatus,
    SystemStatus,
    OpenProject(PathBuf),
    OpenUrl(String),
    Wifi(bool),
    Bluetooth(bool),
    Vpn { enabled: bool, name: String },
    RunTests(PathBuf),
    MemorySearch(String),
    Remember(String),
    Update,
    Rollback,
    RestartUserService(String),
}

pub struct Proposal {
    pub route: &'static str,
    pub context: String,
    pub tool: &'static str,
    pub tier: Tier,
    pub action: Action,
}

pub enum Classification {
    Conversation,
    Proposal(Proposal),
    Blocked {
        route: &'static str,
        tool: &'static str,
        message: String,
    },
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Manifest {
    tools: BTreeMap<String, Tier>,
}

#[derive(Clone, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct TierOverrides {
    #[serde(default)]
    tiers: BTreeMap<String, Tier>,
}

pub fn tool_tiers_json() -> Result<String, &'static str> {
    let manifest = manifest()?;
    let overrides = read_overrides()?;
    let mut output = BTreeMap::new();
    for (tool, minimum) in manifest.tools {
        let effective = overrides.tiers.get(&tool).copied().unwrap_or(minimum);
        if effective < minimum {
            return Err("policy_override_below_manifest");
        }
        output.insert(
            tool,
            serde_json::json!({"minimum":minimum.as_str(),"effective":effective.as_str()}),
        );
    }
    serde_json::to_string(&output).map_err(|_| "policy_unavailable")
}

pub fn set_tool_tier(tool: &str, tier: &str) -> Result<String, &'static str> {
    let manifest = manifest()?;
    let minimum = manifest
        .tools
        .get(tool)
        .copied()
        .ok_or("tool_not_in_manifest")?;
    let tier = Tier::from_str(tier).ok_or("invalid_tier")?;
    if tier < minimum {
        return Err("tier_cannot_be_lowered");
    }
    let mut overrides = read_overrides()?;
    if tier == minimum {
        overrides.tiers.remove(tool);
    } else {
        overrides.tiers.insert(tool.to_string(), tier);
    }
    validate_existing_routines(&manifest, &overrides)?;
    let path = override_path()?;
    let content = toml::to_string(&overrides).map_err(|_| "policy_unavailable")?;
    super::routes::write_private_atomic(&path, content.as_bytes())
        .map_err(|_| "policy_unavailable")?;
    tool_tiers_json()
}

pub fn validate_routine_steps(steps: &[String], maximum_tier: &str) -> Result<(), &'static str> {
    let manifest = manifest()?;
    let overrides = read_overrides()?;
    validate_routine_steps_with(steps, maximum_tier, &manifest, &overrides)
}

fn validate_routine_steps_with(
    steps: &[String],
    maximum_tier: &str,
    manifest: &Manifest,
    overrides: &TierOverrides,
) -> Result<(), &'static str> {
    if steps.is_empty() || steps.len() > 32 {
        return Err("invalid_routine_steps");
    }
    let maximum = Tier::from_str(maximum_tier).ok_or("invalid_routine_tier")?;
    if maximum == Tier::Blocked {
        return Err("blocked_tier_not_valid_for_routine");
    }
    for tool in steps {
        let tier = tier_with_overrides(tool, manifest, overrides)?;
        if tier == Tier::Blocked {
            return Err("routine_contains_blocked_tool");
        }
        if tier > maximum {
            return Err("routine_exceeds_maximum_tier");
        }
    }
    Ok(())
}

#[derive(Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct RoutineStore {
    #[serde(default)]
    routines: BTreeMap<String, Routine>,
}

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Routine {
    steps: Vec<String>,
    maximum_tier: String,
}

pub fn save_routine(
    id: &str,
    steps_json: &str,
    maximum_tier: &str,
) -> Result<String, &'static str> {
    if steps_json.len() > 4096 {
        return Err("invalid_routine_steps");
    }
    if id.is_empty()
        || id.len() > 64
        || !id
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || "-_".contains(character))
    {
        return Err("invalid_routine_id");
    }
    let steps: Vec<String> =
        serde_json::from_str(steps_json).map_err(|_| "invalid_routine_steps")?;
    validate_routine_steps(&steps, maximum_tier)?;
    let mut store = read_routines()?;
    store.routines.insert(
        id.to_string(),
        Routine {
            steps,
            maximum_tier: maximum_tier.to_string(),
        },
    );
    validate_existing_routines(&manifest()?, &read_overrides()?)?;
    let content = toml::to_string(&store).map_err(|_| "routine_store_unavailable")?;
    super::routes::write_private_atomic(&routine_path()?, content.as_bytes())
        .map_err(|_| "routine_store_unavailable")?;
    serde_json::to_string(&store.routines).map_err(|_| "routine_store_unavailable")
}

fn effective_tier(tool: &str, declared: Tier) -> Result<Tier, &'static str> {
    let manifest = manifest()?;
    let overrides = read_overrides()?;
    Ok(declared.max(tier_with_overrides(tool, &manifest, &overrides)?))
}

fn tier_with_overrides(
    tool: &str,
    manifest: &Manifest,
    overrides: &TierOverrides,
) -> Result<Tier, &'static str> {
    let minimum = manifest
        .tools
        .get(tool)
        .copied()
        .ok_or("tool_not_in_manifest")?;
    let override_tier = overrides.tiers.get(tool).copied().unwrap_or(minimum);
    if override_tier < minimum {
        return Err("policy_override_below_manifest");
    }
    Ok(minimum.max(override_tier))
}

fn validate_existing_routines(
    manifest: &Manifest,
    overrides: &TierOverrides,
) -> Result<(), &'static str> {
    let store = read_routines()?;
    for routine in store.routines.values() {
        validate_routine_steps_with(&routine.steps, &routine.maximum_tier, manifest, overrides)?;
    }
    Ok(())
}

fn manifest() -> Result<Manifest, &'static str> {
    toml::from_str(include_str!("../tool-policy.toml")).map_err(|_| "policy_manifest_invalid")
}

fn read_overrides() -> Result<TierOverrides, &'static str> {
    match fs::read_to_string(override_path()?) {
        Ok(source) => {
            let overrides: TierOverrides =
                toml::from_str(&source).map_err(|_| "policy_override_invalid")?;
            let manifest = manifest()?;
            for (tool, tier) in &overrides.tiers {
                let minimum = manifest
                    .tools
                    .get(tool)
                    .copied()
                    .ok_or("policy_override_invalid")?;
                if *tier < minimum {
                    return Err("policy_override_below_manifest");
                }
            }
            Ok(overrides)
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(TierOverrides::default()),
        Err(_) => Err("policy_unavailable"),
    }
}

fn read_routines() -> Result<RoutineStore, &'static str> {
    match fs::read_to_string(routine_path()?) {
        Ok(source) => toml::from_str(&source).map_err(|_| "routine_store_invalid"),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(RoutineStore::default()),
        Err(_) => Err("routine_store_unavailable"),
    }
}

fn config_dir() -> Result<PathBuf, &'static str> {
    let home = std::env::var_os("HOME").ok_or("home_unavailable")?;
    Ok(PathBuf::from(home).join(".config/hero"))
}

fn override_path() -> Result<PathBuf, &'static str> {
    Ok(config_dir()?.join("policy.toml"))
}

fn routine_path() -> Result<PathBuf, &'static str> {
    Ok(config_dir()?.join("routines.toml"))
}

pub fn classify(query: &str, cwd: &str) -> Classification {
    let text = query.trim().to_lowercase();
    let cwd = PathBuf::from(cwd);
    let context = cwd
        .canonicalize()
        .map(|path| path.display().to_string())
        .unwrap_or_else(|_| "diretório atual indisponível".into());

    let proposal = if starts_with_any(
        &text,
        &["ative modo jogo", "ligue modo jogo", "ligue o modo jogo"],
    ) {
        Some((
            "sistema",
            "game_mode.toggle",
            Tier::Alter,
            Action::GameMode(true),
        ))
    } else if [
        "abra projeto",
        "abra o projeto",
        "abra meu projeto",
        "abra projeto atual",
        "abra o projeto atual",
        "abra meu projeto atual",
    ]
    .contains(&text.as_str())
    {
        Some((
            "código",
            "project.open",
            Tier::Free,
            Action::OpenProject(cwd.clone()),
        ))
    } else if starts_with_any(
        &text,
        &["mostre logs do compose", "mostre os logs do compose"],
    ) {
        Some((
            "código",
            "compose.logs",
            Tier::Free,
            Action::ComposeLogs(cwd.clone()),
        ))
    } else if starts_with_any(
        &text,
        &["rode os testes", "execute os testes", "rode testes"],
    ) {
        Some((
            "código",
            "project.tests",
            Tier::Alter,
            Action::RunTests(cwd.clone()),
        ))
    } else if starts_with_any(
        &text,
        &[
            "mostre estado do sistema",
            "mostre o estado do sistema",
            "diagnóstico do sistema",
        ],
    ) {
        Some((
            "saúde-do-sistema",
            "system.status",
            Tier::Free,
            Action::SystemStatus,
        ))
    } else if starts_with_any(
        &text,
        &["ligue wifi", "ligue o wifi", "ative wifi", "ative o wifi"],
    ) {
        Some(("sistema", "network.wifi", Tier::Alter, Action::Wifi(true)))
    } else if starts_with_any(
        &text,
        &[
            "desligue wifi",
            "desligue o wifi",
            "desative wifi",
            "desative o wifi",
        ],
    ) {
        Some(("sistema", "network.wifi", Tier::Alter, Action::Wifi(false)))
    } else if starts_with_any(
        &text,
        &[
            "ligue bluetooth",
            "ligue o bluetooth",
            "ative bluetooth",
            "ative o bluetooth",
        ],
    ) {
        Some((
            "sistema",
            "network.bluetooth",
            Tier::Alter,
            Action::Bluetooth(true),
        ))
    } else if starts_with_any(
        &text,
        &[
            "desligue bluetooth",
            "desligue o bluetooth",
            "desative bluetooth",
            "desative o bluetooth",
        ],
    ) {
        Some((
            "sistema",
            "network.bluetooth",
            Tier::Alter,
            Action::Bluetooth(false),
        ))
    } else if let Some(name) = text
        .strip_prefix("ligue vpn ")
        .or_else(|| text.strip_prefix("ative vpn "))
    {
        let name = name.trim();
        if valid_connection_name(name) {
            Some((
                "sistema",
                "network.vpn",
                Tier::Alter,
                Action::Vpn {
                    enabled: true,
                    name: name.to_string(),
                },
            ))
        } else {
            None
        }
    } else if let Some(name) = text
        .strip_prefix("desligue vpn ")
        .or_else(|| text.strip_prefix("desative vpn "))
    {
        let name = name.trim();
        if valid_connection_name(name) {
            Some((
                "sistema",
                "network.vpn",
                Tier::Alter,
                Action::Vpn {
                    enabled: false,
                    name: name.to_string(),
                },
            ))
        } else {
            None
        }
    } else if starts_with_any(
        &text,
        &[
            "desative modo jogo",
            "desligue modo jogo",
            "desligue o modo jogo",
        ],
    ) {
        Some((
            "sistema",
            "game_mode.toggle",
            Tier::Alter,
            Action::GameMode(false),
        ))
    } else if starts_with_any(
        &text,
        &[
            "suba compose",
            "suba o compose",
            "inicie compose",
            "inicie o compose",
        ],
    ) {
        Some((
            "sistema",
            "compose.up",
            Tier::Alter,
            Action::Compose {
                up: true,
                cwd: cwd.clone(),
            },
        ))
    } else if starts_with_any(
        &text,
        &[
            "derrube compose",
            "derrube o compose",
            "pare compose",
            "pare o compose",
        ],
    ) {
        Some((
            "sistema",
            "compose.down",
            Tier::Alter,
            Action::Compose {
                up: false,
                cwd: cwd.clone(),
            },
        ))
    } else if starts_with_any(
        &text,
        &[
            "git status",
            "mostre o status do git",
            "mostre status do git",
        ],
    ) {
        Some((
            "código",
            "git.status",
            Tier::Free,
            Action::GitStatus(cwd.clone()),
        ))
    } else if starts_with_any(
        &text,
        &["mostre gpu", "status da gpu", "mostre o status da gpu"],
    ) {
        Some((
            "saúde-do-sistema",
            "gpu.status",
            Tier::Free,
            Action::GpuStatus,
        ))
    } else if text.starts_with("abra ") {
        let rest = query.trim().get(5..).unwrap_or("").trim();
        let normalized_url = rest.to_ascii_lowercase();
        if (normalized_url.starts_with("https://") || normalized_url.starts_with("http://"))
            && !rest
                .chars()
                .any(|character| character.is_whitespace() || character.is_control())
            && rest
                .split_once("://")
                .is_some_and(|(_, host)| !host.is_empty())
        {
            Some((
                "criação",
                "desktop.open_url",
                Tier::Free,
                Action::OpenUrl(rest.to_string()),
            ))
        } else {
            None
        }
    } else if let Some(rest) = text.strip_prefix("busque na memória ") {
        if rest.trim().is_empty() {
            None
        } else {
            Some((
                "memória",
                "memory.search",
                Tier::Free,
                Action::MemorySearch(rest.to_string()),
            ))
        }
    } else if let Some(rest) = text.strip_prefix("crie uma nota ") {
        Some((
            "memória",
            "memory.remember",
            Tier::Free,
            Action::Remember(rest.to_string()),
        ))
    } else if starts_with_any(&text, &["atualize o sistema", "atualize sistema"]) {
        Some(("sistema", "system.update", Tier::Alter, Action::Update))
    } else if starts_with_any(
        &text,
        &[
            "reverta a atualização",
            "volte a atualização",
            "faça rollback",
        ],
    ) {
        Some(("sistema", "system.rollback", Tier::Alter, Action::Rollback))
    } else if let Some(service) = text
        .strip_prefix("reinicie serviço ")
        .or_else(|| text.strip_prefix("reinicie o serviço "))
    {
        let service = service.trim();
        if valid_unit_name(service) {
            Some((
                "sistema",
                "services.restart",
                Tier::Alter,
                Action::RestartUserService(service.to_string()),
            ))
        } else {
            None
        }
    } else {
        None
    };

    if let Some((route, tool, tier, action)) = proposal {
        let effective =
            match effective_tier(tool, tier) {
                Ok(effective) => effective,
                Err(_) => return Classification::Blocked {
                    route,
                    tool: "policy.configuration",
                    message:
                        "A configuração da Policy Engine está inválida. Nenhuma ação foi executada."
                            .into(),
                },
            };
        if effective == Tier::Blocked {
            return Classification::Blocked {
                route,
                tool,
                message: "Esta ferramenta está bloqueada pela política local. Nenhuma ação foi executada.".into(),
            };
        }
        return Classification::Proposal(Proposal {
            route,
            context,
            tool,
            tier: effective,
            action,
        });
    }

    let blocked_tool = if starts_with_any(&text, &["execute dd ", "rode dd "]) {
        Some("disk.raw_write")
    } else if text.contains("firewall") {
        Some("system.firewall")
    } else if text.contains("/etc") {
        Some("system.etc")
    } else {
        None
    };
    if starts_with_any(
        &text,
        &[
            "apague ",
            "remova ",
            "rode rm ",
            "execute rm ",
            "execute dd ",
            "rode dd ",
            "mude o firewall",
            "mude firewall",
            "altere o firewall",
            "altere firewall",
            "configure o firewall",
            "configure firewall",
            "ative o firewall",
            "ative firewall",
            "desative o firewall",
            "desative firewall",
            "ligue o firewall",
            "ligue firewall",
            "desligue o firewall",
            "desligue firewall",
            "altere /etc",
            "mude /etc",
            "edite /etc",
            "modifique /etc",
            "apague /etc",
        ],
    ) {
        return Classification::Blocked {
            route: "sistema",
            tool: blocked_tool.unwrap_or("filesystem.delete"),
            message:
                "Esta ação está bloqueada pelo manifesto de segurança. Nenhum dado foi alterado."
                    .into(),
        };
    }

    if starts_with_any(
        &text,
        &[
            "instale ",
            "execute ",
            "rode ",
            "atualize ",
            "reinicie ",
            "ligue ",
            "desligue ",
            "abra ",
            "crie ",
            "suba ",
            "derrube ",
        ],
    ) {
        return Classification::Blocked {
            route: "sistema",
            tool: "action.unsupported",
            message: "Ainda não há uma ferramenta permitida para esta solicitação. Nenhuma ação foi executada.".into(),
        };
    }

    Classification::Conversation
}

fn starts_with_any(text: &str, prefixes: &[&str]) -> bool {
    prefixes.iter().any(|prefix| text.starts_with(prefix))
}

fn valid_unit_name(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value.chars().all(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '@' | '_' | '-' | '.' | ':')
        })
}

fn valid_connection_name(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value.chars().all(|character| !character.is_control())
}
