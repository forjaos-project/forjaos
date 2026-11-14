//! `forja` — porta de entrada do ForjaOS (ADR-020). Subcomandos entram aqui conforme os itens do TODO.
mod dev;
mod doctor;
mod install;

use clap::{CommandFactory, FromArgMatches, Parser, Subcommand, ValueEnum};
use std::ffi::OsString;

#[derive(Clone, Copy, Debug, PartialEq, Eq, ValueEnum)]
enum Language {
    #[value(name = "pt-br")]
    PtBr,
    En,
}

#[derive(Parser)]
#[command(
    name = "forja",
    version,
    about = "ForjaOS: diagnóstico, instalação e assistente em um comando"
)]
struct Cli {
    /// Idioma da ajuda: pt-br ou en
    #[arg(long, global = true, value_enum, default_value = "pt-br")]
    lang: Language,
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Gerencia chaves de API no KWallet
    Keys {
        #[command(subcommand)]
        action: KeysAction,
    },
    /// Aplica um perfil de primeiro boot e o nome do mascote
    Setup {
        #[arg(long, help = "Perfil do primeiro boot")]
        profile: String,
        #[arg(long, help = "Nome do mascote")]
        mascot: String,
        #[arg(long, default_value = "pt-BR")]
        language: String,
        #[arg(long, default_value = "br")]
        keyboard: String,
        #[arg(long)]
        unity: bool,
        #[arg(long = "claude-code")]
        claude_code: bool,
        #[arg(long)]
        github: bool,
        #[arg(long, help = "Instala Dev Containers CLI")]
        devcontainers: bool,
        #[arg(
            long,
            help = "Instala VS Code e extensão Dev Containers (software Microsoft)"
        )]
        vscode_devcontainers: bool,
        #[arg(long = "api-key")]
        api_keys: Vec<String>,
    },
    /// Verifica o sistema (kernel, GPU, Docker, Git, IA, serviços, portas) e sai com código ≠ 0 se algo crítico falhar
    Doctor {
        /// Saída em JSON para scripts
        #[arg(long)]
        json: bool,
    },
    /// Instala ferramentas de desenvolvimento no espaço do usuário
    Install {
        #[command(subcommand)]
        package: InstallPackage,
    },
    /// Cria ambientes Distrobox rootless usando Podman
    Box {
        #[command(subcommand)]
        action: BoxAction,
    },
    /// Instala e configura Docker CE em modo rootless
    Docker {
        #[command(subcommand)]
        action: DockerAction,
    },
}

