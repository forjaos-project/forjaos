mod actions;
mod ai;
mod audit;
mod persona;
mod policy;
mod router;
mod routes;
mod session_lock;
#[cfg(unix)]
mod socket;
#[cfg(test)]
mod test_support;
mod voice;

use policy::{Classification, Proposal, Tier};
use serde_json::json;
use std::collections::{HashMap, VecDeque};
use std::io::Read;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{mpsc, oneshot, watch};
use zbus::{connection, fdo, interface, object_server::SignalEmitter};

const BUS_NAME: &str = "org.forjaos.Hero";
const OBJECT_PATH: &str = "/org/forjaos/Hero";
const VOICE_FAILURE_MESSAGE: &str = "Desculpe, não consegui responder agora.";
const VOICE_ACTION_TIMEOUT_MESSAGE: &str =
    "O turno expirou. Verifique o estado da ação antes de repetir.";

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
    state_epoch: Arc<AtomicU64>,
    microphone_enabled: bool,
    mic_stream: Option<voice::MicStream>,
    wake_detector: Option<voice::WakeDetector>,
    capture: Option<voice::Capture>,
    capture_origin: Option<CaptureOrigin>,
    voice_origin: CaptureOrigin,
    wake_endpoint: Option<voice::WakeEndpoint>,
    voice_generation: u64,
    voice_tx: mpsc::UnboundedSender<VoiceEvent>,
    stt_task: Option<tokio::task::JoinHandle<()>>,
    thinking_task: Option<tokio::task::JoinHandle<()>>,
    active_voice_action: Option<ActiveVoiceAction>,
    speech: Option<SpeechTask>,
    pending: HashMap<String, PendingAction>,
    voice_pending_id: Option<String>,
    history: VecDeque<ai::Turn>,
}

