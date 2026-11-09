"""O nome do produto é só "ForjaOS", sem descritor (ADR-031).

Strings de protótipo como `DevOS` continuam permitidas nas tabelas de substituição
(ADR-028), mas nunca como descritor aceito do nome.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESCRIPTOR = re.compile(r"the\s+devos", re.IGNORECASE)


class ProductNameTests(unittest.TestCase):
    def test_tela_specs_and_generator_have_no_descriptor(self):
        files = [ROOT / "scripts" / "gen_tela_specs.py", *sorted((ROOT / "docs/design-system/telas").glob("*.md"))]
        offenders = [str(p.relative_to(ROOT)) for p in files if DESCRIPTOR.search(p.read_text(encoding="utf-8"))]
        self.assertEqual(offenders, [])

    def test_prd_has_no_descriptor(self):
        prd = (ROOT / "docs" / "PRD.md").read_text(encoding="utf-8")
        self.assertIsNone(DESCRIPTOR.search(prd))

    def test_devos_substitution_cites_adr_031(self):
        source = (ROOT / "scripts" / "gen_tela_specs.py").read_text(encoding="utf-8")
        self.assertIn('"DevOS": ("ForjaOS", "ADR-031")', source)


if __name__ == "__main__":
    unittest.main()
