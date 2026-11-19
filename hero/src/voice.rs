use std::fs;
use std::path::PathBuf;
use std::process::Stdio;
use std::time::Duration;

use base64::Engine;
use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
use tokio::process::Command;
use tokio::sync::oneshot;

const MAX_AUDIO_BYTES: usize = 16_000 * 2 * 30;
const CAPTURE_SECONDS: u64 = 30;

enum CaptureCommand {
    Finish,
    Cancel,
}

pub struct Capture {
    command: oneshot::Sender<CaptureCommand>,
    task: tokio::task::JoinHandle<Result<Vec<u8>, &'static str>>,
}

impl Capture {
    pub fn start() -> Result<Self, &'static str> {
        let mut command = Command::new("pw-cat");
        command.args([
            "--record",
            "--raw",
            "--format",
            "s16",
            "--rate",
            "16000",
            "--channels",
            "1",
            "-",
        ]);
        Self::start_command(command)
    }

    fn start_command(mut command: Command) -> Result<Self, &'static str> {
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
                                    if let Ok(Ok(size)) = tokio::time::timeout(Duration::from_millis(250), output.read(&mut block)).await {
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
        microphone_enabled, set_microphone_enabled, transcribe_with_command, Capture,
        MAX_AUDIO_BYTES,
    };
    use crate::test_support::TestHome;
    use std::fs;
    use std::time::Duration;
    use tokio::process::Command;

    fn python_command(script: &str) -> Command {
        let mut command = Command::new(if cfg!(windows) { "python" } else { "python3" });
        command.args(["-u", "-c", script]);
        command
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
}
