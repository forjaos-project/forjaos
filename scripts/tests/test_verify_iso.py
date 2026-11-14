"""Contract tests for the install ISO size and checksum verifier."""

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/verify-iso.py"


class VerifyIsoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.iso = self.directory / "forjaos.iso"

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True, text=True, check=False,
        )

    def test_create_and_check_checksum(self):
        self.iso.write_bytes(b"installable ISO fixture")
        created = self.run_cli("create", self.iso)
        self.assertEqual(created.returncode, 0, created.stderr)
        manifest = self.directory / "SHA256SUMS"
        expected = hashlib.sha256(self.iso.read_bytes()).hexdigest()
        self.assertEqual(manifest.read_text(), f"{expected}  forjaos.iso\n")
        checked = self.run_cli("check", manifest)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.iso.write_bytes(b"corrupted")
        self.assertNotEqual(self.run_cli("check", manifest).returncode, 0)

    def test_missing_and_empty_iso_fail(self):
        self.assertNotEqual(self.run_cli("create", self.iso).returncode, 0)
        self.iso.touch()
        self.assertNotEqual(self.run_cli("create", self.iso).returncode, 0)

    def test_decimal_six_gb_limit(self):
        with self.iso.open("wb") as stream:
            stream.truncate(6_000_000_001)
        result = self.run_cli("create", self.iso)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("6 GB", result.stderr)
        self.assertFalse((self.directory / "SHA256SUMS").exists())

    def test_github_release_asset_limit(self):
        with self.iso.open("wb") as stream:
            stream.truncate(2 * 1024**3)
        result = self.run_cli("create", self.iso)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("2 GiB", result.stderr)
        self.assertFalse((self.directory / "SHA256SUMS").exists())

    def test_rejects_manifest_paths_and_invalid_digest(self):
        manifest = self.directory / "SHA256SUMS"
        self.iso.write_bytes(b"fixture")
        for line in ("0" * 64 + "  ../forjaos.iso\n", "bad  forjaos.iso\n"):
            manifest.write_text(line)
            self.assertNotEqual(self.run_cli("check", manifest).returncode, 0)


if __name__ == "__main__":
    unittest.main()
