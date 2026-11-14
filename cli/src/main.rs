//! `forja` — porta de entrada do ForjaOS (ADR-020). Subcomandos entram aqui conforme os itens do TODO.
mod doctor;

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "forja", version, about = "ForjaOS: diagnóstico, instalação e assistente em um comando")]
struct Cli {
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
}

fn main() {
    let cli = Cli::parse();
    let code = match cli.command {
        Command::Doctor { json } => doctor::run(json),
    };
    std::process::exit(code);
}
