mod actions;
mod ai;
mod audit;
mod persona;
mod policy;
mod router;
mod routes;
#[cfg(unix)]
mod socket;
#[cfg(test)]
mod test_support;

use policy::{Classification, Proposal, Tier};
use serde_json::json;
use std::collections::{HashMap, VecDeque};
use std::io::Read;
use std::time::{Duration, Instant};
use tokio::sync::watch;
use zbus::{connection, fdo, interface, object_server::SignalEmitter};

const BUS_NAME: &str = "org.forjaos.Hero";
const OBJECT_PATH: &str = "/org/forjaos/Hero";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum State {
    Off,
    Idle,
    Listening,
    Recording,
    Transcribing,
    Thinking,
    Speaking,
    Error,
}

impl State {
    fn as_str(self) -> &'static str {
        match self {
            Self::Off => "desligado",
            Self::Idle => "ocioso",
            Self::Listening => "escutando",
            Self::Recording => "gravando",
            Self::Transcribing => "transcrevendo",
            Self::Thinking => "pensando",
            Self::Speaking => "falando",
            Self::Error => "erro",
        }
    }

    fn parse(value: &str) -> Option<Self> {
        Some(match value {
            "desligado" => Self::Off,
            "ocioso" => Self::Idle,
            "escutando" => Self::Listening,
            "gravando" => Self::Recording,
            "transcrevendo" => Self::Transcribing,
            "pensando" => Self::Thinking,
            "falando" => Self::Speaking,
            "erro" => Self::Error,
            _ => return None,
        })
    }

    fn can_transition_to(self, next: Self) -> bool {
        matches!(
            (self, next),
            (Self::Off, Self::Idle)
                | (
                    Self::Idle,
                    Self::Off | Self::Listening | Self::Thinking | Self::Error
                )
                | (
                    Self::Listening,
                    Self::Off | Self::Idle | Self::Recording | Self::Error
                )
                | (
                    Self::Recording,
                    Self::Off | Self::Idle | Self::Transcribing | Self::Error
                )
                | (
                    Self::Transcribing,
                    Self::Off | Self::Idle | Self::Thinking | Self::Error
                )
                | (
                    Self::Thinking,
                    Self::Off | Self::Idle | Self::Speaking | Self::Error
                )
                | (
                    Self::Speaking,
                    Self::Off | Self::Idle | Self::Listening | Self::Error
                )
                | (Self::Error, Self::Off | Self::Idle)
        )
    }
}

struct Hero {
    state: State,
    state_tx: watch::Sender<&'static str>,
    pending: HashMap<String, PendingAction>,
    history: VecDeque<ai::Turn>,
}

struct PendingAction {
    proposal: Proposal,
    expires_at: Instant,
}

impl Hero {
    async fn transition_to(
        &mut self,
        next: &str,
        emitter: &SignalEmitter<'_>,
    ) -> fdo::Result<bool> {
        let Some(next) = State::parse(next) else {
            return Err(fdo::Error::InvalidArgs("estado HERO desconhecido".into()));
        };
        if self.state == next {
            return Ok(false);
        }
        if !self.state.can_transition_to(next) {
            return Err(fdo::Error::InvalidArgs(
                "transição de estado HERO inválida".into(),
            ));
        }
        self.state = next;
        let _ = self.state_tx.send(next.as_str());
        Self::state_changed(self, emitter).await?;
        Self::state_transitioned(emitter, next.as_str()).await?;
        Ok(true)
    }
}

#[interface(name = "org.forjaos.Hero")]
impl Hero {
    #[zbus(property)]
    fn state(&self) -> String {
        self.state.as_str().to_string()
    }

