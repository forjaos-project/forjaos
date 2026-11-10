"""Contract tests for the five static Guará mascot SVGs (FR-054)."""

import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from brand.mascot.build_guara import render


ROOT = Path(__file__).resolve().parents[2]
MASCOT = ROOT / "brand" / "mascot"
PALETTE = json.loads((ROOT / "brand" / "palette.json").read_text(encoding="utf-8"))
STATES = tuple(PALETTE["mascot"]["states"])
LAYERS = tuple(PALETTE["mascot"]["svg_layers"])
SVG_NS = "{http://www.w3.org/2000/svg}"
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


class GuaraStructureTests(unittest.TestCase):
    def svg(self, state):
        return (MASCOT / f"guara-{state}.svg").read_text(encoding="utf-8")

    def test_all_states_exist_with_stable_layers(self):
        self.assertEqual(STATES, ("idle", "listening", "thinking", "speaking", "error"))
        self.assertEqual(LAYERS, ("body", "ears", "eyes", "mouth", "glow", "badge"))
        for state in STATES:
            with self.subTest(state=state):
                root = ET.fromstring(self.svg(state))
                self.assertEqual(root.tag, f"{SVG_NS}svg")
                self.assertEqual(root.attrib["viewBox"], "0 0 512 512")
                self.assertEqual(root.attrib["data-state"], state)
                layers = [child.attrib.get("id") for child in root if child.tag == f"{SVG_NS}g"]
                self.assertEqual(layers, list(LAYERS))

    def test_common_silhouette_is_identical_across_states(self):
        reference = None
        for state in STATES:
            root = ET.fromstring(self.svg(state))
            common = [ET.tostring(root.find(f"{SVG_NS}g[@id='{layer}']")) for layer in ("body", "ears")]
            if reference is None:
                reference = common
            else:
                self.assertEqual(common, reference, state)

    def test_assets_are_self_contained_and_use_palette_colors(self):
        permitted = {
            value.lower()
            for theme in PALETTE["themes"].values()
            for value in theme["colors"].values()
            if isinstance(value, str) and value.startswith("#")
        }
        for state in STATES:
            with self.subTest(state=state):
                svg = self.svg(state)
                self.assertNotIn("<text", svg)
                self.assertNotIn("<image", svg)
                self.assertNotRegex(svg, r"(?:href|url)=[\"']https?://")
                self.assertLessEqual({color.lower() for color in HEX.findall(svg)}, permitted)
                self.assertNotIn("#000000", svg.lower())

    def test_state_expressions_are_distinct(self):
        for layer in ("eyes", "mouth", "glow", "badge"):
            variants = []
            for state in STATES:
                root = ET.fromstring(self.svg(state))
                variants.append(ET.tostring(root.find(f"{SVG_NS}g[@id='{layer}']")))
            self.assertEqual(len(set(variants)), len(STATES), layer)

    def test_state_ring_uses_declared_color(self):
        colors = PALETTE["themes"]["dark"]["colors"]
        for state, token in PALETTE["mascot"]["state_colors"].items():
            with self.subTest(state=state):
                root = ET.fromstring(self.svg(state))
                glow = root.find(f"{SVG_NS}g[@id='glow']")
                self.assertIn(colors[token], ET.tostring(glow, encoding="unicode"))

    def test_versioned_svgs_match_generator(self):
        for state in STATES:
            with self.subTest(state=state):
                self.assertEqual(self.svg(state), render(state, PALETTE))


if __name__ == "__main__":
    unittest.main()
