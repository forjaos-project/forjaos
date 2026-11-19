#!/usr/bin/env python3
"""Build one speaker-disjoint trainer manifest from private WAV manifests."""

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
import wave
from pathlib import Path


PHRASES = ("Guará", "Tupã", "Jaci", "Iara", "Ipê", "Boto", "Curió", "Arara")
OUTPUT_FIELDS = ("split", "label", "path", "source", "phrase", "speaker_code")
POSITIVE_FIELDS = {"speaker_code", "phrase", "path", "environment", "device"}
NEGATIVE_FIELDS = {"source", "speaker_code", "path"}


def read_rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source, delimiter="\t")
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path.name}: colunas ausentes: {', '.join(sorted(missing))}")
        return [dict(row) for row in reader]


def resolve_wav(manifest: Path, value: str, line: int) -> Path:
    relative = Path(value.strip())
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"{manifest.name}, linha {line}: caminho deve ser relativo")
    root = manifest.resolve(strict=True).parent
    candidate = root / relative
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError(f"{manifest.name}, linha {line}: WAV ausente ou link simbólico")
    audio = candidate.resolve(strict=True)
    if not audio.is_relative_to(root):
        raise ValueError(f"{manifest.name}, linha {line}: arquivo fora da pasta privada")
    with wave.open(str(audio), "rb") as stream:
        valid = (
            stream.getnchannels() == 1
            and stream.getframerate() == 16_000
            and stream.getsampwidth() == 2
            and stream.getnframes() > 0
            and stream.getcomptype() == "NONE"
        )
    if not valid:
        raise ValueError(f"{manifest.name}, linha {line}: esperado WAV PCM mono 16 kHz/16 bits")
    return audio


def split_groups(groups: set[str]) -> dict[str, str]:
    ordered = sorted(groups, key=lambda value: hashlib.sha256(value.encode("utf-8")).digest())
    total = len(ordered)
    if total < 3:
        raise ValueError("são necessários pelo menos três grupos independentes")
    train_end = min(max(1, int(total * 0.8)), total - 2)
    dev_end = min(max(train_end + 1, int(total * 0.9)), total - 1)
    return {
        group: "train" if index < train_end else "dev" if index < dev_end else "test"
        for index, group in enumerate(ordered)
    }


def prepare(positive_manifest: Path, negative_manifest: Path, output: Path, phrase: str) -> dict:
    if phrase not in PHRASES:
        raise ValueError(f"frase fora da lista FR-021: {phrase}")
    output_path = output.resolve(strict=False)
    input_paths = {
        positive_manifest.resolve(strict=True),
        negative_manifest.resolve(strict=True),
    }
    if output_path in input_paths:
        raise ValueError("a saída não pode substituir um manifesto de origem")

    positives: list[dict] = []
    positive_rows = read_rows(positive_manifest, POSITIVE_FIELDS)
    for line, row in enumerate(positive_rows, start=2):
        if row["phrase"].strip() != phrase:
            continue
        speaker = row["speaker_code"].strip()
        if not speaker or any(char in speaker for char in " /\\\t\r\n"):
            raise ValueError(f"corpus positivo, linha {line}: speaker_code inválido")
        if not row["environment"].strip() or not row["device"].strip():
            raise ValueError(f"corpus positivo, linha {line}: ambiente e dispositivo obrigatórios")
        audio = resolve_wav(positive_manifest, row["path"], line)
        positives.append({"source": "human", "speaker_code": speaker, "audio": audio})

    negatives: list[dict] = []
    negative_rows = read_rows(negative_manifest, NEGATIVE_FIELDS)
    for line, row in enumerate(negative_rows, start=2):
        source = row["source"].strip()
        speaker = row["speaker_code"].strip()
        if source not in {"common_voice", "noise"}:
            raise ValueError(f"corpus negativo, linha {line}: origem deve ser common_voice ou noise")
        if source == "common_voice" and not speaker:
            raise ValueError(f"corpus negativo, linha {line}: Common Voice exige código anônimo")
        if source == "noise" and speaker:
            raise ValueError(f"corpus negativo, linha {line}: ruído não pode ter speaker_code")
        audio = resolve_wav(negative_manifest, row["path"], line)
        negatives.append({"source": source, "speaker_code": speaker, "audio": audio})

    human_speakers = {item["speaker_code"] for item in positives}
    if len(human_speakers) < 20:
        raise ValueError(f"{phrase}: {len(human_speakers)} locutores humanos; FR-081 exige 20")
    if not positives or not negatives:
        raise ValueError("são necessárias gravações positivas e WAVs negativos")

    groups = {
        f"{item['source']}:{item['speaker_code']}" if item["speaker_code"] else
        f"noise:{hashlib.sha256(str(item['audio']).encode()).hexdigest()}"
        for item in (*positives, *negatives)
    }
    assignments = split_groups(groups)
    rows = []
    output_root = output.resolve().parent
    for label, items in (("wake", positives), ("negative", negatives)):
        for item in items:
            group = (
                f"{item['source']}:{item['speaker_code']}" if item["speaker_code"] else
                f"noise:{hashlib.sha256(str(item['audio']).encode()).hexdigest()}"
            )
            try:
                relative_audio = item["audio"].relative_to(output_root)
            except ValueError as error:
                raise ValueError("manifesto de saída deve ficar em uma pasta ancestral dos WAVs") from error
            rows.append({
                "split": assignments[group],
                "label": label,
                "path": relative_audio.as_posix(),
                "source": item["source"],
                "phrase": phrase if label == "wake" else "",
                "speaker_code": item["speaker_code"],
            })

    counts = {split: {label: 0 for label in ("wake", "negative")} for split in ("train", "dev", "test")}
    for row in rows:
        counts[row["split"]][row["label"]] += 1
    if any(not counts[split][label] for split in counts for label in ("wake", "negative")):
        raise ValueError("a divisão por locutor deixou um split sem amostras positivas ou negativas")

    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ValueError("arquivo de saída inválido")
    stage = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8", prefix=f".{output.name}.stage-",
            dir=output.parent, delete=False,
        ) as target:
            stage = Path(target.name)
            writer = csv.DictWriter(target, fieldnames=OUTPUT_FIELDS, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        os.chmod(stage, 0o600)
        stage.replace(output)
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)
    return {
        "output": str(output),
        "phrase": phrase,
        "human_speakers": len(human_speakers),
        "counts": counts,
        "consent_review": "origem e autorização ainda exigem conferência manual",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Monta manifesto privado WeKws com divisões por locutor")
    parser.add_argument("phrase", choices=PHRASES, help="uma frase FR-021 por execução")
    parser.add_argument("positive_manifest", type=Path, help="corpus privado validado pelo validate_corpus.py")
    parser.add_argument("negative_manifest", type=Path, help="TSV privado com source, speaker_code e path para WAVs")
    parser.add_argument("output", type=Path, help="manifest.tsv sob uma pasta ancestral dos WAVs")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.positive_manifest, args.negative_manifest, args.output, args.phrase), ensure_ascii=False, indent=2))
    except (OSError, ValueError, EOFError, wave.Error, csv.Error) as error:
        print(f"Preparação do manifesto: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
