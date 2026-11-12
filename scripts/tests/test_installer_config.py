"""FR-010: the network installer must pin and verify its bootc payload."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "image/build_files/installer/configure_installer.py"
BRANDING_SCRIPT = ROOT / "image/build_files/installer/generate_branding.py"
SPEC = importlib.util.spec_from_file_location("configure_installer", SCRIPT)
if SPEC is not None and SPEC.loader is not None:
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
else:
    module = None
BRANDING_SPEC = importlib.util.spec_from_file_location("generate_branding", BRANDING_SCRIPT)
if BRANDING_SPEC is not None and BRANDING_SPEC.loader is not None:
    branding = importlib.util.module_from_spec(BRANDING_SPEC)
    BRANDING_SPEC.loader.exec_module(branding)
else:
    branding = None


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
        self.assertIn("root=live:CDLABEL=ForjaOS-Installer rd.live.image", iso_config)
        self.assertNotIn("${root}", iso_config)
        self.assertNotIn("selinux=0", iso_config)
        self.assertNotIn("enforcing=0", iso_config)

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

    def test_anaconda_tmux_starts_via_service_shell_with_selinux_enforcing(self):
        module.configure(self.root, self.source, self.target, self.key)
        drop_in = (self.root / "usr/lib/systemd/system/anaconda.service.d/10-forjaos-tmux.conf").read_text()
        self.assertIn("ExecStart=\n", drop_in)
        self.assertIn(
            "ExecStart=/usr/bin/sh -c '/usr/bin/tmux -u -f /usr/share/anaconda/tmux.conf start'",
            drop_in,
        )
        self.assertNotIn("setenforce", drop_in)
        self.assertNotIn("enforcing=0", drop_in)

    def test_installer_branding_uses_project_identity_and_tokens(self):
        branding.generate(self.root / "sources", ROOT / "brand")
        sources = self.root / "sources"
        identity = (sources / "os-release").read_text()
        self.assertIn('NAME="ForjaOS"', identity)
        self.assertIn("ID=forjaos", identity)
        self.assertNotIn("Fedora Linux", identity)
        profile = (sources / "forjaos.conf").read_text()
        self.assertIn("os_id = forjaos", profile)
        self.assertIn("custom_stylesheet = /usr/share/anaconda/pixmaps/forjaos.css", profile)
        stylesheet = (sources / "forjaos.css").read_text()
        palette = json.loads((ROOT / "brand/palette.json").read_text())["themes"]["dark"]["colors"]
        self.assertIn(palette["canvas"], stylesheet)
        self.assertIn(palette["accent-cyan"], stylesheet)
        self.assertIn("Plus Jakarta Sans", stylesheet)
        self.assertNotIn("fedora.css", stylesheet)
        web_style = (sources / "branding.css").read_text()
        self.assertIn(palette["accent-cyan"], web_style)
        self.assertIn("ForjaOS", web_style)
        self.assertIn("Plus Jakarta Sans", web_style)
        self.assertEqual((sources / "forjaos-logo.png").read_bytes(),
                         (ROOT / "brand/logo/png/forjaos-256.png").read_bytes())

    def test_branding_rpm_does_not_pull_optional_browser_stack(self):
        containerfile = (ROOT / "image/build_files/installer/Containerfile").read_text()
        self.assertIn("dnf install -y --setopt=install_weak_deps=False /tmp/forjaos-branding.rpm", containerfile)
        spec = (ROOT / "image/build_files/installer/forjaos-branding.spec").read_text()
        self.assertIn("Provides:       fedora-release-identity-basic = %{base_identity_evr}", spec)


if __name__ == "__main__":
    unittest.main()
