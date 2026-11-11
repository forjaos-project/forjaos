"""Behavioral fixtures for the F0-004 rootfs branding checker."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "check_branding.py"


class BrandingCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "rootfs"
        (self.root / "etc").mkdir(parents=True)
        (self.root / "etc/os-release").write_text(
            'NAME="ForjaOS"\nID=forjaos\nID_LIKE=fedora\nPRETTY_NAME="ForjaOS 0.1"\n'
            'HOME_URL="https://forjaos.org"\nBUG_REPORT_URL="https://forjaos.org/issues"\n',
            encoding="utf-8",
        )
        binary = self.base / "bin"
        binary.mkdir()
        rpm = binary / "rpm"
        rpm.write_text(
            "#!/usr/bin/env bash\n"
            "if [ \"${TEST_RPM_FAIL:-0}\" = 1 ]; then echo 'rpm failed' >&2; exit 7; fi\n"
            "printf '%s' \"${TEST_RPM_PACKAGES:-}\"\n",
            encoding="utf-8",
        )
        rpm.chmod(0o755)
        lsinitrd = binary / "lsinitrd"
        lsinitrd.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "sys.stdout.buffer.write(open(os.environ['TEST_INITRAMFS_LOGO'], 'rb').read())\n",
            encoding="utf-8",
        )
        lsinitrd.chmod(0o755)
        self.env = os.environ.copy()
        self.env["PATH"] = f"{binary}{os.pathsep}{self.env['PATH']}"

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def check(self, *, packages="", fail_rpm=False):
        env = self.env.copy()
        env["TEST_RPM_PACKAGES"] = packages
        env["TEST_RPM_FAIL"] = "1" if fail_rpm else "0"
        result = subprocess.run(
            [sys.executable, str(CHECKER), "--rootfs", str(self.root), "--json"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        return result, json.loads(result.stdout)

    def test_clean_rootfs_allows_fedora_id_like_and_legal_documents(self):
        self.write("usr/share/licenses/forjaos/Fedora-Legal.txt", "Fedora license")
        self.write("usr/share/doc/forjaos/README", "Bazzite source attribution")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report, {"status": "ok", "findings": []})

    def test_rejects_inherited_terminal_banner_and_rotating_tip(self):
        self.write("usr/share/ublue-os/motd/template.md", "# Welcome to Bazzite\n")
        self.write("usr/share/ublue-os/motd/tips/20-bazzite.md", "Bazzite help\n")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertTrue(any(item["path"].endswith("/template.md") for item in report["findings"]))
        self.assertTrue(any(item["path"].endswith("/20-bazzite.md") for item in report["findings"]))

    def test_rejects_stale_boot_splash_logo_in_initramfs(self):
        self.write("usr/share/pixmaps/system-logo-white.png", "ForjaOS logo")
        self.write("usr/lib/modules/test-kernel/initramfs.img", "initramfs fixture")
        stale_logo = self.base / "embedded-logo.png"
        stale_logo.write_text("Bazzite logo", encoding="utf-8")
        self.env["TEST_INITRAMFS_LOGO"] = str(stale_logo)
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertTrue(any(item["path"].endswith("/initramfs.img") and item["kind"] == "image"
                            for item in report["findings"]), report)

        stale_logo.write_text("ForjaOS logo", encoding="utf-8")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 0, report)

    def test_rejects_inherited_login_and_lock_wallpaper(self):
        self.write(
            "usr/lib/plasmalogin/defaults.conf",
            "[Greeter][Wallpaper][org.kde.image][General]\n"
            "Image=file:///usr/share/backgrounds/default.jxl\n"
            "PreviewImage=file:///usr/share/backgrounds/default.jxl\n",
        )
        self.write(
            "etc/xdg/kscreenlockerrc",
            "[Greeter][Wallpaper][org.kde.image][General]\n"
            "Image=/usr/share/wallpapers/convergence.jxl\n"
            "PreviewImage=/usr/share/wallpapers/convergence.jxl\n",
        )
        self.write("usr/share/wallpapers/convergence.jxl", "inherited login art")
        self.write("usr/share/wallpapers/ForjaOS/dark-abstract.jxl", "ForjaOS login art")
        default = self.root / "usr/share/backgrounds/default.jxl"
        default.parent.mkdir(parents=True)
        try:
            default.symlink_to("/usr/share/wallpapers/convergence.jxl")
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")

        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertEqual(
            {item["path"] for item in report["findings"] if item["kind"] == "image"},
            {"/usr/lib/plasmalogin/defaults.conf", "/etc/xdg/kscreenlockerrc"},
            report,
        )

        legacy = self.root / "usr/share/wallpapers/convergence.jxl"
        legacy.unlink()
        legacy.symlink_to("ForjaOS/dark-abstract.jxl")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 0, report)

    def test_rejects_active_first_login_launcher_icon(self):
        self.write("etc/xdg/kdeglobals", "[KDE]\nLookAndFeelPackage=com.valve.vapor.desktop\n")
        setup = "usr/share/plasma/look-and-feel/com.valve.vapor.desktop/contents/plasmoidsetupscripts/org.kde.plasma.kickoff.js"
        self.write(setup, 'applet.writeConfig("icon", "distributor-logo-steamdeck")\n')
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertTrue(any(f["kind"] == "image" and f["path"].endswith("org.kde.plasma.kickoff.js")
                            for f in report["findings"]), report)

        self.write(setup, 'applet.writeConfig("icon", "start-here")\n')
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 0, report)

    def test_rejects_inherited_icon_used_by_existing_launcher_profiles(self):
        self.write("usr/share/icons/hicolor/scalable/places/start-here.svg", "ForjaOS icon")
        alias = "usr/share/icons/hicolor/scalable/places/distributor-logo-steamdeck.svg"
        generic = "usr/share/icons/hicolor/scalable/places/distributor-logo.svg"
        self.write(generic, "inherited violet icon")
        (self.root / alias).symlink_to("distributor-logo.svg")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertTrue(any(f["kind"] == "image" and f["path"].endswith("distributor-logo-steamdeck.svg")
                            for f in report["findings"]), report)

        legacy = self.root / generic
        legacy.unlink()
        legacy.symlink_to("start-here.svg")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 0, report)

    def test_rejects_missing_or_wrong_identity(self):
        (self.root / "etc/os-release").write_text('NAME="Bazzite"\nID=bazzite\n', encoding="utf-8")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["status"], "fail")
        self.assertEqual({item["kind"] for item in report["findings"]}, {"identity", "text"})
        self.assertEqual(len([f for f in report["findings"] if f["kind"] == "identity"]), 6)

    def test_rejects_incomplete_fr003_identity(self):
        self.write("etc/os-release", 'NAME=ForjaOS\nID=forjaos\nPRETTY_NAME=ForjaOS\n')
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertEqual(len(report["findings"]), 4)

    def test_os_release_brand_exception_only_applies_to_id_like(self):
        path = self.root / "etc/os-release"
        with path.open("a") as stream:
            stream.write('LOGO=fedora-logo-icon\n')
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertTrue(any(f.get("line") == 7 for f in report["findings"]))

    def test_scans_discover_remote_descriptors(self):
        self.write("usr/share/flatpak/remotes.d/default.flatpakrepo", '[Flatpak Repo]\nTitle=Fedora Apps\n')
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertTrue(any(f.get("line") == 2 for f in report["findings"]))

    def test_scans_visible_application_labels_but_not_internal_commands(self):
        self.write("usr/share/applications/portal.desktop",
                   "[Desktop Entry]\nName=Bazzite Portal\nExec=/usr/bin/yafti\nIcon=/usr/share/ublue-os/bazzite/portal.svg\n")
        self.write("usr/share/applications/steam.desktop",
                   "[Desktop Entry]\nName=Steam\nExec=/usr/bin/bazzite-steam\nIcon=steam\n")
        self.write("usr/share/applications/hidden.desktop",
                   "[Desktop Entry]\nNoDisplay=true\nName=Bazzite Updater\n")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertEqual({f["path"] for f in report["findings"]},
                         {"/usr/share/applications/portal.desktop"})
        self.assertEqual({f["line"] for f in report["findings"]}, {2, 4})

    def test_scans_discover_desktop_application_metadata(self):
        self.write("usr/share/metainfo/portal.xml",
                   '<component type="desktop-application"><id>portal</id><name>Bazzite Portal</name></component>')
        self.write("usr/share/metainfo/font.xml",
                   '<component type="font"><id>font</id><name>Fedora Font</name></component>')
        self.write("usr/share/metainfo/os.xml",
                   '<component type="operating-system"><id>os</id><name>Fedora Linux</name></component>')
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertEqual({f["path"] for f in report["findings"]},
                         {"/usr/share/metainfo/portal.xml", "/usr/share/metainfo/os.xml"})

    def test_scans_yafti_actions_only_when_krunner_plugin_exposes_them(self):
        yaml = "usr/share/yafti/yafti.yml"
        self.write(yaml, "title: Bazzite Portal\n"
                         "description: Configure Bazzite\n"
                         "label: Enable Bazzite CLI\n"
                         "id: bazzite-internal\n"
                         "script: ujust bazzite-cli enable\n")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 0, report)
        self.write("usr/lib64/qt6/plugins/kf6/krunner/krunner-yafti.so", "plugin")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertEqual({f["path"] for f in report["findings"]}, {"/" + yaml})
        self.assertEqual({f["line"] for f in report["findings"]}, {1, 2, 3})

    def test_rejects_each_forbidden_package_family(self):
        result, report = self.check(
            packages="forjaos-branding\nfedora-logos\nfedora-release-identity-kinoite\nbazzite-branding\nbluefin-branding\n"
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            {item["value"] for item in report["findings"] if item["kind"] == "package"},
            {"fedora-logos", "fedora-release-identity-kinoite", "bazzite-branding", "bluefin-branding"},
        )

    def test_rejects_visible_text_and_branded_path(self):
        self.write("etc/issue", "ForjaOS\nWelcome to Universal Blue\n")
        self.write("usr/share/wallpapers/Bazzite/default.svg", "<svg></svg>")
        self.write("usr/share/plasma/look-and-feel/org.forjaos.desktop/colors.colors", "Title=Bluefin\n")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(f["path"] == "/etc/issue" and f["line"] == 2 for f in report["findings"]))
        self.assertTrue(any("Bazzite" in f["path"] and f["kind"] == "path" for f in report["findings"]))
        self.assertTrue(any(f["path"].endswith("colors.colors") and f["kind"] == "text" for f in report["findings"]))

    def test_rejects_branded_symlink_target(self):
        target = self.root / "usr/share/icons/hicolor/32x32/apps/start-here.png"
        target.parent.mkdir(parents=True)
        self.write("usr/share/icons/hicolor/32x32/apps/fedora-logo.png", "PNG")
        try:
            target.symlink_to("fedora-logo.png")
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(f["path"].endswith("start-here.png") and f["kind"] == "path" for f in report["findings"]))

    def test_rejects_missing_forjaos_branding_package(self):
        result, report = self.check(packages="some-other-package\n")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(f["kind"] == "package" and f["value"] == "forjaos-branding missing" for f in report["findings"]))

    def test_rpm_error_is_not_a_clean_pass(self):
        result, report = self.check(fail_rpm=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["status"], "error")
        self.assertTrue(any(f["kind"] == "inspection" for f in report["findings"]))

    def test_directory_symlink_is_not_read_as_a_file(self):
        linked = self.root / "etc/xdg/systemd/user"
        linked.parent.mkdir(parents=True)
        try:
            linked.symlink_to("/etc", target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symlinks unavailable: {error}")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 0, report)

    def test_scans_directory_links_inside_the_rootfs(self):
        self.write("opt/theme/banner.qml", 'text: "Bazzite"\n')
        linked = self.root / "usr/share/plasma/look-and-feel/default"
        linked.parent.mkdir(parents=True)
        linked.symlink_to("/opt/theme", target_is_directory=True)
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 1, report)
        self.assertTrue(any(f["kind"] == "text" and f.get("line") == 1 for f in report["findings"]))

    def test_resolves_intermediate_absolute_links_in_rootfs(self):
        self.write("usr/etc/os-release", (self.root / "etc/os-release").read_text())
        (self.root / "etc/os-release").unlink()
        (self.root / "etc").rmdir()
        (self.root / "etc").symlink_to("/usr/etc", target_is_directory=True)
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 0, report)

    def test_link_loop_is_an_inspection_error(self):
        linked = self.root / "etc/issue"
        linked.symlink_to("issue")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 2, report)
        self.assertEqual(report["status"], "error")

    def test_identity_link_loop_preserves_json_error_output(self):
        identity = self.root / "etc/os-release"
        identity.unlink()
        identity.symlink_to("os-release")
        self.write("etc/issue", "ForjaOS\n")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 2, report)
        self.assertEqual(report["status"], "error")

    def test_link_cannot_escape_selected_rootfs(self):
        linked = self.root / "etc/issue"
        linked.symlink_to("../../host-issue")
        (self.base / "host-issue").write_text("Bazzite")
        result, report = self.check(packages="forjaos-branding\n")
        self.assertEqual(result.returncode, 2, report)
        self.assertTrue(any("escapes rootfs" in f["value"] for f in report["findings"]))

    def test_json_is_deterministic(self):
        self.write("etc/motd", "Bluefin\n")
        first, report = self.check(packages="bazzite-branding\n")
        second, _ = self.check(packages="bazzite-branding\n")
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(report["status"], "fail")


if __name__ == "__main__":
    unittest.main()
