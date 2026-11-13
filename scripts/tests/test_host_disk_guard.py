"""Windows host reserve behavior; all threshold probes are dry runs."""

import html
import os
import shutil
import subprocess
import sys
import tempfile
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

    def test_watch_uses_graceful_stop_and_logs_success(self):
        with tempfile.TemporaryDirectory() as directory:
            stub = Path(directory) / "docker-stub.cmd"
            stub.write_text('@echo off\necho %* > "%~dp0called.txt"\nexit /b 0\n')
            result = self.probe_real_stop_with_stub(stub)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("RESULT=STOPPED_DOCKER", result.stdout)
            self.assertEqual((Path(directory) / "called.txt").read_text().strip(),
                             "desktop stop --timeout 120")
            self.assertIn("DOCKER_STOPPED", (Path(directory) / "guard-output" / "events.log").read_text())

    def test_watch_reports_stop_failure_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            stub = Path(directory) / "docker-stub.cmd"
            stub.write_text('@echo off\necho %* > "%~dp0called.txt"\nexit /b 7\n')
            result = self.probe_real_stop_with_stub(stub)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertNotIn("RESULT=STOPPED_DOCKER", result.stdout)
            self.assertEqual((Path(directory) / "called.txt").read_text().strip(),
                             "desktop stop --timeout 120")
            self.assertIn("STOP_FAILED", (Path(directory) / "guard-output" / "events.log").read_text())

    def test_test_mode_rejects_non_stub_executable(self):
        real_executable = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        result = self.probe_real_stop_with_stub(real_executable)
        self.assertEqual(result.returncode, 3)
        self.assertIn("stub CLI", result.stderr)
        self.assertNotIn("RESULT=STOPPED_DOCKER", result.stdout)

    def probe_real_stop_with_stub(self, stub: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
             "-Mode", "Watch", "-FreeGiBOverride", "119", "-TestMode",
             "-DockerCliOverride", str(stub)],
            text=True, capture_output=True, timeout=15, check=False,
        )

    def test_verify_rejects_tampered_task_or_script(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "check-disk.ps1"
            shutil.copyfile(SCRIPT, target)
            xml_path = root / "task.xml"
            good_xml = self.task_xml(target)
            xml_path.write_text(good_xml, encoding="utf-8")

            good = self.verify_fixture(xml_path, target, "Ready")
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertIn("RESULT=VERIFIED", good.stdout)

            xml_path.write_text(good_xml.replace("IgnoreNew", "Parallel"), encoding="utf-8")
            bad_schedule = self.verify_fixture(xml_path, target, "Ready")
            self.assertNotEqual(bad_schedule.returncode, 0)

            xml_path.write_text(good_xml, encoding="utf-8")
            disabled = self.verify_fixture(xml_path, target, "Disabled")
            self.assertNotEqual(disabled.returncode, 0)

            target.write_text("tampered", encoding="utf-8")
            stale = self.verify_fixture(xml_path, target, "Ready")
            self.assertNotEqual(stale.returncode, 0, stale.stdout + stale.stderr)

    def verify_fixture(self, xml_path: Path, target: Path, state: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(INSTALLER),
             "-Mode", "Verify", "-TestMode", "-TaskXmlPath", str(xml_path),
             "-InstalledScriptPath", str(target), "-TaskState", state],
            text=True, capture_output=True, timeout=15, check=False,
        )

    def task_xml(self, target: Path) -> str:
        sid = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "[Security.Principal.WindowsIdentity]::GetCurrent().User.Value"],
            text=True, capture_output=True, timeout=15, check=True,
        ).stdout.strip()
        command = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        arguments = f'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{target}" -Mode Watch'
        def escaped(value: object) -> str:
            return html.escape(str(value), quote=True)
        return (
            '<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">'
            '<Triggers><CalendarTrigger><StartBoundary>2026-11-12T00:00:00</StartBoundary>'
            '<Repetition><Interval>PT1M</Interval><Duration>P1D</Duration></Repetition>'
            '<ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>'
            '</CalendarTrigger></Triggers>'
            f'<Principals><Principal><UserId>{escaped(sid)}</UserId>'
            '<LogonType>InteractiveToken</LogonType></Principal></Principals>'
            '<Settings><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>'
            '<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>'
            '<ExecutionTimeLimit>PT3M</ExecutionTimeLimit>'
            '<MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>'
            '<StartWhenAvailable>true</StartWhenAvailable></Settings>'
            f'<Actions><Exec><Command>{escaped(command)}</Command>'
            f'<Arguments>{escaped(arguments)}</Arguments>'
            f'<WorkingDirectory>{escaped(target.parent)}</WorkingDirectory>'
            '</Exec></Actions></Task>'
        )


if __name__ == "__main__":
    unittest.main()
