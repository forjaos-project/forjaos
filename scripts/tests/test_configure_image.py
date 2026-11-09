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
ICON_SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)


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
        info = self.root / "usr/share/ublue-os/image-info.json"
        info.parent.mkdir(parents=True)
        info.write_text(
            json.dumps(
                {
                    "image-name": "bazzite",
                    "image-vendor": "ublue-os",
                    "image-ref": "ostree-image-signed:docker://ghcr.io/ublue-os/bazzite",
                    "image-tag": "stable",
                    "image-branch": "stable",
                    "base-image-name": "kinoite",
                    "fedora-version": "45",
                }
            ),
            encoding="utf-8",
        )
        self.key = self.root / "source.pub"
        self.key.write_bytes(PUBLIC_KEY)
        self.icons = self.root / "source-icons"
        self.icons.mkdir()
        for size in ICON_SIZES:
            (self.icons / f"forjaos-{size}.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([size % 256]))

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
                "--icons-dir",
                str(self.icons),
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
            'LOGO=forjaos-icon',
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
            policy["transports"]["docker"]["ghcr.io/forjaos-project"],
            [
                {
                    "type": "sigstoreSigned",
                    "keyPath": "/etc/pki/containers/forjaos.pub",
                    "signedIdentity": {"type": "matchRepository"},
                }
            ],
        )

    def test_sigstore_attachments_enabled_for_project_namespace(self):
        # Sem use-sigstore-attachments o containers/image não lê a assinatura cosign
        # (containers-registries.d(5)), e a regra sigstoreSigned nunca é satisfeita.
        for _ in range(2):
            result = self.run_helper()
            self.assertEqual(result.returncode, 0, result.stderr)
        config = self.root / "etc/containers/registries.d/forjaos-project.yaml"
        self.assertEqual(
            config.read_text(encoding="utf-8"),
            "docker:\n  ghcr.io/forjaos-project:\n    use-sigstore-attachments: true\n",
        )

    def test_trust_covers_every_variant_of_the_project(self):
        # A regra fica no namespace: trocar de variante (bootc switch para a outra imagem
        # ForjaOS) também exige assinatura, em vez de cair no "" insecureAcceptAnything.
        for image_name in ("forjaos", "forjaos-nvidia-open"):
            with self.subTest(image_name=image_name):
                result = self.run_helper(image_name)
                self.assertEqual(result.returncode, 0, result.stderr)
                release = (self.root / "usr/lib/os-release").read_text(encoding="utf-8")
                self.assertIn(f"VARIANT_ID={image_name}\n", release)
                docker = json.loads(
                    (self.root / "etc/containers/policy.json").read_text(encoding="utf-8")
                )["transports"]["docker"]
                self.assertEqual(docker["ghcr.io/forjaos-project"][0]["type"], "sigstoreSigned")
                self.assertEqual(
                    [k for k in docker if k.startswith("ghcr.io/forjaos-project/")], [],
                    "regra por imagem deixaria a outra variante sem verificação",
                )

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

    def test_image_info_points_to_each_forjaos_variant(self):
        for image_name in ("forjaos", "forjaos-nvidia-open"):
            with self.subTest(image_name=image_name):
                result = self.run_helper(image_name)
                self.assertEqual(result.returncode, 0, result.stderr)
                info = json.loads(
                    (self.root / "usr/share/ublue-os/image-info.json").read_text(encoding="utf-8")
                )
                self.assertEqual(info["image-name"], image_name)
                self.assertEqual(info["image-vendor"], "forjaos-project")
                self.assertEqual(
                    info["image-ref"],
                    f"ostree-image-signed:docker://ghcr.io/forjaos-project/{image_name}",
                )
                self.assertEqual(info["image-tag"], "testing")
                self.assertEqual(info["image-branch"], "testing")
                self.assertEqual(info["base-image-name"], "kinoite")
                self.assertEqual(info["fedora-version"], "45")

    def test_missing_or_malformed_image_info_leaves_identity_untouched(self):
        info = self.root / "usr/share/ublue-os/image-info.json"
        before = (self.root / "usr/lib/os-release").read_bytes()
        info.unlink()
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual((self.root / "usr/lib/os-release").read_bytes(), before)
        info.write_text("{invalid", encoding="utf-8")
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual((self.root / "usr/lib/os-release").read_bytes(), before)

    def test_installs_all_approved_logo_sizes_into_hicolor(self):
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        for size in ICON_SIZES:
            with self.subTest(size=size):
                source = self.icons / f"forjaos-{size}.png"
                destination = (
                    self.root / f"usr/share/icons/hicolor/{size}x{size}/apps/forjaos-icon.png"
                )
                self.assertEqual(destination.read_bytes(), source.read_bytes())

    def test_missing_logo_size_does_not_write_identity_or_image_info(self):
        release = self.root / "usr/lib/os-release"
        info = self.root / "usr/share/ublue-os/image-info.json"
        before_release = release.read_bytes()
        before_info = info.read_bytes()
        (self.icons / "forjaos-48.png").unlink()
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual(release.read_bytes(), before_release)
        self.assertEqual(info.read_bytes(), before_info)


if __name__ == "__main__":
    unittest.main()
