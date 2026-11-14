//! `forja` — porta de entrada do ForjaOS (ADR-020). Subcomandos entram aqui conforme os itens do TODO.
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
        Command::Doctor { json } => doctor::run(json),
        Command::Install { package } => match package {
            InstallPackage::Unity { yes, json } => install::unity(yes, json),
            InstallPackage::ClaudeCode { yes, json } => install::claude_code(yes, json),
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
            .mut_subcommand("doctor", |doctor| {
                doctor
                    .about("Check the system and report critical failures")
                    .mut_arg("json", |arg| arg.help("Output JSON for scripts"))
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
            });
    }
    command = command
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
                });
            localized_help(install, lang, "forja install")
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
