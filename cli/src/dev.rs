//! Rootless container workflows for `forja`.
use serde::Serialize;
use std::io::{self, IsTerminal, Write};
use std::process::{Command, Stdio};

const DOCKER_REPO: &str = "https://download.docker.com/linux/fedora/docker-ce.repo";

#[derive(Serialize)]
struct BoxResult<'a> {
    distro: &'a str,
    name: &'a str,
    status: &'a str,
    message: &'a str,
    #[serde(skip_serializing_if = "Option::is_none")]
    enter: Option<&'a str>,
}

fn valid_name(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 63
        && value.as_bytes()[0].is_ascii_alphanumeric()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'.' | b'-'))
}

fn image(distro: &str) -> Option<&'static str> {
    match distro {
        "ubuntu" => Some("docker.io/library/ubuntu:24.04"),
        "arch" => Some("docker.io/library/archlinux:latest"),
        "fedora" => Some("registry.fedoraproject.org/fedora-toolbox:latest"),
        _ => None,
    }
}

fn report_box(distro: &str, name: &str, status: &str, message: &str, json: bool) {
    if json {
        println!(
            "{}",
            serde_json::to_string(&BoxResult {
                distro,
                name,
                status,
                message,
                enter: (status == "created").then_some("distrobox enter <name>"),
            })
            .expect("serialize distrobox result")
        );
    } else {
        println!("{message}");
    }
}

pub fn box_create(distro: &str, name: Option<&str>, json: bool) -> i32 {
    let Some(image) = image(distro) else {
        report_box(distro, "", "error", "Distro não suportada.", json);
        return 2;
    };
    let generated_name = format!("forja-{distro}");
    let name = name.unwrap_or(&generated_name);
    if !valid_name(name) {
        report_box(distro, name, "error", "Nome de container inválido.", json);
        return 2;
    }
    let mut create = Command::new("distrobox");
    create
        .env("DBX_CONTAINER_MANAGER", "podman")
        .args(["create", "--yes", "--name", name, "--image", image]);
    let output = match create.output() {
        Ok(output) => output,
        Err(error) => {
            report_box(
                distro,
                name,
                "error",
                "Distrobox/Podman indisponível.",
                json,
            );
            eprintln!("forja box: {error}");
            return 1;
        }
    };
    if !output.status.success() {
        let details = String::from_utf8_lossy(&output.stderr).trim().to_string();
        report_box(distro, name, "error", &details, json);
        return output.status.code().unwrap_or(1);
    }
    if json {
        report_box(
            distro,
            name,
            "created",
            "Container rootless criado com Podman.",
            true,
        );
        return 0;
    }
    println!("Container {name} criado com Podman rootless. Entrando...");
    let status = Command::new("distrobox")
        .env("DBX_CONTAINER_MANAGER", "podman")
        .args(["enter", "--name", name])
        .status();
    match status {
        Ok(status) => status.code().unwrap_or(1),
        Err(error) => {
            eprintln!("forja box: não foi possível entrar no container: {error}");
            1
        }
    }
}

fn confirmed(yes: bool, json: bool) -> bool {
    if yes {
        return true;
    }
    if json {
        return false;
    }
    println!("Rota: forja docker install");
    println!("Contexto: adiciona o repositório oficial Docker e aplica pacotes Docker CE ao sistema bootc via rpm-ostree. A operação exige senha de administrador e reinicialização; o daemon root privilegiado não será ativado.");
    if !io::stdin().is_terminal() {
        println!("Instalação não iniciada. Use --yes para confirmar explicitamente.");
        return false;
    }
    print!("Continuar? [s/N] ");
    let _ = io::stdout().flush();
    let mut answer = String::new();
    io::stdin().read_line(&mut answer).is_ok()
        && matches!(
            answer.trim().to_lowercase().as_str(),
            "s" | "sim" | "y" | "yes"
        )
}

fn run(program: &str, args: &[&str], json: bool) -> Result<i32, String> {
    let mut command = Command::new(program);
    command.args(args).stdin(Stdio::inherit());
    if json {
        let output = command
            .output()
            .map_err(|error| format!("não foi possível executar {program}: {error}"))?;
        if !output.status.success() && !output.stderr.is_empty() {
            eprint!("{}", String::from_utf8_lossy(&output.stderr));
        }
        Ok(output.status.code().unwrap_or(1))
    } else {
        command
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .status()
            .map(|status| status.code().unwrap_or(1))
            .map_err(|error| format!("não foi possível executar {program}: {error}"))
    }
}

