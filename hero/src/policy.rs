use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

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
    Compose {
        up: bool,
        cwd: PathBuf,
    },
    ComposeLogs(PathBuf),
    GitStatus(PathBuf),
    GpuStatus,
    SystemStatus,
    OpenProject(PathBuf),
    OpenUrl(String),
    Wifi(bool),
    Bluetooth(bool),
    Vpn {
        enabled: bool,
        name: String,
    },
    RunTests(PathBuf),
    MemorySearch(String),
    Remember(String),
    Update,
    Rollback,
    RestartUserService(String),
    ServiceList,
    ServiceStatus(String),
    OpenApp(String),
    CodeDelegate {
        agent: String,
        cwd: PathBuf,
        task: String,
    },
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
            "tests.run",
            Tier::Alter,
            Action::RunTests(cwd.clone()),
        ))
    } else if starts_with_any(
        &text,
        &[
            "mostre estado do sistema",
            "mostre o estado do sistema",
            "diagnóstico do sistema",
            "diagnostico do sistema",
            "saúde do sistema",
            "saude do sistema",
            "saúde do computador",
            "saude do computador",
            "estado atual do sistema",
            "status da cpu",
            "status da memória",
            "status da memoria",
            "temperatura da gpu",
            "temperatura da cpu",
            "qual a temperatura",
            "qual é a temperatura",
            "qual e a temperatura",
            "mostre a temperatura",
            "uso da cpu",
            "uso de cpu",
            "uso de ram",
            "uso de memória ram",
            "uso de memoria ram",
            "estado da rede",
            "status da rede",
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
        &[
            "liste os serviços",
            "liste serviços",
            "mostre serviços",
            "mostre os serviços",
        ],
    ) {
        Some(("sistema", "services.list", Tier::Free, Action::ServiceList))
    } else if let Some(service) = text
        .strip_prefix("status do serviço ")
        .or_else(|| text.strip_prefix("status do servico "))
        .or_else(|| text.strip_prefix("mostre o serviço "))
        .or_else(|| text.strip_prefix("mostre o servico "))
    {
        let service = service.trim();
        if valid_unit_name(service) {
            Some((
                "sistema",
                "services.status",
                Tier::Free,
                Action::ServiceStatus(service.to_string()),
            ))
        } else {
            None
        }
    } else if starts_with_any(
        &text,
        &["ligue wifi", "ligue o wifi", "ative wifi", "ative o wifi"],
    ) {
        Some(("sistema", "wifi.toggle", Tier::Alter, Action::Wifi(true)))
    } else if starts_with_any(
        &text,
        &[
            "desligue wifi",
            "desligue o wifi",
            "desative wifi",
            "desative o wifi",
        ],
    ) {
        Some(("sistema", "wifi.toggle", Tier::Alter, Action::Wifi(false)))
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
            "bluetooth.toggle",
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
            "bluetooth.toggle",
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
                "vpn.toggle",
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
                "vpn.toggle",
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
    } else if let Some(app) = text
        .strip_prefix("abra aplicativo ")
        .or_else(|| text.strip_prefix("abra o aplicativo "))
    {
        let app = app.trim();
        if valid_desktop_id(app) {
            Some((
                "sistema",
                "apps.launch",
                Tier::Alter,
                Action::OpenApp(app.to_string()),
            ))
        } else {
            None
        }
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
                "url.open",
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
    } else if let Some(agent) = code_agent(&text) {
        if !cwd.is_dir() || query.trim().is_empty() || query.chars().count() > 4000 {
            None
        } else {
            Some((
                "código",
                "code.delegate",
                Tier::Alter,
                Action::CodeDelegate {
                    agent: agent.to_string(),
                    cwd: cwd.clone(),
                    task: query.trim().to_string(),
                },
            ))
        }
    } else {
        None
    };

    if let Some((route, tool, tier, action)) = proposal {
        let project_scoped = matches!(
            &action,
            Action::CodeDelegate { .. }
                | Action::OpenProject(_)
                | Action::Compose { .. }
                | Action::ComposeLogs(_)
                | Action::GitStatus(_)
                | Action::RunTests(_)
        );
        if project_scoped && !known_project_path(&cwd) {
            return Classification::Blocked {
                route,
                tool,
                message: "Não identifiquei um projeto permitido. Informe o nome de um projeto Git cadastrado; nenhuma ação foi executada.".into(),
            };
        }
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

fn code_agent(text: &str) -> Option<&'static str> {
    let asks_to_delegate = [
        "peça", "peca", "pede", "mande", "manda", "delegue", "delegar",
    ]
    .iter()
    .any(|word| text.contains(word));
    if !asks_to_delegate {
        return None;
    }
    if text.contains("claude") {
        Some("claude-code")
    } else if text.contains("codex") {
        Some("codex")
    } else if text.contains("hermes") {
        Some("hermes")
    } else {
        None
    }
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

fn valid_desktop_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 255
        && value.chars().all(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-')
        })
}

