"""FR-010/FR-014: wireless firmware is available inside the live installer."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTAINERFILE = ROOT / "image/build_files/installer/Containerfile"
BUILD_SCRIPT = ROOT / ".github/scripts/build-iso.sh"


class InstallerWifiFirmwareTests(unittest.TestCase):
    def test_installer_installs_intel_dvm_firmware_and_checks_initramfs(self):
        containerfile = CONTAINERFILE.read_text(encoding="utf-8")
        self.assertIn("iwlwifi-dvm-firmware", containerfile)
        self.assertIn("iwlwifi-5000-5.ucode", containerfile)
        self.assertIn("--add-drivers iwlwifi", containerfile)
        self.assertIn("grep -Fq 'iwlwifi-5000-5.ucode'", containerfile)
        self.assertIn("/usr/share/licenses/iwlwifi-dvm-firmware/LICENCE.iwlwifi_firmware", containerfile)

    def test_iso_license_inventory_includes_firmware_package_notice(self):
        containerfile = CONTAINERFILE.read_text(encoding="utf-8")
        build_script = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("iwlwifi-dvm-firmware", containerfile)
        self.assertIn("generate_third_party_licenses.py", build_script)
        self.assertIn("THIRD_PARTY_LICENSES.md", build_script)


if __name__ == "__main__":
    unittest.main()
