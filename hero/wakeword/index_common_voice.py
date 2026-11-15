#!/usr/bin/env python3
"""Index Brazilian Portuguese negative clips without extracting audio."""

import argparse
import csv
import io
import json
import re
import tarfile
import unicodedata
from collections import Counter
from pathlib import Path


ARCHIVE_ROOT = "cv-corpus-27.0-2026-09-11/pt/"
VARIANT = "Portuguese (Brasil)"
WAKE_NAMES = frozenset({"guara", "tupa", "jaci", "iara", "ipe", "boto", "curio", "arara"})
SPLITS = ("train", "dev", "test")


def contains_wake_name(sentence: str) -> bool:
    folded = "".join(
        char for char in unicodedata.normalize("NFD", sentence.casefold())
        if unicodedata.category(char) != "Mn"
    )
    return bool(WAKE_NAMES.intersection(re.findall(r"\w+", folded)))


def index(archive_path: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = output_dir / "common-voice-pt-br-negative-candidates.tsv"
    counts = Counter()
    speakers: dict[str, set[str]] = {}

    with tarfile.open(archive_path, "r:gz") as archive, manifest.open(
        "w", encoding="utf-8", newline=""
    ) as output:
        writer = csv.writer(output, delimiter="\t")
        writer.writerow(("split", "client_id", "path"))
        for split in SPLITS:
            speakers[split] = set()
            member = archive.getmember(ARCHIVE_ROOT + split + ".tsv")
            with archive.extractfile(member) as binary:
                if binary is None:
                    raise ValueError(f"metadados ausentes: {split}")
                rows = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8"), delimiter="\t")
                required = {"client_id", "path", "sentence", "variant"}
                if not required.issubset(rows.fieldnames or ()):
                    raise ValueError(f"colunas ausentes: {split}")
                for row in rows:
                    counts[split + "_total"] += 1
                    if row["variant"] != VARIANT:
                        continue
                    counts[split + "_pt_br"] += 1
                    if contains_wake_name(row["sentence"]):
                        counts[split + "_excluded_names"] += 1
                        continue
                    clip, client = row["path"], row["client_id"]
                    if not clip.endswith(".mp3") or "/" in clip or "\\" in clip or not client:
                        counts[split + "_invalid"] += 1
                        continue
                    writer.writerow((split, client, ARCHIVE_ROOT + "clips/" + clip))
                    speakers[split].add(client)
                    counts[split + "_selected"] += 1

    overlaps = {
        first + "_" + second: len(speakers[first] & speakers[second])
        for first, second in (("train", "dev"), ("train", "test"), ("dev", "test"))
    }
    summary = {
        "source": archive_path.name,
        "scope": "Brazilian Portuguese candidate negatives; metadata only, no audio extracted",
        "counts": dict(counts),
        "speakers_per_split": {split: len(speakers[split]) for split in SPLITS},
        "speaker_overlap": overlaps,
        "clips_verified_in_archive": False,
        "fr081_20_speaker_validation": "pending; these clips do not replace authorized phrase recordings",
    }
    (output_dir / "common-voice-pt-br-negative-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexa metadados negativos pt-BR do Common Voice")
    parser.add_argument("archive", type=Path, help="Arquivo cv-corpus-*-pt.tar.gz")
    parser.add_argument("output_dir", type=Path, help="Pasta privada fora do repositório")
    args = parser.parse_args()
    try:
        summary = index(args.archive, args.output_dir)
    except (OSError, ValueError, KeyError, tarfile.TarError, csv.Error) as error:
        parser.exit(1, f"Common Voice: {error}\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not any(summary["speaker_overlap"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
