"""Guard the ISO CI authority boundary and installation guide."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/iso.yml"


class IsoWorkflowTests(unittest.TestCase):
    def test_real_builds_are_gated_for_both_variants(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("variant: [forjaos, forjaos-nvidia-open]", source)
        self.assertIn(".github/scripts/build-iso.sh", source)
        self.assertIn("scripts/verify-iso.py create", source)
        self.assertIn("scripts/verify-iso.py check", source)
        self.assertIn("cosign verify-blob", source)
        self.assertIn("--bundle", source)
        self.assertIn("actions/upload-artifact@", source)
        self.assertIn("'image/build_files/installer/**'", source)
        self.assertIn("'brand/palette.json'", source)
        self.assertIn("'brand/logo/**'", source)
        self.assertIn("'brand/fonts/**'", source)
        self.assertIn("THIRD_PARTY_LICENSES.md", source)

    def test_pr_job_has_no_release_authority(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        build_section = source.split("\n  release:\n", 1)[0]
        self.assertIn("pull_request:", source)
        self.assertIn("workflow_dispatch:", source)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", build_section)
        self.assertIn("contents: read", build_section)
        self.assertNotIn("contents: write", build_section)
        self.assertNotIn("gh release create", build_section)
        self.assertNotIn("gh release upload", build_section)
        self.assertNotIn("delete:packages", build_section)

    def test_release_requires_main_and_creates_verified_draft(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("release_tag:", source)
        self.assertIn('IMAGE_CHANNEL', source)
        release_section = source.split("\n  release:\n", 1)[1]
        for required in (
            "github.ref == 'refs/heads/main'", "contents: write",
            "actions/download-artifact@", "gh release create", "--draft",
            "gh release download", "scripts/verify-iso.py check",
            "cosign verify-blob", "v[0-9]+", "SHA256SUMS",
        ):
            with self.subTest(required=required):
                self.assertIn(required, release_section)

if __name__ == "__main__":
    unittest.main()
