"""Check that the installation guide retains critical integrity and media steps."""

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


if __name__ == "__main__":
    unittest.main()
