use std::fs;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;

use base64::Engine;
use serde::Deserialize;
use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
use tokio::process::Command;
use tokio::sync::{broadcast, oneshot, watch};

const MAX_AUDIO_BYTES: usize = 16_000 * 2 * 30;
const CAPTURE_SECONDS: u64 = 30;
const FRAME_BYTES: usize = 16_000 * 2 * 80 / 1000;
const STREAM_RETRY: Duration = Duration::from_secs(1);
const AEC_SOURCE: &str = "forjaos.hero.aec.source";
const WAKE_SPEECH_RMS: u64 = 400;
const WAKE_MIN_SPEECH_FRAMES: u16 = 4;
const WAKE_QUIET_FRAMES: u16 = 10;
const WAKE_WAIT_FRAMES: u16 = 63;
const WAKE_WORKER: &str = "/usr/libexec/forjaos/hero-wakeword";
const WAKE_WORKER_SOURCE: &str = "/usr/share/forjaos/wakeword/worker.py";

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct WakeConfig {
    model: PathBuf,
    #[serde(default = "default_wake_threshold")]
    threshold: f32,
}

fn default_wake_threshold() -> f32 {
    0.5
}

impl WakeConfig {
    fn load() -> Option<Self> {
        let home = std::env::var_os("HOME")?;
        let path = PathBuf::from(home).join(".config/hero/wakeword.toml");
        let config: Self = toml::from_str(&fs::read_to_string(path).ok()?).ok()?;
        if !config.model.is_absolute()
            || !regular_file(&config.model)
            || !config.threshold.is_finite()
            || config.threshold <= 0.0
            || config.threshold >= 1.0
            || !regular_file(std::path::Path::new(WAKE_WORKER_SOURCE))
        {
            return None;
        }
        Some(config)
    }

    fn command(&self) -> Command {
        let mut command = Command::new(WAKE_WORKER);
        command
            .arg("--model")
            .arg(&self.model)
            .arg("--threshold")
            .arg(self.threshold.to_string());
        command
    }
}

pub fn selected_piper_model() -> Result<PathBuf, &'static str> {
    let voice = crate::persona::load().voice.ok_or("voice_not_selected")?;
    if voice.is_empty()
        || voice.len() > 96
        || !voice
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
    {
        return Err("invalid_voice_id");
    }
    let home = std::env::var_os("HOME").ok_or("home_unavailable")?;
    let model = PathBuf::from(home)
        .join(".local/share/hero/voices")
        .join(format!("{voice}.onnx"));
    let config = model.with_file_name(format!("{voice}.onnx.json"));
    if !regular_file(&model) || !regular_file(&config) {
        return Err("voice_model_unavailable");
    }
    Ok(model)
}

fn regular_file(path: &std::path::Path) -> bool {
    fs::symlink_metadata(path).is_ok_and(|metadata| metadata.file_type().is_file())
}

pub async fn speak(text: &str, cancel: oneshot::Receiver<()>) -> Result<(), &'static str> {
    let model = selected_piper_model()?;
    let mut command = Command::new("/usr/libexec/forjaos/hero-speak");
    command.args(["--model", model.to_str().ok_or("invalid_voice_path")?]);
    speak_with_command(text, cancel, command).await
}

async fn speak_with_command(
    text: &str,
    mut cancel: oneshot::Receiver<()>,
    mut command: Command,
) -> Result<(), &'static str> {
    if text.trim().is_empty() || text.chars().count() > 4000 {
        return Err("invalid_speech_text");
    }
    let mut process = command
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .kill_on_drop(true)
        .spawn()
        .map_err(|_| "local_tts_unavailable")?;
    let Some(mut input) = process.stdin.take() else {
        return Err("local_tts_unavailable");
    };
    input
        .write_all(text.as_bytes())
        .await
        .map_err(|_| "local_tts_failed")?;
    input.shutdown().await.map_err(|_| "local_tts_failed")?;
    drop(input);
    let result = tokio::select! {
        status = process.wait() => status.map_err(|_| "local_tts_failed").and_then(|status| {
            if status.success() { Ok(()) } else { Err("local_tts_failed") }
        }),
        _ = &mut cancel => Err("speech_cancelled"),
        () = tokio::time::sleep(Duration::from_secs(60)) => Err("speech_timeout"),
    };
    if process.try_wait().is_ok_and(|status| status.is_none()) {
        #[cfg(unix)]
        if let Some(pid) = process.id() {
            // hero-speak handles SIGTERM and terminates its Piper and PipeWire children.
            unsafe { libc::kill(pid as i32, libc::SIGTERM) };
        }
        #[cfg(not(unix))]
        let _ = process.start_kill();
        if tokio::time::timeout(Duration::from_secs(2), process.wait())
            .await
            .is_err()
        {
            let _ = process.start_kill();
            let _ = process.wait().await;
        }
    }
    result
}

