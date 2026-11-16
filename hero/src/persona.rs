use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Persona {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub instructions: Option<String>,
}

pub fn load() -> Persona {
    let Ok(path) = config_path() else {
        return Persona::default();
    };
    let Ok(source) = fs::read_to_string(path) else {
        return Persona::default();
    };
    toml::from_str(&source).unwrap_or_default()
}

pub fn set_instructions(instructions: &str) -> Result<String, &'static str> {
    if instructions.len() > 4000
        || instructions
            .chars()
            .any(|character| character.is_control() && !matches!(character, '\n' | '\t'))
    {
        return Err("invalid_persona_instructions");
    }
    let mut persona = load();
    persona.instructions = if instructions.trim().is_empty() {
        None
    } else {
        Some(instructions.trim().to_string())
    };
    let serialized = toml::to_string(&persona).map_err(|_| "persona_unavailable")?;
    let path = config_path()?;
    super::routes::write_private_atomic(&path, serialized.as_bytes())
        .map_err(|_| "persona_unavailable")?;
    serde_json::to_string(&persona).map_err(|_| "persona_unavailable")
}

fn config_path() -> Result<PathBuf, &'static str> {
    let home = std::env::var_os("HOME").ok_or("home_unavailable")?;
    Ok(PathBuf::from(home).join(".config/hero/persona.toml"))
}
