"""FR-010: the network installer must pin and verify its bootc payload."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "image/build_files/installer/configure_installer.py"
SPEC = importlib.util.spec_from_file_location("configure_installer", SCRIPT)
if SPEC is not None and SPEC.loader is not None:
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
else:
    module = None


class InstallerConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key = self.root / "public.pem"
        self.key.write_text("-----BEGIN PUBLIC KEY-----\nfixture\n-----END PUBLIC KEY-----\n")
        self.digest = "sha256:" + "a" * 64
        self.source = "ghcr.io/forjaos-project/forjaos@" + self.digest
        self.target = "ghcr.io/forjaos-project/forjaos:stable"

    def test_signed_remote_source_and_interactive_storage(self):
        module.configure(self.root, self.source, self.target, self.key)
        kickstart = (self.root / "usr/share/anaconda/interactive-defaults.ks").read_text()
        self.assertIn(f"bootc --source-imgref registry:{self.source}", kickstart)
        self.assertIn(f"--target-imgref {self.target}", kickstart)
        self.assertNotIn("containers-storage:", kickstart)
        for forbidden in ("clearpart", "autopart", "ignoredisk", "zerombr"):
            self.assertNotIn(forbidden, kickstart)

        policy = json.loads((self.root / "etc/containers/policy.json").read_text())
        self.assertEqual(policy["default"], [{"type": "reject"}])
        rule = policy["transports"]["docker"]["ghcr.io/forjaos-project"]
        self.assertEqual(rule[0]["type"], "sigstoreSigned")
        self.assertEqual(rule[0]["signedIdentity"], {"type": "matchRepository"})
        self.assertEqual(rule[0]["keyPath"], "/etc/pki/containers/forjaos.pub")
        self.assertEqual((self.root / "etc/pki/containers/forjaos.pub").read_text(), self.key.read_text())
        self.assertIn("use-sigstore-attachments: true", (self.root / "etc/containers/registries.d/forjaos-project.yaml").read_text())
        self.assertIn("enforce-container-sigpolicy = true", (self.root / "usr/lib/bootc/install/90-forjaos-signature.toml").read_text())

        iso_config = (self.root / "usr/lib/image-builder/bootc/iso.yaml").read_text()
        self.assertIn('label: "ForjaOS-Installer"', iso_config)
        self.assertIn("inst.graphical", iso_config)
        self.assertNotIn("selinux=0", iso_config)

    def test_rejects_unpinned_or_foreign_payload(self):
        for source in (
            "ghcr.io/forjaos-project/forjaos:testing",
            "ghcr.io/other/forjaos@" + self.digest,
            "ghcr.io/forjaos-project/forjaos@sha256:invalid",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                module.configure(self.root, source, self.target, self.key)

    def test_rejects_invalid_target_or_key(self):
        with self.assertRaises(ValueError):
            module.configure(self.root, self.source, "ghcr.io/other/forjaos:stable", self.key)
        self.key.write_text("invalid")
        with self.assertRaises(ValueError):
            module.configure(self.root, self.source, self.target, self.key)


if __name__ == "__main__":
    unittest.main()