enum CaptureCommand {
    Finish,
    Cancel,
}

#[derive(Clone)]
enum MicPacket {
    Audio(Arc<[u8]>),
    Disconnected,
}

pub struct MicStream {
    packets: broadcast::Sender<MicPacket>,
    connected: watch::Receiver<bool>,
    cancel: oneshot::Sender<()>,
    task: tokio::task::JoinHandle<()>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WakeEndpointResult {
    SpeechComplete,
    NoSpeech,
    Disconnected,
}

#[derive(Default)]
struct WakeEndpointDetector {
    frames: u16,
    speech_frames: u16,
    quiet_frames: u16,
}

impl WakeEndpointDetector {
    fn observe(&mut self, frame: &[u8]) -> Option<WakeEndpointResult> {
        if frame.len() != FRAME_BYTES {
            return Some(WakeEndpointResult::Disconnected);
        }
        self.frames = self.frames.saturating_add(1);
        let (samples, _) = frame.as_chunks::<2>();
        let sum_of_squares = samples
            .iter()
            .map(|sample| {
                let value = i16::from_le_bytes([sample[0], sample[1]]) as i64;
                (value * value) as u64
            })
            .sum::<u64>();
        let speech = sum_of_squares > WAKE_SPEECH_RMS.pow(2) * (FRAME_BYTES / 2) as u64;
        if speech {
            self.speech_frames = self.speech_frames.saturating_add(1);
            self.quiet_frames = 0;
        } else if self.speech_frames > 0 {
            self.quiet_frames = self.quiet_frames.saturating_add(1);
        }
        if self.speech_frames >= WAKE_MIN_SPEECH_FRAMES && self.quiet_frames >= WAKE_QUIET_FRAMES {
            return Some(WakeEndpointResult::SpeechComplete);
        }
        if self.quiet_frames >= WAKE_QUIET_FRAMES && self.speech_frames < WAKE_MIN_SPEECH_FRAMES {
            self.speech_frames = 0;
        }
        if self.frames >= WAKE_WAIT_FRAMES && self.speech_frames < WAKE_MIN_SPEECH_FRAMES {
            return Some(WakeEndpointResult::NoSpeech);
        }
        None
    }
}

pub struct WakeEndpoint {
    task: tokio::task::JoinHandle<()>,
}

impl WakeEndpoint {
    pub fn start<F>(stream: &MicStream, finished: F) -> Self
    where
        F: FnOnce(WakeEndpointResult) + Send + 'static,
    {
        let mut packets = stream.packets.subscribe();
        let task = tokio::spawn(async move {
            let mut detector = WakeEndpointDetector::default();
            let result = loop {
                match packets.recv().await {
                    Ok(MicPacket::Audio(frame)) => {
                        if let Some(result) = detector.observe(&frame) {
                            break result;
                        }
                    }
                    _ => break WakeEndpointResult::Disconnected,
                }
            };
            finished(result);
        });
        Self { task }
    }

    pub async fn stop(self) {
        self.task.abort();
        let _ = self.task.await;
    }
}

pub struct WakeDetector {
    cancel: oneshot::Sender<()>,
    task: tokio::task::JoinHandle<()>,
}

impl WakeDetector {
    pub fn start_configured<F>(
        stream: &MicStream,
        state: watch::Receiver<&'static str>,
        epoch: Arc<AtomicU64>,
        detected: F,
    ) -> Option<Self>
    where
        F: Fn(u64) + Send + 'static,
    {
        let config = WakeConfig::load()?;
        Some(Self::start_with_factory(
            stream,
            state,
            epoch,
            move || config.command(),
            detected,
        ))
    }

