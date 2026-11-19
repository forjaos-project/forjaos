"""Tests for private wake-word training manifest preparation."""

import csv
import os
import tempfile
import wave
import unittest
from pathlib import Path

from prepare_manifest import OUTPUT_FIELDS, prepare, split_groups


class PrepareManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "audio").mkdir()

    def write_wav(self, relative: str) -> str:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16_000)
            output.writeframes(b"\x01\x00" * 160)
        return path.relative_to(self.root).as_posix()

    def write_tsv(self, name: str, fields: tuple[str, ...], rows: list[dict]) -> Path:
        path = self.root / name
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def corpus(self):
        positives = []
        negatives = []
        for index in range(20):
            positives.append({
                "speaker_code": f"human-{index:02}", "phrase": "Guará",
                "path": self.write_wav(f"audio/human-{index:02}.wav"),
                "environment": "sala", "device": "microfone-anonimo",
            })
        for index in range(30):
            negatives.append({
                "source": "common_voice", "speaker_code": f"cv-{index:02}",
                "path": self.write_wav(f"audio/cv-{index:02}.wav"),
            })
        positive = self.write_tsv(
            "positive.tsv", ("speaker_code", "phrase", "path", "environment", "device"), positives
        )
        negative = self.write_tsv("negative.tsv", ("source", "speaker_code", "path"), negatives)
        return positive, negative

    def test_builds_speaker_disjoint_manifest_with_all_splits(self):
        positive, negative = self.corpus()
        output = self.root / "manifest.tsv"
        summary = prepare(positive, negative, output, "Guará")
        self.assertEqual(summary["human_speakers"], 20)
        with output.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source, delimiter="\t"))
        self.assertEqual(set(rows[0]), set(OUTPUT_FIELDS))
        for split in ("train", "dev", "test"):
            self.assertTrue(any(row["split"] == split and row["label"] == "wake" for row in rows))
            self.assertTrue(any(row["split"] == split and row["label"] == "negative" for row in rows))
        speaker_splits = {}
        for row in rows:
            if row["speaker_code"]:
                key = f"{row['source']}:{row['speaker_code']}"
                self.assertEqual(speaker_splits.setdefault(key, row["split"]), row["split"])
        if os.name == "posix":
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_rejects_missing_fr081_coverage(self):
        positive, negative = self.corpus()
        with positive.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source, delimiter="\t"))[:19]
        incomplete = self.write_tsv(
            "incomplete.tsv", ("speaker_code", "phrase", "path", "environment", "device"), rows
        )
        with self.assertRaisesRegex(ValueError, "FR-081 exige 20"):
            prepare(incomplete, negative, self.root / "manifest.tsv", "Guará")

    def test_rejects_path_escape(self):
        positive, negative = self.corpus()
        with negative.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source, delimiter="\t"))
        rows[0]["path"] = "../outside.wav"
        escaped = self.write_tsv("escaped.tsv", ("source", "speaker_code", "path"), rows)
        with self.assertRaisesRegex(ValueError, "caminho deve ser relativo"):
            prepare(positive, escaped, self.root / "manifest.tsv", "Guará")

    def test_small_group_set_still_fills_three_splits(self):
        assignments = split_groups({"speaker-a", "speaker-b", "speaker-c"})
        self.assertEqual(set(assignments.values()), {"train", "dev", "test"})


if __name__ == "__main__":
    unittest.main()
