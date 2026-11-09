"""Testes do logo ForjaOS v1 (FR-053, ADR-027).

Rodar: python3 -m unittest discover -s brand/tests -p 'test_*.py'
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOGO = ROOT / "brand" / "logo"
PALETTE = json.loads((ROOT / "brand" / "palette.json").read_text(encoding="utf-8"))
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def theme_hexes(theme):
    colors = PALETTE["themes"][theme]["colors"]
    return {v.lower() for v in colors.values() if isinstance(v, str) and v.startswith("#")}


def read(name):
    return (LOGO / name).read_text(encoding="utf-8")


class SvgAssertions:
    def assert_clean_svg(self, svg):
        self.assertIn('viewBox="', svg)
        self.assertNotIn("<text", svg, "texto deve estar em contornos")
        self.assertNotIn("<image", svg)
        self.assertNotRegex(svg, r'href="(https?:)?//', "sem referência externa")
        for banned in ("DevOS", "DeveloperOS", "24.04"):
            self.assertNotIn(banned, svg)

    def assert_theme_colors(self, svg, theme):
        used = {h.lower() for h in HEX.findall(svg)}
        self.assertTrue(used, "versão em cor precisa ter cor")
        self.assertLessEqual(used, theme_hexes(theme), f"cor fora do tema {theme}")

    def assert_mono(self, svg):
        self.assertEqual(HEX.findall(svg), [], "mono não pode ter hex")
        self.assertIn("currentColor", svg)
        self.assertNotIn("<linearGradient", svg)
        self.assertNotIn("<filter", svg)


class MarkTests(unittest.TestCase, SvgAssertions):
    VARIANTS = {"forjaos-mark-on-dark.svg": "dark", "forjaos-mark-on-light.svg": "light"}

    def test_files_and_structure(self):
        for name in [*self.VARIANTS, "forjaos-mark-mono.svg"]:
            with self.subTest(name=name):
                svg = read(name)
                self.assertIn('viewBox="0 0 512 512"', svg)
                for part in ("anvil", "horn", "spark", "core"):
                    self.assertIn(f'id="{part}"', svg)
                self.assert_clean_svg(svg)

    def test_color_variants_use_only_their_theme(self):
        for name, theme in self.VARIANTS.items():
            with self.subTest(name=name):
                self.assert_theme_colors(read(name), theme)

    def test_spark_uses_brand_accents(self):
        dark = read("forjaos-mark-on-dark.svg").lower()
        colors = PALETTE["themes"]["dark"]["colors"]
        for token in ("accent-cyan", "accent-violet", "accent-orange"):
            self.assertIn(colors[token].lower(), dark, token)

    def test_lower_anvil_has_its_own_gradient(self):
        for name in self.VARIANTS:
            with self.subTest(name=name):
                self.assertIn('id="anvil-bottom-grad"', read(name))

    def test_glow_only_on_dark(self):
        self.assertIn("<filter", read("forjaos-mark-on-dark.svg"))
        self.assertNotIn("<filter", read("forjaos-mark-on-light.svg"))

    def test_mono(self):
        self.assert_mono(read("forjaos-mark-mono.svg"))


class LogoTests(unittest.TestCase, SvgAssertions):
    VARIANTS = {"forjaos-logo-on-dark.svg": "dark", "forjaos-logo-on-light.svg": "light"}

    def test_wordmark_source(self):
        data = json.loads(read("src/wordmark.json"))
        self.assertEqual(data["font"], "Plus Jakarta Sans 700")
        self.assertEqual(data["license"], "OFL-1.1")
        for key in ("forja", "os"):
            self.assertTrue(data[key]["d"].strip(), key)
            self.assertGreater(data[key]["advance"], 0)

    def test_files_and_structure(self):
        for name in [*self.VARIANTS, "forjaos-logo-mono.svg"]:
            with self.subTest(name=name):
                svg = read(name)
                for part in ('id="mark"', 'id="wordmark"', 'id="word-forja"', 'id="word-os"'):
                    self.assertIn(part, svg)
                self.assertIn('id="logo-tile"', svg)
                self.assertIn('id="logo-divider"', svg)
                self.assert_clean_svg(svg)

    def test_wordmark_colors(self):
        for name, theme in self.VARIANTS.items():
            with self.subTest(name=name):
                svg = read(name)
                self.assert_theme_colors(svg, theme)
                colors = PALETTE["themes"][theme]["colors"]
                forja = re.search(r'id="word-forja"[^>]*fill="([^"]+)"', svg).group(1)
                os_ = re.search(r'id="word-os"[^>]*fill="([^"]+)"', svg).group(1)
                self.assertEqual(forja.lower(), colors["text-strong"].lower())
                self.assertEqual(os_.lower(), colors["accent-cyan"].lower())

    def test_mono(self):
        self.assert_mono(read("forjaos-logo-mono.svg"))


class IconTests(unittest.TestCase, SvgAssertions):
    SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)

    def test_svgs(self):
        dark = PALETTE["themes"]["dark"]["colors"]
        for name in ("forjaos-icon.svg", "forjaos-icon-small.svg"):
            with self.subTest(name=name):
                svg = read(name)
                self.assertIn('viewBox="0 0 512 512"', svg)
                tile = re.search(r'<rect id="tile"[^>]*>', svg).group(0)
                self.assertIn(f'fill="{dark["void"]}"', tile)
                self.assertIn(f'stroke="{dark["layer-3"]}"', tile)
                self.assertIn('id="tile-inner"', svg)
                self.assertIn(f'stroke="{dark["accent-cyan-deep"]}"', svg)
                self.assert_clean_svg(svg)
                self.assert_theme_colors(svg, "dark")

    def test_small_variant_is_simplified(self):
        small = read("forjaos-icon-small.svg")
        self.assertNotIn('id="nodes"', small)
        self.assertNotIn("<filter", small)
        self.assertIn('id="nodes"', read("forjaos-icon.svg"))

    def test_png_sources(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_logo", LOGO / "build_logo.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(tuple(sorted(mod.PNG_SIZES)), self.SIZES)
        for size in self.SIZES:
            expected = "forjaos-icon-small.svg" if size <= 32 else "forjaos-icon.svg"
            self.assertEqual(mod.png_source(size), expected, size)

    def test_pngs(self):
        from PIL import Image
        for size in self.SIZES:
            with self.subTest(size=size):
                with Image.open(LOGO / "png" / f"forjaos-{size}.png") as img:
                    self.assertEqual(img.size, (size, size))
                    self.assertEqual(img.mode, "RGBA")
                    # cantos transparentes (placa arredondada)
                    self.assertEqual(img.getpixel((0, 0))[3], 0)


class FreshnessTests(unittest.TestCase):
    def run_check(self, directory):
        import subprocess
        import sys
        return subprocess.run(
            [sys.executable, str(LOGO / "build_logo.py"), "--check", "--dir", str(directory)],
            capture_output=True, text=True,
        )

    def test_committed_svgs_are_fresh(self):
        result = self.run_check(LOGO)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_detects_stale_svg(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "logo"
            shutil.copytree(LOGO, copy, ignore=shutil.ignore_patterns("__pycache__"))
            target = copy / "forjaos-mark-on-dark.svg"
            target.write_text(target.read_text(encoding="utf-8").replace("<title>", "<title>x"), encoding="utf-8")
            result = self.run_check(copy)
            self.assertEqual(result.returncode, 1)
            self.assertIn("forjaos-mark-on-dark.svg", result.stdout + result.stderr)

    def test_licenses_registered(self):
        text = (ROOT / "brand" / "LICENSES.md").read_text(encoding="utf-8")
        for needle in ("Plus Jakarta Sans", "OFL-1.1", "CC BY-SA 4.0", "brand/logo/"):
            self.assertIn(needle, text)

    def test_readme_lists_every_file(self):
        readme = read("README.md")
        for path in LOGO.glob("forjaos-*.svg"):
            self.assertIn(path.name, readme)


if __name__ == "__main__":
    unittest.main()
