#!/usr/bin/env python3
"""Play local Piper chunks through PipeWire without storing audio."""

import argparse
import base64
import binascii
import json
import signal
import subprocess
import sys
from pathlib import Path


MAX_TEXT_CHARS = 4000
MAX_LINE_CHARS = 16 * 1024 * 1024
MAX_CHUNK_BYTES = 12 * 1024 * 1024
VOICE_WORKER = "/usr/libexec/forjaos/voice-worker"
PIPEWIRE_PLAYER = "/usr/sbin/pw-cat"


class SpeechHandle:
    def __init__(self, model: Path, text: str):
        if not text.strip() or len(text) > MAX_TEXT_CHARS:
            raise ValueError("texto deve ter entre 1 e 4000 caracteres")
        self.model = model
        self.text = text
        self.synthesizer = None
        self.player = None
        self.cancelled = False

    def cancel(self, *_):
        self.cancelled = True
        for process in (self.synthesizer, self.player):
            if process is not None and process.poll() is None:
                process.terminate()

    def run(self) -> int:
        self.synthesizer = subprocess.Popen(
            [VOICE_WORKER, "tts", "--model", str(self.model)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        try:
            self.synthesizer.stdin.write(self.text)
            self.synthesizer.stdin.close()
            chunks = 0
            total_samples = 0
            finished = False
            while not self.cancelled:
                line = self.synthesizer.stdout.readline(MAX_LINE_CHARS + 1)
                if not line:
                    break
                if len(line) > MAX_LINE_CHARS or not line.endswith("\n"):
                    raise ValueError("bloco TTS excede o limite")
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError("evento TTS inválido")
                if event.get("event") == "error":
                    raise RuntimeError(event.get("error", "falha TTS local"))
                if event.get("event") == "done":
                    if event.get("chunks") != chunks:
                        raise ValueError("contagem de blocos TTS divergente")
                    finished = True
                    break
                if event.get("event") != "audio" or event.get("sequence") != chunks:
                    raise ValueError("sequência TTS inválida")
                rate = event.get("sample_rate")
                if not isinstance(rate, int) or rate < 8000 or rate > 48000:
                    raise ValueError("taxa de áudio TTS inválida")
                if self.player is None:
                    self.player = subprocess.Popen(
                        [PIPEWIRE_PLAYER, "--playback", "--raw", "--format", "s16",
                         "--rate", str(rate), "--channels", "1", "-"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                elif rate != self.rate:
                    raise ValueError("taxa de áudio TTS mudou entre blocos")
                self.rate = rate
                audio = base64.b64decode(event.get("pcm_s16le_base64", ""), validate=True)
                if not audio or len(audio) % 2 or len(audio) > MAX_CHUNK_BYTES:
                    raise ValueError("bloco PCM TTS inválido")
                visemes = event.get("visemes")
                if not isinstance(visemes, list):
                    raise ValueError("visemas TTS ausentes")
                print(json.dumps({
                    "event": "visemes", "sequence": chunks,
                    "offset_ms": round(total_samples * 1000 / rate), "items": visemes,
                }), flush=True)
                self.player.stdin.write(audio)
                self.player.stdin.flush()
                total_samples += len(audio) // 2
                chunks += 1
            if self.cancelled:
                print(json.dumps({"event": "cancelled"}), flush=True)
                return 130
            if not finished:
                raise ValueError("sintetizador TTS terminou sem evento final")
            if self.synthesizer.wait(timeout=5) != 0:
                raise RuntimeError("sintetizador TTS falhou")
            if self.player is not None:
                self.player.stdin.close()
                if self.player.wait(timeout=max(30, total_samples / self.rate + 10)) != 0:
                    raise RuntimeError("reprodução PipeWire falhou")
            print(json.dumps({"event": "done", "chunks": chunks}), flush=True)
            return 0
        finally:
            for process in (self.synthesizer, self.player):
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reproduz fala local do HERO pelo PipeWire")
    parser.add_argument("--model", required=True, type=Path)
    args = parser.parse_args()
    text = sys.stdin.read(MAX_TEXT_CHARS + 1)
    try:
        handle = SpeechHandle(args.model, text)
        signal.signal(signal.SIGTERM, handle.cancel)
        signal.signal(signal.SIGINT, handle.cancel)
        return handle.run()
    except (OSError, ValueError, RuntimeError, TypeError, binascii.Error,
            subprocess.TimeoutExpired) as error:
        if "handle" in locals() and handle.cancelled:
            print(json.dumps({"event": "cancelled"}), flush=True)
            return 130
        print(json.dumps({"event": "error", "error": str(error)}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
