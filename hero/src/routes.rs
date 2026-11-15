use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::path::{Path, PathBuf};

const ROUTES: &[&str] = &[
    "conversa-de-voz",
    "sistema",
    "pesquisa",
    "criação",
    "código",
    "saúde-do-sistema",
    "memória",
];

#[derive(Clone, Copy, Debug, Default, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Provider {
    #[default]
    Ollama,
    Anthropic,
    #[serde(rename = "openai")]
    OpenAi,
    #[serde(rename = "openrouter")]
    OpenRouter,
    Nous,
}

impl Provider {
    pub fn parse(value: &str) -> Option<Self> {
        Some(match value {
            "ollama" => Self::Ollama,
            "anthropic" => Self::Anthropic,
            "openai" => Self::OpenAi,
            "openrouter" => Self::OpenRouter,
            "nous" => Self::Nous,
            _ => return None,
        })
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Ollama => "ollama",
            Self::Anthropic => "anthropic",
            Self::OpenAi => "openai",
            Self::OpenRouter => "openrouter",
            Self::Nous => "nous",
        }
    }

    pub fn is_cloud(self) -> bool {
        self != Self::Ollama
    }
}

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RouteProvider {
    #[serde(default)]
    pub provider: Provider,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub model: Option<String>,
}

#[derive(Debug, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct RouteConfig {
    #[serde(default)]
    routes: BTreeMap<String, RouteProvider>,
}

pub fn provider_for(route: &str) -> Result<RouteProvider, &'static str> {
    validate_route(route)?;
    let config = read_config()?;
    let choice = config.routes.get(route).cloned().unwrap_or_default();
    validate_choice(route, &choice)?;
    Ok(choice)
}

pub fn list_json() -> Result<String, &'static str> {
    let config = read_config()?;
    let mut visible = BTreeMap::new();
    for route in ROUTES {
        let choice = config.routes.get(*route).cloned().unwrap_or_default();
        validate_choice(route, &choice)?;
        visible.insert(*route, choice);
    }
    serde_json::to_string(&visible).map_err(|_| "route_config_unavailable")
}

pub fn set_provider(route: &str, provider: &str, model: &str) -> Result<String, &'static str> {
    validate_route(route)?;
    let provider = Provider::parse(provider).ok_or("provider_not_supported")?;
    let model = if model.trim().is_empty() {
        None
    } else {
        let model = model.trim();
        if model.len() > 128
            || !model
                .chars()
                .all(|character| character.is_ascii_alphanumeric() || "-_.:/".contains(character))
        {
            return Err("invalid_model_id");
        }
        Some(model.to_string())
    };
    let choice = RouteProvider { provider, model };
    validate_choice(route, &choice)?;

    let mut config = read_config()?;
    config.routes.insert(route.to_string(), choice);
    let serialized = toml::to_string(&config).map_err(|_| "route_config_unavailable")?;
    write_private_atomic(&config_path()?, serialized.as_bytes())
        .map_err(|_| "route_config_unavailable")?;
    list_json()
}

fn validate_route(route: &str) -> Result<(), &'static str> {
    if ROUTES.contains(&route) {
        Ok(())
    } else {
        Err("route_not_supported")
    }
}

fn validate_choice(route: &str, choice: &RouteProvider) -> Result<(), &'static str> {
    if matches!(route, "conversa-de-voz" | "sistema") && choice.provider.is_cloud() {
        return Err("cloud_provider_forbidden_on_local_route");
    }
    if choice.provider.is_cloud() && choice.model.as_deref().is_none_or(str::is_empty) {
        return Err("provider_model_required");
    }
    if choice.model.as_deref().is_some_and(|model| {
        model.len() > 128
            || !model
                .chars()
                .all(|character| character.is_ascii_alphanumeric() || "-_.:/".contains(character))
    }) {
        return Err("invalid_model_id");
    }
    Ok(())
}

fn read_config() -> Result<RouteConfig, &'static str> {
    let path = config_path()?;
    let source = match fs::read_to_string(&path) {
        Ok(source) => source,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(RouteConfig::default()),
        Err(_) => return Err("route_config_unavailable"),
    };
    toml::from_str(&source).map_err(|_| "route_config_invalid")
}

fn config_path() -> Result<PathBuf, &'static str> {
    let home = std::env::var_os("HOME").ok_or("home_unavailable")?;
    Ok(PathBuf::from(home).join(".config/hero/routes.toml"))
}

pub fn write_private_atomic(path: &Path, content: &[u8]) -> io::Result<()> {
    let parent = path
        .parent()
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "invalid config path"))?;
    fs::create_dir_all(parent)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(parent, fs::Permissions::from_mode(0o700))?;
        if let Ok(metadata) = fs::symlink_metadata(path) {
            if metadata.file_type().is_symlink() || !metadata.file_type().is_file() {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidInput,
                    "unsafe config path",
                ));
            }
        }
    }

    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "invalid config filename"))?;
    let temp = path.with_file_name(format!(".{file_name}.{}.tmp", std::process::id()));
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options.open(&temp)?;
    file.write_all(content)?;
    file.sync_all()?;
    drop(file);
    fs::rename(&temp, path)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(path, fs::Permissions::from_mode(0o600))?;
    }
    Ok(())
}
