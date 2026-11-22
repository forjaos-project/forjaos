"""The installer must queue its public MOK without claiming a failed request succeeded."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "image/build_files/installer/stage_mok.sh"


@unittest.skipUnless(os.name == "posix", "runs with the Linux installer shell")
class StageMokTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.efi = self.root / "efi"
        self.cert = self.root / "secure_boot.der"
        self.cert.write_bytes(b"public certificate fixture")
        self.target_efi = self.root / "target/boot/efi/EFI"
        (self.target_efi / "fedora").mkdir(parents=True)
        (self.target_efi / "BOOT").mkdir()
        (self.target_efi / "fedora/mmx64.efi").write_bytes(b"signed target MokManager")
        (self.target_efi / "fedora/shimx64.efi").write_bytes(b"signed target shim")
        (self.target_efi / "BOOT/BOOTX64.EFI").write_bytes(b"signed target shim")
        self.calls = self.root / "calls"
        binary = self.root / "bin"
        binary.mkdir()
        self.binary = binary
        fake = binary / "mokutil"
        fake.write_text(
            '#!/usr/bin/env bash\n'
            'printf "%s\\n" "$*" >> "$MOK_CALLS"\n'
            'case "$1" in\n'
            '  --timeout) [[ "$2" == "-1" ]];;\n'
            '  --import) [[ "$MOK_STATE" == error ]] && exit 2; '
            '[[ "$MOK_STATE" == pending ]] && exit 0; '
            'read -r first; read -r second; '
            '[[ "$first" == universalblue && "$second" == universalblue ]];;\n'
            'esac\n'
        )
        fake.chmod(0o755)
        self.env = os.environ.copy()
        self.env.update(PATH=f"{binary}:{self.env['PATH']}", MOK_CALLS=str(self.calls))

    def run_script(self, state="absent"):
        return subprocess.run(
            ["bash", str(SCRIPT), str(self.efi), str(self.cert), str(self.target_efi)],
            env={**self.env, "MOK_STATE": state}, capture_output=True, text=True,
        )

    def test_skips_non_efi_system_without_calling_mokutil(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.calls.exists())

    def test_imports_public_key_with_unlimited_prompt_time(self):
        self.efi.mkdir()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls.read_text().splitlines(), [
            "--timeout -1", f"--import {self.cert}",
        ])
        self.assertEqual(
            (self.target_efi / "BOOT/mmx64.efi").read_bytes(),
            (self.target_efi / "fedora/mmx64.efi").read_bytes(),
        )
        self.assertIn("MOK_FALLBACK_MANAGER_INSTALLED", result.stdout)
        self.assertIn("MOK_STAGE_IMPORT_OK", result.stdout)
        self.assertNotIn("universalblue", result.stdout + result.stderr)

    def test_does_not_replace_a_different_fallback_bootloader(self):
        self.efi.mkdir()
        (self.target_efi / "BOOT/BOOTX64.EFI").write_bytes(b"different vendor")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.target_efi / "BOOT/mmx64.efi").exists())
        self.assertIn("MOK_FALLBACK_UNCHANGED", result.stdout)

    def test_missing_target_mok_manager_fails_before_enrollment(self):
        self.efi.mkdir()
        (self.target_efi / "fedora/mmx64.efi").unlink()
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_remounts_esp_when_boot_mount_hides_it(self):
        self.efi.mkdir()
        actual_efi = self.root / "esp/EFI"
        (actual_efi / "fedora").mkdir(parents=True)
        (actual_efi / "BOOT").mkdir()
        for relative in ("fedora/mmx64.efi", "fedora/shimx64.efi", "BOOT/BOOTX64.EFI"):
            (actual_efi / relative).write_bytes((self.target_efi / relative).read_bytes())
        (self.target_efi / "fedora/mmx64.efi").unlink()
        (self.binary / "findmnt").write_text('#!/bin/sh\necho "/dev/sda1 vfat"\n')
        (self.binary / "mount").write_text(
            '#!/bin/sh\nln -s "$FAKE_ESP/EFI" "$2/EFI"\n'
        )
        (self.binary / "umount").write_text('#!/bin/sh\nrm "$1/EFI"\n')
        for command in ("findmnt", "mount", "umount"):
            (self.binary / command).chmod(0o755)
        self.env.update(FAKE_ESP=str(self.root / "esp"), TMPDIR=str(self.root))
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MOK_STAGE_ESP_REMOUNTED", result.stdout)
        self.assertEqual(
            (actual_efi / "BOOT/mmx64.efi").read_bytes(),
            b"signed target MokManager",
        )
        self.assertIn("MOK_FALLBACK_MANAGER_INSTALLED", result.stdout)

    def test_repeating_an_enrollment_request_is_safe(self):
        self.efi.mkdir()
        result = self.run_script("pending")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls.read_text().splitlines(), [
            "--timeout -1", f"--import {self.cert}",
        ])

    def test_refuses_failed_enrollment_request(self):
        self.efi.mkdir()
        result = self.run_script("error")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls.read_text().splitlines(), [
            "--timeout -1", f"--import {self.cert}",
        ])


if __name__ == "__main__":
    unittest.main()