    #[zbus(signal, name = "StateChanged")]
    async fn state_transitioned(emitter: &SignalEmitter<'_>, state: &str) -> zbus::Result<()>;

    async fn ask_text(
        &mut self,
        query: &str,
        cwd: &str,
        snapshot_json: &str,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> String {
        if snapshot_json.len() > 1024 {
            return json!({"status":"invalid_snapshot","answer":"Contexto do aplicativo inválido."}).to_string();
        }
        let snapshot = match serde_json::from_str::<ai::SnapshotDoApp>(snapshot_json) {
            Ok(snapshot) => snapshot,
            Err(_) => {
                return json!({"status":"invalid_snapshot","answer":"Contexto do aplicativo inválido."}).to_string()
            }
        };
        let resolved_project =
            policy::resolve_project_context(cwd, query, snapshot.window_title.as_deref());
        let effective_cwd = resolved_project
            .as_ref()
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_else(|| cwd.to_string());
        self.pending
            .retain(|_, pending| pending.expires_at > Instant::now());
        if self.state != State::Idle {
            return ai::busy();
        }
        let _ = self.transition_to("pensando", &emitter).await;
        let result = match policy::classify(query, &effective_cwd) {
            Classification::Conversation => {
                let route = router::classify(query).await;
                let context = snapshot_context(route, &effective_cwd, &snapshot);
                let history = self.history.iter().cloned().collect::<Vec<_>>();
                let response = ai::ask(query, route, &context, &snapshot, &history).await;
                if let Ok(value) = serde_json::from_str::<serde_json::Value>(&response) {
                    if value["status"] == "ok" {
                        if let Some(answer) = value["answer"].as_str() {
                            self.history.push_back(ai::Turn {
                                user: query.to_string(),
                                assistant: answer.to_string(),
                            });
                            while self.history.len() > 10 {
                                self.history.pop_front();
                            }
                        }
                    }
                }
                response
            }
            Classification::Blocked {
                route,
                tool,
                message,
            } => {
                audit::record(route, tool, "bloqueado", "recusado", 0);
                json!({
                    "status":"blocked",
                    "route":route,
                    "tool":tool,
                    "context":"nenhum",
                    "tier":"bloqueado",
                    "requires_confirmation":false,
                    "answer":message
                })
                .to_string()
            }
            Classification::Proposal(proposal) => match proposal.tier {
                Tier::Alter => match confirmation_id() {
                    Some(id) => {
                        audit::record(
                            proposal.route,
                            proposal.tool,
                            "alterar",
                            "confirmacao_pendente",
                            0,
                        );
                        let response = json!({
                            "status":"confirmation_required",
                            "route":proposal.route,
                            "tool":proposal.tool,
                            "context":&proposal.context,
                            "tier":"alterar",
                            "requires_confirmation":true,
                            "confirmation_id":&id,
                            "answer":format!("Confirme a ação {}.", proposal.tool)
                        })
                        .to_string();
                        self.pending.insert(
                            id,
                            PendingAction {
                                proposal,
                                expires_at: Instant::now() + Duration::from_secs(120),
                            },
                        );
                        response
                    }
                    None => {
                        audit::record(
                            proposal.route,
                            proposal.tool,
                            proposal.tier.as_str(),
                            "confirmacao_indisponivel",
                            0,
                        );
                        json!({
                            "status":"confirmation_unavailable",
                            "route":proposal.route,
                            "tool":proposal.tool,
                            "context":proposal.context,
                            "tier":"alterar",
                            "requires_confirmation":true,
                            "answer":"Não foi possível criar uma confirmação segura; nenhuma ação foi executada."
                        }).to_string()
                    }
                },
                Tier::Free => {
                    let started = Instant::now();
                    let result = actions::execute(proposal.action.clone()).await;
                    let elapsed = started.elapsed().as_millis();
                    let (status, decision, answer) = match result {
                        Ok(answer) => ("ok", "executado", answer),
                        Err(error) => ("action_failed", "falha", error),
                    };
                    audit::record(proposal.route, proposal.tool, "livre", decision, elapsed);
                    json!({
                        "status":status,
                        "route":proposal.route,
                        "tool":proposal.tool,
                        "context":proposal.context,
                        "tier":"livre",
                        "requires_confirmation":false,
                        "answer":answer
                    })
                    .to_string()
                }
                Tier::Blocked => {
                    audit::record(
                        proposal.route,
                        proposal.tool,
                        proposal.tier.as_str(),
                        "recusado",
                        0,
                    );
                    json!({
                        "status":"blocked",
                        "route":proposal.route,
                        "tool":proposal.tool,
                        "context":proposal.context,
                        "tier":"bloqueado",
                        "requires_confirmation":false,
                        "answer":"Esta ferramenta está bloqueada pela política local. Nenhuma ação foi executada."
                    }).to_string()
                }
            },
        };
        let _ = self.transition_to("ocioso", &emitter).await;
        result
    }

    async fn confirm_action(
        &mut self,
        id: &str,
        approved: bool,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> String {
        if approved && self.state != State::Idle {
            return ai::busy();
        }
        let Some(pending) = self.pending.remove(id) else {
            return json!({"status":"confirmation_not_found"}).to_string();
        };
        let proposal = pending.proposal;
        if pending.expires_at <= Instant::now() {
            audit::record(
                proposal.route,
                proposal.tool,
                proposal.tier.as_str(),
                "expirado",
                0,
            );
            return json!({
                "status":"confirmation_expired",
                "route":proposal.route,
                "tool":proposal.tool,
                "tier":proposal.tier.as_str(),
                "answer":"A confirmação expirou. Solicite a ação novamente."
            })
            .to_string();
        }
        if !approved {
            audit::record(
                proposal.route,
                proposal.tool,
                proposal.tier.as_str(),
                "cancelado",
                0,
            );
            return json!({
                "status":"cancelled",
                "route":proposal.route,
                "tool":proposal.tool,
                "tier":proposal.tier.as_str(),
                "answer":"Ação cancelada; nada foi executado."
            })
            .to_string();
        }
        let _ = self.transition_to("pensando", &emitter).await;
        let started = Instant::now();
        let result = actions::execute(proposal.action).await;
        actions::record_hero_action(proposal.tool, result.is_ok(), &proposal.context).await;
        let elapsed = started.elapsed().as_millis();
        let (status, decision, answer) = match result {
            Ok(answer) => ("ok", "executado", answer),
            Err(error) => ("action_failed", "falha", error),
        };
        audit::record(
            proposal.route,
            proposal.tool,
            proposal.tier.as_str(),
            decision,
            elapsed,
        );
        let response = json!({
            "status":status,
            "route":proposal.route,
            "tool":proposal.tool,
            "context":proposal.context,
            "tier":proposal.tier.as_str(),
            "requires_confirmation":false,
            "answer":answer
        })
        .to_string();
        let _ = self.transition_to("ocioso", &emitter).await;
        response
    }

    fn route_providers(&self) -> String {
        routes::list_json().unwrap_or_else(|error| json!({"error":error}).to_string())
    }

    fn set_route_provider(
        &mut self,
        route: &str,
        provider: &str,
        model: &str,
    ) -> fdo::Result<String> {
        routes::set_provider(route, provider, model)
            .map_err(|error| fdo::Error::InvalidArgs(error.into()))
    }

    fn persona(&self) -> String {
        serde_json::to_string(&persona::load()).unwrap_or_else(|_| "{}".to_string())
    }

    fn set_persona_instructions(&mut self, instructions: &str) -> fdo::Result<String> {
        persona::set_instructions(instructions)
            .map_err(|error| fdo::Error::InvalidArgs(error.into()))
    }

    fn tool_tiers(&self) -> String {
        policy::tool_tiers_json().unwrap_or_else(|error| json!({"error":error}).to_string())
    }

    fn set_tool_tier(&mut self, tool: &str, tier: &str) -> fdo::Result<String> {
        policy::set_tool_tier(tool, tier).map_err(|error| fdo::Error::InvalidArgs(error.into()))
    }

    fn save_routine(
        &mut self,
        id: &str,
        steps_json: &str,
        maximum_tier: &str,
    ) -> fdo::Result<String> {
        policy::save_routine(id, steps_json, maximum_tier)
            .map_err(|error| fdo::Error::InvalidArgs(error.into()))
    }
}

fn snapshot_context(route: &str, cwd: &str, snapshot: &ai::SnapshotDoApp) -> String {
    let mut parts = Vec::new();
    if let Some(application) = snapshot.application.as_deref() {
        let application = application
            .chars()
            .filter(|character| !character.is_control())
            .take(100)
            .collect::<String>();
        if !application.is_empty() {
            parts.push(format!("aplicativo: {application}"));
        }
    }
    if let Some(title) = snapshot.window_title.as_deref() {
        let title = title
            .chars()
            .filter(|character| !character.is_control())
            .take(160)
            .collect::<String>();
        if !title.is_empty() {
            parts.push(format!("janela: {title}"));
        }
    }
    if matches!(route, "código" | "criação") {
        if let Some(project) = std::path::Path::new(cwd)
            .file_name()
            .and_then(|name| name.to_str())
        {
            parts.push(format!("projeto atual: {project}"));
        }
    }
    if parts.is_empty() {
        "nenhum contexto adicional".to_string()
    } else {
        parts.join("; ")
    }
}

fn confirmation_id() -> Option<String> {
    let mut bytes = [0u8; 24];
    std::fs::File::open("/dev/urandom")
        .and_then(|mut source| source.read_exact(&mut bytes))
        .ok()?;
    Some(bytes.iter().map(|byte| format!("{byte:02x}")).collect())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let (state_tx, state_rx) = watch::channel(State::Idle.as_str());
    #[cfg(unix)]
    let state_socket = socket::bind()?;
    #[cfg(not(unix))]
    let _ = state_rx;
    let hero = Hero {
        state: State::Idle,
        state_tx,
        pending: HashMap::new(),
        history: VecDeque::new(),
    };
    let _connection = connection::Builder::session()?
        .name(BUS_NAME)?
        .serve_at(OBJECT_PATH, hero)?
        .build()
        .await?;

    #[cfg(unix)]
    socket::serve(state_socket, state_rx).await?;
    #[cfg(not(unix))]
    std::future::pending::<()>().await;
    Ok(())
}

#[cfg(test)]
mod tests {
    #[cfg(unix)]
    use super::confirmation_id;
    use super::{snapshot_context, Hero, PendingAction, State};
    use crate::ai::SnapshotDoApp;
    use std::collections::{HashMap, VecDeque};
    use tokio::sync::watch;

    #[test]
    fn state_names_round_trip_and_unknown_values_are_rejected() {
        for (state, name) in [
            (State::Off, "desligado"),
            (State::Idle, "ocioso"),
            (State::Listening, "escutando"),
            (State::Recording, "gravando"),
            (State::Transcribing, "transcrevendo"),
            (State::Thinking, "pensando"),
            (State::Speaking, "falando"),
            (State::Error, "erro"),
        ] {
            assert_eq!(state.as_str(), name);
            assert_eq!(State::parse(name), Some(state));
        }
        assert_eq!(State::parse("unknown"), None);
    }

    #[test]
    fn state_machine_accepts_only_declared_transitions() {
        let states = [
            State::Off,
            State::Idle,
            State::Listening,
            State::Recording,
            State::Transcribing,
            State::Thinking,
            State::Speaking,
            State::Error,
        ];
        let allowed = [
            (State::Off, State::Idle),
            (State::Idle, State::Off),
            (State::Idle, State::Listening),
            (State::Idle, State::Thinking),
            (State::Idle, State::Error),
            (State::Listening, State::Off),
            (State::Listening, State::Idle),
            (State::Listening, State::Recording),
            (State::Listening, State::Error),
            (State::Recording, State::Off),
            (State::Recording, State::Idle),
            (State::Recording, State::Transcribing),
            (State::Recording, State::Error),
            (State::Transcribing, State::Off),
            (State::Transcribing, State::Idle),
            (State::Transcribing, State::Thinking),
            (State::Transcribing, State::Error),
            (State::Thinking, State::Off),
            (State::Thinking, State::Idle),
            (State::Thinking, State::Speaking),
            (State::Thinking, State::Error),
            (State::Speaking, State::Off),
            (State::Speaking, State::Idle),
            (State::Speaking, State::Listening),
            (State::Speaking, State::Error),
            (State::Error, State::Off),
            (State::Error, State::Idle),
        ];
        for from in states {
            for to in states {
                assert_eq!(
                    from.can_transition_to(to),
                    allowed.contains(&(from, to)),
                    "transição {} -> {}",
                    from.as_str(),
                    to.as_str()
                );
            }
        }
    }

    #[test]
    fn snapshot_context_is_sanitized_and_limited_to_relevant_routes() {
        let empty = SnapshotDoApp::default();
        assert_eq!(
            snapshot_context("sistema", "/home/rodri/game-api", &empty),
            "nenhum contexto adicional"
        );
        let snapshot = SnapshotDoApp {
            application: Some("Konsole\nnoise".into()),
            window_title: Some("issue\u{7} #92".into()),
            ..SnapshotDoApp::default()
        };
        assert_eq!(
            snapshot_context("código", "/home/rodri/game-api", &snapshot),
            "aplicativo: Konsolenoise; janela: issue #92; projeto atual: game-api"
        );
        assert_eq!(
            snapshot_context("criação", "/home/rodri/game-api", &SnapshotDoApp::default()),
            "projeto atual: game-api"
        );
        let long = SnapshotDoApp {
            application: Some("x".repeat(150)),
            ..SnapshotDoApp::default()
        };
        assert_eq!(
            snapshot_context("sistema", ".", &long).chars().count(),
            "aplicativo: ".chars().count() + 100
        );
    }

    #[test]
    fn hero_properties_and_invalid_setters_are_safe() {
        let (state_tx, _) = watch::channel(State::Idle.as_str());
        let mut hero = Hero {
            state: State::Idle,
            state_tx,
            pending: HashMap::<String, PendingAction>::new(),
            history: VecDeque::new(),
        };
        assert_eq!(hero.state(), "ocioso");
        assert!(hero.set_route_provider("unknown", "ollama", "").is_err());
        assert!(hero.set_persona_instructions("inválido\u{7}").is_err());
        assert!(hero.set_tool_tier("unknown.tool", "livre").is_err());
        assert!(hero.save_routine("invalid id", "[]", "livre").is_err());
    }

    #[cfg(unix)]
    #[test]
    fn confirmation_ids_are_192_bit_hex_tokens() {
        let id = confirmation_id().expect("/dev/urandom available");
        assert_eq!(id.len(), 48);
        assert!(id.chars().all(|character| character.is_ascii_hexdigit()));
    }
}
