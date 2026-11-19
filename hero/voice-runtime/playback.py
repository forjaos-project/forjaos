#!/usr/bin/env python3
"""Play local Piper chunks through PipeWire without storing audio."""

import argparse
import base64
import binascii
import json
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path


MAX_TEXT_CHARS = 4000
MAX_LINE_CHARS = 16 * 1024 * 1024
MAX_CHUNK_BYTES = 12 * 1024 * 1024
VOICE_WORKER = "/usr/libexec/forjaos/voice-worker"
PIPEWIRE_PLAYER = "/usr/bin/pw-cat"
PIPEWIRE_DUMP = "/usr/bin/pw-dump"
AEC_SINK = "forjaos.hero.aec.sink"
PLAYER_NODE = "forjaos.hero.speech"


def aec_sink_available() -> bool:
    try:
        result = subprocess.run(
            [PIPEWIRE_DUMP], capture_output=True, timeout=2, check=True,
        )
        nodes = json.loads(result.stdout)
        return any(node.get("info", {}).get("props", {}).get("node.name") == AEC_SINK
                   for node in nodes)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        return False


def aec_playback_linked(player_node: str) -> bool:
    try:
        result = subprocess.run(
            [PIPEWIRE_DUMP], capture_output=True, timeout=2, check=True,
        )
        graph = json.loads(result.stdout)
        if not isinstance(graph, list):
            return False
        names = {
            node["id"]: node.get("info", {}).get("props", {}).get("node.name")
            for node in graph if node.get("type") == "PipeWire:Interface:Node"
        }
        player_ids = {node_id for node_id, name in names.items()
                      if name == player_node}
        links = [node for node in graph
                 if node.get("type") == "PipeWire:Interface:Link"
                 and node.get("info", {}).get("output-node-id") in player_ids]
        return bool(links) and all(
            names.get(link["info"]["input-node-id"]) == AEC_SINK for link in links
        )
    except (OSError, KeyError, ValueError, TypeError, subprocess.SubprocessError):
        return False


def wait_for_aec_playback(player: subprocess.Popen, player_node: str) -> None:
    deadline = time.monotonic() + 2
    while player.poll() is None:
        if aec_playback_linked(player_node):
            return
        if time.monotonic() >= deadline:
            break
        time.sleep(0.05)
    raise RuntimeError("reprodução fora do sink AEC do HERO")


class SpeechHandle:
    def __init__(self, model: Path, text: str):
        if not text.strip() or len(text) > MAX_TEXT_CHARS:
            raise ValueError("texto deve ter entre 1 e 4000 caracteres")
        self.model = model
        self.text = text
        self.synthesizer = None
        self.player = None
        self.player_node = None
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
                    if not aec_sink_available():
                        raise RuntimeError("sink AEC do HERO indisponível")
                    self.player_node = f"{PLAYER_NODE}.{secrets.token_hex(8)}"
                    properties = json.dumps({
                        "node.name": self.player_node,
                        "node.dont-reconnect": True,
                    }, separators=(",", ":"))
                    self.player = subprocess.Popen(
                        [PIPEWIRE_PLAYER, "--playback", "--raw",
                         f"--target={AEC_SINK}",
                         f"--properties={properties}",
                         "--format", "s16",
                         "--rate", str(rate), "--channels", "1", "-"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    wait_for_aec_playback(self.player, self.player_node)
                elif rate != self.rate:
                    raise ValueError("taxa de áudio TTS mudou entre blocos")
                elif not aec_playback_linked(self.player_node):
                    raise RuntimeError("reprodução saiu do sink AEC do HERO")
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
