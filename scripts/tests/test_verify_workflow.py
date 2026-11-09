"""GOV-011 / ADR-033: o workflow verify.yml deve rodar os mesmos comandos do gate /test."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")

REQUIRED = [
    "python3 -m unittest discover -s scripts/tests -p 'test_*.py'",
    "python3 -m unittest discover -s brand/tests -p 'test_*.py'",
    "scripts/run-shell-tests.sh",
    "scripts/check-tokens.sh",
    "scripts/check-agents-sync.sh",
    "python3 scripts/roadmap.py validate --branch",
    "python3 scripts/gen_tela_specs.py --check",
    "python3 brand/logo/build_logo.py --check",
]


class VerifyWorkflowTest(unittest.TestCase):
    def test_runs_on_pull_request(self):
        self.assertRegex(WORKFLOW, r"(?m)^on:\n(?:  .*\n)*?  pull_request:")

    def test_runs_every_gate_command(self):
        runs = re.findall(r"(?m)^\s+run: (.+)$", WORKFLOW)
        for cmd in REQUIRED:
            with self.subTest(cmd=cmd):
                self.assertIn(cmd, runs)  # linha inteira, sem eco nem comentário

    def test_no_step_can_be_skipped_or_ignored(self):
        code = "\n".join(l.split(" #")[0] for l in WORKFLOW.splitlines() if not l.lstrip().startswith("#"))
        self.assertNotIn("continue-on-error", code)
        self.assertIsNone(re.search(r"(?m)^\s+if:", code))

    def test_fetches_full_history_for_roadmap_base(self):
        self.assertIn("fetch-depth: 0", WORKFLOW)

    def test_actions_pinned_by_sha(self):
        for ref in re.findall(r"uses: (\S+)", WORKFLOW):
            with self.subTest(ref=ref):
                self.assertRegex(ref, r"@[0-9a-f]{40}$")

    def test_read_only_permissions(self):
        self.assertIn("contents: read", WORKFLOW)
        self.assertNotIn("write", WORKFLOW.split("jobs:")[0].replace("# ", ""))


if __name__ == "__main__":
    unittest.main()
