"""Behavioral fixtures for the F0-004 rootfs branding checker."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "check_branding.py"


class BrandingCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "rootfs"
        (self.root / "etc").mkdir(parents=True)
        (self.root / "etc/os-release").write_text(
            'NAME="ForjaOS"\nID=forjaos\nID_LIKE=fedora\nPRETTY_NAME="ForjaOS 0.1"\n',
            encoding="utf-8",
        )
        binary = self.base / "bin"
        binary.mkdir()
        rpm = binary / "rpm"
        rpm.write_text(
            "#!/usr/bin/env bash\n"
            "if [ \"${TEST_RPM_FAIL:-0}\" = 1 ]; then echo 'rpm failed' >&2; exit 7; fi\n"
            "printf '%s' \"${TEST_RPM_PACKAGES:-}\"\n",
            encoding="utf-8",
        )
        rpm.chmod(0o755)
        self.env = os.environ.copy()
        self.env["PATH"] = f"{binary}{os.pathsep}{self.env['PATH']}"

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def check(self, *, packages="", fail_rpm=False):
        env = self.env.copy()
        env["TEST_RPM_PACKAGES"] = packages
        env["TEST_RPM_FAIL"] = "1" if fail_rpm else "0"
        result = subprocess.run(
            [sys.executable, str(CHECKER), "--rootfs", str(self.root), "--json"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        return result, json.loads(result.stdout)

    def test_clean_rootfs_allows_fedora_id_like_and_legal_documents(self):
        self.write("usr/share/licenses/forjaos/Fedora-Legal.txt", "Fedora license")
        self.write("usr/share/doc/forjaos/README", "Bazzite source attribution")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report, {"status": "ok", "findings": []})

    def test_rejects_missing_or_wrong_identity(self):
        (self.root / "etc/os-release").write_text('NAME="Bazzite"\nID=bazzite\n', encoding="utf-8")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["status"], "fail")
        self.assertEqual({item["kind"] for item in report["findings"]}, {"identity"})
        self.assertEqual(len(report["findings"]), 3)

    def test_rejects_each_forbidden_package_family(self):
        result, report = self.check(
            packages="forjaos-branding\nfedora-logos\nfedora-release-identity-kinoite\nbazzite-branding\nbluefin-branding\n"
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            {item["value"] for item in report["findings"] if item["kind"] == "package"},
            {"fedora-logos", "fedora-release-identity-kinoite", "bazzite-branding", "bluefin-branding"},
        )

    def test_rejects_visible_text_and_branded_path(self):
        self.write("etc/issue", "ForjaOS\nWelcome to Universal Blue\n")
        self.write("usr/share/wallpapers/Bazzite/default.svg", "<svg></svg>")
        self.write("usr/share/plasma/look-and-feel/org.forjaos.desktop/colors.colors", "Title=Bluefin\n")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(f["path"] == "/etc/issue" and f["line"] == 2 for f in report["findings"]))
        self.assertTrue(any("Bazzite" in f["path"] and f["kind"] == "path" for f in report["findings"]))
        self.assertTrue(any(f["path"].endswith("colors.colors") and f["kind"] == "text" for f in report["findings"]))

    def test_rejects_branded_symlink_target(self):
        target = self.root / "usr/share/icons/hicolor/32x32/apps/start-here.png"
        target.parent.mkdir(parents=True)
        self.write("usr/share/icons/hicolor/32x32/apps/fedora-logo.png", "PNG")
        try:
            target.symlink_to("fedora-logo.png")
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(f["path"].endswith("start-here.png") and f["kind"] == "path" for f in report["findings"]))

    def test_rejects_missing_forjaos_branding_package(self):
        result, report = self.check(packages="some-other-package\n")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(f["kind"] == "package" and f["value"] == "forjaos-branding missing" for f in report["findings"]))

    def test_rpm_error_is_not_a_clean_pass(self):
        result, report = self.check(fail_rpm=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["status"], "error")
        self.assertTrue(any(f["kind"] == "inspection" for f in report["findings"]))

    def test_directory_symlink_is_not_read_as_a_file(self):
        linked = self.root / "etc/xdg/systemd/user"
        linked.parent.mkdir(parents=True)
        try:
            linked.symlink_to("/etc", target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 0, report)

    def test_json_is_deterministic(self):
        self.write("etc/motd", "Bluefin\n")
        first, report = self.check(packages="bazzite-branding\n")
        second, _ = self.check(packages="bazzite-branding\n")
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(report["status"], "fail")


if __name__ == "__main__":
    unittest.main()