pub fn docker_install(yes: bool, json: bool) -> i32 {
    if !confirmed(yes, json) {
        if json {
            println!(
                "{}",
                serde_json::json!({"package":"docker-ce", "status":"confirmation_required"})
            );
            return 2;
        }
        return 1;
    }
    if Command::new("rpm-ostree")
        .arg("--version")
        .output()
        .is_err()
    {
        eprintln!("forja docker: este fluxo requer um sistema bootc com rpm-ostree.");
        return 1;
    }
    let repo = run(
        "sudo",
        &["dnf", "config-manager", "--add-repo", DOCKER_REPO],
        json,
    );
    if !matches!(repo, Ok(0)) {
        eprintln!("forja docker: não foi possível configurar a fonte oficial do Docker.");
        return repo.unwrap_or(1);
    }
    let packages = [
        "docker-ce",
        "docker-ce-cli",
        "containerd.io",
        "docker-buildx-plugin",
        "docker-compose-plugin",
        "docker-ce-rootless-extras",
    ];
    let mut args = vec!["install", "--idempotent"];
    args.extend(packages);
    let status = run("sudo", &args, json);
    if !matches!(status, Ok(0)) {
        eprintln!("forja docker: o overlay RPM falhou. O repositório oficial foi mantido para nova tentativa.");
        return status.unwrap_or(1);
    }
    let message = "Docker CE instalado. Reinicie e execute `forja docker setup-rootless`; Podman permanece padrão.";
    if json {
        println!(
            "{}",
            serde_json::json!({
                "package": "docker-ce",
                "status": "reboot_required",
                "message": "Docker CE instalado; reinicie e execute forja docker setup-rootless."
            })
        );
    } else {
        println!("{message}");
    }
    0
}

pub fn docker_setup_rootless(json: bool) -> i32 {
    let setup = Command::new("dockerd-rootless-setuptool.sh")
        .arg("install")
        .output();
    let output = match setup {
        Ok(output) => output,
        Err(error) => {
            if json {
                println!(
                    "{}",
                    serde_json::json!({"package":"docker-ce", "status":"error"})
                );
                return 1;
            }
            eprintln!("Docker CE rootless ainda não está disponível; reinicie após `forja docker install`: {error}");
            return 1;
        }
    };
    if !output.status.success() {
        if json {
            println!(
                "{}",
                serde_json::json!({"package":"docker-ce", "status":"error"})
            );
            return output.status.code().unwrap_or(1);
        }
        eprint!("{}", String::from_utf8_lossy(&output.stderr));
        return output.status.code().unwrap_or(1);
    }
    if !json {
        print!("{}", String::from_utf8_lossy(&output.stdout));
    }
    let status = run(
        "systemctl",
        &["--user", "enable", "--now", "docker.service"],
        json,
    );
    if !matches!(status, Ok(0)) {
        eprintln!("forja docker: a configuração rootless foi instalada, mas o serviço do usuário não iniciou.");
        return status.unwrap_or(1);
    }
    if json {
        println!(
            "{}",
            serde_json::json!({"package":"docker-ce", "status":"rootless_ready", "podman_default":true})
        );
    } else {
        println!("Docker CE rootless ativo no usuário; Podman continua como padrão.");
    }
    0
}

pub fn ssh_add(json: bool) -> i32 {
    let output = Command::new("ssh-add")
        .env("SSH_ASKPASS", "/usr/bin/ksshaskpass")
        .env("SSH_ASKPASS_REQUIRE", "force")
        .stdin(Stdio::null())
        .output();
    let Ok(output) = output else {
        if json {
            println!("{}", serde_json::json!({"ssh_agent":"error"}));
        } else {
            eprintln!("forja keys ssh-add: não foi possível iniciar ssh-add.");
        }
        return 1;
    };
    if json {
        println!(
            "{}",
            serde_json::json!({"ssh_agent": if output.status.success() { "ready" } else { "cancelled_or_failed" }})
        );
    } else {
        print!("{}", String::from_utf8_lossy(&output.stdout));
        if !output.status.success() {
            eprint!("{}", String::from_utf8_lossy(&output.stderr));
        }
    }
    output.status.code().unwrap_or(1)
}