    fn start_with_factory<C, F>(
        stream: &MicStream,
        mut state: watch::Receiver<&'static str>,
        epoch: Arc<AtomicU64>,
        command: C,
        detected: F,
    ) -> Self
    where
        C: Fn() -> Command + Send + 'static,
        F: Fn(u64) + Send + 'static,
    {
        let packets = stream.packets.clone();
        let (cancel, mut receiver) = oneshot::channel();
        let task = tokio::spawn(async move {
            loop {
                if !matches!(*state.borrow(), "ocioso" | "falando") {
                    tokio::select! {
                        _ = &mut receiver => return,
                        changed = state.changed() => {
                            if changed.is_err() { return; }
                        }
                    }
                    continue;
                }
                let mut frames = packets.subscribe();
                let child = command()
                    .stdin(Stdio::piped())
                    .stdout(Stdio::piped())
                    .stderr(Stdio::null())
                    .kill_on_drop(true)
                    .spawn();
                let Ok(mut process) = child else {
                    tokio::select! {
                        _ = &mut receiver => return,
                        () = tokio::time::sleep(STREAM_RETRY) => continue,
                    }
                };
                let (Some(mut input), Some(output)) = (process.stdin.take(), process.stdout.take())
                else {
                    let _ = process.start_kill();
                    let _ = process.wait().await;
                    return;
                };
                let mut output = BufReader::new(output);
                let mut activated = None;
                loop {
                    let mut marker = [0u8; 5];
                    tokio::select! {
                        biased;
                        _ = &mut receiver => {
                            let _ = process.start_kill();
                            let _ = process.wait().await;
                            return;
                        }
                        changed = state.changed() => {
                            if changed.is_err() { return; }
                            if !matches!(*state.borrow(), "ocioso" | "falando") { break; }
                        }
                        packet = frames.recv() => {
                            match packet {
                                Ok(MicPacket::Audio(frame)) => {
                                    if !matches!(tokio::time::timeout(Duration::from_secs(1), input.write_all(&frame)).await, Ok(Ok(()))) {
                                        break;
                                    }
                                }
                                _ => break,
                            }
                        }
                        read = output.read_exact(&mut marker) => {
                            if read.is_err() || marker != *b"wake\n" { break; }
                            if matches!(*state.borrow(), "ocioso" | "falando") {
                                let current = epoch.load(Ordering::SeqCst);
                                detected(current);
                                activated = Some(current);
                            }
                            break;
                        }
                    }
                }
                let _ = process.start_kill();
                let _ = process.wait().await;
                if let Some(activation_epoch) = activated {
                    tokio::select! {
                        _ = &mut receiver => return,
                        _ = async {
                            while epoch.load(Ordering::SeqCst) == activation_epoch
                                && matches!(*state.borrow(), "ocioso" | "falando")
                            {
                                if state.changed().await.is_err() { break; }
                            }
                        } => {},
                        () = tokio::time::sleep(STREAM_RETRY) => {},
                    }
                } else {
                    tokio::select! {
                        _ = &mut receiver => return,
                        () = tokio::time::sleep(STREAM_RETRY) => {},
                    }
                }
            }
        });
        Self { cancel, task }
    }

    pub async fn stop(self) {
        let _ = self.cancel.send(());
        let _ = self.task.await;
    }
}

impl MicStream {
    pub fn is_ready(&self) -> bool {
        *self.connected.borrow()
    }

    pub fn start() -> Self {
        Self::start_with_target(
            || {
                let mut command = Command::new("pw-cat");
                command.args([
                "--record",
                "--raw",
                "--target=forjaos.hero.aec.source",
                "--media-role=Communication",
                "--properties={\"node.name\":\"forjaos.hero.microphone\",\"media.name\":\"HERO microphone\",\"application.name\":\"ForjaOS HERO\",\"node.dont-reconnect\":true}",
                "--format",
                "s16",
                "--rate",
                "16000",
                "--channels",
                "1",
                "-",
            ]);
                command
            },
            Some(AEC_SOURCE),
        )
    }

    #[cfg(test)]
    pub(crate) fn start_with_factory<F>(factory: F) -> Self
    where
        F: Fn() -> Command + Send + 'static,
    {
        Self::start_with_target(factory, None)
    }

