use serde::Deserialize;
use serde_json::json;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Default, Deserialize)]
struct Persona {
    name: Option<String>,
    voice: Option<String>,
}

fn config_path() -> Result<PathBuf, String> {
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .ok_or_else(|| "HOME não está definido".to_string())?;
    Ok(home.join(".config/hero/persona.toml"))
}

fn load() -> Result<Persona, String> {
    let path = config_path()?;
    let source = match fs::read_to_string(path) {
        Ok(source) => source,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => String::new(),
        Err(error) => return Err(error.to_string()),
    };
    let mut persona = Persona::default();
    for line in source.lines() {
        let Some((key, value)) = line.split_once('=') else {
            continue;
        };
        let value = value.trim();
        match key.trim() {
            "name" => persona.name = parse_toml_string(value),
            "voice" => persona.voice = parse_toml_string(value),
            _ => {}
        }
    }
    Ok(persona)
}

fn parse_toml_string(value: &str) -> Option<String> {
    serde_json::from_str(value).ok()
}

fn write_value(key: &str, value: &str) -> Result<(), String> {
    let path = config_path()?;
    let parent = path
        .parent()
        .ok_or_else(|| "diretório de configuração inválido".to_string())?;
    fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    restrict_dir(parent)?;
    let current = fs::read_to_string(&path).unwrap_or_default();
    let mut lines = current
        .lines()
        .filter(|line| {
            line.split_once('=')
                .is_none_or(|(found, _)| found.trim() != key)
        })
        .map(str::to_string)
        .collect::<Vec<_>>();
    lines.push(format!("{key} = {}", json!(value)));
    let temporary = path.with_extension("toml.tmp");
    let mut file = OpenOptions::new()
        .create(true)
        .truncate(true)
        .write(true)
        .open(&temporary)
        .map_err(|error| error.to_string())?;
    file.write_all(lines.join("\n").as_bytes())
        .and_then(|_| file.write_all(b"\n"))
        .map_err(|error| error.to_string())?;
    file.sync_all().map_err(|error| error.to_string())?;
    restrict_file(&temporary)?;
    fs::rename(temporary, path).map_err(|error| error.to_string())
}

pub fn status(json_output: bool) -> i32 {
    let result = load().map(|persona| {
        let voice_installed = persona
            .voice
            .as_deref()
            .is_some_and(|voice| voice_paths(voice).is_ok());
        let name = persona.name.unwrap_or_else(|| "Guará".into());
        let wakeword = wakeword_path(&name).is_file();
        json!( {
            "command":"mascot status",
            "status":"ok",
            "name":name,
            "wakeword": if wakeword { "installed" } else { "not_installed" },
            "voice":persona.voice,
            "voice_status":if voice_installed { "installed" } else { "not_installed" }
        })
    });
    report(result, json_output)
}

pub fn set_name(name: &str, json_output: bool) -> i32 {
    let name = name.trim();
    if !(2..=24).contains(&name.chars().count())
        || !name
            .chars()
            .all(|character| character.is_alphabetic() || matches!(character, ' ' | '-' | '\''))
    {
        return report(
            Err("O nome deve ter 2–24 letras, espaços, hífens ou apóstrofos.".into()),
            json_output,
        );
    }
    report(
        write_value("name", name)
            .map(|()| json!({"command":"mascot name", "status":"ok", "name":name})),
        json_output,
    )
}

pub fn set_voice(voice: &str, json_output: bool) -> i32 {
    let Ok(paths) = voice_paths(voice) else {
        return report(
            Err("Voz indisponível. Instale localmente os arquivos .onnx e .onnx.json do Piper antes de selecioná-la.".into()),
            json_output,
        );
    };
    let _ = paths;
    report(
        write_value("voice", voice)
            .map(|()| json!({"command":"mascot voice", "status":"ok", "voice":voice})),
        json_output,
    )
}

pub fn train(name: &str, json_output: bool) -> i32 {
    let name = name.trim();
    if !(2..=24).contains(&name.chars().count())
        || !name
            .chars()
            .all(|character| character.is_alphabetic() || matches!(character, ' ' | '-' | '\''))
    {
        return report(
            Err("O nome deve ter 2–24 letras, espaços, hífens ou apóstrofos.".into()),
            json_output,
        );
    }
    let trainer = Path::new("/usr/libexec/forjaos/train-wakeword");
    if !trainer.is_file() {
        return report(
            Err("Treinador de wake word não está instalado. Nenhum treino foi iniciado.".into()),
            json_output,
        );
    }
    let result = Command::new(trainer).args(["--name", name]).status();
    match result {
        Ok(status) if status.success() => report(
            Ok(json!({"command":"mascot train", "status":"queued", "name":name})),
            json_output,
        ),
        Ok(status) => report(
            Err(format!("Treinamento terminou com {status}.")),
            json_output,
        ),
        Err(error) => report(Err(error.to_string()), json_output),
    }
}

fn voice_paths(voice: &str) -> Result<(PathBuf, PathBuf), String> {
    if voice.is_empty()
        || voice.len() > 96
        || !voice
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
    {
        return Err("identificador de voz inválido".into());
    }
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .ok_or_else(|| "HOME não está definido".to_string())?;
    let model = home
        .join(".local/share/hero/voices")
        .join(format!("{voice}.onnx"));
    let config = model.with_file_name(format!("{voice}.onnx.json"));
    if model.is_file() && config.is_file() {
        Ok((model, config))
    } else {
        Err("arquivos de voz ausentes".into())
    }
}

fn wakeword_path(name: &str) -> PathBuf {
    let slug = name
        .chars()
        .filter(|character| character.is_alphanumeric())
        .flat_map(char::to_lowercase)
        .collect::<String>();
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_default();
    home.join(".local/share/hero/wakewords")
        .join(format!("{slug}.onnx"))
}

fn report(result: Result<serde_json::Value, String>, json_output: bool) -> i32 {
    match result {
        Ok(value) => {
            if json_output {
                println!("{value}");
            } else if let Some(name) = value["name"].as_str() {
                println!("Mascote: {name}");
                if value["command"] == "mascot status" {
                    println!(
                        "Wake word: {}",
                        value["wakeword"].as_str().unwrap_or("indisponível")
                    );
                    println!(
                        "Voz: {} ({})",
                        value["voice"].as_str().unwrap_or("não selecionada"),
                        value["voice_status"].as_str().unwrap_or("indisponível")
                    );
                }
            } else if let Some(voice) = value["voice"].as_str() {
                println!("Voz selecionada: {voice}");
            } else {
                println!("Treino local enfileirado.");
            }
            0
        }
        Err(error) => {
            if json_output {
                println!(
                    "{}",
                    json!({"command":"mascot", "status":"error", "error":error})
                );
            } else {
                eprintln!("forja mascot: {error}");
            }
            1
        }
    }
}

#[cfg(unix)]
fn restrict_dir(path: &Path) -> Result<(), String> {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(path, fs::Permissions::from_mode(0o700)).map_err(|error| error.to_string())
}

#[cfg(not(unix))]
fn restrict_dir(_path: &Path) -> Result<(), String> {
    Ok(())
}

#[cfg(unix)]
fn restrict_file(path: &Path) -> Result<(), String> {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(path, fs::Permissions::from_mode(0o600)).map_err(|error| error.to_string())
}

#[cfg(not(unix))]
fn restrict_file(_path: &Path) -> Result<(), String> {
    Ok(())
}
