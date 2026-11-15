use std::path::PathBuf;

#[derive(Clone, Copy)]
pub enum Tier {
    Free,
    Alter,
}

impl Tier {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Free => "livre",
            Self::Alter => "alterar",
        }
    }
}

#[derive(Clone)]
pub enum Action {
    GameMode(bool),
    Compose { up: bool, cwd: PathBuf },
    GitStatus(PathBuf),
    GpuStatus,
    OpenUrl(String),
    MemorySearch(String),
    Remember(String),
    Update,
    Rollback,
    RestartUserService(String),
}

pub struct Proposal {
    pub route: &'static str,
    pub context: String,
    pub tool: &'static str,
    pub tier: Tier,
    pub action: Action,
}

pub enum Classification {
    Conversation,
    Proposal(Proposal),
    Blocked {
        route: &'static str,
        message: String,
    },
}

pub fn classify(query: &str, cwd: &str) -> Classification {
    let text = query.trim().to_lowercase();
    let cwd = PathBuf::from(cwd);
    let context = cwd
        .canonicalize()
        .map(|path| path.display().to_string())
        .unwrap_or_else(|_| "diretório atual indisponível".into());

    let proposal = if starts_with_any(
        &text,
        &["ative modo jogo", "ligue modo jogo", "ligue o modo jogo"],
    ) {
        Some((
            "sistema",
            "game_mode.toggle",
            Tier::Alter,
            Action::GameMode(true),
        ))
    } else if starts_with_any(
        &text,
        &[
            "desative modo jogo",
            "desligue modo jogo",
            "desligue o modo jogo",
        ],
    ) {
        Some((
            "sistema",
            "game_mode.toggle",
            Tier::Alter,
            Action::GameMode(false),
        ))
    } else if starts_with_any(
        &text,
        &[
            "suba compose",
            "suba o compose",
            "inicie compose",
            "inicie o compose",
        ],
    ) {
        Some((
            "sistema",
            "compose.up",
            Tier::Alter,
            Action::Compose {
                up: true,
                cwd: cwd.clone(),
            },
        ))
    } else if starts_with_any(
        &text,
        &[
            "derrube compose",
            "derrube o compose",
            "pare compose",
            "pare o compose",
        ],
    ) {
        Some((
            "sistema",
            "compose.down",
            Tier::Alter,
            Action::Compose {
                up: false,
                cwd: cwd.clone(),
            },
        ))
    } else if starts_with_any(
        &text,
        &[
            "git status",
            "mostre o status do git",
            "mostre status do git",
        ],
    ) {
        Some((
            "código",
            "git.status",
            Tier::Free,
            Action::GitStatus(cwd.clone()),
        ))
    } else if starts_with_any(
        &text,
        &["mostre gpu", "status da gpu", "mostre o status da gpu"],
    ) {
        Some((
            "saúde-do-sistema",
            "gpu.status",
            Tier::Free,
            Action::GpuStatus,
        ))
    } else if text.starts_with("abra ") {
        let rest = query.trim().get(5..).unwrap_or("").trim();
        let normalized_url = rest.to_ascii_lowercase();
        if (normalized_url.starts_with("https://") || normalized_url.starts_with("http://"))
            && !rest
                .chars()
                .any(|character| character.is_whitespace() || character.is_control())
            && rest
                .split_once("://")
                .is_some_and(|(_, host)| !host.is_empty())
        {
            Some((
                "criação",
                "desktop.open_url",
                Tier::Free,
                Action::OpenUrl(rest.to_string()),
            ))
        } else {
            None
        }
    } else if let Some(rest) = text.strip_prefix("busque na memória ") {
        if rest.trim().is_empty() {
            None
        } else {
            Some((
                "memória",
                "memory.search",
                Tier::Free,
                Action::MemorySearch(rest.to_string()),
            ))
        }
    } else if let Some(rest) = text.strip_prefix("crie uma nota ") {
        Some((
            "memória",
            "memory.remember",
            Tier::Free,
            Action::Remember(rest.to_string()),
        ))
    } else if starts_with_any(&text, &["atualize o sistema", "atualize sistema"]) {
        Some(("sistema", "system.update", Tier::Alter, Action::Update))
    } else if starts_with_any(
        &text,
        &[
            "reverta a atualização",
            "volte a atualização",
            "faça rollback",
        ],
    ) {
        Some(("sistema", "system.rollback", Tier::Alter, Action::Rollback))
    } else if let Some(service) = text
        .strip_prefix("reinicie serviço ")
        .or_else(|| text.strip_prefix("reinicie o serviço "))
    {
        let service = service.trim();
        if valid_unit_name(service) {
            Some((
                "sistema",
                "services.restart",
                Tier::Alter,
                Action::RestartUserService(service.to_string()),
            ))
        } else {
            None
        }
    } else {
        None
    };

    if let Some((route, tool, tier, action)) = proposal {
        return Classification::Proposal(Proposal {
            route,
            context,
            tool,
            tier,
            action,
        });
    }

    if starts_with_any(
        &text,
        &[
            "apague ",
            "remova ",
            "rode rm ",
            "execute rm ",
            "execute dd ",
            "mude o firewall",
            "altere /etc",
        ],
    ) {
        return Classification::Blocked {
            route: "sistema",
            message:
                "Esta ação está bloqueada pelo manifesto de segurança. Nenhum dado foi alterado."
                    .into(),
        };
    }

    if starts_with_any(
        &text,
        &[
            "instale ",
            "execute ",
            "rode ",
            "atualize ",
            "reinicie ",
            "ligue ",
            "desligue ",
            "abra ",
            "crie ",
            "suba ",
            "derrube ",
        ],
    ) {
        return Classification::Blocked {
            route: "sistema",
            message: "Ainda não há uma ferramenta permitida para esta solicitação. Nenhuma ação foi executada.".into(),
        };
    }

    Classification::Conversation
}

fn starts_with_any(text: &str, prefixes: &[&str]) -> bool {
    prefixes.iter().any(|prefix| text.starts_with(prefix))
}

fn valid_unit_name(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value.chars().all(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '@' | '_' | '-' | '.' | ':')
        })
}
