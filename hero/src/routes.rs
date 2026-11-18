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

#[cfg(test)]
mod tests {
    use super::{validate_choice, validate_route, write_private_atomic, Provider, RouteProvider};
    use crate::test_support::TestHome;
    use std::fs;
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn unique_path(name: &str) -> PathBuf {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock after epoch")
            .as_nanos();
        std::env::temp_dir().join(format!("hero-{name}-{}-{stamp}", std::process::id()))
    }

    #[test]
    fn providers_have_stable_config_names_and_cloud_flags() {
        for (name, provider, cloud) in [
            ("ollama", Provider::Ollama, false),
            ("anthropic", Provider::Anthropic, true),
            ("openai", Provider::OpenAi, true),
            ("openrouter", Provider::OpenRouter, true),
            ("nous", Provider::Nous, true),
        ] {
            assert_eq!(Provider::parse(name), Some(provider));
            assert_eq!(provider.as_str(), name);
            assert_eq!(provider.is_cloud(), cloud);
        }
        assert_eq!(Provider::parse("unknown"), None);
    }

    #[test]
    fn providers_are_restricted_by_route_and_cloud_model() {
        assert_eq!(validate_route("sistema"), Ok(()));
        assert_eq!(validate_route("unsupported"), Err("route_not_supported"));
        assert_eq!(
            validate_choice(
                "conversa-de-voz",
                &RouteProvider {
                    provider: Provider::OpenAi,
                    model: Some("gpt-test".into()),
                }
            ),
            Err("cloud_provider_forbidden_on_local_route")
        );
        assert_eq!(
            validate_choice(
                "pesquisa",
                &RouteProvider {
                    provider: Provider::Anthropic,
                    model: None,
                }
            ),
            Err("provider_model_required")
        );
        assert_eq!(
            validate_choice(
                "pesquisa",
                &RouteProvider {
                    provider: Provider::OpenRouter,
                    model: Some("bad model".into()),
                }
            ),
            Err("invalid_model_id")
        );
        assert_eq!(
            validate_choice("sistema", &RouteProvider::default()),
            Ok(())
        );
    }

    #[test]
    fn private_atomic_writer_creates_and_replaces_a_file() {
        let dir = unique_path("atomic");
        let path = dir.join("config.toml");
        write_private_atomic(&path, b"first=true").expect("write initial config");
        write_private_atomic(&path, b"first=false").expect("replace config");
        assert_eq!(fs::read(&path).expect("read config"), b"first=false");
        fs::remove_dir_all(dir).expect("remove test directory");
    }

    #[test]
    fn route_configuration_defaults_and_updates_are_persisted() {
        let _home = TestHome::new();
        assert_eq!(
            super::provider_for("pesquisa").unwrap().provider,
            Provider::Ollama
        );
        let updated = super::set_provider("pesquisa", "openai", "gpt-test")
            .expect("set cloud provider on research route");
        let routes: serde_json::Value = serde_json::from_str(&updated).expect("routes JSON");
        assert_eq!(routes["pesquisa"]["provider"], "openai");
        assert_eq!(routes["pesquisa"]["model"], "gpt-test");
        assert_eq!(
            super::provider_for("pesquisa").unwrap().provider,
            Provider::OpenAi
        );
        assert_eq!(
            super::set_provider("sistema", "openai", "gpt-test"),
            Err("cloud_provider_forbidden_on_local_route")
        );
        assert_eq!(
            super::set_provider("pesquisa", "openai", "bad model"),
            Err("invalid_model_id")
        );
        assert!(super::list_json().is_ok());
    }

    #[test]
    fn malformed_route_configuration_is_rejected() {
        let home = TestHome::new();
        let config_dir = home.root().join(".config/hero");
        fs::create_dir_all(&config_dir).expect("create route config directory");
        fs::write(config_dir.join("routes.toml"), "invalid = [\n")
            .expect("write invalid route config");
        assert_eq!(
            super::provider_for("pesquisa").unwrap_err(),
            "route_config_invalid"
        );
        assert_eq!(super::list_json(), Err("route_config_invalid"));
    }
}
