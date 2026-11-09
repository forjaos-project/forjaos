"""Behavior tests for the minimal ForjaOS image build helper."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "image" / "build_files" / "configure_image.py"
PUBLIC_KEY = b"-----BEGIN PUBLIC KEY-----\nZmFrZQ==\n-----END PUBLIC KEY-----\n"


class ConfigureImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        lib = self.root / "usr" / "lib"
        lib.mkdir(parents=True)
        (lib / "os-release").write_text(
            'NAME="Bazzite"\n'
            'ID=bazzite\n'
            'ID_LIKE="fedora"\n'
            'VERSION_ID=45\n'
            'PRETTY_NAME="Bazzite"\n'
            'LOGO=bazzite-logo\n'
            'CPE_NAME="cpe:/o:universal-blue:bazzite:45"\n'
            'VARIANT_ID=bazzite-nvidia-open\n'
            'BUILD_ID="Stable (F45.20261105)"\n',
            encoding="utf-8",
        )
        etc = self.root / "etc"
        etc.mkdir()
        if os.name != "nt":
            (etc / "os-release").symlink_to("../usr/lib/os-release")
        policy = etc / "containers" / "policy.json"
        policy.parent.mkdir()
        policy.write_text(
            json.dumps(
                {
                    "default": [{"type": "reject"}],
                    "transports": {
                        "docker": {
                            "ghcr.io/ublue-os": [
                                {"type": "sigstoreSigned", "keyPath": "/etc/pki/containers/ublue-os.pub"}
                            ],
                            "": [{"type": "insecureAcceptAnything"}],
                        },
                        "oci": {"": [{"type": "insecureAcceptAnything"}]},
                    },
                }
            ),
            encoding="utf-8",
        )
        self.key = self.root / "source.pub"
        self.key.write_bytes(PUBLIC_KEY)

    def run_helper(self, image_name="forjaos-nvidia-open"):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(self.root),
                "--public-key",
                str(self.key),
                "--image-name",
                image_name,
            ],
            capture_output=True,
            text=True,
        )

    def test_nvidia_identity_and_scoped_policy_preserve_upstream_rules(self):
        for _ in range(2):
            result = self.run_helper()
            self.assertEqual(result.returncode, 0, result.stderr)
        release = (self.root / "usr/lib/os-release").read_text(encoding="utf-8")
        for field in (
            'NAME="ForjaOS"',
            'PRETTY_NAME="ForjaOS 0.1"',
            'VERSION_ID=0.1',
            'ID=forjaos',
            'ID_LIKE=fedora',
            'HOME_URL="https://github.com/forjaos-project/forjaos"',
            'BUG_REPORT_URL="https://github.com/forjaos-project/forjaos/issues"',
            'VARIANT_ID=forjaos-nvidia-open',
            'BUILD_ID="Stable (F45.20261105)"',
        ):
            self.assertIn(field + "\n", release)
        self.assertNotIn("Bazzite", release)
        self.assertNotIn("bazzite", release)
        self.assertEqual((self.root / "etc/pki/containers/forjaos.pub").read_bytes(), PUBLIC_KEY)
        policy = json.loads((self.root / "etc/containers/policy.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["default"], [{"type": "reject"}])
        self.assertEqual(policy["transports"]["docker"]["ghcr.io/ublue-os"][0]["type"], "sigstoreSigned")
        self.assertEqual(policy["transports"]["oci"][""], [{"type": "insecureAcceptAnything"}])
        self.assertEqual(
            policy["transports"]["docker"]["ghcr.io/forjaos-project/forjaos-nvidia-open"],
            [
                {
                    "type": "sigstoreSigned",
                    "keyPath": "/etc/pki/containers/forjaos.pub",
                    "signedIdentity": {"type": "matchRepository"},
                }
            ],
        )

    def test_generic_variant_has_its_own_trust_scope(self):
        result = self.run_helper("forjaos")
        self.assertEqual(result.returncode, 0, result.stderr)
        release = (self.root / "usr/lib/os-release").read_text(encoding="utf-8")
        self.assertIn("VARIANT_ID=forjaos\n", release)
        policy = json.loads((self.root / "etc/containers/policy.json").read_text(encoding="utf-8"))
        self.assertIn("ghcr.io/forjaos-project/forjaos", policy["transports"]["docker"])
        self.assertNotIn("ghcr.io/forjaos-project/forjaos-nvidia-open", policy["transports"]["docker"])

    def test_missing_policy_or_key_does_not_change_identity(self):
        before = (self.root / "usr/lib/os-release").read_bytes()
        (self.root / "etc/containers/policy.json").unlink()
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / "usr/lib/os-release").read_bytes(), before)
        (self.root / "etc/containers/policy.json").write_text('{"default": [], "transports": {"docker": {}}}')
        self.key.unlink()
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / "usr/lib/os-release").read_bytes(), before)

    def test_unknown_image_name_is_rejected(self):
        result = self.run_helper("unapproved-image")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
