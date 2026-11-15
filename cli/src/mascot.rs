use serde::Deserialize;
use serde_json::json;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

const PIPER_VOICE_REVISION: &str = "cf910fb59f1d79ab3b625a63993a108751c6c25d";

struct PiperVoice {
    id: &'static str,
    speaker: &'static str,
    model_sha256: &'static str,
    config_sha256: &'static str,
}

const PIPER_VOICES: &[PiperVoice] = &[
    PiperVoice {
        id: "pt_BR-cadu-medium",
        speaker: "cadu",
        model_sha256: "d5a662e3f606d5a49dd29ba9ce90c304ae45dd9543f8b0c773bcb0de282499de",
        config_sha256: "9fa837b7c1237ea5978bcd7be38c130798e8faa064f754873bb4ce5fc498bd88",
    },
    PiperVoice {
        id: "pt_BR-jeff-medium",
        speaker: "jeff",
        model_sha256: "82ddcdb01a0342f078bd89ce2815eda27185818d15e15f06fb9a72ac3bce94e1",
        config_sha256: "078ea4e42a680ca3cb662a8929237c32e2c0d581f5363f2f55f09bc266497bf6",
    },
];

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
    let current = match fs::read_to_string(&path) {
        Ok(current) => current,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => String::new(),
        Err(error) => return Err(error.to_string()),
    };
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

pub fn list_voices(json_output: bool) -> i32 {
    let home = std::env::var_os("HOME").map(PathBuf::from);
    let voices = PIPER_VOICES
        .iter()
        .map(|voice| {
            let installed = home.as_ref().is_some_and(|home| {
                let directory = home.join(".local/share/hero/voices");
                verify_file(
                    &directory.join(format!("{}.onnx", voice.id)),
                    63_221_984,
                    voice.model_sha256,
                ) && verify_file(
                    &directory.join(format!("{}.onnx.json", voice.id)),
                    5_465,
                    voice.config_sha256,
                )
            });
            json!({
                "id":voice.id,
                "language":"pt-BR",
                "license":"CC0",
                "installed":installed
            })
        })
        .collect::<Vec<_>>();
    if json_output {
        println!(
            "{}",
            json!({"command":"mascot voices list", "status":"ok", "voices":voices})
        );
    } else {
        for voice in PIPER_VOICES {
            let installed = home.as_ref().is_some_and(|home| {
                let directory = home.join(".local/share/hero/voices");
                verify_file(
                    &directory.join(format!("{}.onnx", voice.id)),
                    63_221_984,
                    voice.model_sha256,
                ) && verify_file(
                    &directory.join(format!("{}.onnx.json", voice.id)),
                    5_465,
                    voice.config_sha256,
                )
            });
            println!(
                "{} · pt-BR · CC0 · {}",
                voice.id,
                if installed {
                    "instalada"
                } else {
                    "não instalada"
                }
            );
        }
    }
    0
}

pub fn download_voice(id: &str, json_output: bool) -> i32 {
    let Some(voice) = PIPER_VOICES.iter().find(|voice| voice.id == id) else {
        return report(
            Err("ID indisponível. Consulte `forja mascot voices list`.".into()),
            json_output,
        );
    };
    report(
        install_voice(voice)
            .map(|()| json!({"command":"mascot voices download", "status":"ok", "voice":voice.id})),
        json_output,
    )
}