    fn start_with_target<F>(factory: F, target: Option<&'static str>) -> Self
    where
        F: Fn() -> Command + Send + 'static,
    {
        let (packets, _) = broadcast::channel(64);
        let (connected_tx, connected) = watch::channel(false);
        let (cancel, mut receiver) = oneshot::channel();
        let sender = packets.clone();
        let task = tokio::spawn(async move {
            loop {
                if let Some(target) = target {
                    if !pipewire_node_available(target).await {
                        tokio::select! {
                            _ = &mut receiver => return,
                            () = tokio::time::sleep(STREAM_RETRY) => continue,
                        }
                    }
                }
                let mut command = factory();
                let child = command
                    .stdin(Stdio::null())
                    .stdout(Stdio::piped())
                    .stderr(Stdio::null())
                    .kill_on_drop(true)
                    .spawn();
                if let Ok(mut process) = child {
                    if let Some(mut output) = process.stdout.take() {
                        let mut pending = Vec::with_capacity(FRAME_BYTES + 4096);
                        let mut block = [0u8; 4096];
                        let mut verified_source = target.is_none();
                        'capture: loop {
                            tokio::select! {
                                _ = &mut receiver => {
                                    let _ = connected_tx.send(false);
                                    let _ = sender.send(MicPacket::Disconnected);
                                    let _ = process.start_kill();
                                    let _ = process.wait().await;
                                    return;
                                }
                                read = output.read(&mut block) => {
                                    match read {
                                        Ok(0) | Err(_) => break,
                                        Ok(size) => {
                                            pending.extend_from_slice(&block[..size]);
                                            while pending.len() >= FRAME_BYTES {
                                                if !verified_source {
                                                    if !pipewire_capture_linked(target.unwrap_or_default()).await {
                                                        break 'capture;
                                                    }
                                                    verified_source = true;
                                                }
                                                let frame: Arc<[u8]> = pending.drain(..FRAME_BYTES).collect::<Vec<_>>().into();
                                                if !*connected_tx.borrow() {
                                                    let _ = connected_tx.send(true);
                                                }
                                                let _ = sender.send(MicPacket::Audio(frame));
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    let _ = connected_tx.send(false);
                    let _ = sender.send(MicPacket::Disconnected);
                    let _ = process.start_kill();
                    let _ = process.wait().await;
                }
                tokio::select! {
                    _ = &mut receiver => return,
                    () = tokio::time::sleep(STREAM_RETRY) => {},
                }
            }
        });
        Self {
            packets,
            connected,
            cancel,
            task,
        }
    }

    pub async fn stop(self) {
        let _ = self.cancel.send(());
        let _ = self.task.await;
    }
}

async fn pipewire_node_available(name: &str) -> bool {
    let Some(nodes) = pipewire_graph().await else {
        return false;
    };
    nodes.as_array().is_some_and(|nodes| {
        nodes
            .iter()
            .any(|node| node["info"]["props"]["node.name"] == name)
    })
}

async fn pipewire_capture_linked(source: &str) -> bool {
    let Some(graph) = pipewire_graph().await else {
        return false;
    };
    capture_linked_in_graph(&graph, source)
}

fn capture_linked_in_graph(graph: &Value, source: &str) -> bool {
    let Some(nodes) = graph.as_array() else {
        return false;
    };
    let source_id = nodes
        .iter()
        .find(|node| node["info"]["props"]["node.name"] == source)
        .map(|node| &node["id"]);
    let input_id = nodes
        .iter()
        .find(|node| node["info"]["props"]["node.name"] == "forjaos.hero.microphone")
        .map(|node| &node["id"]);
    let (Some(source_id), Some(input_id)) = (source_id, input_id) else {
        return false;
    };
    let links: Vec<_> = nodes
        .iter()
        .filter(|node| node["type"] == "PipeWire:Interface:Link")
        .filter(|node| node["info"]["input-node-id"] == *input_id)
        .collect();
    !links.is_empty()
        && links
            .iter()
            .all(|link| link["info"]["output-node-id"] == *source_id)
}

async fn pipewire_graph() -> Option<Value> {
    let mut command = Command::new("pw-dump");
    command.kill_on_drop(true);
    let Ok(Ok(output)) = tokio::time::timeout(Duration::from_secs(2), command.output()).await
    else {
        return None;
    };
    if !output.status.success() || output.stdout.len() > 4 * 1024 * 1024 {
        return None;
    }
    serde_json::from_slice(&output.stdout).ok()
}

pub struct Capture {
    command: oneshot::Sender<CaptureCommand>,
    task: tokio::task::JoinHandle<Result<Vec<u8>, &'static str>>,
}

impl Capture {
    pub fn start_from_stream(stream: &MicStream) -> Result<Self, &'static str> {
        if !stream.is_ready() {
            return Err("pipewire_capture_unavailable");
        }
        let mut packets = stream.packets.subscribe();
        let connected = stream.connected.clone();
        let (command, mut receiver) = oneshot::channel();
        let task = tokio::spawn(async move {
            let mut audio = Vec::with_capacity(16_000 * 2);
            let deadline = tokio::time::sleep(Duration::from_secs(CAPTURE_SECONDS));
            tokio::pin!(deadline);
            loop {
                tokio::select! {
                    biased;
                    control = &mut receiver => {
                        return match control {
                            Ok(CaptureCommand::Finish) => {
                                if !*connected.borrow() {
                                    return Err("pipewire_capture_failed");
                                }
                                if audio.is_empty() {
                                    match tokio::time::timeout(Duration::from_millis(250), packets.recv()).await {
                                        Ok(Ok(MicPacket::Audio(frame))) => audio.extend_from_slice(&frame),
                                        Ok(_) => return Err("pipewire_capture_failed"),
                                        Err(_) => {},
                                    }
                                }
                                if !audio.is_empty() && audio.len().is_multiple_of(2) {
                                    Ok(audio)
                                } else {
                                    Err("empty_or_invalid_audio")
                                }
                            }
                            _ => Err("capture_cancelled"),
                        };
                    }
                    packet = packets.recv() => {
                        match packet {
                            Ok(MicPacket::Audio(frame)) if audio.len() + frame.len() <= MAX_AUDIO_BYTES => audio.extend_from_slice(&frame),
                            Ok(MicPacket::Audio(_)) => return Err("audio_duration_exceeded"),
                            _ => return Err("pipewire_capture_failed"),
                        }
                    }
                    () = &mut deadline => return Err("audio_duration_exceeded"),
                }
            }
        });
        Ok(Self { command, task })
    }

    #[cfg(test)]
    pub(crate) fn start_command(mut command: Command) -> Result<Self, &'static str> {
        let mut process = command
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .kill_on_drop(true)
            .spawn()
            .map_err(|_| "pipewire_capture_unavailable")?;
        let mut output = process
            .stdout
            .take()
            .ok_or("pipewire_capture_unavailable")?;
        let (command, mut receiver) = oneshot::channel();
        let task = tokio::spawn(async move {
            let mut audio = Vec::with_capacity(16_000 * 2);
            let mut block = [0u8; 4096];
            let deadline = tokio::time::sleep(Duration::from_secs(CAPTURE_SECONDS));
            tokio::pin!(deadline);
            let result = loop {
                tokio::select! {
                    biased;
                    control = &mut receiver => {
                        break match control {
                            Ok(CaptureCommand::Finish) => {
                                if audio.is_empty() {
                                    if let Ok(Ok(size)) = tokio::time::timeout(Duration::from_secs(2), output.read(&mut block)).await {
                                        if size <= MAX_AUDIO_BYTES {
                                            audio.extend_from_slice(&block[..size]);
                                        }
                                    }
                                }
                                if !audio.is_empty() && audio.len().is_multiple_of(2) {
                                    Ok(audio)
                                } else {
                                    Err("empty_or_invalid_audio")
                                }
                            }
                            _ => Err("capture_cancelled"),
                        };
                    }
                    read = output.read(&mut block) => {
                        match read {
                            Ok(0) | Err(_) => break Err("pipewire_capture_failed"),
                            Ok(size) if audio.len() + size > MAX_AUDIO_BYTES => break Err("audio_duration_exceeded"),
                            Ok(size) => audio.extend_from_slice(&block[..size]),
                        }
                    }
                    () = &mut deadline => break Err("audio_duration_exceeded"),
                }
            };
            let _ = process.start_kill();
            let _ = process.wait().await;
            result
        });
        Ok(Self { command, task })
    }

    pub async fn finish(self) -> Result<Vec<u8>, &'static str> {
        let _ = self.command.send(CaptureCommand::Finish);
        self.task.await.map_err(|_| "pipewire_capture_failed")?
    }

    pub async fn cancel(self) {
        let _ = self.command.send(CaptureCommand::Cancel);
        let _ = self.task.await;
    }
}

pub async fn transcribe(audio: &[u8]) -> Result<String, &'static str> {
    let mut command = Command::new("/usr/libexec/forjaos/voice-worker");
    command.arg("stt-server");
    transcribe_with_command(audio, command).await
}

async fn transcribe_with_command(
    audio: &[u8],
    mut command: Command,
) -> Result<String, &'static str> {
    if audio.is_empty() || !audio.len().is_multiple_of(2) || audio.len() > MAX_AUDIO_BYTES {
        return Err("empty_or_invalid_audio");
    }
    let mut process = command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .kill_on_drop(true)
        .spawn()
        .map_err(|_| "local_stt_unavailable")?;
    let request = json!({
        "sample_rate": 16_000,
        "pcm_s16le_base64": base64::engine::general_purpose::STANDARD.encode(audio),
    })
    .to_string();
    let Some(mut input) = process.stdin.take() else {
        return Err("local_stt_unavailable");
    };
    let Some(output) = process.stdout.take() else {
        return Err("local_stt_unavailable");
    };
    let response = tokio::time::timeout(Duration::from_secs(60), async move {
        input.write_all(request.as_bytes()).await?;
        input.write_all(b"\n").await?;
        input.shutdown().await?;
        let mut reader = BufReader::new(output.take(8192));
        let mut line = Vec::new();
        reader.read_until(b'\n', &mut line).await?;
        Ok::<Vec<u8>, std::io::Error>(line)
    })
    .await
    .map_err(|_| "local_stt_timeout")?
    .map_err(|_| "local_stt_unavailable")?;
    let _ = process.start_kill();
    let _ = process.wait().await;
    let parsed: Value = serde_json::from_slice(&response).map_err(|_| "local_stt_invalid_reply")?;
    if parsed["status"] != "ok" {
        return Err("local_stt_failed");
    }
    let text = parsed["text"].as_str().ok_or("local_stt_invalid_reply")?;
    let text = text.trim();
    if text.is_empty() || text.chars().count() > 4000 {
        return Err("local_stt_no_speech");
    }
    Ok(text.to_string())
}

fn microphone_path() -> Result<PathBuf, &'static str> {
    let home = std::env::var_os("HOME").ok_or("home_unavailable")?;
    Ok(PathBuf::from(home).join(".config/hero/microphone.state"))
}

pub fn microphone_enabled() -> bool {
    let Ok(path) = microphone_path() else {
        return false;
    };
    match fs::read(path) {
        Ok(bytes) => bytes == b"enabled\n",
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => false,
        Err(_) => false,
    }
}

pub fn set_microphone_enabled(enabled: bool) -> Result<(), &'static str> {
    let path = microphone_path()?;
    super::routes::write_private_atomic(&path, if enabled { b"enabled\n" } else { b"disabled\n" })
        .map_err(|_| "microphone_state_unavailable")
}

#[cfg(test)]
mod tests {
    use super::{
        microphone_enabled, selected_piper_model, set_microphone_enabled, speak_with_command,
        transcribe_with_command, Capture, MicPacket, MicStream, WakeDetector, WakeEndpoint,
        WakeEndpointDetector, WakeEndpointResult, FRAME_BYTES, MAX_AUDIO_BYTES,
    };
    use crate::test_support::TestHome;
    use std::fs;
    use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
    use std::sync::Arc;
    use std::time::Duration;
    use tokio::{
        process::Command,
        sync::{mpsc, oneshot, watch},
    };

