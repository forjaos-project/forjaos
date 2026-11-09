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

    def test_glow_only_on_dark(self):
        self.assertIn("<filter", read("forjaos-mark-on-dark.svg"))
        self.assertNotIn("<filter", read("forjaos-mark-on-light.svg"))

    def test_mono(self):
        self.assert_mono(read("forjaos-mark-mono.svg"))


if __name__ == "__main__":
    unittest.main()