fn install_voice(voice: &PiperVoice) -> Result<(), String> {
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .ok_or_else(|| "HOME não está definido".to_string())?;
    let directory = home.join(".local/share/hero/voices");
    fs::create_dir_all(&directory).map_err(|error| error.to_string())?;
    restrict_dir(&directory)?;

    let model_name = format!("{}.onnx", voice.id);
    let config_name = format!("{}.onnx.json", voice.id);
    let model_path = directory.join(&model_name);
    let config_path = directory.join(&config_name);
    for (path, size, hash) in [
        (&model_path, 63_221_984, voice.model_sha256),
        (&config_path, 5_465, voice.config_sha256),
    ] {
        if fs::symlink_metadata(path).is_ok() && !verify_file(path, size, hash) {
            return Err(format!(
                "{} já existe e não corresponde ao modelo validado; remova-o manualmente antes de tentar novamente.",
                path.display()
            ));
        }
    }
    if verify_file(&model_path, 63_221_984, voice.model_sha256)
        && verify_file(&config_path, 5_465, voice.config_sha256)
    {
        return Ok(());
    }

    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| error.to_string())?
        .as_nanos();
    let staging = directory.join(format!(
        ".{}.stage-{}-{nonce}",
        voice.id,
        std::process::id()
    ));
    fs::create_dir(&staging).map_err(|error| error.to_string())?;
    if let Err(error) = restrict_dir(&staging) {
        let _ = fs::remove_dir_all(&staging);
        return Err(error);
    }
    let result = (|| {
        let model_stage = staging.join(&model_name);
        let config_stage = staging.join(&config_name);
        download_piper_file(voice, &model_name, &model_stage)?;
        download_piper_file(voice, &config_name, &config_stage)?;
        if !verify_file(&model_stage, 63_221_984, voice.model_sha256)
            || !verify_file(&config_stage, 5_465, voice.config_sha256)
        {
            return Err("O download da voz não corresponde ao tamanho/SHA-256 fixado.".into());
        }
        restrict_file(&model_stage)?;
        restrict_file(&config_stage)?;
        if fs::symlink_metadata(&model_path).is_err() {
            fs::hard_link(&model_stage, &model_path).map_err(|error| error.to_string())?;
            fs::remove_file(&model_stage).map_err(|error| error.to_string())?;
        }
        if fs::symlink_metadata(&config_path).is_err() {
            fs::hard_link(&config_stage, &config_path).map_err(|error| error.to_string())?;
            fs::remove_file(&config_stage).map_err(|error| error.to_string())?;
        }
        Ok(())
    })();
    let _ = fs::remove_dir_all(&staging);
    result
}

fn download_piper_file(
    voice: &PiperVoice,
    filename: &str,
    destination: &Path,
) -> Result<(), String> {
    let url = format!(
        "https://huggingface.co/rhasspy/piper-voices/resolve/{}/pt/pt_BR/{}/medium/{}",
        PIPER_VOICE_REVISION, voice.speaker, filename
    );
    let output = Command::new("curl")
        .args([
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--max-time",
            "300",
            "--max-filesize",
            "70000000",
            "--output",
        ])
        .arg(destination)
        .arg(url)
        .output()
        .map_err(|error| format!("curl: {error}"))?;
    if output.status.success() {
        Ok(())
    } else {
        let detail = String::from_utf8_lossy(&output.stderr).trim().to_string();
        Err(if detail.is_empty() {
            format!("download de {filename} falhou ({})", output.status)
        } else {
            format!("download de {filename} falhou: {detail}")
        })
    }
}

fn verify_file(path: &Path, expected_size: u64, expected_sha256: &str) -> bool {
    let Ok(metadata) = fs::symlink_metadata(path) else {
        return false;
    };
    if !metadata.file_type().is_file() || metadata.len() != expected_size {
        return false;
    }
    let Ok(output) = Command::new("sha256sum").arg(path).output() else {
        return false;
    };
    output.status.success()
        && String::from_utf8_lossy(&output.stdout)
            .split_whitespace()
            .next()
            .is_some_and(|digest| digest.eq_ignore_ascii_case(expected_sha256))
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
    let result = Command::new("systemd-run")
        .args([
            "--user",
            "--quiet",
            "--collect",
            "--unit=forja-wakeword-train.service",
        ])
        .arg(trainer)
        .args(["--name", name])
        .status();
    match result {
        Ok(status) if status.success() => report(
            Ok(json!({
                "command":"mascot train",
                "status":"queued",
                "name":name,
                "unit":"forja-wakeword-train.service"
            })),
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
                if value["command"] == "mascot voices download" {
                    println!("Voz baixada e validada: {voice}.");
                } else {
                    println!("Voz selecionada: {voice}");
                }
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
