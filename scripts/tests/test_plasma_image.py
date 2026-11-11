"""F1-006: package the Plasma theme without breaking the Fedora KDE dependency graph."""

from pathlib import Path
import importlib.util
import re
import tempfile
import unittest
from unittest import mock


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

    def test_cleanup_removes_only_visible_inherited_apps(self):
        spec = importlib.util.spec_from_file_location("configure_plasma", PROFILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = {
                "usr/share/applications/bazzite-documentation.desktop": "Name=Documentation\nComment=Bazzite docs\n",
                "usr/share/applications/discourse.desktop": "Name=Discourse\nComment=Universal Blue\n",
                "usr/share/metainfo/io.github.rfrench3.bazzite-updater.metainfo.xml": "<name>Bazzite Updater</name>",
                "usr/share/applications/steam.desktop": "Name=Steam\nExec=bazzite-steam\n",
                "etc/safe": "keep",
            }
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            module.remove_inherited_apps(root)
            for relative in list(files)[:3]:
                self.assertFalse((root / relative).exists(), relative)
            self.assertEqual((root / "usr/share/applications/steam.desktop").read_text(), files["usr/share/applications/steam.desktop"])
            self.assertEqual((root / "etc/safe").read_text(), "keep")
        self.assertIn("dnf remove -y --no-autoremove bazzite-portal", CONTAINERFILE.read_text())
        self.assertIn("dnf remove -y --no-autoremove krunner-yafti", CONTAINERFILE.read_text())
        self.assertIn("dnf remove -y --no-autoremove fedora-appstream-metadata fira-code-fonts", CONTAINERFILE.read_text())

    def test_login_art_replaces_legacy_image_without_editing_etc(self):
        spec = importlib.util.spec_from_file_location("configure_plasma", PROFILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "usr/share/wallpapers/ForjaOS/dark-abstract.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"ForjaOS PNG")
            legacy = root / "usr/share/wallpapers/convergence.jxl"
            legacy.write_bytes(b"inherited login art")
            (legacy.parent / "convergence.png").write_bytes(b"inherited wallpaper picker art")
            backgrounds = root / "usr/share/backgrounds"
            backgrounds.mkdir(parents=True)
            for name in ("default.jxl", "default-dark.jxl"):
                (backgrounds / name).symlink_to("/usr/share/wallpapers/convergence.jxl")
            etc = root / "etc/xdg/kscreenlockerrc"
            etc.parent.mkdir(parents=True)
            etc.write_text("Image=/usr/share/wallpapers/convergence.jxl\n", encoding="utf-8")

            def convert(command, **kwargs):
                self.assertEqual(command[0], "magick")
                self.assertEqual(Path(command[1]), source)
                Path(command[-1]).write_bytes(b"ForjaOS JXL")

            with mock.patch("subprocess.run", side_effect=convert) as run:
                module.rebrand_login_art(root)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(legacy.readlink(), Path("ForjaOS/dark-abstract.jxl"))
            self.assertEqual((source.parent / "dark-abstract.jxl").read_bytes(), b"ForjaOS JXL")
            self.assertFalse((legacy.parent / "convergence.png").exists())
            self.assertEqual(etc.read_text(encoding="utf-8"), "Image=/usr/share/wallpapers/convergence.jxl\n")
            for name in ("default.jxl", "default-dark.jxl"):
                self.assertEqual((backgrounds / name).readlink(), Path("/usr/share/wallpapers/convergence.jxl"))

    def test_rebrands_active_vapor_first_login_launcher_without_editing_etc(self):
        spec = importlib.util.spec_from_file_location("configure_plasma", PROFILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            setup = root / "usr/share/plasma/look-and-feel/com.valve.vapor.desktop/contents/plasmoidsetupscripts/org.kde.plasma.kickoff.js"
            setup.parent.mkdir(parents=True)
            setup.write_text('applet.writeConfig("icon", "distributor-logo-steamdeck")\n', encoding="utf-8")
            config = root / "etc/xdg/kdeglobals"
            config.parent.mkdir(parents=True)
            config.write_text("[KDE]\nLookAndFeelPackage=com.valve.vapor.desktop\n", encoding="utf-8")
            icons = root / "usr/share/icons/hicolor/scalable/places"
            icons.mkdir(parents=True)
            (icons / "start-here.svg").write_text("ForjaOS icon", encoding="utf-8")
            (icons / "distributor-logo.svg").write_text("inherited violet icon", encoding="utf-8")
            (icons / "distributor-logo-steamdeck.svg").symlink_to("distributor-logo.svg")
            module.rebrand_first_login_launcher(root)
            self.assertIn('applet.writeConfig("icon", "start-here")', setup.read_text(encoding="utf-8"))
            self.assertEqual((icons / "distributor-logo.svg").readlink(), Path("start-here.svg"))
            self.assertEqual((icons / "distributor-logo-steamdeck.svg").readlink(), Path("distributor-logo.svg"))
            self.assertEqual(config.read_text(encoding="utf-8"),
                             "[KDE]\nLookAndFeelPackage=com.valve.vapor.desktop\n")


if __name__ == "__main__":
    unittest.main()
