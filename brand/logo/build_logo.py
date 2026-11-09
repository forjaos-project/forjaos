#!/usr/bin/env python3
"""Gerador do logo ForjaOS v1 (FR-053).

Toda cor vem de brand/palette.json (ADR-027): este arquivo não contém hex.

Uso:
  python3 brand/logo/build_logo.py           # (re)gera os SVGs em brand/logo/
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PALETTE_PATH = HERE.parent / "palette.json"

# Geometria da marca no espaço 512x512. Corpo simétrico em x = 256.
ANVIL = (
    "M150 150H362C392 150 400 176 384 196L332 256V300L400 372H112L180 300V256"
    "L128 196C112 176 120 150 150 150Z"
)
HORN = "M160 150L92 178C68 188 76 206 100 210L144 218"
SPARK_LEFT = "M238 240L210 278L238 316"
SPARK_RIGHT = "M274 240L302 278L274 316"
CORE = (256, 278, 11)
NODES = ((172, 150), (344, 150), (392, 372))
ANVIL_STROKE = 22
SPARK_STROKE = 18
NODE_R = 7

# Tokens por variante: (gradiente da bigorna, gradiente do spark, núcleo, fundo dos nós)
VARIANTS = {
    "on-dark": {
        "theme": "dark",
        "anvil": ("accent-cyan", "accent-violet"),
        "spark": ("accent-orange", "danger"),
        "core": "accent-cyan",
        "node_fill": "void",
        "glow": True,
    },
    "on-light": {
        "theme": "light",
        "anvil": ("accent-cyan", "accent-indigo"),
        "spark": ("accent-orange", "danger"),
        "core": "accent-cyan",
        "node_fill": "layer-1",
        "glow": False,
    },
    "mono": {"theme": None, "glow": False},
}


def load_palette(path=PALETTE_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def color(palette, theme, token):
    return palette["themes"][theme]["colors"][token]


def mark_defs(palette, variant, prefix):
    """Gradientes e filtro da marca; ids prefixados para reuso no mesmo SVG."""
    spec = VARIANTS[variant]
    if spec["theme"] is None:
        return ""
    theme = spec["theme"]
    a0, a1 = (color(palette, theme, t) for t in spec["anvil"])
    s0, s1 = (color(palette, theme, t) for t in spec["spark"])
    out = [
        f'<linearGradient id="{prefix}anvil-grad" gradientUnits="userSpaceOnUse" '
        f'x1="200" y1="140" x2="290" y2="360">'
        f'<stop offset="0" stop-color="{a0}"/><stop offset="1" stop-color="{a1}"/></linearGradient>',
        f'<linearGradient id="{prefix}spark-grad" gradientUnits="userSpaceOnUse" '
        f'x1="256" y1="240" x2="256" y2="316">'
        f'<stop offset="0" stop-color="{s0}"/><stop offset="1" stop-color="{s1}"/></linearGradient>',
    ]
    if spec["glow"]:
        out.append(
            f'<filter id="{prefix}glow" x="-20%" y="-20%" width="140%" height="140%">'
            '<feGaussianBlur in="SourceGraphic" stdDeviation="8" result="blur"/>'
            '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
            "</filter>"
        )
    return "".join(out)


def mark_body(palette, variant, prefix=""):
    """Elementos da marca (sem <svg>), no espaço 512x512."""
    spec = VARIANTS[variant]
    mono = spec["theme"] is None
    anvil_paint = "currentColor" if mono else f"url(#{prefix}anvil-grad)"
    spark_paint = "currentColor" if mono else f"url(#{prefix}spark-grad)"
    core_paint = "currentColor" if mono else color(palette, spec["theme"], spec["core"])
    glow = f' filter="url(#{prefix}glow)"' if spec["glow"] else ""
    line = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    cx, cy, r = CORE
    parts = [
        f'<g id="{prefix}mark"{glow}>',
        f'<path id="{prefix}anvil" d="{ANVIL}" {line} stroke="{anvil_paint}" stroke-width="{ANVIL_STROKE}"/>',
        f'<path id="{prefix}horn" d="{HORN}" {line} stroke="{anvil_paint}" stroke-width="{ANVIL_STROKE}"/>',
        f'<g id="{prefix}spark" {line} stroke="{spark_paint}" stroke-width="{SPARK_STROKE}">'
        f'<path d="{SPARK_LEFT}"/><path d="{SPARK_RIGHT}"/></g>',
        f'<circle id="{prefix}core" cx="{cx}" cy="{cy}" r="{r}" fill="{core_paint}"/>',
    ]
    if not mono:
        fill = color(palette, spec["theme"], spec["node_fill"])
        nodes = "".join(
            f'<circle cx="{x}" cy="{y}" r="{NODE_R}" fill="{fill}" stroke="{anvil_paint}" stroke-width="4"/>'
            for x, y in NODES
        )
        parts.append(f'<g id="{prefix}nodes">{nodes}</g>')
    parts.append("</g>")
    return "".join(parts)


def svg_doc(view_box, width, height, defs, body, title="ForjaOS"):
    defs_block = f"<defs>{defs}</defs>" if defs else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" '
        f'width="{width}" height="{height}" role="img" aria-label="{title}">'
        f"<title>{title}</title>{defs_block}{body}</svg>\n"
    )


def mark_svg(palette, variant):
    return svg_doc("0 0 512 512", 512, 512, mark_defs(palette, variant, ""), mark_body(palette, variant, ""))


def build(palette=None):
    """Retorna {nome_do_arquivo: conteúdo} de cada SVG gerado."""
    palette = palette or load_palette()
    return {f"forjaos-mark-{v}.svg": mark_svg(palette, v) for v in VARIANTS}


def main(argv=None):
    for name, content in build().items():
        (HERE / name).write_text(content, encoding="utf-8")
        print(f"escrito brand/logo/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
