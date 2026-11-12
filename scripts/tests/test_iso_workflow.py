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
        self.assertIn("'image/build_files/installer/Containerfile'", source)
        self.assertIn("'image/build_files/installer/configure_installer.py'", source)

    def test_pr_job_has_no_release_authority(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request:", source)
        self.assertIn("workflow_dispatch:", source)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", source)
        self.assertIn("contents: read", source)
        self.assertNotIn("contents: write", source)
        self.assertNotIn("gh release create", source)
        self.assertNotIn("gh release upload", source)
        self.assertNotIn("delete:packages", source)

if __name__ == "__main__":
    unittest.main()
