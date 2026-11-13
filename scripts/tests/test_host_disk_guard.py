"""Windows host reserve behavior; all threshold probes are dry runs."""

import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "host" / "check-disk.ps1"
INSTALLER = SCRIPT.with_name("install-disk-guard.ps1")


@unittest.skipUnless(sys.platform == "win32", "Windows host guard")
class HostDiskGuardTests(unittest.TestCase):
    def probe(self, mode: str, free_gib: float) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
             "-Mode", mode, "-FreeGiBOverride", str(free_gib), "-DryRun"],
            text=True, capture_output=True, timeout=15, check=False,
        )

    def test_preflight_allows_exact_reserve(self):
        result = self.probe("Check", 160)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESULT=PASS", result.stdout)

    def test_preflight_blocks_below_reserve(self):
        result = self.probe("Check", 159.9)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("RESULT=BLOCK", result.stdout)

    def test_watch_stops_only_below_threshold(self):
        safe = self.probe("Watch", 120)
        low = self.probe("Watch", 119.9)
        self.assertEqual(safe.returncode, 0, safe.stderr)
        self.assertIn("RESULT=SAFE", safe.stdout)
        self.assertEqual(low.returncode, 0, low.stderr)
        self.assertIn("RESULT=WOULD_STOP_DOCKER", low.stdout)

    def test_override_requires_dry_run(self):
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
             "-Mode", "Watch", "-FreeGiBOverride", "0"],
            text=True, capture_output=True, timeout=15, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("RESULT=STOPPED_DOCKER", result.stdout)

    def test_installer_plans_one_minute_guard_on_c(self):
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(INSTALLER),
             "-Mode", "Plan"],
            text=True, capture_output=True, timeout=15, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESULT=PLAN", result.stdout)
        self.assertIn("INTERVAL_MIN=1", result.stdout)
        self.assertIn("TARGET=C:", result.stdout)


if __name__ == "__main__":
    unittest.main()
