"""FR-051 contracts for deterministic theme assets from the canonical palette."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


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
                    else:
                        self.assertIn(canvas, content)
                    if relative_path.endswith(".json"):
                        data = json.loads(content)
                        self.assertEqual(data["colors"]["editor.background"], canvas)
                    else:
                        self.assertIn("Generated from brand/palette.json", content)

    def test_repository_assets_are_current(self):
        result = self.run_generator(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_generator(ROOT, "--check")
        self.assertEqual(result.returncode, 0, result.stderr)

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


if __name__ == "__main__":
    unittest.main()
