"""F0-009: the image must install a real identity RPM with base-compatible Provides."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "image/build_files/forjaos-branding.spec"
BUILDER = ROOT / "image/build_files/build_branding_rpm.sh"
CONTAINERFILE = ROOT / "image/Containerfile"


class BrandingRpmTests(unittest.TestCase):
    def test_spec_replaces_only_inherited_identity_packages(self):
        spec = SPEC.read_text(encoding="utf-8")
        self.assertRegex(spec, r"(?m)^Name:\s+forjaos-branding$")
        self.assertRegex(spec, r"(?m)^Provides:\s+system-logos(?:\s|$)")
        self.assertRegex(spec, r"(?m)^Provides:\s+system-release(?:\s|$)")
        self.assertRegex(
            spec,
            r"(?m)^Provides:\s+fedora-release-identity\s*=\s*%\{base_identity_evr\}$",
        )
        self.assertEqual(
            set(re.findall(r"(?m)^Obsoletes:\s+([^\s]+)", spec)),
            {"fedora-logos", "fedora-release-identity-kinoite"},
        )
        self.assertIn("/usr/lib/os-release", spec)
        self.assertIn("/usr/lib/systemd/system-preset/80-kde-desktop.preset", spec)
        self.assertIn("/usr/share/pixmaps/system-logo-white.png", spec)

    def test_image_installs_rpm_before_variant_configuration(self):
        source = CONTAINERFILE.read_text(encoding="utf-8")
        self.assertIn("AS branding-builder", source)
        self.assertIn("build_branding_rpm.sh", source)
        self.assertIn("COPY --from=branding-builder", source)
        install = "dnf install -y /tmp/forjaos-branding.rpm"
        self.assertIn(install, source)
        self.assertLess(source.index(install), source.index("configure_image.py \\"))

    @unittest.skipIf(os.name == "nt", "Bash fixture runs in CI/WSL")
    def test_builder_uses_identity_version_from_base_rpm(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            fake_bin = directory / "bin"
            fake_bin.mkdir()
            log = directory / "build.log"
            output = directory / "forjaos-branding.rpm"
            rpm = fake_bin / "rpm"
            rpm.write_text(
                '#!/usr/bin/env bash\n'
                '[[ "$*" == *"fedora-release-identity-kinoite"* || "$*" == *"fedora-logos"* ]] || exit 3\n'
                'printf "45-14"\n',
                encoding="utf-8",
            )
            rpmbuild = fake_bin / "rpmbuild"
            rpmbuild.write_text(
                '#!/usr/bin/env bash\n'
                'printf "%s\\n" "$*" > "$TEST_BUILD_LOG"\n'
                'for arg in "$@"; do\n'
                '  if [[ "$arg" == _topdir\\ * ]]; then topdir="${arg#_topdir }"; fi\n'
                'done\n'
                'mkdir -p "$topdir/RPMS/noarch"\n'
                'printf "synthetic rpm" > "$topdir/RPMS/noarch/forjaos-branding-0.1-1.noarch.rpm"\n',
                encoding="utf-8",
            )
            rpm.chmod(0o755)
            rpmbuild.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
            env["TEST_BUILD_LOG"] = str(log)
            result = subprocess.run(
                [
                    "bash",
                    str(BUILDER),
                    str(ROOT / "image/build_files"),
                    str(ROOT / "brand/logo/png"),
                    str(output),
                    "forjaos",
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), b"synthetic rpm")
            self.assertIn("base_identity_evr 45-14", log.read_text(encoding="utf-8"))
            self.assertIn("base_logos_evr 45-14", log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