enum VoiceEvent {
    Trigger(TriggerRequest),
    WakeDetected(u64),
    WakeEndpointFinished(u64, voice::WakeEndpointResult),
    CaptureExpired(u64),
    TurnExpired(u64),
    Transcribed(u64, Result<String, &'static str>),
    TurnCompleted(u64, String, String),
    ActionCompleted(VoiceActionResult),
    SpeechCompleted(u64, Result<(), &'static str>),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum CaptureOrigin {
    PushToTalk,
    WakeWord,
}

impl CaptureOrigin {
    fn as_str(self) -> &'static str {
        match self {
            Self::PushToTalk => "push_to_talk",
            Self::WakeWord => "wake_word",
        }
    }
}

#[derive(Clone, Copy)]
enum TriggerMode {
    Start,
    Stop,
    Toggle,
}

struct TriggerRequest {
    mode: TriggerMode,
    epoch: u64,
    response: oneshot::Sender<String>,
}

struct VoiceTrigger {
    state_rx: watch::Receiver<&'static str>,
    state_epoch: Arc<AtomicU64>,
    voice_tx: mpsc::UnboundedSender<VoiceEvent>,
}

#[interface(name = "org.forjaos.Hero.Trigger")]
impl VoiceTrigger {
    async fn start_push_to_talk(
        &self,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> String {
        self.dispatch(TriggerMode::Start, emitter).await
    }

    async fn stop_push_to_talk(
        &self,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> String {
        self.dispatch(TriggerMode::Stop, emitter).await
    }

    async fn toggle_push_to_talk(
        &self,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> String {
        self.dispatch(TriggerMode::Toggle, emitter).await
    }
}

impl VoiceTrigger {
    async fn dispatch(&self, mode: TriggerMode, emitter: SignalEmitter<'_>) -> String {
        let epoch = self.state_epoch.load(Ordering::SeqCst);
        let state = *self.state_rx.borrow();
        if !trigger_allowed(mode, state) {
            let _ = Hero::voice_ignored(&emitter, state).await;
            audit_voice(
                "conversa-de-voz",
                "audio.trigger",
                "livre",
                "ignorado_ocupado",
                0,
            );
            return ai::busy();
        }
        let (response, receiver) = oneshot::channel();
        if self
            .voice_tx
            .send(VoiceEvent::Trigger(TriggerRequest {
                mode,
                epoch,
                response,
            }))
            .is_err()
        {
            return json!({"status":"unavailable"}).to_string();
        }
        match tokio::time::timeout(Duration::from_secs(5), receiver).await {
            Ok(Ok(reply)) => reply,
            _ => json!({"status":"unavailable"}).to_string(),
        }
    }
}

fn trigger_allowed(mode: TriggerMode, state: &str) -> bool {
    match mode {
        TriggerMode::Start => matches!(state, "ocioso" | "falando" | "gravando"),
        TriggerMode::Stop => state == "gravando",
        TriggerMode::Toggle => matches!(state, "ocioso" | "falando" | "gravando"),
    }
}

struct VoiceActionResult {
    generation: u64,
    result: Result<String, String>,
}

struct ActiveVoiceAction {
    route: &'static str,
    tool: &'static str,
    tier: Tier,
}

struct SpeechTask {
    cancel: oneshot::Sender<()>,
    task: tokio::task::JoinHandle<()>,
}

struct PendingAction {
    proposal: Proposal,
    expires_at: Instant,
}

impl Hero {
    async fn handle_voice_event(&mut self, event: VoiceEvent, emitter: &SignalEmitter<'_>) {
        match event {
            VoiceEvent::Trigger(request) => {
                if request.response.is_closed() {
                    return;
                }
                let state = self.state.as_str();
                if request.epoch != self.state_epoch.load(Ordering::SeqCst)
                    || !trigger_allowed(request.mode, state)
                {
                    let _ = Self::voice_ignored(emitter, state).await;
                    audit_voice(
                        "conversa-de-voz",
                        "audio.trigger",
                        "livre",
                        "ignorado_ocupado",
                        0,
                    );
                    let _ = request.response.send(ai::busy());
                    return;
                }
                let reply = match request.mode {
                    TriggerMode::Start => self.start_push_to_talk(emitter.clone()).await,
                    TriggerMode::Stop => self.stop_push_to_talk(emitter.clone()).await,
                    TriggerMode::Toggle => self.toggle_push_to_talk(emitter.clone()).await,
                };
                let _ = request.response.send(reply);
            }
            VoiceEvent::WakeDetected(epoch) => {
                if epoch != self.state_epoch.load(Ordering::SeqCst)
                    || !matches!(self.state, State::Idle | State::Speaking)
                    || !self.microphone_enabled
                {
                    let _ = Self::voice_ignored(emitter, self.state.as_str()).await;
                    audit::record_trigger(
                        "wake_word",
                        "conversa-de-voz",
                        "audio.trigger",
                        "livre",
                        "ignorado_ocupado",
                        0,
                    );
                } else {
                    let _ = self
                        .start_capture(CaptureOrigin::WakeWord, emitter.clone())
                        .await;
                }
            }
            VoiceEvent::WakeEndpointFinished(generation, result)
                if generation == self.voice_generation
                    && self.capture_origin == Some(CaptureOrigin::WakeWord) =>
            {
                match result {
                    voice::WakeEndpointResult::SpeechComplete => {
                        let _ = self.stop_push_to_talk(emitter.clone()).await;
                    }
                    voice::WakeEndpointResult::NoSpeech
                    | voice::WakeEndpointResult::Disconnected => {
                        if let Some(endpoint) = self.wake_endpoint.take() {
                            endpoint.stop().await;
                        }
                        if let Some(capture) = self.capture.take() {
                            capture.cancel().await;
                        }
                        self.capture_origin = None;
                        self.voice_generation = self.voice_generation.wrapping_add(1);
                        let _ = self.transition_to("ocioso", emitter).await;
                        let _ = Self::voice_failed(
                            emitter,
                            match result {
                                voice::WakeEndpointResult::NoSpeech => "wake_no_speech",
                                _ => "pipewire_capture_failed",
                            },
                        )
                        .await;
                    }
                }
            }
            VoiceEvent::TurnExpired(generation)
                if generation == self.voice_generation
                    && matches!(
                        self.state,
                        State::Recording | State::Transcribing | State::Thinking | State::Speaking
                    ) =>
            {
                let stage = self.state;
                let active_action = self.active_voice_action.take();
                self.voice_generation = self.voice_generation.wrapping_add(1);
                if let Some(capture) = self.capture.take() {
                    capture.cancel().await;
                }
                if let Some(endpoint) = self.wake_endpoint.take() {
                    endpoint.stop().await;
                }
                self.capture_origin = None;
                if let Some(task) = self.stt_task.take() {
                    task.abort();
                }
                if let Some(task) = self.thinking_task.take() {
                    task.abort();
                }
                if let Some(speech) = self.speech.take() {
                    let _ = speech.cancel.send(());
                    let _ = speech.task.await;
                }
                if let Some(id) = self.voice_pending_id.take() {
                    self.pending.remove(&id);
                }
                if let Some(action) = &active_action {
                    self.audit_current(
                        action.route,
                        action.tool,
                        action.tier.as_str(),
                        "turno_expirado",
                        60_000,
                    );
                }
                let _ = self.transition_to("erro", emitter).await;
                let _ = self.transition_to("ocioso", emitter).await;
                if stage == State::Speaking {
                    let _ = Self::voice_failed(emitter, "speech_timeout").await;
                } else {
                    let message = if active_action.is_some() {
                        VOICE_ACTION_TIMEOUT_MESSAGE
                    } else {
                        VOICE_FAILURE_MESSAGE
                    };
                    let _ = Self::voice_answer(emitter, message).await;
                }
            }
            VoiceEvent::CaptureExpired(generation)
                if generation == self.voice_generation && self.capture.is_some() =>
            {
                if let Some(endpoint) = self.wake_endpoint.take() {
                    endpoint.stop().await;
                }
                if let Some(capture) = self.capture.take() {
                    capture.cancel().await;
                }
                self.capture_origin = None;
                let _ = self.transition_to("erro", emitter).await;
                let _ = self.transition_to("ocioso", emitter).await;
                let _ = Self::voice_failed(emitter, "audio_duration_exceeded").await;
            }
            VoiceEvent::Transcribed(generation, result)
                if generation == self.voice_generation && self.state == State::Transcribing =>
            {
                self.stt_task.take();
                match result {
                    Ok(text) => {
                        audit::record_trigger(
                            self.voice_origin.as_str(),
                            "conversa-de-voz",
                            "audio.transcribe",
                            "livre",
                            "transcrito",
                            0,
                        );
                        let _ = Self::voice_transcribed(emitter, &text).await;
                        let _ = self.transition_to("pensando", emitter).await;
                        self.handle_voice_text(text, generation, emitter).await;
                    }
                    Err(_error) => {
                        audit::record_trigger(
                            self.voice_origin.as_str(),
                            "conversa-de-voz",
                            "audio.transcribe",
                            "livre",
                            "falha",
                            0,
                        );
                        let _ = self.transition_to("pensando", emitter).await;
                        self.start_speech(VOICE_FAILURE_MESSAGE.to_string(), generation, emitter)
                            .await;
                    }
                }
            }
            VoiceEvent::TurnCompleted(generation, query, response)
                if generation == self.voice_generation && self.state == State::Thinking =>
            {
                self.thinking_task.take();
                let (answer, success) = voice_answer_from_reply(&response);
                if success {
                    self.history.push_back(ai::Turn {
                        user: query,
                        assistant: answer.clone(),
                    });
                    while self.history.len() > 10 {
                        self.history.pop_front();
                    }
                }
                self.start_speech(answer, generation, emitter).await;
            }
            VoiceEvent::ActionCompleted(completed)
                if completed.generation == self.voice_generation
                    && self.state == State::Thinking =>
            {
                self.thinking_task.take();
                self.active_voice_action.take();
                let answer = completed
                    .result
                    .unwrap_or_else(|_| VOICE_FAILURE_MESSAGE.into());
                self.start_speech(bounded_voice_answer(answer), completed.generation, emitter)
                    .await;
            }
            VoiceEvent::SpeechCompleted(generation, result)
                if generation == self.voice_generation && self.state == State::Speaking =>
            {
                self.speech.take();
                let _ = self.transition_to("ocioso", emitter).await;
                if let Err(error) = result {
                    if error != "speech_cancelled" {
                        let _ = Self::voice_failed(emitter, error).await;
                    }
                }
            }
            _ => {}
        }
    }

    async fn start_speech(&mut self, answer: String, generation: u64, emitter: &SignalEmitter<'_>) {
        let _ = Self::voice_answer(emitter, &answer).await;
        let _ = self.transition_to("falando", emitter).await;
        let (cancel, receiver) = oneshot::channel();
        let voice_tx = self.voice_tx.clone();
        let task = tokio::spawn(async move {
            let result = voice::speak(&answer, receiver).await;
            let _ = voice_tx.send(VoiceEvent::SpeechCompleted(generation, result));
        });
        self.speech = Some(SpeechTask { cancel, task });
    }

    async fn handle_voice_text(
        &mut self,
        text: String,
        generation: u64,
        emitter: &SignalEmitter<'_>,
    ) {
        if let Some(id) = self.voice_pending_id.take() {
            if let Some(pending) = self.pending.remove(&id) {
                let proposal = pending.proposal;
                if pending.expires_at <= Instant::now() {
                    self.audit_current(proposal.route, proposal.tool, "alterar", "expirado", 0);
                    self.start_speech(
                        "A confirmação expirou. Solicite a ação novamente.".into(),
                        generation,
                        emitter,
                    )
                    .await;
                    return;
                }
                if is_voice_confirmation(&text) {
                    if session_lock::locked(emitter.connection()).await {
                        self.audit_current(
                            proposal.route,
                            proposal.tool,
                            "alterar",
                            "sessao_bloqueada",
                            0,
                        );
                        self.start_speech(
                            "Desbloqueie a tela e solicite a ação novamente.".into(),
                            generation,
                            emitter,
                        )
                        .await;
                    } else {
                        self.start_voice_action(proposal, generation, true);
                    }
                    return;
                }
                self.audit_current(proposal.route, proposal.tool, "alterar", "cancelado", 0);
                if is_voice_cancellation(&text) {
                    self.start_speech(
                        "Ação cancelada; nada foi executado.".into(),
                        generation,
                        emitter,
                    )
                    .await;
                    return;
                }
            }
        }

        let project = policy::resolve_project_context("", &text, None)
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default();
        match policy::classify(&text, &project) {
            Classification::Conversation => {
                let history = self.history.iter().cloned().collect::<Vec<_>>();
                let voice_tx = self.voice_tx.clone();
                self.thinking_task = Some(tokio::spawn(async move {
                    let response = ai::ask(
                        &text,
                        "conversa-de-voz",
                        "nenhum contexto adicional",
                        &ai::SnapshotDoApp::default(),
                        &history,
                    )
                    .await;
                    let _ = voice_tx.send(VoiceEvent::TurnCompleted(generation, text, response));
                }));
            }
            Classification::Blocked {
                route,
                tool,
                message,
            } => {
                self.audit_current(route, tool, "bloqueado", "recusado", 0);
                self.start_speech(bounded_voice_answer(message), generation, emitter)
                    .await;
            }
            Classification::Proposal(proposal)
                if matches!(&proposal.action, policy::Action::CodeDelegate { .. }) =>
            {
                self.audit_current(
                    proposal.route,
                    proposal.tool,
                    proposal.tier.as_str(),
                    "requer_modo_texto",
                    0,
                );
                self.start_speech(
                    "Delegação de código requer o modo texto para acompanhar a tarefa longa. Nenhuma ação foi executada."
                        .into(),
                    generation,
                    emitter,
                )
                .await;
            }
            Classification::Proposal(proposal) => match proposal.tier {
                Tier::Blocked => {
                    self.audit_current(proposal.route, proposal.tool, "bloqueado", "recusado", 0);
                    self.start_speech(
                        "Esta ação está bloqueada pela política local.".into(),
                        generation,
                        emitter,
                    )
                    .await;
                }
                Tier::Alter => {
                    if session_lock::locked(emitter.connection()).await {
                        self.audit_current(
                            proposal.route,
                            proposal.tool,
                            "alterar",
                            "sessao_bloqueada",
                            0,
                        );
                        self.start_speech(
                            "Desbloqueie a tela antes de solicitar esta ação.".into(),
                            generation,
                            emitter,
                        )
                        .await;
                        return;
                    }
                    let Some(id) = confirmation_id() else {
                        self.start_speech(
                            "Não foi possível criar uma confirmação segura.".into(),
                            generation,
                            emitter,
                        )
                        .await;
                        return;
                    };
                    let prompt = format!(
                        "Confirma a ação {}? Pressione o botão de voz novamente e diga apenas confirmo ou cancelo.",
                        proposal.tool
                    );
                    self.audit_current(
                        proposal.route,
                        proposal.tool,
                        "alterar",
                        "confirmacao_pendente",
                        0,
                    );
                    self.pending.insert(
                        id.clone(),
                        PendingAction {
                            proposal,
                            expires_at: Instant::now() + Duration::from_secs(120),
                        },
                    );
                    self.voice_pending_id = Some(id);
                    self.start_speech(prompt, generation, emitter).await;
                }
                Tier::Free => {
                    if session_lock::locked(emitter.connection()).await
                        && !proposal.action.allowed_while_locked()
                    {
                        self.audit_current(
                            proposal.route,
                            proposal.tool,
                            "livre",
                            "sessao_bloqueada",
                            0,
                        );
                        self.start_speech(
                            "Desbloqueie a tela antes de solicitar esta ação.".into(),
                            generation,
                            emitter,
                        )
                        .await;
                    } else {
                        self.start_voice_action(proposal, generation, false);
                    }
                }
            },
        }
    }

    fn audit_current(
        &self,
        route: &str,
        tool: &str,
        tier: &str,
        decision: &str,
        duration_ms: u128,
    ) {
        audit::record_trigger(
            self.voice_origin.as_str(),
            route,
            tool,
            tier,
            decision,
            duration_ms,
        );
    }

    fn start_voice_action(&mut self, proposal: Proposal, generation: u64, approved: bool) {
        self.active_voice_action = Some(ActiveVoiceAction {
            route: proposal.route,
            tool: proposal.tool,
            tier: proposal.tier,
        });
        let voice_tx = self.voice_tx.clone();
        let origin = self.voice_origin.as_str();
        self.thinking_task = Some(tokio::spawn(async move {
            audit::record_trigger(
                origin,
                proposal.route,
                proposal.tool,
                proposal.tier.as_str(),
                "iniciado",
                0,
            );
            let started = Instant::now();
            let result = actions::execute(proposal.action).await;
            let elapsed_ms = started.elapsed().as_millis();
            audit::record_trigger(
                origin,
                proposal.route,
                proposal.tool,
                proposal.tier.as_str(),
                if result.is_ok() { "executado" } else { "falha" },
                elapsed_ms,
            );
            if approved {
                actions::record_hero_action(proposal.tool, result.is_ok(), &proposal.context).await;
            }
            let _ = voice_tx.send(VoiceEvent::ActionCompleted(VoiceActionResult {
                generation,
                result,
            }));
        }));
    }

    async fn start_push_to_talk(&mut self, emitter: SignalEmitter<'_>) -> String {
        if self.capture_origin == Some(CaptureOrigin::WakeWord) {
            if let Some(endpoint) = self.wake_endpoint.take() {
                endpoint.stop().await;
            }
            if let Some(capture) = self.capture.take() {
                capture.cancel().await;
            }
            self.capture_origin = None;
            let _ = self.transition_to("ocioso", &emitter).await;
        }
        self.start_capture(CaptureOrigin::PushToTalk, emitter).await
    }

    async fn start_capture(&mut self, origin: CaptureOrigin, emitter: SignalEmitter<'_>) -> String {
        if !self.microphone_enabled {
            return json!({"status":"microphone_disabled"}).to_string();
        }
        if !matches!(self.state, State::Idle | State::Speaking) || self.capture.is_some() {
            audit::record_trigger(
                origin.as_str(),
                "conversa-de-voz",
                "audio.trigger",
                "livre",
                "ignorado_ocupado",
                0,
            );
            let _ = Self::voice_ignored(&emitter, self.state.as_str()).await;
            return ai::busy();
        }
        if !self
            .mic_stream
            .as_ref()
            .is_some_and(voice::MicStream::is_ready)
        {
            audit::record_trigger(
                origin.as_str(),
                "conversa-de-voz",
                "audio.capture",
                "livre",
                "indisponivel",
                0,
            );
            return json!({"status":"capture_failed","reason":"pipewire_capture_unavailable"})
                .to_string();
        }
        self.voice_generation = self.voice_generation.wrapping_add(1);
        let generation = self.voice_generation;
        if let Some(speech) = self.speech.take() {
            let _ = speech.cancel.send(());
            let _ = speech.task.await;
            audit::record_trigger(
                origin.as_str(),
                "conversa-de-voz",
                "speech.cancel",
                "livre",
                "interrompido",
                0,
            );
        }
        let _ = self.transition_to("escutando", &emitter).await;
        let capture = self
            .mic_stream
            .as_ref()
            .map(voice::Capture::start_from_stream)
            .unwrap_or(Err("pipewire_capture_unavailable"));
        match capture {
            Ok(capture) => {
                self.capture = Some(capture);
                self.capture_origin = Some(origin);
                self.voice_origin = origin;
                let _ = self.transition_to("gravando", &emitter).await;
                if origin == CaptureOrigin::WakeWord {
                    if let Some(stream) = self.mic_stream.as_ref() {
                        let voice_tx = self.voice_tx.clone();
                        self.wake_endpoint =
                            Some(voice::WakeEndpoint::start(stream, move |result| {
                                let _ = voice_tx
                                    .send(VoiceEvent::WakeEndpointFinished(generation, result));
                            }));
                    }
                }
                let voice_tx = self.voice_tx.clone();
                tokio::spawn(async move {
                    tokio::time::sleep(Duration::from_secs(30)).await;
                    let _ = voice_tx.send(VoiceEvent::CaptureExpired(generation));
                });
                let voice_tx = self.voice_tx.clone();
                tokio::spawn(async move {
                    tokio::time::sleep(Duration::from_secs(60)).await;
                    let _ = voice_tx.send(VoiceEvent::TurnExpired(generation));
                });
                audit::record_trigger(
                    origin.as_str(),
                    "conversa-de-voz",
                    "audio.capture",
                    "livre",
                    "iniciado",
                    0,
                );
                json!({"status":"recording"}).to_string()
            }
            Err(error) => {
                let _ = self.transition_to("erro", &emitter).await;
                let _ = self.transition_to("ocioso", &emitter).await;
                json!({"status":"capture_failed","reason":error}).to_string()
            }
        }
    }

    async fn stop_push_to_talk(&mut self, emitter: SignalEmitter<'_>) -> String {
        if let Some(endpoint) = self.wake_endpoint.take() {
            endpoint.stop().await;
        }
        let Some(capture) = self.capture.take() else {
            return json!({"status":"not_recording"}).to_string();
        };
        self.capture_origin = None;
        let audio = match capture.finish().await {
            Ok(audio) => audio,
            Err(error) => {
                let _ = self.transition_to("erro", &emitter).await;
                let _ = self.transition_to("ocioso", &emitter).await;
                return json!({"status":"capture_failed","reason":error}).to_string();
            }
        };
        let _ = self.transition_to("transcrevendo", &emitter).await;
        let generation = self.voice_generation;
        let voice_tx = self.voice_tx.clone();
        self.stt_task = Some(tokio::spawn(async move {
            let result = voice::transcribe(&audio).await;
            drop(audio);
            let _ = voice_tx.send(VoiceEvent::Transcribed(generation, result));
        }));
        json!({"status":"transcribing"}).to_string()
    }

    async fn toggle_push_to_talk(&mut self, emitter: SignalEmitter<'_>) -> String {
        if self.capture_origin == Some(CaptureOrigin::WakeWord) {
            self.start_push_to_talk(emitter).await
        } else if self.capture.is_some() {
            self.stop_push_to_talk(emitter).await
        } else {
            self.start_push_to_talk(emitter).await
        }
    }

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
        self.state_epoch.fetch_add(1, Ordering::SeqCst);
        let _ = self.state_tx.send(next.as_str());
        Self::state_changed(self, emitter).await?;
        Self::state_transitioned(emitter, next.as_str()).await?;
        Ok(true)
    }
}

fn voice_answer_from_reply(response: &str) -> (String, bool) {
    let Ok(reply) = serde_json::from_str::<serde_json::Value>(response) else {
        return (VOICE_FAILURE_MESSAGE.to_string(), false);
    };
    if reply["status"] == "ok" {
        if let Some(answer) = reply["answer"].as_str() {
            let answer = answer.trim();
            if !answer.is_empty() && answer.chars().count() <= 4000 {
                return (answer.to_string(), true);
            }
        }
    }
    (VOICE_FAILURE_MESSAGE.to_string(), false)
}

fn bounded_voice_answer(answer: String) -> String {
    let answer = answer.trim();
    if answer.is_empty() || answer.chars().count() > 4000 {
        VOICE_FAILURE_MESSAGE.into()
    } else {
        answer.into()
    }
}

fn voice_control_word(text: &str) -> String {
    text.trim()
        .trim_end_matches(['.', '!', '?'])
        .trim()
        .to_lowercase()
}

fn is_voice_confirmation(text: &str) -> bool {
    voice_control_word(text) == "confirmo"
}

fn is_voice_cancellation(text: &str) -> bool {
    voice_control_word(text) == "cancelo"
}

fn audit_voice(route: &str, tool: &str, tier: &str, decision: &str, duration_ms: u128) {
    audit::record_trigger("push_to_talk", route, tool, tier, decision, duration_ms);
}

#[interface(name = "org.forjaos.Hero")]
impl Hero {
    #[zbus(property)]
    fn state(&self) -> String {
        self.state.as_str().to_string()
    }

    #[zbus(property)]
    fn microphone_enabled(&self) -> bool {
        self.microphone_enabled
    }

    #[zbus(property)]
    async fn set_microphone_enabled(
        &mut self,
        enabled: bool,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> fdo::Result<()> {
        if self.microphone_enabled == enabled {
            return Ok(());
        }
        voice::set_microphone_enabled(enabled).map_err(|error| fdo::Error::Failed(error.into()))?;
        self.microphone_enabled = enabled;
        if !enabled {
            if let Some(detector) = self.wake_detector.take() {
                detector.stop().await;
            }
            if let Some(endpoint) = self.wake_endpoint.take() {
                endpoint.stop().await;
            }
            if self.capture.is_some() || self.stt_task.is_some() {
                self.voice_generation = self.voice_generation.wrapping_add(1);
            }
            if let Some(capture) = self.capture.take() {
                capture.cancel().await;
            }
            self.capture_origin = None;
            if let Some(task) = self.stt_task.take() {
                task.abort();
            }
            if let Some(stream) = self.mic_stream.take() {
                stream.stop().await;
            }
        } else {
            let stream = voice::MicStream::start();
            let voice_tx = self.voice_tx.clone();
            self.wake_detector = voice::WakeDetector::start_configured(
                &stream,
                self.state_tx.subscribe(),
                self.state_epoch.clone(),
                move |epoch| {
                    let _ = voice_tx.send(VoiceEvent::WakeDetected(epoch));
                },
            );
            self.mic_stream = Some(stream);
        }
        if !enabled
            && matches!(
                self.state,
                State::Listening | State::Recording | State::Transcribing
            )
        {
            let _ = self.transition_to("ocioso", &emitter).await;
        }
        audit::record_trigger(
            "microphone",
            "microfone",
            "microphone.switch",
            "livre",
            if enabled { "ligado" } else { "desligado" },
            0,
        );
        Ok(())
    }

    #[zbus(signal, name = "StateChanged")]
    async fn state_transitioned(emitter: &SignalEmitter<'_>, state: &str) -> zbus::Result<()>;

    #[zbus(signal, name = "VoiceTranscribed")]
    async fn voice_transcribed(emitter: &SignalEmitter<'_>, text: &str) -> zbus::Result<()>;

    #[zbus(signal, name = "VoiceFailed")]
    async fn voice_failed(emitter: &SignalEmitter<'_>, reason: &str) -> zbus::Result<()>;

    #[zbus(signal, name = "VoiceAnswer")]
    async fn voice_answer(emitter: &SignalEmitter<'_>, answer: &str) -> zbus::Result<()>;

    #[zbus(signal, name = "VoiceIgnored")]
    async fn voice_ignored(emitter: &SignalEmitter<'_>, state: &str) -> zbus::Result<()>;

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
        if session_lock::locked(emitter.connection()).await {
            return json!({
                "status":"locked",
                "answer":"Desbloqueie a tela para usar o modo texto."
            })
            .to_string();
        }
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
                Tier::Alter if session_lock::locked(emitter.connection()).await => {
                    audit::record(
                        proposal.route,
                        proposal.tool,
                        "alterar",
                        "sessao_bloqueada",
                        0,
                    );
                    json!({
                        "status":"locked",
                        "route":proposal.route,
                        "tool":proposal.tool,
                        "context":proposal.context,
                        "tier":"alterar",
                        "requires_confirmation":false,
                        "answer":"Desbloqueie a tela antes de solicitar esta ação. Nenhuma ação foi executada."
                    }).to_string()
                }
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
        if approved && session_lock::locked(emitter.connection()).await {
            return json!({
                "status":"locked",
                "answer":"Desbloqueie a tela para confirmar esta ação. Nenhuma ação foi executada."
            })
            .to_string();
        }
        let Some(pending) = self.pending.remove(id) else {
            return json!({"status":"confirmation_not_found"}).to_string();
        };
        if self.voice_pending_id.as_deref() == Some(id) {
            self.voice_pending_id = None;
        }
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
    let state_epoch = Arc::new(AtomicU64::new(0));
    #[cfg(unix)]
    let state_socket = socket::bind()?;
    #[cfg(not(unix))]
    let _ = state_rx;
    let (voice_tx, mut voice_rx) = mpsc::unbounded_channel();
    let microphone_enabled = voice::microphone_enabled();
    let mic_stream = microphone_enabled.then(voice::MicStream::start);
    let wake_tx = voice_tx.clone();
    let wake_detector = mic_stream.as_ref().and_then(|stream| {
        voice::WakeDetector::start_configured(
            stream,
            state_rx.clone(),
            state_epoch.clone(),
            move |epoch| {
                let _ = wake_tx.send(VoiceEvent::WakeDetected(epoch));
            },
        )
    });
    let trigger = VoiceTrigger {
        state_rx: state_rx.clone(),
        state_epoch: state_epoch.clone(),
        voice_tx: voice_tx.clone(),
    };
    let hero = Hero {
        state: State::Idle,
        state_tx,
        state_epoch,
        microphone_enabled,
        mic_stream,
        wake_detector,
        capture: None,
        capture_origin: None,
        voice_origin: CaptureOrigin::PushToTalk,
        wake_endpoint: None,
        voice_generation: 0,
        voice_tx,
        stt_task: None,
        thinking_task: None,
        active_voice_action: None,
        speech: None,
        pending: HashMap::new(),
        voice_pending_id: None,
        history: VecDeque::new(),
    };
    let connection = connection::Builder::session()?
        .name(BUS_NAME)?
        .serve_at(OBJECT_PATH, hero)?
        .serve_at(OBJECT_PATH, trigger)?
        .build()
        .await?;

    #[cfg(unix)]
    let mut socket_task = tokio::spawn(socket::serve(state_socket, state_rx));
    #[cfg(unix)]
    loop {
        tokio::select! {
            Some(event) = voice_rx.recv() => {
                let interface = connection.object_server().interface::<_, Hero>(OBJECT_PATH).await?;
                interface.get_mut().await.handle_voice_event(event, interface.signal_emitter()).await;
            }
            result = &mut socket_task => {
                result??;
                break;
            }
        }
    }
    #[cfg(not(unix))]
    while let Some(event) = voice_rx.recv().await {
        let interface = connection
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await?;
        interface
            .get_mut()
            .await
            .handle_voice_event(event, interface.signal_emitter())
            .await;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    #[cfg(unix)]
    use super::confirmation_id;
    use super::{
        bounded_voice_answer, is_voice_cancellation, is_voice_confirmation, snapshot_context,
        voice_answer_from_reply, ActiveVoiceAction, CaptureOrigin, Hero, PendingAction, SpeechTask,
        State, TriggerMode, TriggerRequest, VoiceEvent, VoiceTrigger, OBJECT_PATH,
        VOICE_FAILURE_MESSAGE,
    };
    use crate::ai::SnapshotDoApp;
    #[cfg(unix)]
    use crate::policy::{Action, Proposal, Tier};
    use crate::test_support::TestHome;
    use crate::voice::{Capture, MicStream};
    use std::collections::{HashMap, VecDeque};
    use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
    use std::sync::Arc;
    use std::time::Duration;
    #[cfg(unix)]
    use std::time::Instant;
    use tokio::sync::{mpsc, oneshot, watch};
    use zbus::connection;

    struct TestScreenSaver {
        active: Arc<AtomicBool>,
    }

    #[zbus::interface(name = "org.freedesktop.ScreenSaver")]
    impl TestScreenSaver {
        fn get_active(&self) -> bool {
            self.active.load(Ordering::SeqCst)
        }
    }

    async fn voice_test_connection() -> (zbus::Connection, zbus::Connection) {
        voice_test_connection_with_lock(None).await
    }

    async fn voice_test_connection_with_lock(
        active: Option<Arc<AtomicBool>>,
    ) -> (zbus::Connection, zbus::Connection) {
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind private D-Bus peer");
        let peer = tokio::net::TcpStream::connect(listener.local_addr().expect("peer address"))
            .await
            .expect("connect private D-Bus peer");
        let server_stream = listener.accept().await.expect("accept private peer").0;
        let (state_tx, state_rx) = watch::channel(State::Idle.as_str());
        let (voice_tx, _) = mpsc::unbounded_channel();
        let state_epoch = Arc::new(AtomicU64::new(0));
        let trigger = VoiceTrigger {
            state_rx,
            state_epoch: state_epoch.clone(),
            voice_tx: voice_tx.clone(),
        };
        let hero = Hero {
            state: State::Idle,
            state_tx,
            state_epoch,
            microphone_enabled: true,
            mic_stream: None,
            wake_detector: None,
            capture: None,
            capture_origin: None,
            voice_origin: CaptureOrigin::PushToTalk,
            wake_endpoint: None,
            voice_generation: 0,
            voice_tx,
            stt_task: None,
            thinking_task: None,
            active_voice_action: None,
            speech: None,
            pending: HashMap::new(),
            voice_pending_id: None,
            history: VecDeque::new(),
        };
        let server = connection::Builder::tcp_stream(server_stream)
            .server(zbus::Guid::generate())
            .expect("server GUID")
            .p2p()
            .serve_at(OBJECT_PATH, hero)
            .expect("serve HERO")
            .serve_at(OBJECT_PATH, trigger)
            .expect("serve trigger");
        let client = connection::Builder::tcp_stream(peer).p2p();
        let client = if let Some(active) = active {
            client
                .serve_at("/ScreenSaver", TestScreenSaver { active })
                .expect("serve screen locker")
        } else {
            client
        };
        tokio::try_join!(server.build(), client.build()).expect("connect private D-Bus peer")
    }

    #[tokio::test]
    async fn direct_trigger_is_rejected_while_text_owns_the_hero_interface() {
        let (server, client) = voice_test_connection().await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let mut hero = interface.get_mut().await;
        hero.transition_to("pensando", interface.signal_emitter())
            .await
            .expect("text turn starts");
        let reply = tokio::time::timeout(
            Duration::from_secs(1),
            client.call_method(
                None::<&str>,
                OBJECT_PATH,
                Some("org.forjaos.Hero.Trigger"),
                "StartPushToTalk",
                &(),
            ),
        )
        .await
        .expect("trigger responds without waiting for text")
        .expect("trigger reply");
        let answer: String = reply.body().deserialize().expect("reply body");
        assert_eq!(answer, crate::ai::busy());
        assert_eq!(hero.state, State::Thinking);
        assert!(hero.capture.is_none());
    }

    #[tokio::test]
    async fn queued_trigger_does_not_start_after_a_text_turn_finishes() {
        let (server, _client) = voice_test_connection().await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let mut hero = interface.get_mut().await;
        let stale_epoch = hero.state_epoch.load(Ordering::SeqCst);
        hero.transition_to("pensando", interface.signal_emitter())
            .await
            .expect("text turn starts");
        hero.transition_to("ocioso", interface.signal_emitter())
            .await
            .expect("text turn finishes");
        let (response, receiver) = oneshot::channel();
        hero.handle_voice_event(
            VoiceEvent::Trigger(TriggerRequest {
                mode: TriggerMode::Start,
                epoch: stale_epoch,
                response,
            }),
            interface.signal_emitter(),
        )
        .await;
        assert_eq!(receiver.await.expect("trigger reply"), crate::ai::busy());
        assert_eq!(hero.state, State::Idle);
        assert!(hero.capture.is_none());
    }

    #[tokio::test]
    async fn unavailable_microphone_does_not_interrupt_speech() {
        let (server, _client) = voice_test_connection().await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let mut hero = interface.get_mut().await;
        hero.transition_to("pensando", interface.signal_emitter())
            .await
            .expect("turn starts");
        hero.transition_to("falando", interface.signal_emitter())
            .await
            .expect("speech starts");
        let (cancel, receiver) = oneshot::channel();
        let task = tokio::spawn(async move {
            receiver.await.expect("cancel received");
        });
        hero.speech = Some(SpeechTask { cancel, task });
        let generation = hero.voice_generation;

        let reply = hero
            .start_push_to_talk(interface.signal_emitter().clone())
            .await;
        assert_eq!(
            serde_json::from_str::<serde_json::Value>(&reply).unwrap()["reason"],
            "pipewire_capture_unavailable"
        );
        assert_eq!(hero.state, State::Speaking);
        assert_eq!(hero.voice_generation, generation);
        assert!(hero.speech.is_some());
        assert!(hero.capture.is_none());

        let speech = hero.speech.take().expect("speech is still active");
        speech.cancel.send(()).expect("stop synthetic speech");
        speech.task.await.expect("speech task");
    }

    #[tokio::test]
    async fn direct_trigger_stops_a_synthetic_recording() {
        let (server, client) = voice_test_connection().await;
        let (voice_tx, mut voice_rx) = mpsc::unbounded_channel();
        let trigger = server
            .object_server()
            .interface::<_, VoiceTrigger>(OBJECT_PATH)
            .await
            .expect("trigger interface");
        trigger.get_mut().await.voice_tx = voice_tx;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        {
            let mut hero = interface.get_mut().await;
            hero.transition_to("escutando", interface.signal_emitter())
                .await
                .expect("listen");
            hero.transition_to("gravando", interface.signal_emitter())
                .await
                .expect("record");
            let mut command =
                tokio::process::Command::new(if cfg!(windows) { "python" } else { "python3" });
            command.args([
                "-u",
                "-c",
                "import sys,time; sys.stdout.buffer.write(b'\\x00\\x01'*1600); sys.stdout.flush(); time.sleep(5)",
            ]);
            hero.capture = Some(Capture::start_command(command).expect("synthetic capture"));
        }
        let call = tokio::spawn(async move {
            client
                .call_method(
                    None::<&str>,
                    OBJECT_PATH,
                    Some("org.forjaos.Hero.Trigger"),
                    "StopPushToTalk",
                    &(),
                )
                .await
                .expect("stop reply")
                .body()
                .deserialize::<String>()
                .expect("reply body")
        });
        let event = tokio::time::timeout(Duration::from_secs(1), voice_rx.recv())
            .await
            .expect("trigger received")
            .expect("trigger event");
        interface
            .get_mut()
            .await
            .handle_voice_event(event, interface.signal_emitter())
            .await;
        let reply = tokio::time::timeout(Duration::from_secs(2), call)
            .await
            .expect("stop completed")
            .expect("call task");
        assert_eq!(
            serde_json::from_str::<serde_json::Value>(&reply).unwrap()["status"],
            "transcribing"
        );
        let mut hero = interface.get_mut().await;
        assert_eq!(hero.state, State::Transcribing);
        if let Some(task) = hero.stt_task.take() {
            task.abort();
        }
    }

    #[tokio::test]
    async fn push_to_talk_takes_over_a_wake_capture_and_ignores_late_wake() {
        let (server, _client) = voice_test_connection().await;
        let stream = MicStream::start_with_factory(|| {
            let mut command =
                tokio::process::Command::new(if cfg!(windows) { "python" } else { "python3" });
            command.args(["-u", "-c", "import sys,time; time.sleep(.2); frame=b'\\x00\\x05'*1280; [(sys.stdout.buffer.write(frame),sys.stdout.flush(),time.sleep(.01)) for _ in range(250)]; time.sleep(2)"]);
            command
        });
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let mut hero = interface.get_mut().await;
        hero.mic_stream = Some(stream);
        tokio::time::timeout(Duration::from_secs(2), async {
            while !hero.mic_stream.as_ref().is_some_and(MicStream::is_ready) {
                tokio::time::sleep(Duration::from_millis(20)).await;
            }
        })
        .await
        .expect("microphone ready");
        hero.handle_voice_event(VoiceEvent::WakeDetected(0), interface.signal_emitter())
            .await;
        assert_eq!(hero.state, State::Recording);
        assert_eq!(hero.capture_origin, Some(CaptureOrigin::WakeWord));
        let reply = hero
            .start_push_to_talk(interface.signal_emitter().clone())
            .await;
        assert_eq!(
            serde_json::from_str::<serde_json::Value>(&reply).unwrap()["status"],
            "recording"
        );
        assert_eq!(hero.capture_origin, Some(CaptureOrigin::PushToTalk));
        assert!(hero.wake_endpoint.is_none());
        let epoch = hero.state_epoch.load(Ordering::SeqCst);
        hero.handle_voice_event(VoiceEvent::WakeDetected(epoch), interface.signal_emitter())
            .await;
        assert_eq!(hero.capture_origin, Some(CaptureOrigin::PushToTalk));
        if let Some(capture) = hero.capture.take() {
            capture.cancel().await;
        }
        if let Some(stream) = hero.mic_stream.take() {
            stream.stop().await;
        }
    }

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
        let (voice_tx, _) = mpsc::unbounded_channel();
        let mut hero = Hero {
            state: State::Idle,
            state_tx,
            state_epoch: Arc::new(AtomicU64::new(0)),
            microphone_enabled: true,
            mic_stream: None,
            wake_detector: None,
            capture: None,
            capture_origin: None,
            voice_origin: CaptureOrigin::PushToTalk,
            wake_endpoint: None,
            voice_generation: 0,
            voice_tx,
            stt_task: None,
            thinking_task: None,
            active_voice_action: None,
            speech: None,
            pending: HashMap::<String, PendingAction>::new(),
            voice_pending_id: None,
            history: VecDeque::new(),
        };
        assert_eq!(hero.state(), "ocioso");
        assert!(hero.set_route_provider("unknown", "ollama", "").is_err());
        assert!(hero.set_persona_instructions("inválido\u{7}").is_err());
        assert!(hero.set_tool_tier("unknown.tool", "livre").is_err());
        assert!(hero.save_routine("invalid id", "[]", "livre").is_err());
    }

    #[tokio::test]
    async fn stale_voice_events_cannot_end_a_new_recording() {
        let (server, _client) = voice_test_connection().await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let mut command =
            tokio::process::Command::new(if cfg!(windows) { "python" } else { "python3" });
        command.args(["-u", "-c", "import time; time.sleep(5)"]);
        {
            let mut hero = interface.get_mut().await;
            hero.state = State::Recording;
            hero.voice_generation = 9;
            hero.capture = Some(Capture::start_command(command).expect("synthetic capture"));
            hero.handle_voice_event(VoiceEvent::CaptureExpired(8), interface.signal_emitter())
                .await;
            assert!(hero.capture.is_some());
            assert_eq!(hero.state, State::Recording);
            hero.handle_voice_event(VoiceEvent::CaptureExpired(9), interface.signal_emitter())
                .await;
            assert!(hero.capture.is_none());
            assert_eq!(hero.state, State::Idle);
        }
    }

    #[tokio::test]
    async fn microphone_mute_aborts_transcription_and_invalidates_its_result() {
        let _home = TestHome::new();
        let (server, _client) = voice_test_connection().await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let task = tokio::spawn(async { tokio::time::sleep(Duration::from_secs(5)).await });
        let abort = task.abort_handle();
        {
            let mut hero = interface.get_mut().await;
            hero.state = State::Transcribing;
            hero.voice_generation = 3;
            hero.stt_task = Some(task);
            hero.set_microphone_enabled(false, interface.signal_emitter().clone())
                .await
                .expect("mute microphone");
            assert_eq!(hero.state, State::Idle);
            assert_eq!(hero.voice_generation, 4);
            assert!(hero.stt_task.is_none());
            hero.handle_voice_event(
                VoiceEvent::Transcribed(3, Ok("stale".into())),
                interface.signal_emitter(),
            )
            .await;
            assert_eq!(hero.state, State::Idle);
        }
        tokio::task::yield_now().await;
        assert!(abort.is_finished());
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn locked_session_rejects_text_and_pending_mutating_actions() {
        let _home = TestHome::new();
        let active = Arc::new(AtomicBool::new(true));
        let (server, _client) = voice_test_connection_with_lock(Some(active.clone())).await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let mut hero = interface.get_mut().await;
        let conversation = hero
            .ask_text("olá", ".", "{}", interface.signal_emitter().clone())
            .await;
        let conversation: serde_json::Value =
            serde_json::from_str(&conversation).expect("JSON response");
        assert_eq!(conversation["status"], "locked");
        assert_eq!(hero.state, State::Idle);
        assert!(hero.history.is_empty());
        let request = hero
            .ask_text("ligue wifi", ".", "{}", interface.signal_emitter().clone())
            .await;
        let request: serde_json::Value = serde_json::from_str(&request).expect("JSON response");
        assert_eq!(request["status"], "locked");
        assert!(hero.pending.is_empty());

        let id = "existing-confirmation".to_string();
        hero.pending.insert(
            id.clone(),
            PendingAction {
                proposal: Proposal {
                    route: "sistema",
                    context: "nenhum".into(),
                    tool: "wifi.toggle",
                    tier: Tier::Alter,
                    action: Action::Wifi(true),
                },
                expires_at: Instant::now() + Duration::from_secs(120),
            },
        );
        let confirmation = hero
            .confirm_action(&id, true, interface.signal_emitter().clone())
            .await;
        let confirmation: serde_json::Value =
            serde_json::from_str(&confirmation).expect("JSON response");
        assert_eq!(confirmation["status"], "locked");
        assert!(hero.pending.contains_key(&id));

        active.store(false, Ordering::SeqCst);
        let request = hero
            .ask_text("ligue wifi", ".", "{}", interface.signal_emitter().clone())
            .await;
        let request: serde_json::Value = serde_json::from_str(&request).expect("JSON response");
        assert_eq!(request["status"], "confirmation_required");
        assert!(hero.pending.contains_key(&id));
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn voice_action_requires_confirmation_and_rechecks_the_screen_lock() {
        let _home = TestHome::new();
        let active = Arc::new(AtomicBool::new(false));
        let (server, _client) = voice_test_connection_with_lock(Some(active.clone())).await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let mut hero = interface.get_mut().await;
        hero.state = State::Thinking;
        hero.voice_generation = 3;
        hero.handle_voice_text("ligue wifi".into(), 3, interface.signal_emitter())
            .await;
        assert_eq!(hero.state, State::Speaking);
        let id = hero.voice_pending_id.clone().expect("voice confirmation");
        assert!(hero.pending.contains_key(&id));
        assert!(hero.thinking_task.is_none());
        hero.handle_voice_event(
            VoiceEvent::SpeechCompleted(3, Err("voice_not_selected")),
            interface.signal_emitter(),
        )
        .await;

        active.store(true, Ordering::SeqCst);
        hero.state = State::Thinking;
        hero.voice_generation = 4;
        hero.handle_voice_text("Confirmo.".into(), 4, interface.signal_emitter())
            .await;
        assert_eq!(hero.state, State::Speaking);
        assert!(hero.voice_pending_id.is_none());
        assert!(hero.pending.is_empty());
        assert!(hero.thinking_task.is_none());

        hero.handle_voice_event(
            VoiceEvent::SpeechCompleted(4, Err("voice_not_selected")),
            interface.signal_emitter(),
        )
        .await;
        active.store(false, Ordering::SeqCst);
        hero.state = State::Thinking;
        hero.voice_generation = 5;
        hero.handle_voice_text("ligue wifi".into(), 5, interface.signal_emitter())
            .await;
        assert!(hero.voice_pending_id.is_some());
        hero.handle_voice_event(
            VoiceEvent::SpeechCompleted(5, Err("voice_not_selected")),
            interface.signal_emitter(),
        )
        .await;
        hero.state = State::Thinking;
        hero.voice_generation = 6;
        hero.handle_voice_text("cancelo".into(), 6, interface.signal_emitter())
            .await;
        assert_eq!(hero.state, State::Speaking);
        assert!(hero.voice_pending_id.is_none());
        assert!(hero.pending.is_empty());
        assert!(hero.thinking_task.is_none());
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn voice_free_action_runs_through_the_policy_actor() {
        let _home = TestHome::new();
        let active = Arc::new(AtomicBool::new(false));
        let (server, _client) = voice_test_connection_with_lock(Some(active)).await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let (voice_tx, mut voice_rx) = mpsc::unbounded_channel();
        let mut hero = interface.get_mut().await;
        hero.voice_tx = voice_tx;
        hero.state = State::Thinking;
        hero.voice_generation = 8;
        hero.handle_voice_text("mostre gpu".into(), 8, interface.signal_emitter())
            .await;
        assert_eq!(hero.state, State::Thinking);
        let active = hero.active_voice_action.as_ref().expect("active action");
        assert_eq!(active.tool, "gpu.status");
        assert_eq!(active.tier, Tier::Free);
        let event = tokio::time::timeout(Duration::from_secs(5), voice_rx.recv())
            .await
            .expect("action result")
            .expect("voice event");
        match &event {
            VoiceEvent::ActionCompleted(completed) => {
                assert_eq!(completed.generation, 8);
            }
            _ => panic!("expected policy action result"),
        }
        hero.handle_voice_event(event, interface.signal_emitter())
            .await;
        assert_eq!(hero.state, State::Speaking);
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn explicit_voice_confirmation_consumes_pending_action_once() {
        let _home = TestHome::new();
        let active = Arc::new(AtomicBool::new(false));
        let (server, _client) = voice_test_connection_with_lock(Some(active)).await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let (voice_tx, mut voice_rx) = mpsc::unbounded_channel();
        let mut hero = interface.get_mut().await;
        hero.voice_tx = voice_tx;
        hero.state = State::Thinking;
        hero.voice_generation = 9;
        let id = "voice-action".to_string();
        hero.pending.insert(
            id.clone(),
            PendingAction {
                proposal: Proposal {
                    route: "sistema",
                    context: "nenhum".into(),
                    tool: "app.open",
                    tier: Tier::Alter,
                    action: Action::OpenApp("invalid;".into()),
                },
                expires_at: Instant::now() + Duration::from_secs(120),
            },
        );
        hero.voice_pending_id = Some(id.clone());
        hero.handle_voice_text("confirmo".into(), 9, interface.signal_emitter())
            .await;
        assert!(hero.pending.is_empty());
        assert!(hero.voice_pending_id.is_none());
        let active = hero.active_voice_action.as_ref().expect("active action");
        assert_eq!(active.tier, Tier::Alter);
        let event = tokio::time::timeout(Duration::from_secs(5), voice_rx.recv())
            .await
            .expect("action result")
            .expect("voice event");
        match &event {
            VoiceEvent::ActionCompleted(completed) => {
                assert!(completed.result.is_err());
            }
            _ => panic!("expected confirmed action result"),
        }
        hero.handle_voice_event(event, interface.signal_emitter())
            .await;
        assert_eq!(hero.state, State::Speaking);
    }

    #[test]
    fn voice_confirmation_requires_an_explicit_word() {
        assert!(is_voice_confirmation("Confirmo."));
        assert!(!is_voice_confirmation("sim"));
        assert!(!is_voice_confirmation("confirmo o resto"));
        assert!(is_voice_cancellation("Cancelo!"));
        assert_eq!(bounded_voice_answer(" ".into()), VOICE_FAILURE_MESSAGE);
    }

    #[tokio::test]
    async fn local_voice_turn_advances_from_transcription_to_speech_and_idle() {
        let (server, _client) = voice_test_connection().await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let mut hero = interface.get_mut().await;
        hero.state = State::Transcribing;
        hero.voice_generation = 4;
        hero.handle_voice_event(
            VoiceEvent::Transcribed(4, Ok("Olá, HERO".into())),
            interface.signal_emitter(),
        )
        .await;
        assert_eq!(hero.state, State::Thinking);
        hero.thinking_task.take().expect("local turn task").abort();
        let reply = serde_json::json!({"status":"ok","answer":"Resposta local"}).to_string();
        hero.handle_voice_event(
            VoiceEvent::TurnCompleted(4, "Olá, HERO".into(), reply),
            interface.signal_emitter(),
        )
        .await;
        assert_eq!(hero.state, State::Speaking);
        assert_eq!(hero.history.len(), 1);
        assert_eq!(hero.history[0].assistant, "Resposta local");
        assert!(hero.speech.is_some());
        hero.handle_voice_event(
            VoiceEvent::SpeechCompleted(4, Err("local_tts_unavailable")),
            interface.signal_emitter(),
        )
        .await;
        assert_eq!(hero.state, State::Idle);
        assert!(hero.speech.is_none());
    }

    #[tokio::test]
    async fn voice_turn_timeout_cancels_pending_thinking_and_returns_to_idle() {
        let (server, _client) = voice_test_connection().await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let task = tokio::spawn(async { tokio::time::sleep(Duration::from_secs(5)).await });
        let abort = task.abort_handle();
        let mut hero = interface.get_mut().await;
        hero.state = State::Thinking;
        hero.voice_generation = 10;
        hero.thinking_task = Some(task);
        hero.handle_voice_event(VoiceEvent::TurnExpired(9), interface.signal_emitter())
            .await;
        assert_eq!(hero.state, State::Thinking);
        hero.handle_voice_event(VoiceEvent::TurnExpired(10), interface.signal_emitter())
            .await;
        assert_eq!(hero.state, State::Idle);
        assert_eq!(hero.voice_generation, 11);
        assert!(hero.thinking_task.is_none());
        drop(hero);
        tokio::task::yield_now().await;
        assert!(abort.is_finished());
    }

    #[tokio::test]
    async fn voice_action_timeout_clears_the_active_action() {
        let (server, _client) = voice_test_connection().await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let mut hero = interface.get_mut().await;
        hero.state = State::Thinking;
        hero.voice_generation = 20;
        hero.active_voice_action = Some(ActiveVoiceAction {
            route: "sistema",
            tool: "wifi.toggle",
            tier: crate::policy::Tier::Alter,
        });
        let task = tokio::spawn(async { tokio::time::sleep(Duration::from_secs(5)).await });
        let abort = task.abort_handle();
        hero.thinking_task = Some(task);
        hero.handle_voice_event(VoiceEvent::TurnExpired(20), interface.signal_emitter())
            .await;
        assert_eq!(hero.state, State::Idle);
        assert!(hero.active_voice_action.is_none());
        assert!(hero.thinking_task.is_none());
        drop(hero);
        tokio::task::yield_now().await;
        assert!(abort.is_finished());
    }

    #[tokio::test]
    async fn stt_failure_uses_the_fixed_local_voice_answer() {
        let (server, _client) = voice_test_connection().await;
        let interface = server
            .object_server()
            .interface::<_, Hero>(OBJECT_PATH)
            .await
            .expect("HERO interface");
        let mut hero = interface.get_mut().await;
        hero.state = State::Transcribing;
        hero.voice_generation = 7;
        hero.handle_voice_event(
            VoiceEvent::Transcribed(7, Err("local_stt_failed")),
            interface.signal_emitter(),
        )
        .await;
        assert_eq!(hero.state, State::Speaking);
        assert!(hero.history.is_empty());
        assert!(hero.speech.is_some());
        hero.handle_voice_event(
            VoiceEvent::SpeechCompleted(7, Err("voice_not_selected")),
            interface.signal_emitter(),
        )
        .await;
        assert_eq!(hero.state, State::Idle);
    }

    #[test]
    fn voice_provider_failure_uses_a_fixed_local_phrase() {
        assert_eq!(
            voice_answer_from_reply(
                &serde_json::json!({"status":"backend_unavailable","answer":"provider details"})
                    .to_string()
            ),
            (VOICE_FAILURE_MESSAGE.to_string(), false)
        );
        assert_eq!(
            voice_answer_from_reply("invalid JSON"),
            (VOICE_FAILURE_MESSAGE.to_string(), false)
        );
        assert_eq!(
            voice_answer_from_reply(
                &serde_json::json!({"status":"ok","answer":"  pronto  "}).to_string()
            ),
            ("pronto".to_string(), true)
        );
    }

    #[cfg(unix)]
    #[test]
    fn confirmation_ids_are_192_bit_hex_tokens() {
        let id = confirmation_id().expect("/dev/urandom available");
        assert_eq!(id.len(), 48);
        assert!(id.chars().all(|character| character.is_ascii_hexdigit()));
    }
}