    #[test]
    fn microphone_rejects_a_pipewire_link_from_the_default_source() {
        let graph = serde_json::json!([
            {"id": 1, "info": {"props": {"node.name": "forjaos.hero.aec.source"}}},
            {"id": 2, "info": {"props": {"node.name": "forjaos.hero.microphone"}}},
            {"id": 3, "info": {"props": {"node.name": "raw.microphone"}}},
            {"type": "PipeWire:Interface:Link", "info": {"output-node-id": 1, "input-node-id": 2}}
        ]);
        assert!(super::capture_linked_in_graph(
            &graph,
            "forjaos.hero.aec.source"
        ));

        let mut fallback = graph.clone();
        fallback[3]["info"]["output-node-id"] = serde_json::json!(3);
        assert!(!super::capture_linked_in_graph(
            &fallback,
            "forjaos.hero.aec.source"
        ));
        fallback.as_array_mut().expect("PipeWire graph").push(
            serde_json::json!({"type": "PipeWire:Interface:Link", "info": {"output-node-id": 1, "input-node-id": 2}}),
        );
        assert!(!super::capture_linked_in_graph(
            &fallback,
            "forjaos.hero.aec.source"
        ));
    }

    #[test]
    fn wake_endpoint_waits_for_speech_then_closes_after_silence() {
        let mut detector = WakeEndpointDetector::default();
        let quiet = vec![0u8; FRAME_BYTES];
        let speech = 1200i16.to_le_bytes().repeat(FRAME_BYTES / 2);
        for _ in 0..12 {
            assert_eq!(detector.observe(&quiet), None);
        }
        for _ in 0..4 {
            assert_eq!(detector.observe(&speech), None);
        }
        for _ in 0..9 {
            assert_eq!(detector.observe(&quiet), None);
        }
        assert_eq!(
            detector.observe(&quiet),
            Some(WakeEndpointResult::SpeechComplete)
        );

        let mut no_speech = WakeEndpointDetector::default();
        for _ in 0..62 {
            assert_eq!(no_speech.observe(&quiet), None);
        }
        assert_eq!(
            no_speech.observe(&quiet),
            Some(WakeEndpointResult::NoSpeech)
        );

        let mut noise = WakeEndpointDetector::default();
        for _ in 0..3 {
            assert_eq!(noise.observe(&speech), None);
        }
        for _ in 0..59 {
            assert_eq!(noise.observe(&quiet), None);
        }
        assert_eq!(noise.observe(&quiet), Some(WakeEndpointResult::NoSpeech));
    }

