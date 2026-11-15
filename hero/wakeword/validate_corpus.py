#!/usr/bin/env python3
"""Check the local, private speaker corpus for FR-081 coverage."""

import argparse
import csv
import json
import sys
import wave
from collections import defaultdict
from pathlib import Path


PHRASES = ("Guará", "Tupã", "Jaci", "Iara", "Ipê", "Boto", "Curió", "Arara")
REQUIRED_COLUMNS = {"speaker_code", "phrase", "path", "environment", "device"}


def validate(manifest: Path) -> dict:
    root = manifest.resolve().parent
    speakers: dict[str, set[str]] = defaultdict(set)
    errors: list[str] = []
    samples = 0

    with manifest.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source, delimiter="\t")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing:
            return {"complete": False, "errors": [f"Colunas ausentes: {', '.join(sorted(missing))}"], "samples": 0}

        for line, row in enumerate(reader, start=2):
            speaker = (row.get("speaker_code") or "").strip()
            phrase = (row.get("phrase") or "").strip()
            relative = Path((row.get("path") or "").strip())
            if not speaker or any(char in speaker for char in " /\\\t\r\n"):
                errors.append(f"Linha {line}: código de locutor inválido")
                continue
            if phrase not in PHRASES:
                errors.append(f"Linha {line}: frase não reconhecida")
                continue
            if not (row.get("environment") or "").strip() or not (row.get("device") or "").strip():
                errors.append(f"Linha {line}: ambiente e dispositivo são obrigatórios")
                continue
            if relative.is_absolute() or not relative.parts or ".." in relative.parts:
                errors.append(f"Linha {line}: caminho deve ser relativo ao manifesto")
                continue
            audio = (root / relative).resolve()
            if not audio.is_relative_to(root) or not audio.is_file():
                errors.append(f"Linha {line}: arquivo de áudio ausente ou fora do corpus")
                continue
            try:
                with wave.open(str(audio), "rb") as stream:
                    valid = (
                        stream.getnchannels() == 1
                        and stream.getframerate() == 16_000
                        and stream.getsampwidth() == 2
                        and stream.getnframes() > 0
                        and stream.getcomptype() == "NONE"
                    )
            except (OSError, EOFError, wave.Error):
                valid = False
            if not valid:
                errors.append(f"Linha {line}: WAV deve ser PCM mono, 16 kHz, 16 bits, não vazio")
                continue
            speakers[phrase].add(speaker)
            samples += 1

    counts = {phrase: len(speakers[phrase]) for phrase in PHRASES}
    missing = {phrase: max(0, 20 - count) for phrase, count in counts.items()}
    return {
        "complete": not errors and all(count >= 20 for count in counts.values()),
        "samples": samples,
        "speakers_per_phrase": counts,
        "missing_speakers_per_phrase": missing,
        "errors": errors,
        "note": "Contagem e formato apenas; origem humana e consentimento exigem conferência separada.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica cobertura do corpus privado FR-081")
    parser.add_argument("manifest", type=Path, help="TSV com speaker_code, phrase, path, environment, device")
    args = parser.parse_args()
    try:
        result = validate(args.manifest)
    except OSError as error:
        result = {"complete": False, "errors": [str(error)]}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if result["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
