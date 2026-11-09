"""F0-003: keep scheduled image publication and failure reporting gated."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "daily-image.yml"


class DailyImageWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")
        cls.image_job = cls.source.split("  image:\n", 1)[1].split("  report_failure:\n", 1)[0]
        cls.report_job = cls.source.split("  report_failure:\n", 1)[1]

    def test_daily_schedule_and_manual_dispatch(self):
        self.assertRegex(self.source, r"(?m)^on:\n  schedule:\n    - cron: '[^']+'\n  workflow_dispatch:")
        self.assertIn("cancel-in-progress: false", self.source)

    def test_two_variants_without_matrix_fail_fast(self):
        self.assertIn("fail-fast: false", self.image_job)
        self.assertRegex(
            self.image_job,
            r"variant: \[forjaos-nvidia-open, forjaos\]",
        )
        self.assertIn("bash .github/scripts/daily-image.sh", self.image_job)
        self.assertIn("${{ matrix.variant }}", self.image_job)

    def test_build_has_only_required_permissions_and_secrets(self):
        self.assertIn("contents: read", self.image_job)
        self.assertIn("packages: write", self.image_job)
        self.assertNotIn("issues: write", self.image_job)
        self.assertIn("SIGNING_SECRET: ${{ secrets.SIGNING_SECRET }}", self.image_job)
        self.assertIn("GH_TOKEN: ${{ github.token }}", self.image_job)
        self.assertIn("apt-get install", self.image_job)
        self.assertIn("podman skopeo", self.image_job)

    def test_failed_matrix_run_is_only_issue_writer(self):
        self.assertIn("needs: image", self.report_job)
        self.assertIn("always() && needs.image.result == 'failure'", self.report_job)
        self.assertIn("issues: write", self.report_job)
        self.assertNotIn("packages: write", self.report_job)
        self.assertNotIn("SIGNING_SECRET", self.report_job)
        self.assertIn("gh issue create", self.report_job)
        self.assertIn("gh issue comment", self.report_job)
        self.assertIn("GITHUB_RUN_ID", self.report_job)

    def test_actions_are_pinned_and_stable_is_not_promoted(self):
        for action in re.findall(r"uses: (\S+)", self.source):
            with self.subTest(action=action):
                self.assertRegex(action, r"@[0-9a-f]{40}$")
        self.assertNotIn(":stable", self.source)
        self.assertNotIn("continue-on-error", self.source)


if __name__ == "__main__":
    unittest.main()
