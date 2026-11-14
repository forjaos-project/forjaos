//! Instaladores no espaço do usuário para ferramentas proprietárias opcionais.
use serde::Serialize;
use std::fs::{self, File, OpenOptions};
use std::io::{self, IsTerminal, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

const UNITY_APPIMAGE_URL: &str =
    "https://public-cdn.cloud.unity3d.com/hub/prod/UnityHub-x86_64.AppImage";
const CLAUDE_INSTALL_URL: &str = "https://claude.ai/install.sh";

#[derive(Serialize)]
struct InstallResult {
    package: &'static str,
    status: &'static str,
    message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    path: Option<String>,
}

fn emit(json: bool, result: InstallResult, code: i32) -> i32 {
    if json {
        println!(
            "{}",
            serde_json::to_string(&result).expect("serialize install result")
        );
    } else {
        println!("{}", result.message);
        if let Some(path) = result.path {
            println!("Instalado em: {path}");
        }
    }
    code
}

fn failed(package: &'static str, json: bool, message: impl Into<String>) -> i32 {
    emit(
        json,
        InstallResult {
            package,
            status: "error",
            message: message.into(),
            path: None,
        },
        1,
    )
}

fn approved(package: &'static str, route: &str, context: &str, yes: bool, json: bool) -> bool {
    if yes {
        return true;
    }
    if json {
        emit(
            true,
            InstallResult {
                package,
                status: "confirmation_required",
                message: "Repita com --yes para autorizar a instalação.".into(),
                path: None,
            },
            2,
        );
        return false;
    }

    println!("Rota: {route}");
    println!("Contexto: {context}");
    if !io::stdin().is_terminal() {
        println!("Instalação não iniciada. Use --yes em uma execução não interativa.");
        return false;
    }

    print!("Continuar? [s/N] ");
    let _ = io::stdout().flush();
    let mut answer = String::new();
    let confirmed = io::stdin().read_line(&mut answer).is_ok()
        && matches!(
            answer.trim().to_lowercase().as_str(),
            "s" | "sim" | "y" | "yes"
        );
    if !confirmed {
        println!("Instalação cancelada.");
    }
    confirmed
}

fn home_dir() -> Result<PathBuf, String> {
    std::env::var_os("HOME")
        .map(PathBuf::from)
        .filter(|path| path.is_absolute())
        .ok_or_else(|| "A variável HOME não aponta para um diretório absoluto.".into())
}

fn temporary_path(directory: &Path, name: &str) -> Result<PathBuf, String> {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|_| "O relógio do sistema está antes do Unix epoch.".to_string())?
        .as_nanos();
    let path = directory.join(format!(".{name}.{}.{}.part", std::process::id(), timestamp));
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)
        .map_err(|error| format!("Não foi possível reservar o arquivo temporário: {error}"))?;
    Ok(path)
}

fn download_unity_appimage(path: &Path) -> Result<(), String> {
    let output = Command::new("curl")
        .args([
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--output",
        ])
        .arg(path)
        .arg(UNITY_APPIMAGE_URL)
        .output()
        .map_err(|error| format!("Não foi possível executar curl: {error}"))?;
    if !output.status.success() {
        let _ = fs::remove_file(path);
        let details = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if details.is_empty() {
            format!("O download do Unity Hub falhou (código {}).", output.status)
        } else {
            format!("O download do Unity Hub falhou: {details}")
        });
    }

    let mut file =
        File::open(path).map_err(|error| format!("Não foi possível abrir o AppImage: {error}"))?;
    let mut magic = [0; 4];
    file.read_exact(&mut magic)
        .map_err(|error| format!("O arquivo baixado está incompleto: {error}"))?;
    if magic != [0x7f, b'E', b'L', b'F'] {
        let _ = fs::remove_file(path);
        return Err("O servidor não retornou um AppImage ELF válido.".into());
    }

    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(path, fs::Permissions::from_mode(0o755))
            .map_err(|error| format!("Não foi possível tornar o AppImage executável: {error}"))?;
        Ok(())
    }
    #[cfg(not(unix))]
    {
        Err("Este instalador só funciona no ForjaOS/Linux.".into())
    }
}

fn desktop_exec_path(path: &Path) -> String {
    path.to_string_lossy()
        .replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('%', "%%")
}

fn fuse_available() -> bool {
    std::env::split_paths(&std::env::var_os("PATH").unwrap_or_default()).any(|directory| {
        ["fusermount3", "fusermount"]
            .iter()
            .any(|binary| directory.join(binary).is_file())
    })
}

