//! `forja` — porta de entrada do ForjaOS (ADR-020). Subcomandos entram aqui conforme os itens do TODO.
mod ai;
mod dev;
mod doctor;
mod install;
mod mascot;
mod memory;

use clap::{CommandFactory, FromArgMatches, Parser, Subcommand, ValueEnum};
use clap_complete::{generate, Shell};
use std::ffi::OsString;
use std::io;

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
    /// Envia uma pergunta ao HERO local pela sessão D-Bus
    Ai {
        #[arg(required_unless_present = "confirm")]
        query: Option<String>,
        /// Confirma uma ação pendente pelo identificador emitido pelo HERO
        #[arg(long, conflicts_with = "query")]
        confirm: Option<String>,
        #[arg(long)]
        json: bool,
    },
    /// Busca e mantém notas locais do vault ForjaOS
    Memory {
        #[command(subcommand)]
        action: MemoryAction,
    },
    /// Configura nome, voz e treino do mascote HERO
    Mascot {
        #[command(subcommand)]
        action: MascotAction,
    },
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
        #[arg(long)]
        json: bool,
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
    /// Controla o Modo Jogo do usuário
    GameMode {
        #[command(subcommand)]
        action: GameModeAction,
    },
    /// Atalhos para o Compose do projeto atual
    Up {
        #[arg(long)]
        json: bool,
    },
    Down {
        #[arg(long)]
        json: bool,
    },
    Logs {
        #[arg(long)]
        json: bool,
    },
    /// Gera completions para o shell informado
    Completions {
        #[arg(value_enum)]
        shell: Shell,
    },
    /// Gera um relatório sanitizado para diagnóstico
    Report {
        #[arg(long)]
        json: bool,
    },
    /// Baixa e prepara a atualização bootc
    Update {
        #[arg(short, long)]
        yes: bool,
        #[arg(long)]
        json: bool,
    },
    /// Agenda a implantação anterior para o próximo boot
    Rollback {
        #[arg(short, long)]
        yes: bool,
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum KeysAction {
    /// Lê uma chave sem eco e a grava no KWallet
    Set {
        provider: String,
        #[arg(long)]
        json: bool,
    },
    /// Adiciona chaves SSH ao agente do usuário com prompt KWallet
    SshAdd {
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum MemoryAction {
    /// Busca notas do vault local
    Search {
        query: String,
        #[arg(long, default_value_t = 20)]
        limit: u32,
        #[arg(long)]
        json: bool,
    },
    /// Lista notas recentes do vault
    Timeline {
        #[arg(long, default_value_t = 1)]
        days: u32,
        #[arg(long, default_value_t = 100)]
        limit: u32,
        #[arg(long)]
        json: bool,
    },
    /// Reconstrói o índice e o grafo a partir do vault Markdown
    Rebuild {
        #[arg(long)]
        json: bool,
    },
    /// Salva uma nota no vault local
    Remember {
        note: String,
        #[arg(long)]
        json: bool,
    },
    /// Abre o visualizador local do vault
    Viewer {
        #[arg(long)]
        json: bool,
    },
    /// Executa o servidor MCP da Memória usando stdio
    Mcp,
}

#[derive(Subcommand)]
enum MascotAction {
    /// Mostra nome e disponibilidade da voz selecionada
    Status {
        #[arg(long)]
        json: bool,
    },
    /// Altera o nome exibido pelo mascote
    Name {
        name: String,
        #[arg(long)]
        json: bool,
    },
    /// Seleciona uma voz Piper já instalada localmente
    Voice {
        voice: String,
        #[arg(long)]
        json: bool,
    },
    /// Inicia treino local de uma wake word personalizada
    Train {
        name: String,
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

#[derive(Subcommand)]
enum GameModeAction {
    /// Mantém o Modo Jogo ativo até ser desligado
    On {
        #[arg(long)]
        json: bool,
    },
    /// Desliga o Modo Jogo até o jogo atual sair
    Off {
        #[arg(long)]
        json: bool,
    },
    /// Informa se o Modo Jogo está ativo
    Status {
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
        Command::Ai {
            query,
            confirm,
            json,
        } => ai::run(query.as_deref(), confirm.as_deref(), json),
        Command::Memory { action } => match action {
            MemoryAction::Search { query, limit, json } => memory::search(&query, limit, json),
            MemoryAction::Timeline { days, limit, json } => memory::timeline(days, limit, json),
            MemoryAction::Rebuild { json } => memory::rebuild(json),
            MemoryAction::Remember { note, json } => memory::remember(&note, json),
            MemoryAction::Viewer { json } => memory::viewer(json),
            MemoryAction::Mcp => memory::mcp(),
        },
        Command::Mascot { action } => match action {
            MascotAction::Status { json } => mascot::status(json),
            MascotAction::Name { name, json } => mascot::set_name(&name, json),
            MascotAction::Voice { voice, json } => mascot::set_voice(&voice, json),
            MascotAction::Train { name, json } => mascot::train(&name, json),
        },
        Command::Keys {
            action: KeysAction::Set { provider, json },
        } => {
            let result = std::process::Command::new("/usr/bin/python3")
                .args(["/usr/libexec/forjaos/keys.py", &provider])
                .stdout(if json {
                    std::process::Stdio::null()
                } else {
                    std::process::Stdio::inherit()
                })
                .status();
            let code = match result {
                Ok(status) => status.code().unwrap_or(1),
                Err(error) => {
                    if !json {
                        eprintln!("forja keys: {error}");
                    }
                    1
                }
            };
            if json {
                println!(
                    "{}",
                    serde_json::json!({"command":"keys set", "provider":provider, "status": if code == 0 { "ok" } else { "error" }, "exit_code":code})
                );
            }
            code
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
            json,
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
            if json {
                command.stdout(std::process::Stdio::null());
            }
            match command.status() {
                Ok(status) => {
                    let code = status.code().unwrap_or(1);
                    if json {
                        println!(
                            "{}",
                            serde_json::json!({"command":"setup", "status": if code == 0 { "ok" } else { "error" }, "exit_code":code})
                        );
                    }
                    code
                }
                Err(error) => {
                    if json {
                        println!(
                            "{}",
                            serde_json::json!({"command":"setup", "status":"error"})
                        );
                    } else {
                        eprintln!("forja setup: {error}");
                    }
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
        Command::GameMode { action } => {
            let (operation, json) = match action {
                GameModeAction::On { json } => ("on", json),
                GameModeAction::Off { json } => ("off", json),
                GameModeAction::Status { json } => ("status", json),
            };
            let mut process = std::process::Command::new("/usr/bin/python3");
            process.args(["/usr/libexec/forjaos/game_mode.py", operation]);
            if json {
                process.arg("--json");
            }
            match process.status() {
                Ok(status) => status.code().unwrap_or(1),
                Err(error) => {
                    eprintln!("forja game-mode: {error}");
                    1
                }
            }
        }
        Command::Up { json } => dev::compose("up", json),
        Command::Down { json } => dev::compose("down", json),
        Command::Logs { json } => dev::compose("logs", json),
        Command::Completions { shell } => {
            generate(shell, &mut Cli::command(), "forja", &mut io::stdout());
            0
        }
        Command::Report { json } => doctor::report(json),
        Command::Update { yes, json } => dev::bootc_action("upgrade", yes, json),
        Command::Rollback { yes, json } => dev::bootc_action("rollback", yes, json),
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
            .mut_subcommand("ai", |ai| {
                ai.about("Send a question to the local HERO assistant")
                    .mut_arg("query", |arg| arg.help("Question to send"))
                    .mut_arg("confirm", |arg| arg.help("Confirm a pending action ID"))
                    .mut_arg("json", |arg| arg.help("Output JSON"))
            })
            .mut_subcommand("memory", |memory| {
                memory
                    .about("Search and maintain the local ForjaOS vault")
                    .mut_subcommand("search", |action| {
                        action
                            .about("Search Markdown notes")
                            .mut_arg("query", |arg| arg.help("Search expression"))
                            .mut_arg("limit", |arg| arg.help("Maximum results"))
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
                    .mut_subcommand("timeline", |action| {
                        action
                            .about("List recent notes")
                            .mut_arg("days", |arg| arg.help("Look-back period in days"))
                            .mut_arg("limit", |arg| arg.help("Maximum entries"))
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
                    .mut_subcommand("rebuild", |action| {
                        action
                            .about("Rebuild the index and graph from Markdown")
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
                    .mut_subcommand("remember", |action| {
                        action
                            .about("Save a note in the local vault")
                            .mut_arg("note", |arg| arg.help("Note text"))
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
                    .mut_subcommand("viewer", |action| {
                        action
                            .about("Open the local vault viewer")
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
                    .mut_subcommand("mcp", |action| {
                        action.about("Run the Memory MCP server over stdio")
                    })
            })
            .mut_subcommand("mascot", |mascot| {
                mascot
                    .about("Configure the HERO mascot name and voice")
                    .mut_subcommand("status", |action| {
                        action
                            .about("Show mascot and local model availability")
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
                    .mut_subcommand("name", |action| {
                        action
                            .about("Set the display name")
                            .mut_arg("name", |arg| arg.help("Mascot name"))
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
                    .mut_subcommand("voice", |action| {
                        action
                            .about("Select an installed local Piper voice")
                            .mut_arg("voice", |arg| arg.help("Local voice model ID"))
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
                    .mut_subcommand("train", |action| {
                        action
                            .about("Train a custom local wake word")
                            .mut_arg("name", |arg| arg.help("Wake word name"))
                            .mut_arg("json", |arg| arg.help("Output JSON"))
                    })
            })
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
            })
            .mut_subcommand("game-mode", |game| {
                game.about("Control per-user Game Mode")
                    .mut_subcommand("on", |on| {
                        on.about("Keep Game Mode active until turned off")
                    })
                    .mut_subcommand("off", |off| {
                        off.about("Turn off Game Mode until the current game exits")
                    })
                    .mut_subcommand("status", |status| status.about("Show Game Mode state"))
            })
            .mut_subcommand("up", |action| {
                action.about("Start current project services")
            })
            .mut_subcommand("down", |action| {
                action.about("Stop current project services")
            })
            .mut_subcommand("logs", |action| action.about("Show current project logs"))
            .mut_subcommand("completions", |completion| {
                completion.about("Generate shell completion script")
            })
            .mut_subcommand("report", |report| {
                report
                    .about("Create a sanitized diagnostic report")
                    .mut_arg("json", |arg| arg.help("Output JSON only"))
            })
            .mut_subcommand("up", |action| {
                action.mut_arg("json", |arg| arg.help("Output JSON"))
            })
            .mut_subcommand("down", |action| {
                action.mut_arg("json", |arg| arg.help("Output JSON"))
            })
            .mut_subcommand("logs", |action| {
                action.mut_arg("json", |arg| arg.help("Output JSON"))
            })
            .mut_subcommand("update", |action| {
                action
                    .about("Download and queue a bootc update")
                    .mut_arg("yes", |arg| arg.help("Confirm without interaction"))
                    .mut_arg("json", |arg| arg.help("Output JSON"))
            })
            .mut_subcommand("rollback", |action| {
                action
                    .about("Queue the previous bootc deployment")
                    .mut_arg("yes", |arg| arg.help("Confirm without interaction"))
                    .mut_arg("json", |arg| arg.help("Output JSON"))
            });
    }
    command = command
        .mut_subcommand("ai", |ai| {
            localized_help(
                ai.about("Envia uma pergunta ao assistente local HERO")
                    .mut_arg("query", |arg| arg.help("Pergunta para o HERO"))
                    .mut_arg("confirm", |arg| arg.help("Confirma uma ação pendente"))
                    .mut_arg("json", |arg| arg.help("Emite JSON")),
                lang,
                "forja ai",
            )
        })
        .mut_subcommand("mascot", |mascot| {
            localized_help(
                mascot
                    .about("Configura nome e voz do mascote HERO")
                    .mut_subcommand("status", |action| {
                        action
                            .about("Mostra o mascote e os modelos locais")
                            .mut_arg("json", |arg| arg.help("Emite JSON"))
                    })
                    .mut_subcommand("name", |action| {
                        action
                            .about("Altera o nome exibido")
                            .mut_arg("name", |arg| arg.help("Nome do mascote"))
                            .mut_arg("json", |arg| arg.help("Emite JSON"))
                    })
                    .mut_subcommand("voice", |action| {
                        action
                            .about("Seleciona uma voz Piper local instalada")
                            .mut_arg("voice", |arg| arg.help("ID do modelo de voz local"))
                            .mut_arg("json", |arg| arg.help("Emite JSON"))
                    })
                    .mut_subcommand("train", |action| {
                        action
                            .about("Treina uma wake word personalizada local")
                            .mut_arg("name", |arg| arg.help("Nome da wake word"))
                            .mut_arg("json", |arg| arg.help("Emite JSON"))
                    }),
                lang,
                "forja mascot",
            )
        })
        .mut_subcommand("memory", |memory| {
            let memory = memory
                .mut_subcommand("search", |action| {
                    let action = action
                        .about("Pesquisa notas Markdown")
                        .mut_arg("query", |arg| arg.help("Texto para pesquisar"))
                        .mut_arg("limit", |arg| arg.help("Máximo de resultados"))
                        .mut_arg("json", |arg| arg.help("Emite JSON"));
                    localized_help(action, lang, "forja memory search")
                })
                .mut_subcommand("timeline", |action| {
                    let action = action
                        .about("Lista notas recentes")
                        .mut_arg("days", |arg| arg.help("Período em dias"))
                        .mut_arg("limit", |arg| arg.help("Máximo de registros"))
                        .mut_arg("json", |arg| arg.help("Emite JSON"));
                    localized_help(action, lang, "forja memory timeline")
                })
                .mut_subcommand("rebuild", |action| {
                    let action = action
                        .about("Reconstrói o índice e o grafo a partir do vault")
                        .mut_arg("json", |arg| arg.help("Emite JSON"));
                    localized_help(action, lang, "forja memory rebuild")
                })
                .mut_subcommand("remember", |action| {
                    let action = action
                        .about("Salva uma nota no vault local")
                        .mut_arg("note", |arg| arg.help("Texto da nota"))
                        .mut_arg("json", |arg| arg.help("Emite JSON"));
                    localized_help(action, lang, "forja memory remember")
                })
                .mut_subcommand("viewer", |action| {
                    let action = action
                        .about("Abre o visualizador local do vault")
                        .mut_arg("json", |arg| arg.help("Emite JSON"));
                    localized_help(action, lang, "forja memory viewer")
                })
                .mut_subcommand("mcp", |action| {
                    localized_help(
                        action.about("Executa o servidor MCP da Memória por stdio"),
                        lang,
                        "forja memory mcp",
                    )
                });
            localized_help(
                memory.about("Busca e mantém o vault local ForjaOS"),
                lang,
                "forja memory",
            )
        })
        .mut_subcommand("keys", |keys| {
            let keys = keys
                .mut_subcommand("set", |set| {
                    let help = if lang == Language::En {
                        "Output JSON"
                    } else {
                        "Emite JSON"
                    };
                    localized_help(set, lang, "forja keys set")
                        .mut_arg("json", |arg| arg.help(help))
                })
                .mut_subcommand("ssh-add", |ssh| {
                    localized_help(ssh, lang, "forja keys ssh-add")
                });
            localized_help(keys, lang, "forja keys")
        })
        .mut_subcommand("doctor", |doctor| {
            localized_help(doctor, lang, "forja doctor")
        })
        .mut_subcommand("setup", |setup| {
            let help = if lang == Language::En {
                "Output JSON"
            } else {
                "Emite JSON"
            };
            localized_help(setup, lang, "forja setup").mut_arg("json", |arg| arg.help(help))
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
        })
        .mut_subcommand("game-mode", |game| {
            let game = game
                .mut_subcommand("on", |on| localized_help(on, lang, "forja game-mode on"))
                .mut_subcommand("off", |off| {
                    localized_help(off, lang, "forja game-mode off")
                })
                .mut_subcommand("status", |status| {
                    localized_help(status, lang, "forja game-mode status")
                });
            localized_help(game, lang, "forja game-mode")
        })
        .mut_subcommand("up", |action| localized_help(action, lang, "forja up"))
        .mut_subcommand("down", |action| localized_help(action, lang, "forja down"))
        .mut_subcommand("logs", |action| localized_help(action, lang, "forja logs"))
        .mut_subcommand("completions", |completion| {
            localized_help(completion, lang, "forja completions")
        })
        .mut_subcommand("report", |report| {
            report
                .about("Gera um relatório de diagnóstico sanitizado")
                .mut_arg("json", |arg| arg.help("Emite somente JSON"))
        })
        .mut_subcommand("up", |action| {
            localized_help(action, lang, "forja up").mut_arg("json", |arg| arg.help("Emite JSON"))
        })
        .mut_subcommand("down", |action| {
            localized_help(action, lang, "forja down").mut_arg("json", |arg| arg.help("Emite JSON"))
        })
        .mut_subcommand("logs", |action| {
            localized_help(action, lang, "forja logs").mut_arg("json", |arg| arg.help("Emite JSON"))
        })
        .mut_subcommand("update", |action| {
            let about = if lang == Language::En {
                "Download and queue a bootc update"
            } else {
                "Baixa e prepara a atualização bootc"
            };
            localized_help(action.about(about), lang, "forja update")
                .mut_arg("yes", |arg| arg.help("Confirma sem interação"))
                .mut_arg("json", |arg| arg.help("Emite JSON"))
        })
        .mut_subcommand("rollback", |action| {
            let about = if lang == Language::En {
                "Queue the previous bootc deployment"
            } else {
                "Agenda a implantação bootc anterior"
            };
            localized_help(action.about(about), lang, "forja rollback")
                .mut_arg("yes", |arg| arg.help("Confirma sem interação"))
                .mut_arg("json", |arg| arg.help("Emite JSON"))
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
        assert!(names.contains(&"game-mode"));
    }

    #[test]
    fn english_help_localizes_new_commands() {
        let help = localized_command(Cli::command(), Language::En)
            .render_long_help()
            .to_string();
        assert!(help.contains("Create rootless Distrobox environments with Podman"));
        assert!(help.contains("Install and configure Docker CE rootless"));
        assert!(help.contains("Control per-user Game Mode"));
        assert!(!help.contains("Cria ambientes Distrobox"));
    }
}
