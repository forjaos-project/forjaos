"""Contract tests for the private training manifest."""

import csv
import tempfile
import unittest
from pathlib import Path

from train import read_manifest, slug


FIELDS = ("split", "label", "path", "source", "phrase", "speaker_code")


class TrainingManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "audio").mkdir()
        for name in ("positive.wav", "negative.wav"):
            (self.root / "audio" / name).write_bytes(b"placeholder")
        self.rows = []
        for split in ("train", "dev", "test"):
            self.rows.extend((
                {
                    "split": split, "label": "wake", "path": "audio/positive.wav",
                    "source": "piper", "phrase": "Luma", "speaker_code": f"piper-{split}",
                },
                {
                    "split": split, "label": "negative", "path": "audio/negative.wav",
                    "source": "common_voice", "phrase": "", "speaker_code": f"cv-{split}",
                },
            ))

    def write_manifest(self, rows=None):
        path = self.root / "manifest.tsv"
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=FIELDS, delimiter="\t")
            writer.writeheader()
            writer.writerows(self.rows if rows is None else rows)
        return path

    def test_accepts_disjoint_splits_and_relative_files(self):
        examples = read_manifest(self.write_manifest(), "Luma")
        self.assertEqual(len(examples), 6)
        self.assertTrue(all(example.path.is_absolute() for example in examples))

    def test_rejects_speaker_overlap_between_splits(self):
        rows = list(self.rows)
        rows[-1] = {**rows[-1], "speaker_code": "cv-train"}
        with self.assertRaisesRegex(ValueError, "mais de uma divisão"):
            read_manifest(self.write_manifest(rows), "Luma")

    def test_rejects_path_escape_and_mismatched_phrase(self):
        rows = list(self.rows)
        rows[0] = {**rows[0], "path": "../outside.wav"}
        with self.assertRaisesRegex(ValueError, "relativo ao manifesto"):
            read_manifest(self.write_manifest(rows), "Luma")
        rows = list(self.rows)
        rows[0] = {**rows[0], "phrase": "Outra"}
        with self.assertRaisesRegex(ValueError, "não corresponde"):
            read_manifest(self.write_manifest(rows), "Luma")

    def test_slug_removes_accents_and_separators(self):
        self.assertEqual(slug("Guará da Silva"), "guaradasilva")


if __name__ == "__main__":
    unittest.main()
