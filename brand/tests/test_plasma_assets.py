"""ForjaOS wallpaper contracts (FR-055, ADR-027)."""

import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
WALLPAPERS = ROOT / "brand" / "wallpapers" / "ForjaOS"
PLASMA = ROOT / "brand" / "plasma"
STEMS = ("dark-abstract", "dark-guara", "light-abstract", "light-guara")
PALETTE = json.loads((ROOT / "brand" / "palette.json").read_text(encoding="utf-8"))
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


class WallpaperTests(unittest.TestCase):
    def test_four_4k_wallpapers_and_vector_sources_exist(self):
        for stem in STEMS:
            with self.subTest(stem=stem):
                svg = WALLPAPERS / f"{stem}.svg"
                png = WALLPAPERS / f"{stem}.png"
                self.assertTrue(svg.is_file())
                data = png.read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">II", data[16:24]), (3840, 2160))

    def test_sources_use_only_palette_colors_and_no_external_assets(self):
        permitted = {
            value.lower()
            for theme in PALETTE["themes"].values()
            for value in theme["colors"].values()
            if isinstance(value, str) and value.startswith("#")
        }
        for stem in STEMS:
            with self.subTest(stem=stem):
                svg = (WALLPAPERS / f"{stem}.svg").read_text(encoding="utf-8")
                self.assertIn('viewBox="0 0 3840 2160"', svg)
                self.assertLessEqual({color.lower() for color in HEX.findall(svg)}, permitted)
                self.assertNotRegex(svg.lower(), r'fedora|bazzite|bluefin|<image|(?:href|xlink:href)="https?://')
                self.assertEqual('id="mascot"' in svg, stem.endswith("guara"))

    def test_generated_sources_are_current_and_license_recorded(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "brand/wallpapers/build_wallpapers.py"), "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        licenses = (ROOT / "brand/LICENSES.md").read_text(encoding="utf-8")
        self.assertIn("brand/wallpapers/ForjaOS/", licenses)
        self.assertIn("CC BY-SA 4.0", licenses)


class PlasmaThemeTests(unittest.TestCase):
    def test_theme_assets_match_palette(self):
        for theme in ("dark", "light"):
            with self.subTest(theme=theme):
                scheme = (PLASMA / "color-schemes" / f"Forja{theme.title()}.colors").read_text(encoding="utf-8")
                colors = PALETTE["themes"][theme]["colors"]
                self.assertIn("[Colors:Window]", scheme)
                self.assertIn("BackgroundNormal=" + ",".join(str(int(colors["canvas"][i:i+2], 16)) for i in (1, 3, 5)), scheme)
                self.assertIn("[Colors:Selection]", scheme)
                self.assertNotRegex(scheme.lower(), r"fedora|bazzite|bluefin|breeze")
                theme_dir = PLASMA / "desktoptheme" / f"forja-{theme}"
                metadata = json.loads((theme_dir / "metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(metadata["KPlugin"]["Id"], f"forja-{theme}")
                panel_svg = (theme_dir / "widgets" / "panel-background.svg").read_text(encoding="utf-8")
                self.assertIn('id="center"', panel_svg)
                self.assertIn('id="hint-bottom-margin"', panel_svg)
                self.assertIn('id="floating-center"', panel_svg)
                self.assertIn(f'id="floating-hint-bottom-margin" width="1" height="{PALETTE["dimensions"]["dock_bottom_offset"]}"', panel_svg)
                self.assertLessEqual({color.lower() for color in HEX.findall(panel_svg)},
                                     {value.lower() for value in colors.values() if isinstance(value, str) and value.startswith("#")})

    def test_look_and_feel_defaults_and_layout(self):
        look = PLASMA / "look-and-feel" / "org.forjaos.desktop"
        metadata = json.loads((look / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["KPackageStructure"], "Plasma/LookAndFeel")
        self.assertEqual(metadata["KPlugin"]["Id"], "org.forjaos.desktop")
        defaults = (look / "contents" / "defaults").read_text(encoding="utf-8")
        self.assertIn("ColorScheme=ForjaDark", defaults)
        self.assertIn("name=forja-dark", defaults)
        self.assertIn("Image=/usr/share/wallpapers/ForjaOS/dark-abstract.png", defaults)
        layout = (look / "contents" / "layouts" / "org.kde.plasma.desktop-layout.js").read_text(encoding="utf-8")
        self.assertIn('top.height = 40', layout)
        self.assertIn('dock.height = 64', layout)
        self.assertIn('dock.location = "bottom"', layout)
        self.assertIn('dock.floating = true', layout)
        self.assertIn('dock.lengthMode = "fit"', layout)
        self.assertNotIn('org.kde.plasma.desktop.defaultPanel', layout)
        self.assertNotRegex(layout.lower(), r"fedora|bazzite|bluefin|bazaar|yafti")
        splash = (look / "contents" / "splash" / "Splash.qml").read_text(encoding="utf-8")
        self.assertIn(PALETTE["themes"]["dark"]["colors"]["canvas"], splash)
        self.assertIn("system-logo-white.png", splash)
        self.assertNotRegex(splash.lower(), r"fedora|bazzite|bluefin|breeze")

    def test_generated_theme_assets_are_current(self):
        result = subprocess.run([sys.executable, str(PLASMA / "build_plasma.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
