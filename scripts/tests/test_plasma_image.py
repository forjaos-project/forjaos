"""F1-006: package the Plasma theme without breaking the Fedora KDE dependency graph."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "image/build_files/forjaos-plasma.spec"
BUILDER = ROOT / "image/build_files/build_plasma_rpm.sh"
CONTAINERFILE = ROOT / "image/Containerfile"
PROFILE = ROOT / "image/build_files/configure_plasma.py"
IDENTITY_SPEC = ROOT / "image/build_files/forjaos-branding.spec"


class PlasmaImageTests(unittest.TestCase):
    def test_rpm_provides_exact_visual_packages_and_requires_mono_font(self):
        spec = SPEC.read_text(encoding="utf-8")
        self.assertRegex(spec, r"(?m)^Name:\s+forjaos-plasma$")
        self.assertRegex(spec, r"(?m)^Provides:\s+plasma-lookandfeel-fedora\s*=\s*%\{base_look_evr\}$")
        self.assertRegex(spec, r"(?m)^Provides:\s+f45-backgrounds-kde\s*=\s*%\{base_wallpaper_evr\}$")
        self.assertNotIn("Obsoletes:", spec)
        self.assertIn("Requires:       jetbrains-mono-fonts", spec)
        for target in ("/usr/share/plasma/look-and-feel/org.forjaos.desktop",
                       "/usr/share/plasma/desktoptheme/forja-dark",
                       "/usr/share/plasma/desktoptheme/forja-light",
                       "/usr/share/color-schemes/ForjaDark.colors",
                       "/usr/share/color-schemes/ForjaLight.colors",
                       "/usr/share/wallpapers/ForjaOS/",
                       "/usr/share/fonts/plus-jakarta-sans/",
                       "/usr/share/kglobalaccel/org.forjaos.terminal.desktop"):
            self.assertIn(target, spec)

    def test_builder_uses_base_evr_and_image_installs_new_rpm(self):
        builder = BUILDER.read_text(encoding="utf-8")
        self.assertIn("rpm -q --qf", builder)
        self.assertIn("plasma-lookandfeel-fedora", builder)
        self.assertIn("f45-backgrounds-kde", builder)
        self.assertIn("base_look_evr", builder)
        self.assertIn("base_wallpaper_evr", builder)
        containerfile = CONTAINERFILE.read_text(encoding="utf-8")
        self.assertIn("build_plasma_rpm.sh", containerfile)
        self.assertIn("dnf install -y /tmp/forjaos-plasma.rpm", containerfile)
        self.assertIn("dnf remove -y --no-autoremove plasma-lookandfeel-fedora f45-backgrounds-kde", containerfile)
        self.assertIn("configure_plasma.py", containerfile)
        self.assertLess(containerfile.index("dnf install -y /tmp/forjaos-branding.rpm"),
                        containerfile.index("dnf install -y /tmp/forjaos-plasma.rpm"))
        self.assertLess(containerfile.index("dnf install -y /tmp/forjaos-plasma.rpm"),
                        containerfile.index("python3 /tmp/configure_plasma.py"))

    def test_profile_cleanup_is_scoped_to_usr_share(self):
        source = PROFILE.read_text(encoding="utf-8")
        self.assertIn('"usr/share/kde-settings/', source)
        self.assertIn('"usr/share/icons/hicolor"', source)
        self.assertIn('remove_directory(root, f"usr/share/plasma/look-and-feel/org.fedoraproject.{style}.desktop")', source)
        self.assertIn('default_wallpaper.symlink_to("ForjaOS")', source)
        self.assertNotIn('root / "etc', source)
        self.assertNotIn("shutil.rmtree(root", source)

    def test_identity_rpm_does_not_publish_inherited_icon_aliases(self):
        self.assertNotIn("fedora-logo-icon", IDENTITY_SPEC.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
