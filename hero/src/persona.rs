use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Persona {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub voice: Option<String>,
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

#[cfg(test)]
mod tests {
    use super::{load, set_instructions};
    use crate::test_support::TestHome;

    #[test]
    fn rejects_oversized_and_control_character_instructions() {
        assert_eq!(
            set_instructions(&"x".repeat(4001)),
            Err("invalid_persona_instructions")
        );
        assert_eq!(
            set_instructions("linha\u{7}inválida"),
            Err("invalid_persona_instructions")
        );
    }

    #[test]
    fn persona_instructions_are_trimmed_persisted_and_clearable() {
        let _home = TestHome::new();
        assert_eq!(load().instructions, None);
        let saved: serde_json::Value =
            serde_json::from_str(&set_instructions("  Seja objetivo.  ").expect("save persona"))
                .expect("persona JSON");
        assert_eq!(saved["instructions"], "Seja objetivo.");
        assert_eq!(load().instructions.as_deref(), Some("Seja objetivo."));

        let cleared: serde_json::Value =
            serde_json::from_str(&set_instructions(" \n ").expect("clear persona"))
                .expect("cleared persona JSON");
        assert!(cleared.get("instructions").is_none());
        assert_eq!(load().instructions, None);
    }

    #[test]
    fn instructions_preserve_cli_selected_voice() {
        let home = TestHome::new();
        let path = home.root().join(".config/hero/persona.toml");
        std::fs::create_dir_all(path.parent().expect("config dir")).expect("create config");
        std::fs::write(&path, "name = \"Guará\"\nvoice = \"pt_BR-cadu-medium\"\n")
            .expect("CLI persona");
        assert_eq!(load().voice.as_deref(), Some("pt_BR-cadu-medium"));
        set_instructions("Seja objetivo.").expect("save instructions");
        let persona = load();
        assert_eq!(persona.name.as_deref(), Some("Guará"));
        assert_eq!(persona.voice.as_deref(), Some("pt_BR-cadu-medium"));
        assert_eq!(persona.instructions.as_deref(), Some("Seja objetivo."));
    }
}