    fn python_command(script: &str) -> Command {
        let mut command = Command::new(if cfg!(windows) { "python" } else { "python3" });
        command.args(["-u", "-c", script]);
        command
    }

    #[tokio::test]
    async fn wake_detector_waits_for_idle_and_uses_the_shared_microphone_stream() {
        let stream = MicStream::start_with_factory(|| {
            python_command("import sys,time; time.sleep(.3); frame=b'\\x00\\x05'*1280; [(sys.stdout.buffer.write(frame),sys.stdout.flush(),time.sleep(.02)) for _ in range(40)]; time.sleep(2)")
        });
        let launches = Arc::new(AtomicUsize::new(0));
        let count = launches.clone();
        let (state_tx, state_rx) = watch::channel("gravando");
        let (wake_tx, mut wake_rx) = mpsc::unbounded_channel();
        let detector = WakeDetector::start_with_factory(
            &stream,
            state_rx,
            Arc::new(AtomicU64::new(7)),
            move || {
                count.fetch_add(1, Ordering::SeqCst);
                python_command("import sys,time; [sys.stdin.buffer.read(2560) for _ in range(4)]; sys.stdout.buffer.write(b'wake\\n'); sys.stdout.flush(); time.sleep(2)")
            },
            move |epoch| {
                let _ = wake_tx.send(epoch);
            },
        );
        tokio::time::sleep(Duration::from_millis(100)).await;
        assert_eq!(launches.load(Ordering::SeqCst), 0);
        state_tx.send("ocioso").expect("wake state");
        let detected = tokio::time::timeout(Duration::from_secs(2), wake_rx.recv())
            .await
            .expect("wake signal");
        assert_eq!(detected, Some(7));
        assert_eq!(launches.load(Ordering::SeqCst), 1);
        state_tx.send("gravando").expect("PTT suspension");
        detector.stop().await;
        stream.stop().await;
    }