pub fn compose(action: &str, json: bool) -> i32 {
    let compose_file = [
        "compose.yaml",
        "compose.yml",
        "docker-compose.yaml",
        "docker-compose.yml",
    ]
    .into_iter()
    .find(|file| std::path::Path::new(file).is_file());
    let Some(compose_file) = compose_file else {
        if json {
            println!(
                "{}",
                serde_json::json!({"command": action, "status": "compose_file_not_found"})
            );
        } else {
            eprintln!("forja {action}: nenhum arquivo Compose encontrado no diretório atual.");
        }
        return 2;
    };

    let mut command = Command::new("podman");
    command.args(["compose", "-f", compose_file, action]);
    if action == "up" {
        command.arg("-d");
    }
    if json {
        let output = match command.output() {
            Ok(output) => output,
            Err(_) => {
                println!(
                    "{}",
                    serde_json::json!({"command": action, "status": "podman_unavailable"})
                );
                return 1;
            }
        };
        let status = output.status;
        println!(
            "{}",
            serde_json::json!({
                "command": action,
                "status": if status.success() { "ok" } else { "error" },
                "exit_code": status.code().unwrap_or(1)
            })
        );
        status.code().unwrap_or(1)
    } else {
        match command.status() {
            Ok(status) => status.code().unwrap_or(1),
            Err(error) => {
                eprintln!("forja {action}: não foi possível iniciar Podman: {error}");
                1
            }
        }
    }
}

pub fn bootc_action(action: &str, yes: bool, json: bool) -> i32 {
    if !yes {
        if json {
            println!(
                "{}",
                serde_json::json!({"command": action, "status": "confirmation_required"})
            );
            return 2;
        }
        let context = match action {
            "upgrade" => "Baixa e prepara uma nova implantação bootc; não reinicia o computador.",
            "rollback" => "Agenda a implantação anterior para o próximo boot e descarta uma atualização staged, se houver.",
            _ => return 2,
        };
        println!("Rota: forja {}", if action == "upgrade" { "update" } else { "rollback" });
        println!("Contexto: {context}");
        if !io::stdin().is_terminal() {
            println!("Ação não iniciada. Use --yes para confirmar explicitamente.");
            return 2;
        }
        print!("Continuar? [s/N] ");
        let _ = io::stdout().flush();
        let mut answer = String::new();
        if !io::stdin().read_line(&mut answer).is_ok_and(|_| {
            matches!(answer.trim().to_lowercase().as_str(), "s" | "sim" | "y" | "yes")
        }) {
            return 2;
        }
    }

    if json {
        let output = Command::new("sudo")
            .args(["bootc", action])
            .stdin(Stdio::inherit())
            .output();
        let Ok(output) = output else {
            println!("{}", serde_json::json!({"command": action, "status": "error"}));
            return 1;
        };
        println!(
            "{}",
            serde_json::json!({
                "command": action,
                "status": if output.status.success() { "ok" } else { "error" },
                "exit_code": output.status.code().unwrap_or(1)
            })
        );
        output.status.code().unwrap_or(1)
    } else {
        match Command::new("sudo").args(["bootc", action]).status() {
            Ok(status) => status.code().unwrap_or(1),
            Err(error) => {
                eprintln!("forja {action}: não foi possível executar sudo bootc: {error}");
                1
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{image, valid_name};

    #[test]
    fn distro_images_are_fixed_to_supported_registries() {
        assert_eq!(image("ubuntu"), Some("docker.io/library/ubuntu:24.04"));
        assert_eq!(image("arch"), Some("docker.io/library/archlinux:latest"));
        assert_eq!(
            image("fedora"),
            Some("registry.fedoraproject.org/fedora-toolbox:latest")
        );
        assert_eq!(image("unknown"), None);
    }

    #[test]
    fn container_names_cannot_inject_arguments() {
        assert!(valid_name("forja-dev_01"));
        assert!(!valid_name("../outside"));
        assert!(!valid_name("--root"));
        assert!(!valid_name(""));
    }
}
