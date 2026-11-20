#!/usr/bin/env python3
"""Local HERO speech worker. Audio is exchanged through pipes, never files."""

import argparse
import base64
import binascii
import json
import select
import sys
from pathlib import Path


MAX_AUDIO_BYTES = 16_000 * 2 * 30
MAX_REQUEST_BYTES = 2_000_000
MAX_TEXT_CHARS = 4_000
IDLE_SECONDS = 300


def viseme_for(phoneme: str) -> str:
    if phoneme in {"m", "b", "p"}:
        return "closed"
    if phoneme in {"f", "v"}:
        return "labiodental"
    if phoneme in {"θ", "ð"}:
        return "alveolar"
    if phoneme in {"t", "d", "s", "z"}:
        return "alveolar"
    if phoneme in {"k", "g", "ɡ"}:
        return "velar"
    if phoneme in {"tʃ", "dʒ", "ʃ", "ʒ"}:
        return "postalveolar"
    if phoneme in {"n", "ɲ"}:
        return "nasal"
    if phoneme in {"l", "ʎ"}:
        return "lateral"
    if phoneme in {"ɾ", "r", "ʁ", "x", "ɣ"}:
        return "rhotic"
    if phoneme in {"a", "ɑ", "æ"}:
        return "open"
    if phoneme in {"ɐ", "ɜ", "e", "ɛ", "ə"}:
        return "mid"
    if phoneme in {"i", "ɪ"}:
        return "wide"
    if phoneme in {"o", "ɔ"}:
        return "round"
    if phoneme in {"u", "ʊ"}:
        return "narrow"
    if phoneme in {"j", "w"}:
        return "glide"
    return "rest"


def viseme_events(alignments, sample_rate: int, sample_count: int) -> list[dict]:
    if not alignments:
        raise ValueError("o modelo Piper não forneceu alinhamentos de fonemas")
    cursor = 0
    events = []
    for alignment in alignments:
        duration = int(alignment.num_samples)
        if duration < 0:
            raise ValueError("alinhamento de fonemas inválido")
        start = cursor
        cursor += duration
        if alignment.phoneme not in {"^", "$", ".", ",", "!", "?", " ", "ˈ", "ˌ"} and duration:
            events.append({
                "phoneme": alignment.phoneme,
                "viseme": viseme_for(alignment.phoneme),
                "start_ms": round(start * 1000 / sample_rate),
                "end_ms": round(cursor * 1000 / sample_rate),
            })
    if cursor != sample_count:
        raise ValueError("alinhamento não corresponde à duração do áudio")
    return events


def regular_model(path: Path) -> Path:
    model = path.resolve()
    config = Path(str(model) + ".json")
    if path.is_symlink() or not model.is_file() or config.is_symlink() or not config.is_file():
        raise ValueError("modelo local ou configuração ausente")
    return model


def speak(model_path: Path) -> int:
    from piper import PiperVoice

    model = regular_model(model_path)
    text = sys.stdin.read(MAX_TEXT_CHARS + 1).strip()
    if not text or len(text) > MAX_TEXT_CHARS:
        raise ValueError("texto deve ter entre 1 e 4000 caracteres")
    voice = PiperVoice.load(model, include_alignments=True)
    sequence = 0
    for chunk in voice.synthesize(text, include_alignments=True):
        if chunk.sample_width != 2 or chunk.sample_channels != 1:
            raise ValueError("formato de áudio Piper inesperado")
        audio = chunk.audio_int16_bytes
        events = viseme_events(chunk.phoneme_alignments, chunk.sample_rate, len(audio) // 2)
        print(json.dumps({
            "event": "audio",
            "sequence": sequence,
            "sample_rate": chunk.sample_rate,
            "pcm_s16le_base64": base64.b64encode(audio).decode("ascii"),
            "visemes": events,
        }), flush=True)
        sequence += 1
    print(json.dumps({"event": "done", "chunks": sequence}), flush=True)
    return 0


def transcribe(model, encoded: str) -> str:
    import numpy as np

    audio = base64.b64decode(encoded, validate=True)
    if not audio or len(audio) % 2 or len(audio) > MAX_AUDIO_BYTES:
        raise ValueError("áudio deve ser PCM 16 kHz mono, 16 bits, com até 30 segundos")
    samples = np.frombuffer(audio, dtype="<i2").astype(np.float32) / 32768.0
    segments, _ = model.transcribe(
        samples, language="pt", beam_size=1, vad_filter=False,
        condition_on_previous_text=False,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


def serve_stt(model_path: Path) -> int:
    from faster_whisper import WhisperModel

    if model_path.is_symlink() or not model_path.is_dir():
        raise ValueError("modelo STT local ausente")
    model = WhisperModel(str(model_path), device="cpu", compute_type="int8", local_files_only=True)
    while select.select([sys.stdin], [], [], IDLE_SECONDS)[0]:
        line = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
        if not line:
            break
        if len(line) > MAX_REQUEST_BYTES:
            print(json.dumps({"status": "error", "error": "requisição de áudio excede o limite"}), flush=True)
            break
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or request.get("sample_rate") != 16_000:
                raise ValueError("sample_rate deve ser 16000")
            encoded = request.get("pcm_s16le_base64")
            if not isinstance(encoded, str):
                raise ValueError("campo de áudio ausente")
            reply = {"status": "ok", "text": transcribe(model, encoded)}
        except (ValueError, TypeError, binascii.Error) as error:
            reply = {"status": "error", "error": str(error)}
        print(json.dumps(reply), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Processo filho de voz local do HERO")
    parser.add_argument("mode", choices=("tts", "stt-server"))
    parser.add_argument("--model", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "tts":
            return speak(args.model)
        return serve_stt(args.model)
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"event": "error", "error": str(error)}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
