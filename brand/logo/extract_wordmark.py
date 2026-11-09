#!/usr/bin/env python3
"""Converte o wordmark "ForjaOS" em contornos (FR-053).

Roda uma vez, quando a fonte ou o espaçamento mudar; o resultado
(brand/logo/src/wordmark.json) é versionado e o gerador não precisa da fonte.

Dependências só deste script (não vão para a imagem nem para o CI):
  fontTools (MIT) e uharfbuzz (Apache-2.0).
Fonte: Plus Jakarta Sans 700 (OFL-1.1), pacote npm @fontsource/plus-jakarta-sans.

Uso:
  python3 brand/logo/extract_wordmark.py --font plus-jakarta-sans-latin-700-normal.woff
"""
import argparse
import io
import json
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
import uharfbuzz as hb

OUT = Path(__file__).resolve().parent / "src" / "wordmark.json"
TRACKING_EM = -0.02  # letter-spacing do display (palette: display-lg)


def shape(font_bytes, text):
    face = hb.Face(font_bytes)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": True})
    return buf.glyph_infos, buf.glyph_positions


def outline(ttfont, font_bytes, text, upem):
    """Path SVG do texto com baseline em y = 0 (y cresce para baixo) e o avanço total."""
    glyph_set = ttfont.getGlyphSet()
    order = ttfont.getGlyphOrder()
    infos, positions = shape(font_bytes, text)
    tracking = TRACKING_EM * upem
    pen = SVGPathPen(glyph_set)
    x = 0.0
    for i, (info, pos) in enumerate(zip(infos, positions)):
        name = order[info.codepoint]
        glyph_set[name].draw(TransformPen(pen, (1, 0, 0, -1, x + pos.x_offset, -pos.y_offset)))
        x += pos.x_advance + (tracking if i < len(infos) - 1 else 0)
    return pen.getCommands(), round(x, 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--font", required=True, help="arquivo .woff/.ttf da Plus Jakarta Sans 700")
    args = ap.parse_args(argv)
    ttfont = TTFont(args.font)
    # O HarfBuzz não lê WOFF compactado: reserializa como TTF em memória.
    ttfont.flavor = None
    raw = io.BytesIO()
    ttfont.save(raw)
    font_bytes = raw.getvalue()
    upem = ttfont["head"].unitsPerEm
    os2 = ttfont["OS/2"]
    forja_d, forja_adv = outline(ttfont, font_bytes, "Forja", upem)
    os_d, os_adv = outline(ttfont, font_bytes, "OS", upem)
    # Espaço entre "Forja" e "OS" = kerning do par "aO" + tracking.
    _, pos = shape(font_bytes, "aO")
    join = pos[0].x_advance - shape(font_bytes, "a")[1][0].x_advance + TRACKING_EM * upem
    data = {
        "font": "Plus Jakarta Sans 700",
        "license": "OFL-1.1",
        "source": "npm @fontsource/plus-jakarta-sans",
        "units_per_em": upem,
        "cap_height": os2.sCapHeight,
        "descender": -abs(os2.sTypoDescender),
        "tracking_em": TRACKING_EM,
        "forja": {"d": forja_d, "advance": forja_adv},
        "os": {"d": os_d, "advance": os_adv, "offset": round(forja_adv + join, 1)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"escrito {OUT.relative_to(Path.cwd()) if OUT.is_relative_to(Path.cwd()) else OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