    #[tokio::test]
    async fn wake_endpoint_consumes_pcm_without_another_microphone_process() {
        let launches = Arc::new(AtomicUsize::new(0));
        let count = launches.clone();
        let stream = MicStream::start_with_factory(move || {
            count.fetch_add(1, Ordering::SeqCst);
            python_command("import sys,time; time.sleep(.2); speech=b'\\x00\\x05'*1280; quiet=bytes(2560); [(sys.stdout.buffer.write(speech),sys.stdout.flush(),time.sleep(.02)) for _ in range(4)]; [(sys.stdout.buffer.write(quiet),sys.stdout.flush(),time.sleep(.02)) for _ in range(10)]; time.sleep(2)")
        });
        let (done_tx, done_rx) = oneshot::channel();
        let endpoint = WakeEndpoint::start(&stream, move |result| {
            let _ = done_tx.send(result);
        });
        let result = tokio::time::timeout(Duration::from_secs(2), done_rx)
            .await
            .expect("endpoint completed")
            .expect("endpoint result");
        assert_eq!(result, WakeEndpointResult::SpeechComplete);
        assert_eq!(launches.load(Ordering::SeqCst), 1);
        endpoint.stop().await;
        stream.stop().await;
    }

    #[test]
    fn microphone_switch_survives_restart_and_fails_closed_on_invalid_state() {
        let home = TestHome::new();
        assert!(!microphone_enabled());
        set_microphone_enabled(false).expect("mute microphone");
        assert!(!microphone_enabled());
        set_microphone_enabled(true).expect("unmute microphone");
        assert!(microphone_enabled());
        let path = home.root().join(".config/hero/microphone.state");
        fs::write(path, b"corrupt\n").expect("corrupt state");
        assert!(!microphone_enabled());
    }

    #[tokio::test]
    async fn capture_reads_pcm_from_a_pipe_and_stops_the_child() {
        let command = python_command("import sys,time; sys.stdout.buffer.write(b'\\x00\\x01'*1600); sys.stdout.flush(); time.sleep(5)");
        let capture = Capture::start_command(command).expect("synthetic capture starts");
        let audio = tokio::time::timeout(Duration::from_secs(2), capture.finish())
            .await
            .expect("capture stops")
            .expect("capture returns PCM");
        assert_eq!(audio.len(), 3200);
        assert_eq!(&audio[..2], &[0, 1]);
    }

    #[tokio::test]
    async fn capture_cancellation_does_not_return_audio() {
        let command = python_command("import time; time.sleep(5)");
        let capture = Capture::start_command(command).expect("synthetic capture starts");
        tokio::time::timeout(Duration::from_secs(2), capture.cancel())
            .await
            .expect("cancel stops the child");
    }

    #[tokio::test]
    async fn one_microphone_process_feeds_push_to_talk_and_another_consumer() {
        let launches = Arc::new(AtomicUsize::new(0));
        let counter = launches.clone();
        let stream = MicStream::start_with_factory(move || {
            counter.fetch_add(1, Ordering::SeqCst);
            python_command("import sys,time; time.sleep(.2); [(sys.stdout.buffer.write(b'\\x00\\x01'*1280),sys.stdout.flush(),time.sleep(.02)) for _ in range(50)]; time.sleep(2)")
        });
        let mut connected = stream.connected.clone();
        tokio::time::timeout(Duration::from_secs(2), async {
            while !*connected.borrow() {
                connected.changed().await.expect("microphone stream");
            }
        })
        .await
        .expect("stream connected");

        let mut wake_consumer = stream.packets.subscribe();
        let capture = Capture::start_from_stream(&stream).expect("PTT subscribes");
        let packet = tokio::time::timeout(Duration::from_secs(2), wake_consumer.recv())
            .await
            .expect("second consumer receives a frame")
            .expect("microphone frame");
        assert!(matches!(packet, MicPacket::Audio(_)));
        tokio::time::sleep(Duration::from_millis(100)).await;
        let audio = capture.finish().await.expect("PTT returns PCM");
        assert!(!audio.is_empty());
        assert!(audio.len() <= MAX_AUDIO_BYTES);
        assert_eq!(&audio[..2], &[0, 1]);
        assert_eq!(launches.load(Ordering::SeqCst), 1);
        stream.stop().await;
    }

    #[tokio::test]
    async fn microphone_without_pcm_is_not_connected() {
        let stream = MicStream::start_with_factory(|| python_command("import time; time.sleep(5)"));
        tokio::time::sleep(Duration::from_millis(150)).await;
        assert!(!*stream.connected.borrow());
        assert!(matches!(
            Capture::start_from_stream(&stream),
            Err("pipewire_capture_unavailable")
        ));
        tokio::time::timeout(Duration::from_secs(2), stream.stop())
            .await
            .expect("stop stalled source");
    }

