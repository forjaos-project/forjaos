"""Check that the installation guide retains critical integrity and media steps."""

import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


GUIDE = Path(__file__).resolve().parents[2] / "docs/install.md"


class InstallGuideTests(unittest.TestCase):
    def test_integrity_and_three_media_methods_are_documented(self):
        guide = GUIDE.read_text(encoding="utf-8")
        for required in (
            "SHA256SUMS", "sha256sum -c", "cosign verify-blob", "cosign.pub",
            "Fedora Media Writer", "Ventoy", "dd", "lsblk", "Secure Boot",
            "docs/releases/", "forjaos-nvidia-open.iso", "forjaos.iso",
        ):
            with self.subTest(required=required):
                self.assertIn(required, guide)

    def test_network_install_dependency_is_explicit(self):
        guide = GUIDE.read_text(encoding="utf-8")
        self.assertIn("conexão com a internet", guide)
        self.assertIn("digest", guide)
        self.assertIn("assinatura do payload", guide)
        self.assertIn("2 GiB", guide)

    def test_candidate_draft_is_not_described_as_stable(self):
        guide = GUIDE.read_text(encoding="utf-8")
        self.assertIn("candidate_tag", guide)
        self.assertIn("rascunho", guide)
        self.assertIn(":testing", guide)
        self.assertIn(":stable", guide)

    def test_selected_iso_uses_combined_release_manifest(self):
        guide = GUIDE.read_text(encoding="utf-8")
        self.assertIn("sha256sum -c --ignore-missing SHA256SUMS", guide)
        self.assertIn("combinado", guide)

    @unittest.skipUnless(shutil.which("sha256sum"), "sha256sum is required")
    def test_combined_manifest_checks_present_iso_and_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected = root / "forjaos-nvidia-open.iso"
            selected.write_bytes(b"selected ISO")
            selected_hash = hashlib.sha256(selected.read_bytes()).hexdigest()
            other_hash = hashlib.sha256(b"other ISO").hexdigest()
            (root / "SHA256SUMS").write_text(
                f"{other_hash}  forjaos.iso\n"
                f"{selected_hash}  forjaos-nvidia-open.iso\n",
                encoding="utf-8",
            )
            command = ["sha256sum", "-c", "--ignore-missing", "SHA256SUMS"]
            valid = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertIn("forjaos-nvidia-open.iso: OK", valid.stdout)

            selected.write_bytes(b"corrupted ISO")
            corrupted = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertNotEqual(corrupted.returncode, 0)
            self.assertIn("forjaos-nvidia-open.iso: FAILED", corrupted.stdout)


if __name__ == "__main__":
    unittest.main()
