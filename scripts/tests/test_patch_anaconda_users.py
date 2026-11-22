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
        root = Path(self.temp.name) / "target"
        policy = root / "etc/selinux/targeted/contexts/files/file_contexts"
        policy.parent.mkdir(parents=True)
        policy.write_text("fixture\n")
        policy_dir = root / "etc/selinux/targeted/policy"
        policy_dir.mkdir()
        (policy_dir / "policy.35").write_bytes(b"fixture")
        for name in ("passwd", "shadow"):
            (root / "etc" / name).write_text("fixture\n")
        self.root = str(root)
        self.util = Mock()
        self.util.execWithRedirect.return_value = 0
        self.os = SimpleNamespace(path=os.path, listdir=os.listdir, getxattr=Mock())
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

    def test_password_setup_succeeds_through_a_linked_target_root(self):
        alias = Path(self.temp.name) / "sysroot"
        if os.name == "nt":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(alias), self.root],
                check=True, capture_output=True,
            )
        else:
            alias.symlink_to(self.root, target_is_directory=True)

        def relabel(command, arguments):
            # setfiles refuses a symbolic-link ancestor (observed in the ISO VM).
            return int(any(
                os.path.normcase(os.path.realpath(argument))
                != os.path.normcase(os.path.normpath(argument))
                for argument in arguments if os.path.isabs(argument)
            ))

        self.util.execWithRedirect.side_effect = relabel
        self.os.getxattr.side_effect = [
            b"system_u:object_r:passwd_file_t:s0\x00",
            b"system_u:object_r:shadow_t:s0\x00",
        ]
        result = self.namespace["set_password"](str(alias))

        self.assertIs(result, self.util.startProgram.return_value)

    def test_uses_target_policy_when_live_policy_lacks_target_types(self):
        policy_dir = Path(self.root) / "etc/selinux/targeted/policy"
        (policy_dir / "policy.9").write_bytes(b"older fixture")
        self.util.execWithRedirect.side_effect = (
            lambda command, arguments: int("-c" not in arguments)
        )
        self.os.getxattr.side_effect = [
            b"system_u:object_r:passwd_file_t:s0\x00",
            b"system_u:object_r:shadow_t:s0\x00",
        ]

        result = self.namespace["set_password"](self.root)

        self.assertIs(result, self.util.startProgram.return_value)
        arguments = self.util.execWithRedirect.call_args.args[1]
        self.assertEqual(Path(arguments[arguments.index("-c") + 1]), policy_dir / "policy.35")

    def test_refuses_password_without_a_target_binary_policy(self):
        (Path(self.root) / "etc/selinux/targeted/policy/policy.35").unlink()

        with self.assertRaisesRegex(OSError, "Target SELinux binary policy not found"):
            self.namespace["set_password"](self.root)

        self.util.execWithRedirect.assert_not_called()
        self.util.startProgram.assert_not_called()

    def test_relabels_account_backups_before_password_replaces_them(self):
        expected = {}
        for name, selinux_type in (
            ("passwd", "passwd_file_t"), ("shadow", "shadow_t"),
            ("group", "passwd_file_t"), ("gshadow", "shadow_t"),
            ("passwd-", "passwd_file_t"), ("shadow-", "shadow_t"),
            ("group-", "passwd_file_t"), ("gshadow-", "shadow_t"),
            (".pwd.lock", "passwd_file_t"),
        ):
            path = str(Path(self.root) / "etc" / name)
            Path(path).write_text("fixture\n")
            expected[path] = f"system_u:object_r:{selinux_type}:s0\x00".encode("ascii")
        labels = {path: b"system_u:object_r:etc_t:s0\x00" for path in expected}

        def relabel(command, arguments):
            for argument in arguments:
                path = str(Path(argument))
                if path in expected:
                    labels[path] = expected[path]
            return 0

        def start_password(*args, **kwargs):
            self.assertEqual(labels, expected)
            return self.util.startProgram.return_value

        self.util.execWithRedirect.side_effect = relabel
        self.os.getxattr.side_effect = lambda path, _: labels[str(Path(path))]
        self.util.startProgram.side_effect = start_password

        self.namespace["set_password"](self.root)


if __name__ == "__main__":
    unittest.main()
