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


if __name__ == "__main__":
    unittest.main()