fn write_unity_desktop_file(
    home: &Path,
    appimage: &Path,
    use_extract_fallback: bool,
) -> Result<PathBuf, String> {
    let applications = home.join(".local/share/applications");
    fs::create_dir_all(&applications)
        .map_err(|error| format!("Não foi possível criar o diretório de aplicativos: {error}"))?;
    let desktop = applications.join("unityhub.desktop");
    let temporary = temporary_path(&applications, "unityhub.desktop")?;
    let appimage_args = if use_extract_fallback {
        " --appimage-extract-and-run"
    } else {
        ""
    };
    let contents = format!(
        "[Desktop Entry]\nType=Application\nName=Unity Hub\nComment=Gerencie projetos e editores Unity\nExec=\"{}\"{} %U\nTerminal=false\nCategories=Development;IDE;\nMimeType=x-scheme-handler/unityhub;\n",
        desktop_exec_path(appimage),
        appimage_args
    );
    if let Err(error) = fs::write(&temporary, contents) {
        let _ = fs::remove_file(&temporary);
        return Err(format!(
            "Não foi possível gravar o lançador do Unity Hub: {error}"
        ));
    }
    if let Err(error) = fs::rename(&temporary, &desktop) {
        let _ = fs::remove_file(&temporary);
        return Err(format!(
            "Não foi possível ativar o lançador do Unity Hub: {error}"
        ));
    }
    Ok(desktop)
}

pub fn unity(yes: bool, json: bool) -> i32 {
    if !approved(
        "unity",
        "forja install unity",
        "baixa o Unity Hub oficial e grava o AppImage e o lançador apenas no seu usuário; pode atualizar o arquivo local existente.",
        yes,
        json,
    ) {
        return if json { 2 } else { 1 };
    }
    if std::env::consts::ARCH != "x86_64" {
        return failed(
            "unity",
            json,
            "O AppImage oficial do Unity Hub está disponível somente para x86_64.",
        );
    }

    let result = (|| {
        let home = home_dir()?;
        let directory = home.join(".local/opt/forja/unityhub");
        fs::create_dir_all(&directory)
            .map_err(|error| format!("Não foi possível criar o diretório local: {error}"))?;
        let temporary = temporary_path(&directory, "UnityHub.AppImage")?;
        if let Err(error) = download_unity_appimage(&temporary) {
            let _ = fs::remove_file(&temporary);
            return Err(error);
        }

        let appimage = directory.join("UnityHub.AppImage");
        if let Err(error) = fs::rename(&temporary, &appimage) {
            let _ = fs::remove_file(&temporary);
            return Err(format!("Não foi possível ativar o Unity Hub: {error}"));
        }
        let use_extract_fallback = !fuse_available();
        write_unity_desktop_file(&home, &appimage, use_extract_fallback)?;
        Ok((appimage, use_extract_fallback))
    })();

    match result {
        Ok((appimage, use_extract_fallback)) => emit(
            json,
            InstallResult {
                package: "unity",
                status: "installed",
                message: if use_extract_fallback {
                    "Unity Hub foi instalado para o usuário atual; o lançador usará o fallback sem FUSE.".into()
                } else {
                    "Unity Hub foi instalado para o usuário atual.".into()
                },
                path: Some(appimage.display().to_string()),
            },
            0,
        ),
        Err(error) => failed("unity", json, error),
    }
}

fn run_claude_installer() -> Result<(), String> {
    let mut curl = Command::new("curl")
        .args([
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            CLAUDE_INSTALL_URL,
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("Não foi possível executar curl: {error}"))?;
    let script = curl
        .stdout
        .take()
        .ok_or_else(|| "Não foi possível abrir o fluxo do instalador oficial.".to_string())?;
    let output = Command::new("bash")
        .arg("-s")
        .stdin(Stdio::from(script))
        .output()
        .map_err(|error| format!("Não foi possível executar bash: {error}"))?;
    let curl_output = curl
        .wait_with_output()
        .map_err(|error| format!("Não foi possível aguardar o download do instalador: {error}"))?;

    if !curl_output.status.success() {
        let details = String::from_utf8_lossy(&curl_output.stderr)
            .trim()
            .to_string();
        return Err(if details.is_empty() {
            format!(
                "O download do instalador oficial falhou (código {}).",
                curl_output.status
            )
        } else {
            format!("O download do instalador oficial falhou: {details}")
        });
    }
    if !output.status.success() {
        let details = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if details.is_empty() {
            format!(
                "O instalador do Claude Code falhou (código {}).",
                output.status
            )
        } else {
            format!("O instalador do Claude Code falhou: {details}")
        });
    }
    Ok(())
}

pub fn claude_code(yes: bool, json: bool) -> i32 {
    if !approved(
        "claude-code",
        "forja install claude-code",
        "executa o instalador oficial da Anthropic com bash; ele instala e atualiza Claude Code no seu usuário, sem sudo.",
        yes,
        json,
    ) {
        return if json { 2 } else { 1 };
    }

    match run_claude_installer() {
        Ok(()) => emit(
            json,
            InstallResult {
                package: "claude-code",
                status: "installed",
                message: "Claude Code foi instalado para o usuário atual; abra um terminal novo e rode claude --version para conferir.".into(),
                path: Some("~/.local/bin/claude".into()),
            },
            0,
        ),
        Err(error) => failed("claude-code", json, error),
    }
}
