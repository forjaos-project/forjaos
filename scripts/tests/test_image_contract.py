"""Behavior tests for the image's RPM and system service contract."""

import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "image/build_files/check_image_contract.py"
SPEC = importlib.util.spec_from_file_location("check_image_contract", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


REQUIRED = {
    "podman", "distrobox", "steam", "steam-devices", "firewalld", "audit",
    "btop", "nvtop", "forjaos-branding", "python3", "git-core",
    "cockpit-bridge", "cockpit-system",
}
STATES = {
    "firewalld.service": "enabled",
    "auditd.service": "enabled",
    "sshd.service": "disabled",
    "cockpit.socket": "disabled",
}


class ImageContractTests(unittest.TestCase):
    def test_valid_inherited_image_passes(self):
        self.assertEqual(MODULE.check_contract(REQUIRED, STATES), [])

    def test_missing_developer_and_gaming_packages_fail(self):
        errors = MODULE.check_contract(REQUIRED - {"podman", "steam"}, STATES)
        self.assertTrue(any("podman" in error for error in errors))
        self.assertTrue(any("steam" in error for error in errors))

    def test_retained_waydroid_fails(self):
        errors = MODULE.check_contract(REQUIRED | {"waydroid-selinux"}, STATES)
        self.assertTrue(any("waydroid-selinux" in error for error in errors))

    def test_wrong_service_states_fail(self):
        states = {**STATES, "firewalld.service": "disabled", "sshd.service": "enabled"}
        errors = MODULE.check_contract(REQUIRED, states)
        self.assertTrue(any("firewalld.service" in error for error in errors))
        self.assertTrue(any("sshd.service" in error for error in errors))

    def test_absent_cockpit_socket_is_safe_when_components_exist(self):
        states = {**STATES, "cockpit.socket": "not-found"}
        self.assertEqual(MODULE.check_contract(REQUIRED, states), [])

    def test_rpm_query_failure_fails_closed(self):
        with patch.object(MODULE.subprocess, "run", return_value=subprocess.CompletedProcess([], 2, "", "bad rpm")):
            with self.assertRaisesRegex(ValueError, "RPM query failed"):
                MODULE.read_packages()

    def test_systemctl_query_failure_fails_closed(self):
        with patch.object(MODULE.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "error")):
            with self.assertRaisesRegex(ValueError, "systemctl query failed"):
                MODULE.read_unit_state("firewalld.service")

    def test_disabled_state_accepts_systemctl_exit_one(self):
        result = subprocess.CompletedProcess([], 1, "disabled\n", "")
        with patch.object(MODULE.subprocess, "run", return_value=result):
            self.assertEqual(MODULE.read_unit_state("sshd.service"), "disabled")


if __name__ == "__main__":
    unittest.main()
