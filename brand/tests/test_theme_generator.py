"""FR-051 contracts for deterministic theme assets from the canonical palette."""

import json
import configparser
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "brand/themes/build_themes.py"
PALETTE = json.loads((ROOT / "brand/palette.json").read_text(encoding="utf-8"))


class ThemeGeneratorTests(unittest.TestCase):
    def run_generator(self, output_dir, *args):
        return subprocess.run(
            [sys.executable, str(GENERATOR), "--output-dir", str(output_dir), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_all_standard_surfaces_have_generated_dark_and_light_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = self.run_generator(output)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_generator(output, "--check")
            self.assertEqual(result.returncode, 0, result.stderr)

            expected = {
                "brand/sddm/ForjaTheme-dark.qml": PALETTE["themes"]["dark"]["colors"]["canvas"],
                "brand/sddm/ForjaTheme-light.qml": PALETTE["themes"]["light"]["colors"]["canvas"],
                "brand/qml/dark/ForjaTheme.qml": PALETTE["themes"]["dark"]["colors"]["canvas"],
                "brand/qml/light/ForjaTheme.qml": PALETTE["themes"]["light"]["colors"]["canvas"],
                "brand/grub/forja-dark/theme.txt": PALETTE["themes"]["dark"]["colors"]["void"],
                "brand/grub/forja-light/theme.txt": PALETTE["themes"]["light"]["colors"]["canvas"],
                "brand/plymouth/forjaos-dark/forjaos.script": PALETTE["themes"]["dark"]["colors"]["canvas"],
                "brand/plymouth/forjaos-light/forjaos.script": PALETTE["themes"]["light"]["colors"]["canvas"],
                "brand/konsole/Forja Dark.colorscheme": PALETTE["themes"]["dark"]["colors"]["canvas"],
                "brand/konsole/Forja Light.colorscheme": PALETTE["themes"]["light"]["colors"]["canvas"],
                "brand/vscode/forja-dark-color-theme.json": PALETTE["themes"]["dark"]["colors"]["canvas"],
                "brand/vscode/forja-light-color-theme.json": PALETTE["themes"]["light"]["colors"]["canvas"],
                "brand/gtk/forja-dark.css": PALETTE["themes"]["dark"]["colors"]["canvas"],
                "brand/gtk/forja-light.css": PALETTE["themes"]["light"]["colors"]["canvas"],
                "brand/tokens.css": PALETTE["themes"]["dark"]["colors"]["canvas"],
            }
            for relative_path, canvas in expected.items():
                with self.subTest(path=relative_path):
                    content = (output / relative_path).read_text(encoding="utf-8")
                    if relative_path.endswith(".colorscheme"):
                        rgb = ",".join(str(int(canvas[index:index + 2], 16)) for index in (1, 3, 5))
                        self.assertIn(f"Color={rgb}", content)
                        parser = configparser.ConfigParser()
                        parser.read_string(content)
                        self.assertIn("Background", parser)
                        self.assertIn("Foreground", parser)
                    else:
                        self.assertIn(canvas, content)
                    if relative_path.endswith(".json"):
                        data = json.loads(content)
                        self.assertEqual(data["colors"]["editor.background"], canvas)
                    else:
                        self.assertIn("Generated from brand/palette.json", content)

            for theme in ("dark", "light"):
                theme_dir = output / f"brand/plymouth/forjaos-{theme}"
                config = (theme_dir / "forjaos.plymouth").read_text(encoding="utf-8")
                script = (theme_dir / "forjaos.script").read_text(encoding="utf-8")
                self.assertIn("ModuleName=script", config)
                self.assertIn("special://logo", script)
                self.assertIn("SetBootProgressFunction", script)
                self.assertNotIn("Image.Text", script)
                for svg in theme_dir.glob("*.svg"):
                    ET.parse(svg)

    def test_repository_assets_are_current(self):
        result = self.run_generator(ROOT, "--check")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_grub_and_plymouth_layout_uses_palette_dimensions(self):
        dimensions = PALETTE["dimensions"]
        grub = (ROOT / "brand/grub/forja-dark/theme.txt").read_text(encoding="utf-8")
        self.assertIn(f"left = {dimensions['grub_menu_left_percent']}%", grub)
        self.assertIn(f"top = {dimensions['grub_menu_top_percent']}%", grub)
        self.assertIn(f"width = {dimensions['grub_menu_width_percent']}%", grub)
        self.assertIn(f"height = {dimensions['grub_menu_height_percent']}%", grub)
        self.assertIn(f"item_padding = {dimensions['grub_menu_item_padding']}", grub)
        self.assertIn(f"item_spacing = {dimensions['grub_menu_item_spacing']}", grub)
        self.assertIn('title-font: "Plus Jakarta Sans Regular 24"', grub)
        self.assertIn('item_font = "JetBrains Mono Regular 12"', grub)

        script = (ROOT / "brand/plymouth/forjaos-dark/forjaos.script").read_text(encoding="utf-8")
        self.assertIn(
            f"logo_sprite.SetY(Window.GetHeight() / 2 - logo_image.GetHeight() / 2 - "
            f"{dimensions['plymouth_logo_vertical_offset']});",
            script,
        )
        self.assertIn(
            f"bar_width = Math.Min({dimensions['plymouth_progress_max_width']}, "
            f"Window.GetWidth() - {2 * dimensions['plymouth_progress_side_margin']});",
            script,
        )
        self.assertIn(
            f"bar_y = Window.GetHeight() / 2 + logo_image.GetHeight() / 2 + "
            f"{dimensions['plymouth_progress_vertical_gap']};",
            script,
        )
        self.assertIn(
            f"bar_fill.SetImage(bar_fill_image.Scale({dimensions['plymouth_progress_min_width']}, "
            f"{dimensions['plymouth_progress_height']}));",
            script,
        )
        svg = (ROOT / "brand/plymouth/forjaos-dark/progress-fill.svg").read_text(encoding="utf-8")
        self.assertIn(f'width="{dimensions["plymouth_progress_max_width"]}"', svg)
        self.assertIn(f'height="{dimensions["plymouth_progress_height"]}"', svg)

    def test_firefox_userchrome_is_only_generated_when_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = self.run_generator(output)
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = (output / "brand/firefox/userChrome-dark.css", output / "brand/firefox/userChrome-light.css")
            self.assertTrue(all(not path.exists() for path in paths))
            result = self.run_generator(output, "--firefox")
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_generator(output, "--check", "--firefox")
            self.assertEqual(result.returncode, 0, result.stderr)
            for path, theme in zip(paths, ("dark", "light")):
                content = path.read_text(encoding="utf-8")
                self.assertIn(PALETTE["themes"][theme]["colors"]["canvas"], content)
                self.assertIn("Generated from brand/palette.json", content)

    def test_check_mode_detects_stale_generated_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = self.run_generator(output)
            self.assertEqual(result.returncode, 0, result.stderr)
            generated = output / "brand/gtk/forja-dark.css"
            generated.write_text("stale\n", encoding="utf-8")
            result = self.run_generator(output, "--check")
            self.assertNotEqual(result.returncode, 0)

    def test_generators_and_outputs_are_in_license_inventory(self):
        licenses = (ROOT / "brand/LICENSES.md").read_text(encoding="utf-8")
        self.assertIn("brand/themes/build_themes.py", licenses)
        self.assertIn("CC BY-SA 4.0", licenses)
        self.assertIn("Apache-2.0", licenses)


if __name__ == "__main__":
    unittest.main()