fn valid_connection_name(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value.chars().all(|character| !character.is_control())
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ProjectConfig {
    #[serde(default)]
    projects: Vec<ProjectEntry>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ProjectEntry {
    name: String,
    path: PathBuf,
}

pub fn resolve_project_context(
    cwd: &str,
    query: &str,
    window_title: Option<&str>,
) -> Option<PathBuf> {
    let projects = known_projects();
    if projects.is_empty() {
        return None;
    }
    if let Ok(current) = Path::new(cwd).canonicalize() {
        if projects.values().any(|path| path == &current) {
            return Some(current);
        }
    }
    let searchable = format!(
        "{} {}",
        query.to_lowercase(),
        window_title.unwrap_or_default().to_lowercase()
    );
    choose_project(&projects, &searchable)
}

fn choose_project(projects: &BTreeMap<String, PathBuf>, searchable: &str) -> Option<PathBuf> {
    let tokens = searchable
        .split(|character: char| !(character.is_ascii_alphanumeric() || "._-".contains(character)))
        .collect::<Vec<_>>();
    let matches = projects
        .iter()
        .filter(|(name, path)| {
            let directory = path
                .file_name()
                .and_then(|value| value.to_str())
                .unwrap_or_default()
                .to_lowercase();
            let name = name.to_lowercase();
            tokens.iter().any(|token| *token == name)
                || (!directory.is_empty() && tokens.iter().any(|token| *token == directory))
        })
        .collect::<Vec<_>>();
    if let Some(longest) = matches.iter().map(|(name, _)| name.len()).max() {
        let mut best = matches
            .into_iter()
            .filter(|(name, _)| name.len() == longest)
            .map(|(_, path)| path.clone());
        let path = best.next()?;
        return best.next().is_none().then_some(path);
    }
    if projects.len() == 1 {
        projects.values().next().cloned()
    } else {
        None
    }
}

fn known_projects() -> BTreeMap<String, PathBuf> {
    let Some(home) = std::env::var_os("HOME").map(PathBuf::from) else {
        return BTreeMap::new();
    };
    let mut projects = BTreeMap::new();
    let config_path = home.join(".config/hero/projects.toml");
    if let Ok(source) = fs::read_to_string(config_path) {
        if let Ok(config) = toml::from_str::<ProjectConfig>(&source) {
            for project in config.projects {
                if !valid_project_name(&project.name) {
                    continue;
                }
                let path = if project.path.is_absolute() {
                    project.path
                } else {
                    home.join(project.path)
                };
                if let Some(path) = canonical_git_project(&path) {
                    projects.insert(project.name, path);
                }
            }
        }
    }
    for name in ["proj", "dev", "code"] {
        let root = home.join(name);
        let Ok(root) = root.canonicalize() else {
            continue;
        };
        let Ok(entries) = fs::read_dir(&root) else {
            continue;
        };
        for entry in entries.flatten() {
            let candidate = entry.path();
            add_detected_project(&mut projects, &candidate, &root);
            if let Ok(children) = fs::read_dir(&candidate) {
                for child in children.flatten() {
                    add_detected_project(&mut projects, &child.path(), &root);
                }
            }
        }
    }
    projects
}

fn known_project_path(path: &Path) -> bool {
    path.canonicalize()
        .ok()
        .is_some_and(|canonical| known_projects().values().any(|known| known == &canonical))
}

fn add_detected_project(projects: &mut BTreeMap<String, PathBuf>, path: &Path, root: &Path) {
    let Some(canonical) = canonical_git_project(path) else {
        return;
    };
    if !canonical.starts_with(root) {
        return;
    }
    let Some(name) = canonical.file_name().and_then(|value| value.to_str()) else {
        return;
    };
    if valid_project_name(name) {
        projects.entry(name.to_string()).or_insert(canonical);
    }
}

fn canonical_git_project(path: &Path) -> Option<PathBuf> {
    let canonical = path.canonicalize().ok()?;
    (canonical.is_dir() && canonical.join(".git").exists()).then_some(canonical)
}

fn valid_project_name(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 64
        && value.as_bytes()[0].is_ascii_alphanumeric()
        && value
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || "@_.:+-".contains(character))
}

#[cfg(test)]
mod tests {
    use super::{
        choose_project, classify, code_agent, manifest, save_routine, set_tool_tier,
        valid_desktop_id, valid_unit_name, validate_routine_steps, Action, Classification, Tier,
    };
    use crate::test_support::TestHome;
    use std::collections::BTreeMap;
    use std::path::PathBuf;

    #[test]
    fn recognizes_only_explicit_supported_code_agents() {
        assert_eq!(
            code_agent("peça para o claude rodar os testes"),
            Some("claude-code")
        );
        assert_eq!(code_agent("pede pro codex revisar o diff"), Some("codex"));
        assert_eq!(code_agent("mande o hermes explicar o erro"), Some("hermes"));
        assert_eq!(code_agent("abra o claude code"), None);
        assert_eq!(code_agent("peça para um agente desconhecido"), None);
    }

    #[test]
    fn validates_service_units_and_desktop_ids_as_atoms() {
        assert!(valid_unit_name("podman.service"));
        assert!(!valid_unit_name("podman.service; reboot"));
        assert!(valid_desktop_id("org.kde.konsole"));
        assert!(!valid_desktop_id("org.kde.konsole; rm -rf ~"));
    }

    #[test]
    fn memory_policy_declares_routes_and_mutation_tiers() {
        let tools = manifest().expect("manifesto de política válido").tools;
        assert_eq!(tools.get("memory.search"), Some(&Tier::Free));
        assert_eq!(tools.get("memory.timeline"), Some(&Tier::Free));
        assert_eq!(tools.get("memory.related"), Some(&Tier::Free));
        assert_eq!(tools.get("memory.remember"), Some(&Tier::Free));
        assert_eq!(tools.get("memory.forget"), Some(&Tier::Alter));
    }

    #[test]
    fn code_delegation_reaches_project_guard_from_a_normal_request() {
        match classify("peça ao codex revisar o diff", ".") {
            Classification::Blocked { tool, .. } => assert_eq!(tool, "code.delegate"),
            Classification::Proposal(_) => panic!("projeto não permitido foi aceito"),
            Classification::Conversation => panic!("pedido de delegação não foi classificado"),
        }
    }

    #[test]
    fn classifies_memory_health_service_app_and_project_code_routes() {
        let home = TestHome::new();
        let project = home.register_project("fixture");
        let cwd = project.to_string_lossy();

        for (query, tool, tier) in [
            ("busque na memória decisões", "memory.search", Tier::Free),
            ("crie uma nota decisão", "memory.remember", Tier::Free),
            ("mostre o estado do sistema", "system.status", Tier::Free),
            ("abra projeto atual", "project.open", Tier::Alter),
            ("mostre logs do compose", "compose.logs", Tier::Free),
            ("rode os testes", "tests.run", Tier::Alter),
            ("suba o compose", "compose.up", Tier::Alter),
            ("derrube o compose", "compose.down", Tier::Alter),
            ("git status", "git.status", Tier::Free),
            ("mostre gpu", "gpu.status", Tier::Free),
            ("abra https://forjaos.dev", "url.open", Tier::Alter),
            ("ligue wifi", "wifi.toggle", Tier::Alter),
            ("desligue bluetooth", "bluetooth.toggle", Tier::Alter),
            ("ligue vpn wireguard", "vpn.toggle", Tier::Alter),
            ("ative modo jogo", "game_mode.toggle", Tier::Alter),
            ("atualize sistema", "system.update", Tier::Alter),
            ("faça rollback", "system.rollback", Tier::Alter),
            (
                "status do serviço podman.service",
                "services.status",
                Tier::Free,
            ),
            (
                "reinicie serviço podman.service",
                "services.restart",
                Tier::Alter,
            ),
            (
                "abra aplicativo org.kde.konsole",
                "apps.launch",
                Tier::Alter,
            ),
        ] {
            match classify(query, &cwd) {
                Classification::Proposal(proposal) => {
                    assert_eq!(proposal.tool, tool, "consulta: {query}");
                    assert_eq!(proposal.tier, tier, "consulta: {query}");
                }
                Classification::Blocked { tool, message, .. } => {
                    panic!("{query} bloqueado como {tool}: {message}")
                }
                Classification::Conversation => panic!("{query} não foi classificado"),
            }
        }

        match classify("peça ao codex revisar fixture", &cwd) {
            Classification::Proposal(proposal) => {
                assert_eq!(proposal.tool, "code.delegate");
                assert_eq!(proposal.tier, Tier::Alter);
                assert!(matches!(proposal.action, Action::CodeDelegate { .. }));
            }
            Classification::Blocked { tool, message, .. } => {
                panic!("projeto cadastrado bloqueado como {tool}: {message}")
            }
            Classification::Conversation => panic!("delegação não classificada"),
        }

        assert!(matches!(
            classify("mude o firewall", &cwd),
            Classification::Blocked {
                tool: "system.firewall",
                ..
            }
        ));
        assert!(matches!(
            classify("rode rm -rf /tmp", &cwd),
            Classification::Blocked {
                tool: "filesystem.delete",
                ..
            }
        ));
    }

    #[test]
    fn policy_overrides_can_raise_but_never_lower_declared_tiers() {
        let _home = TestHome::new();
        assert_eq!(
            set_tool_tier("memory.forget", "livre"),
            Err("tier_cannot_be_lowered")
        );
        let result = set_tool_tier("memory.search", "alterar").expect("raise memory search tier");
        let tiers: serde_json::Value = serde_json::from_str(&result).expect("tiers JSON");
        assert_eq!(tiers["memory.search"]["minimum"], "livre");
        assert_eq!(tiers["memory.search"]["effective"], "alterar");
        assert_eq!(
            set_tool_tier("unknown.tool", "alterar"),
            Err("tool_not_in_manifest")
        );
        assert_eq!(set_tool_tier("system.status", "wrong"), Err("invalid_tier"));
    }

    #[test]
    fn routines_enforce_size_tier_and_blocked_tool_limits() {
        let _home = TestHome::new();
        assert_eq!(
            validate_routine_steps(&[], "livre"),
            Err("invalid_routine_steps")
        );
        assert_eq!(
            validate_routine_steps(&["services.restart".into()], "livre"),
            Err("routine_exceeds_maximum_tier")
        );
        assert_eq!(
            validate_routine_steps(&["filesystem.delete".into()], "alterar"),
            Err("routine_contains_blocked_tool")
        );
        assert_eq!(
            validate_routine_steps(&["memory.search".into()], "bloqueado"),
            Err("blocked_tier_not_valid_for_routine")
        );
        assert_eq!(
            validate_routine_steps(&["memory.search".into()], "livre"),
            Ok(())
        );
        let saved: serde_json::Value = serde_json::from_str(
            &save_routine("daily", r#"["memory.search"]"#, "livre").expect("save valid routine"),
        )
        .expect("routine JSON");
        assert_eq!(saved["daily"]["steps"][0], "memory.search");
        assert_eq!(saved["daily"]["maximum_tier"], "livre");
        assert_eq!(
            save_routine("invalid id", r#"["memory.search"]"#, "livre"),
            Err("invalid_routine_id")
        );
        assert_eq!(
            save_routine(
                "long",
                &format!("[{}]", "\"memory.search\",".repeat(500)),
                "livre"
            ),
            Err("invalid_routine_steps")
        );
    }

    #[test]
    fn resolves_only_an_unambiguous_registered_project() {
        let projects = BTreeMap::from([
            ("game-api".into(), PathBuf::from("/home/dev/game-api")),
            ("forjaos".into(), PathBuf::from("/home/dev/forjaos")),
        ]);
        assert_eq!(
            choose_project(&projects, "peça ao codex testar game-api"),
            Some(PathBuf::from("/home/dev/game-api"))
        );
        assert_eq!(
            choose_project(&projects, "peça ao codex rodar testes"),
            None
        );
        assert_eq!(
            choose_project(
                &BTreeMap::from([("game-api".into(), PathBuf::from("/home/dev/game-api"))]),
                "peça ao codex rodar testes"
            ),
            Some(PathBuf::from("/home/dev/game-api"))
        );
    }
}