    #[tokio::test]
    async fn microphone_disconnect_fails_capture_and_restarts_the_owner() {
        let launches = Arc::new(AtomicUsize::new(0));
        let counter = launches.clone();
        let stream = MicStream::start_with_factory(move || {
            counter.fetch_add(1, Ordering::SeqCst);
            python_command("import sys,time; time.sleep(.2); sys.stdout.buffer.write(b'\\x00\\x01'*1280); sys.stdout.flush()")
        });
        let mut connected = stream.connected.clone();
        tokio::time::timeout(Duration::from_secs(2), async {
            while !*connected.borrow() {
                connected.changed().await.expect("microphone stream");
            }
        })
        .await
        .expect("stream connected");
        let capture = Capture::start_from_stream(&stream).expect("PTT subscribes");
        tokio::time::timeout(Duration::from_secs(2), async {
            while *connected.borrow() {
                connected.changed().await.expect("microphone stream");
            }
        })
        .await
        .expect("stream disconnected");
        assert_eq!(capture.finish().await, Err("pipewire_capture_failed"));
        tokio::time::timeout(Duration::from_secs(3), async {
            while launches.load(Ordering::SeqCst) < 2 {
                tokio::time::sleep(Duration::from_millis(20)).await;
            }
        })
        .await
        .expect("owner retries after disconnect");
        stream.stop().await;
    }

    #[tokio::test]
    async fn stt_pipe_accepts_local_reply_and_rejects_invalid_input() {
        let command = python_command("import sys,json; r=json.loads(sys.stdin.readline()); print(json.dumps({'status':'ok','text':' Olá HERO '}) if r['sample_rate']==16000 and r['pcm_s16le_base64']=='AAE=' else '{}',flush=True)");
        let text = transcribe_with_command(&[0, 1], command)
            .await
            .expect("local STT reply");
        assert_eq!(text, "Olá HERO");

        let invalid = python_command("raise RuntimeError('must not start')");
        assert_eq!(
            transcribe_with_command(&[0], invalid).await,
            Err("empty_or_invalid_audio")
        );
        let oversized = vec![0; MAX_AUDIO_BYTES + 2];
        let invalid = python_command("raise RuntimeError('must not start')");
        assert_eq!(
            transcribe_with_command(&oversized, invalid).await,
            Err("empty_or_invalid_audio")
        );
    }

    #[tokio::test]
    async fn stt_pipe_rejects_worker_errors_without_exposing_audio() {
        let command = python_command(
            "print('{\"status\":\"error\",\"error\":\"model missing\"}',flush=True)",
        );
        assert_eq!(
            transcribe_with_command(&[0, 1], command).await,
            Err("local_stt_failed")
        );
    }

    #[test]
    fn selected_piper_voice_uses_cli_config_and_requires_regular_files() {
        let home = TestHome::new();
        let config = home.root().join(".config/hero/persona.toml");
        fs::create_dir_all(config.parent().expect("config dir")).expect("create config dir");
        fs::write(&config, "voice = \"pt_BR-cadu-medium\"\n").expect("select voice");
        assert_eq!(selected_piper_model(), Err("voice_model_unavailable"));
        let model = home
            .root()
            .join(".local/share/hero/voices/pt_BR-cadu-medium.onnx");
        fs::create_dir_all(model.parent().expect("voice dir")).expect("create voice dir");
        fs::write(&model, b"model").expect("write model");
        fs::write(model.with_file_name("pt_BR-cadu-medium.onnx.json"), b"{}")
            .expect("write config");
        assert_eq!(selected_piper_model(), Ok(model));
        fs::write(config, "voice = \"../outside\"\n").expect("invalid voice");
        assert_eq!(selected_piper_model(), Err("invalid_voice_id"));
    }

    #[tokio::test]
    async fn speech_process_receives_text_and_can_be_cancelled() {
        let command =
            python_command("import sys; sys.exit(0 if sys.stdin.read() == 'resposta' else 2)");
        let (_cancel, receiver) = oneshot::channel();
        assert_eq!(
            speak_with_command("resposta", receiver, command).await,
            Ok(())
        );

        let command = python_command("import sys,time; sys.stdin.read(); time.sleep(5)");
        let (cancel, receiver) = oneshot::channel();
        let task = tokio::spawn(async move { speak_with_command("pare", receiver, command).await });
        tokio::time::sleep(Duration::from_millis(100)).await;
        cancel.send(()).expect("cancel speech");
        assert_eq!(
            tokio::time::timeout(Duration::from_secs(3), task)
                .await
                .expect("speech stops")
                .expect("speech task"),
            Err("speech_cancelled")
        );
    }
}
