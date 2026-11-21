"""Guard the installer password path against SELinux relabel no-ops."""

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


PATCHER = Path(__file__).resolve().parents[2] / "image/build_files/installer/patch_anaconda_users.py"
SPEC = importlib.util.spec_from_file_location("patch_anaconda_users", PATCHER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SOURCE = '''def set_password(root):
    rootargs = ["-R", root]
    if root:
        proc = util.startProgram(["chpasswd", "-e"] + rootargs, stdin=subprocess.PIPE)
        return proc
'''


class PatchAnacondaUsersTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        policy = root / "etc/selinux/targeted/contexts/files/file_contexts"
        policy.parent.mkdir(parents=True)
        policy.write_text("fixture\n")
        for name in ("passwd", "shadow"):
            (root / "etc" / name).write_text("fixture\n")
        self.root = str(root)
        self.util = Mock()
        self.util.execWithRedirect.return_value = 0
        self.os = SimpleNamespace(path=os.path, getxattr=Mock())
        self.namespace = {"os": self.os, "subprocess": subprocess, "util": self.util}
        exec(MODULE.patch(SOURCE), self.namespace)

    def test_relabels_from_live_installer_before_password(self):
        labels = [
            b"system_u:object_r:passwd_file_t:s0\x00",
            b"system_u:object_r:shadow_t:s0\x00",
        ]
        self.os.getxattr.side_effect = labels
        self.namespace["set_password"](self.root)

        args, kwargs = self.util.execWithRedirect.call_args
        self.assertEqual(args[0], "setfiles")
        self.assertEqual(args[1][:3], ["-F", "-r", self.root])
        self.assertEqual(kwargs, {})  # Running in the live installer, not in a chroot.
        self.util.startProgram.assert_called_once()

    def test_refuses_password_when_relabel_did_not_change_type(self):
        self.os.getxattr.return_value = b"system_u:object_r:etc_t:s0\x00"
        with self.assertRaisesRegex(OSError, "Wrong SELinux type"):
            self.namespace["set_password"](self.root)

        self.util.startProgram.assert_not_called()


if __name__ == "__main__":
    unittest.main()