#[derive(Subcommand)]
enum KeysAction {
    /// Lê uma chave sem eco e a grava no KWallet
    Set { provider: String },
    /// Adiciona chaves SSH ao agente do usuário com prompt KWallet
    SshAdd {
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum InstallPackage {
    /// Baixa o Unity Hub oficial como AppImage em ~/.local
    Unity {
        /// Confirma a instalação sem interação
        #[arg(short, long)]
        yes: bool,
        /// Emite somente o resultado estruturado em JSON
        #[arg(long)]
        json: bool,
    },
    /// Instala Claude Code pelo instalador oficial da Anthropic
    #[command(name = "claude-code")]
    ClaudeCode {
        /// Confirma a instalação sem interação
        #[arg(short, long)]
        yes: bool,
        /// Emite somente o resultado estruturado em JSON
        #[arg(long)]
        json: bool,
    },
    /// Instala Homebrew no diretório do usuário
    Homebrew {
        #[arg(short, long)]
        yes: bool,
        #[arg(long)]
        json: bool,
    },
    /// Instala o CLI oficial Dev Containers no usuário
    Devcontainers {
        #[arg(short, long)]
        yes: bool,
        #[arg(long)]
        json: bool,
    },
    /// Instala VS Code e a extensão Dev Containers para o usuário
    VscodeDevcontainers {
        #[arg(short, long)]
        yes: bool,
        #[arg(long)]
        json: bool,
    },
}

#[derive(Clone, Copy, ValueEnum)]
enum BoxDistro {
    Ubuntu,
    Arch,
    Fedora,
}

impl BoxDistro {
    fn as_str(self) -> &'static str {
        match self {
            Self::Ubuntu => "ubuntu",
            Self::Arch => "arch",
            Self::Fedora => "fedora",
        }
    }
}

#[derive(Subcommand)]
enum BoxAction {
    /// Cria a caixa e entra nela; --json cria e informa o comando de entrada
    Create {
        #[arg(value_enum)]
        distro: BoxDistro,
        #[arg(long)]
        name: Option<String>,
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum DockerAction {
    /// Instala Docker CE pela fonte oficial (requer reinicialização)
    Install {
        #[arg(short, long)]
        yes: bool,
        #[arg(long)]
        json: bool,
    },
    /// Configura Docker rootless depois de reiniciar
    SetupRootless {
        #[arg(long)]
        json: bool,
    },
}

fn main() {
    let args = std::env::args_os().collect::<Vec<OsString>>();
    let lang = selected_language(&args);
    let matches = localized_command(Cli::command(), lang)
        .try_get_matches_from(args)
        .unwrap_or_else(|error| error.exit());
    let cli = Cli::from_arg_matches(&matches).expect("parse CLI arguments");
    let _language = cli.lang;
    let code = match cli.command {
        Command::Keys {
            action: KeysAction::Set { provider },
        } => {
            match std::process::Command::new("/usr/bin/python3")
                .args(["/usr/libexec/forjaos/keys.py", &provider])
                .status()
            {
                Ok(status) => status.code().unwrap_or(1),
                Err(error) => {
                    eprintln!("forja keys: {error}");
                    1
                }
            }
        }
        Command::Keys {
            action: KeysAction::SshAdd { json },
        } => dev::ssh_add(json),
        Command::Setup {
            profile,
            mascot,
            language,
            keyboard,
            unity,
            claude_code,
            github,
            devcontainers,
            vscode_devcontainers,
            api_keys,
        } => {
            let mut command = std::process::Command::new("/usr/bin/python3");
            command.arg("/usr/libexec/forjaos/setup_profile.py").args([
                "--profile",
                &profile,
                "--mascot",
                &mascot,
                "--language",
                &language,
                "--keyboard",
                &keyboard,
            ]);
            if unity {
                command.arg("--unity");
            }
            if claude_code {
                command.arg("--claude-code");
            }
            if github {
                command.arg("--github");
            }
            if devcontainers {
                command.arg("--devcontainers");
            }
            if vscode_devcontainers {
                command.arg("--vscode-devcontainers");
            }
            for provider in api_keys {
                command.args(["--api-key", &provider]);
            }
            match command.status() {
                Ok(status) => status.code().unwrap_or(1),
                Err(error) => {
                    eprintln!("forja setup: {error}");
                    1
                }
            }
        }
        Command::Doctor { json } => doctor::run(json),
        Command::Install { package } => match package {
            InstallPackage::Unity { yes, json } => install::unity(yes, json),
            InstallPackage::ClaudeCode { yes, json } => install::claude_code(yes, json),
            InstallPackage::Homebrew { yes, json } => install::homebrew(yes, json),
            InstallPackage::Devcontainers { yes, json } => install::devcontainers(yes, json),
            InstallPackage::VscodeDevcontainers { yes, json } => {
                install::vscode_devcontainers(yes, json)
            }
        },
        Command::Box { action } => match action {
            BoxAction::Create { distro, name, json } => {
                dev::box_create(distro.as_str(), name.as_deref(), json)
            }
        },
        Command::Docker { action } => match action {
            DockerAction::Install { yes, json } => dev::docker_install(yes, json),
            DockerAction::SetupRootless { json } => dev::docker_setup_rootless(json),
        },
    };
    std::process::exit(code);
}

fn selected_language(args: &[OsString]) -> Language {
    let environment_language = std::env::var("FORJA_LANG").ok();
    let explicit = args
        .windows(2)
        .find(|pair| pair[0] == "--lang")
        .and_then(|pair| pair[1].to_str())
        .or_else(|| {
            args.iter()
                .find_map(|arg| arg.to_str()?.strip_prefix("--lang="))
        })
        .or(environment_language.as_deref());
    match explicit {
        Some(value) if value.eq_ignore_ascii_case("en") => Language::En,
        _ => Language::PtBr,
    }
}

fn localized_command(command: clap::Command, lang: Language) -> clap::Command {
    let english = lang == Language::En;
    let (about, usage, commands) = if english {
        (
            "ForjaOS: diagnostics, installation, and assistant in one command",
            "Usage",
            "Commands",
        )
    } else {
        (
            "ForjaOS: diagnóstico, instalação e assistente em um comando",
            "Uso",
            "Comandos",
        )
    };
    let template =
        format!("{{name}} {{version}}\n{{about-with-newline}}\n{usage}: {{usage}}\n\n{{all-args}}");
    let mut command = command
        .about(about)
        .bin_name("forja")
        .disable_help_subcommand(true)
        .help_template(template)
        .subcommand_help_heading(commands)
        .mut_arg("lang", |arg| {
            arg.help(if english {
                "Help language: pt-br or en"
            } else {
                "Idioma da ajuda: pt-br ou en"
            })
            .default_value(if english { "en" } else { "pt-br" })
        })
        .mut_subcommands(|subcommand| {
            subcommand
                .disable_help_subcommand(true)
                .subcommand_help_heading(commands)
        });

    if english {
        command = command
            .mut_subcommand("keys", |keys| {
                keys.about("Store API keys in KWallet")
                    .mut_subcommand("set", |set| set.about("Read and store a key without echo"))
                    .mut_subcommand("ssh-add", |ssh| {
                        ssh.about("Load SSH keys through the KWallet passphrase prompt")
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
            })
            .mut_subcommand("doctor", |doctor| {
                doctor
                    .about("Check the system and report critical failures")
                    .mut_arg("json", |arg| arg.help("Output JSON for scripts"))
            })
            .mut_subcommand("setup", |setup| {
                setup
                    .about("Apply a first-boot profile and mascot")
                    .mut_arg("profile", |arg| arg.help("First-boot profile"))
                    .mut_arg("mascot", |arg| arg.help("Mascot name"))
                    .mut_arg("language", |arg| arg.help("Interface language"))
                    .mut_arg("keyboard", |arg| arg.help("Keyboard layout"))
                    .mut_arg("unity", |arg| arg.help("Install Unity Hub"))
                    .mut_arg("claude_code", |arg| arg.help("Install Claude Code"))
                    .mut_arg("github", |arg| arg.help("Run GitHub CLI authentication"))
                    .mut_arg("devcontainers", |arg| {
                        arg.help("Install Dev Containers CLI")
                    })
                    .mut_arg("vscode_devcontainers", |arg| {
                        arg.help("Install Microsoft's VS Code and Dev Containers extension")
                    })
                    .mut_arg("api_keys", |arg| {
                        arg.help("Store a provider key in KWallet")
                    })
            })
            .mut_subcommand("install", |install| {
                install
                    .about("Install optional development tools for the current user")
                    .disable_help_subcommand(true)
                    .mut_subcommand("unity", |unity| {
                        unity
                            .disable_help_subcommand(true)
                            .about("Download the official Unity Hub AppImage into ~/.local")
                            .mut_arg("yes", |arg| {
                                arg.help("Confirm installation without interaction")
                            })
                            .mut_arg("json", |arg| {
                                arg.help("Output only the structured JSON result")
                            })
                    })
                    .mut_subcommand("claude-code", |claude| {
                        claude
                            .disable_help_subcommand(true)
                            .about("Install Claude Code with Anthropic's official installer")
                            .mut_arg("yes", |arg| {
                                arg.help("Confirm installation without interaction")
                            })
                            .mut_arg("json", |arg| {
                                arg.help("Output only the structured JSON result")
                            })
                    })
                    .mut_subcommand("homebrew", |brew| {
                        brew.about("Install Homebrew in a user-owned Linux prefix")
                            .mut_arg("yes", |arg| arg.help("Confirm without interaction"))
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
                    .mut_subcommand("devcontainers", |devcontainers| {
                        devcontainers
                            .about("Install the official Dev Containers CLI")
                            .mut_arg("yes", |arg| arg.help("Confirm without interaction"))
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
                    .mut_subcommand("vscode-devcontainers", |vscode| {
                        vscode
                            .about("Install Microsoft's VS Code and the Dev Containers extension")
                            .mut_arg("yes", |arg| arg.help("Confirm without interaction"))
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
            })
            .mut_subcommand("box", |box_command| {
                box_command
                    .about("Create rootless Distrobox environments with Podman")
                    .mut_subcommand("create", |create| {
                        create
                            .about("Create and enter a supported distro container")
                            .mut_arg("name", |arg| arg.help("Container name"))
                            .mut_arg("json", |arg| {
                                arg.help("Create only and print the enter command")
                            })
                    })
            })
            .mut_subcommand("docker", |docker| {
                docker
                    .about("Install and configure Docker CE rootless")
                    .mut_subcommand("install", |install| {
                        install
                            .about("Install Docker CE from the official repository")
                            .mut_arg("yes", |arg| {
                                arg.help("Confirm installation without interaction")
                            })
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
                    .mut_subcommand("setup-rootless", |setup| {
                        setup
                            .about("Configure rootless Docker after reboot")
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
            });
    }
    command = command
        .mut_subcommand("keys", |keys| {
            let keys = keys
                .mut_subcommand("set", |set| localized_help(set, lang, "forja keys set"))
                .mut_subcommand("ssh-add", |ssh| {
                    localized_help(ssh, lang, "forja keys ssh-add")
                });
            localized_help(keys, lang, "forja keys")
        })
        .mut_subcommand("doctor", |doctor| {
            localized_help(doctor, lang, "forja doctor")
        })
        .mut_subcommand("install", |install| {
            let install = install
                .disable_help_subcommand(true)
                .mut_subcommand("unity", |unity| {
                    localized_help(unity, lang, "forja install unity")
                })
                .mut_subcommand("claude-code", |claude| {
                    localized_help(claude, lang, "forja install claude-code")
                })
                .mut_subcommand("homebrew", |brew| {
                    localized_help(brew, lang, "forja install homebrew")
                })
                .mut_subcommand("devcontainers", |devcontainers| {
                    localized_help(devcontainers, lang, "forja install devcontainers")
                })
                .mut_subcommand("vscode-devcontainers", |vscode| {
                    localized_help(vscode, lang, "forja install vscode-devcontainers")
                });
            localized_help(install, lang, "forja install")
        })
        .mut_subcommand("box", |box_command| {
            let box_command = box_command.mut_subcommand("create", |create| {
                localized_help(create, lang, "forja box create")
            });
            localized_help(box_command, lang, "forja box")
        })
        .mut_subcommand("docker", |docker| {
            let docker = docker
                .mut_subcommand("install", |install| {
                    localized_help(install, lang, "forja docker install")
                })
                .mut_subcommand("setup-rootless", |setup| {
                    localized_help(setup, lang, "forja docker setup-rootless")
                });
            localized_help(docker, lang, "forja docker")
        });
    localized_help(command, lang, "forja")
}

fn localized_help(command: clap::Command, lang: Language, bin_name: &str) -> clap::Command {
    if lang == Language::En {
        return command;
    }
    let rendered = command
        .clone()
        .bin_name(bin_name)
        .render_help()
        .to_string()
        .replace("Usage:", "Uso:")
        .replace("Options:", "Opções:")
        .replace("<COMMAND>", "<COMANDO>")
        .replace("[OPTIONS]", "[OPÇÕES]")
        .replace("Print help", "Exibe ajuda")
        .replace("Print version", "Exibe a versão");
    command.override_help(rendered)
}

#[cfg(test)]
mod tests {
    use super::{localized_command, Cli, Language};
    use clap::CommandFactory;

    #[test]
    fn command_tree_is_well_formed_and_includes_f2_002() {
        let command = Cli::command();
        command.clone().debug_assert();
        let names = command
            .get_subcommands()
            .map(|subcommand| subcommand.get_name())
            .collect::<Vec<_>>();
        assert!(names.contains(&"box"));
        assert!(names.contains(&"docker"));
        assert!(names.contains(&"install"));
    }

    #[test]
    fn english_help_localizes_new_commands() {
        let help = localized_command(Cli::command(), Language::En)
            .render_long_help()
            .to_string();
        assert!(help.contains("Create rootless Distrobox environments with Podman"));
        assert!(help.contains("Install and configure Docker CE rootless"));
        assert!(!help.contains("Cria ambientes Distrobox"));
    }
}
