"""Protect an existing Btrfs home subvolume during bootc installation."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


PATCHER = Path(__file__).resolve().parents[2] / "image/build_files/installer/patch_anaconda_bootc.py"
SPEC = importlib.util.spec_from_file_location("patch_anaconda_bootc", PATCHER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SOURCE = '''class DeployBootcTask:
    def _clean_physroot(self):
        path = "/mnt/sysimage/home"
        if True:
            if os.path.ismount(path):
                log.debug("Unmounting %s", path)
                safe_exec_program("umount", ["-l", path])

            safe_exec_program("rm", ["-rf", path])
'''


class PatchAnacondaBootcTests(unittest.TestCase):
    def setUp(self):
        self.exec_program = Mock()
        self.mount_device = Mock()
        self.ismount = Mock(return_value=True)
        self.namespace = {
            "os": SimpleNamespace(path=SimpleNamespace(ismount=self.ismount)),
            "blivet": SimpleNamespace(util=SimpleNamespace(get_mount_device=self.mount_device)),
            "PayloadInstallationError": RuntimeError,
            "log": Mock(),
            "safe_exec_program": self.exec_program,
        }
        exec(MODULE.patch(SOURCE), self.namespace)

    def test_unmounted_btrfs_subvolume_is_neither_unmounted_nor_removed(self):
        self.mount_device.return_value = None

        with self.assertRaisesRegex(RuntimeError, "Existing unmounted Btrfs subvolume"):
            self.namespace["DeployBootcTask"]()._clean_physroot()

        self.exec_program.assert_not_called()

    def test_real_mount_is_unmounted_before_cleanup(self):
        self.mount_device.return_value = "/dev/sda3"

        self.namespace["DeployBootcTask"]()._clean_physroot()

        self.assertEqual(self.exec_program.call_args_list, [
            unittest.mock.call("umount", ["-l", "/mnt/sysimage/home"]),
            unittest.mock.call("rm", ["-rf", "/mnt/sysimage/home"]),
        ])

    def test_plain_directory_uses_existing_cleanup(self):
        self.ismount.return_value = False

        self.namespace["DeployBootcTask"]()._clean_physroot()

        self.mount_device.assert_not_called()
        self.exec_program.assert_called_once_with("rm", ["-rf", "/mnt/sysimage/home"])

    def test_refuses_unknown_upstream_layout(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            MODULE.patch("class DeployBootcTask: pass\n")


if __name__ == "__main__":
    unittest.main()
