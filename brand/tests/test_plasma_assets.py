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


if __name__ == "__main__":
    unittest.main()
