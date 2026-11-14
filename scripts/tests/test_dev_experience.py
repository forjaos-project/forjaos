"""First-boot development setup keeps credentials private and edits idempotently."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "image/firstboot"))
import install_homebrew  # noqa: E402
import setup_profile  # noqa: E402


class DevelopmentSetupTests(unittest.TestCase):
    def test_git_and_ssh_configuration_is_idempotent_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config/forjaos"
            success = SimpleNamespace(returncode=0)
            with patch.object(Path, "home", return_value=home), \
                    patch.object(setup_profile, "CONFIG", config), \
                    patch.object(setup_profile.os, "getuid", return_value=1000, create=True), \
                    patch.object(setup_profile, "run", return_value=success) as run:
                self.assertTrue(setup_profile.configure_git_credentials())
                self.assertTrue(setup_profile.configure_git_credentials())
            ssh_config = home / ".ssh/config"
            self.assertEqual(ssh_config.read_text().count("Include ~/.config/forjaos/ssh.conf"), 1)
            self.assertIn("IdentityAgent /run/user/", (config / "ssh.conf").read_text())
            if os.name == "posix":
                self.assertEqual(os.stat(ssh_config).st_mode & 0o777, 0o600)
                self.assertEqual(os.stat(config / "ssh.conf").st_mode & 0o777, 0o600)
            self.assertIn("ExecStart=/usr/bin/ssh-agent", (
                home / ".config/systemd/user/forjaos-ssh-agent.service").read_text())
            self.assertEqual(run.call_count, 6)
            self.assertEqual(run.call_args_list[0].args[0], [
                "git", "config", "--global", "--replace-all", "credential.helper", "libsecret"
            ])

    def test_github_token_is_sent_to_libsecret_without_being_logged(self):
        outputs = [
            SimpleNamespace(returncode=0, stdout="dev-user\n"),
            SimpleNamespace(returncode=0, stdout="secret-token\n"),
            SimpleNamespace(returncode=0),
        ]
        with patch.object(setup_profile.subprocess, "run", side_effect=outputs) as run:
            self.assertTrue(setup_profile.configure_github_credential())
        stored = run.call_args_list[-1]
        self.assertEqual(stored.args[0], ["git", "credential", "approve"])
        self.assertIn("password=secret-token", stored.kwargs["input"])
        self.assertTrue(stored.kwargs["capture_output"])

    def test_shell_setup_preserves_existing_config_and_sets_forja_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config/forjaos"
            zshrc = home / ".zshrc"
            zshrc.write_text("# user setting\n", encoding="utf-8")
            with patch.object(Path, "home", return_value=home), \
                    patch.object(setup_profile, "CONFIG", config):
                setup_profile.configure_shell()
                setup_profile.configure_shell()
            contents = zshrc.read_text(encoding="utf-8")
            self.assertIn("# user setting", contents)
            self.assertIn("starship init zsh", contents)
            self.assertIn("atuin init zsh", contents)
            self.assertEqual(contents.count("# ForjaOS developer shell"), 1)
            self.assertIn("DefaultProfile=ForjaOS.profile", (home / ".config/konsolerc").read_text())

    def test_homebrew_shell_init_is_idempotent_and_preserves_user_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            zshrc = Path(directory) / ".zshrc"
            zshrc.write_text("# existing config\n", encoding="utf-8")
            install_homebrew.add_shell_init(zshrc)
            install_homebrew.add_shell_init(zshrc)
            contents = zshrc.read_text(encoding="utf-8")
            self.assertIn("# existing config", contents)
            self.assertEqual(contents.count(install_homebrew.INIT), 1)
            if os.name == "posix":
                self.assertEqual(os.stat(zshrc).st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
