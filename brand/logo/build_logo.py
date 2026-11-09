#!/usr/bin/env python3
"""Gerador do logo ForjaOS v1 (FR-053).

Toda cor vem de brand/palette.json (ADR-027): este arquivo não contém hex.

Uso:
  python3 brand/logo/build_logo.py           # (re)gera os SVGs em brand/logo/
  python3 brand/logo/build_logo.py --png     # e os PNGs 16–512 em brand/logo/png/
  python3 brand/logo/build_logo.py --check   # falha se algum SVG versionado estiver desatualizado
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PALETTE_PATH = HERE.parent / "palette.json"

# Geometria da marca no espaço 512x512. Corpo simétrico em x = 256.
ANVIL_TOP = "M150 150H362"
ANVIL_LEFT = "M150 150C120 150 112 176 128 196L180 256V300"
ANVIL_RIGHT = "M362 150C392 150 400 176 384 196L332 256V300"
ANVIL_BOTTOM = "M180 300L112 372H400L332 300"
HORN = "M160 150L92 178C68 188 76 206 100 210L144 218"
SPARK_LEFT = "M238 240L210 278L238 316"
SPARK_RIGHT = "M274 240L302 278L274 316"
CORE = (256, 278, 11)
NODES = ((172, 150), (344, 150), (392, 372))
ANVIL_STROKE = 22
SPARK_STROKE = 18
NODE_R = 6

# Tokens por variante: gradiente da bigorna, gradiente do spark, núcleo e nós (rebites claros sobre o traço)
VARIANTS = {
    "on-dark": {
        "theme": "dark",
        "anvil": ("accent-cyan", "accent-violet"),
        "anvil_bottom": ("accent-violet", "accent-sky"),
        "spark": ("accent-orange", "danger"),
        "core": "accent-cyan",
        "node_fill": "primary",
        "glow": True,
    },
    "on-light": {
        "theme": "light",
        "anvil": ("accent-cyan", "accent-indigo"),
        "anvil_bottom": ("accent-indigo", "text-strong"),
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


def mark_defs(palette, variant, prefix, small=False):
    """Gradientes e filtro da marca; ids prefixados para reuso no mesmo SVG."""
    spec = VARIANTS[variant]
    if spec["theme"] is None:
        return ""
    theme = spec["theme"]
    a0, a1 = (color(palette, theme, t) for t in spec["anvil"])
    b0, b1 = (color(palette, theme, t) for t in spec["anvil_bottom"])
    s0, s1 = (color(palette, theme, t) for t in spec["spark"])
    out = [
        f'<linearGradient id="{prefix}anvil-grad" gradientUnits="userSpaceOnUse" '
        f'x1="150" y1="150" x2="362" y2="150">'
        f'<stop offset="0" stop-color="{a0}"/><stop offset="1" stop-color="{a1}"/></linearGradient>',
        f'<linearGradient id="{prefix}anvil-left-grad" gradientUnits="userSpaceOnUse" '
        f'x1="150" y1="150" x2="180" y2="300">'
        f'<stop offset="0" stop-color="{a0}"/><stop offset="1" stop-color="{b0}"/></linearGradient>',
        f'<linearGradient id="{prefix}anvil-right-grad" gradientUnits="userSpaceOnUse" '
        f'x1="362" y1="150" x2="332" y2="300">'
        f'<stop offset="0" stop-color="{a1}"/><stop offset="1" stop-color="{b1}"/></linearGradient>',
        f'<linearGradient id="{prefix}anvil-bottom-grad" gradientUnits="userSpaceOnUse" '
        f'x1="180" y1="372" x2="332" y2="372">'
        f'<stop offset="0" stop-color="{b0}"/><stop offset="1" stop-color="{b1}"/></linearGradient>',
        f'<linearGradient id="{prefix}spark-grad" gradientUnits="userSpaceOnUse" '
        f'x1="256" y1="240" x2="256" y2="316">'
        f'<stop offset="0" stop-color="{s0}"/><stop offset="1" stop-color="{s1}"/></linearGradient>',
    ]
    if spec["glow"] and not small:
        out.append(
            f'<filter id="{prefix}glow" x="-20%" y="-20%" width="140%" height="140%">'
            '<feGaussianBlur in="SourceGraphic" stdDeviation="8" result="blur"/>'
            '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
            "</filter>"
        )
    return "".join(out)


SMALL = {"anvil": 38, "spark": 30}
# Spark da variante pequena: chevrons mais próximos do centro e sem o ponto (≤ 32 px).
SMALL_SPARK_LEFT = "M240 246L216 280L240 314"
SMALL_SPARK_RIGHT = "M272 246L296 280L272 314"


def mark_body(palette, variant, prefix="", small=False):
    """Elementos da marca (sem <svg>), no espaço 512x512.

    small=True: traço mais grosso, sem nós e sem brilho (ícone ≤ 32 px).
    """
    spec = VARIANTS[variant]
    mono = spec["theme"] is None
    anvil_w = SMALL["anvil"] if small else ANVIL_STROKE
    spark_w = SMALL["spark"] if small else SPARK_STROKE
    anvil_paint = "currentColor" if mono else f"url(#{prefix}anvil-grad)"
    left_paint = "currentColor" if mono else f"url(#{prefix}anvil-left-grad)"
    right_paint = "currentColor" if mono else f"url(#{prefix}anvil-right-grad)"
    bottom_paint = "currentColor" if mono else f"url(#{prefix}anvil-bottom-grad)"
    spark_paint = "currentColor" if mono else f"url(#{prefix}spark-grad)"
    core_paint = "currentColor" if mono else color(palette, spec["theme"], spec["core"])
    glow = f' filter="url(#{prefix}glow)"' if spec["glow"] and not small else ""
    line = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    cx, cy, r = CORE
    left, right = (SMALL_SPARK_LEFT, SMALL_SPARK_RIGHT) if small else (SPARK_LEFT, SPARK_RIGHT)
    parts = [
        f'<g id="{prefix}mark"{glow}>',
        f'<g id="{prefix}anvil" fill="none" stroke-linecap="round" stroke-linejoin="round" '
        f'stroke-width="{anvil_w}">'
        f'<path d="{ANVIL_TOP}" stroke="{anvil_paint}"/>'
        f'<path d="{ANVIL_LEFT}" stroke="{left_paint}"/>'
        f'<path d="{ANVIL_RIGHT}" stroke="{right_paint}"/>'
        f'<path d="{ANVIL_BOTTOM}" stroke="{bottom_paint}"/></g>',
        f'<path id="{prefix}horn" d="{HORN}" {line} stroke="{bottom_paint}" stroke-width="{anvil_w}"/>',
        f'<g id="{prefix}spark" {line} stroke="{spark_paint}" stroke-width="{spark_w}">'
        f'<path d="{left}"/><path d="{right}"/></g>',
    ]
    if not small:
        parts.append(f'<circle id="{prefix}core" cx="{cx}" cy="{cy}" r="{r}" fill="{core_paint}"/>')
    if not mono and not small:
        fill = color(palette, spec["theme"], spec["node_fill"])
        nodes = "".join(
            f'<circle cx="{x}" cy="{y}" r="{NODE_R}" fill="{fill}"/>'
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


WORDMARK_PATH = HERE / "src" / "wordmark.json"
# Logotipo horizontal: placa da marca, divisor e wordmark do protótipo.
LOGO_HEIGHT = 420
LOGO_TILE = (40, 40, 340)
LOGO_DIVIDER_X = 425
MARK_CENTER_Y = LOGO_HEIGHT / 2
CAP_HEIGHT = 118  # altura das maiúsculas do wordmark
WORD_X = 500
WORD_COLORS = {"on-dark": ("text-strong", "accent-cyan"), "on-light": ("text-strong", "accent-cyan")}


def load_wordmark(path=WORDMARK_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def wordmark_body(palette, variant, wm, x, baseline):
    k = CAP_HEIGHT / wm["cap_height"]
    if VARIANTS[variant]["theme"] is None:
        forja_fill = os_fill = "currentColor"
    else:
        theme = VARIANTS[variant]["theme"]
        forja_fill, os_fill = (color(palette, theme, t) for t in WORD_COLORS[variant])
    return (
        f'<g id="wordmark" transform="translate({x} {baseline}) scale({k:.6f})">'
        f'<path id="word-forja" fill="{forja_fill}" d="{wm["forja"]["d"]}"/>'
        f'<path id="word-os" fill="{os_fill}" transform="translate({wm["os"]["offset"]} 0)" d="{wm["os"]["d"]}"/>'
        "</g>"
    )


def logo_svg(palette, variant, wm):
    k = CAP_HEIGHT / wm["cap_height"]
    word_w = (wm["os"]["offset"] + wm["os"]["advance"]) * k
    baseline = MARK_CENTER_Y + CAP_HEIGHT / 2
    width = round(WORD_X + word_w + 40)
    x, y, side = LOGO_TILE
    if VARIANTS[variant]["theme"] is None:
        fill, outline, inner = "none", "currentColor", "currentColor"
    else:
        theme = VARIANTS[variant]["theme"]
        colors = palette["themes"][theme]["colors"]
        if theme == "dark":
            fill, outline, inner = colors["void"], colors["layer-3"], colors["accent-cyan-deep"]
        else:
            fill, outline, inner = colors["layer-1"], colors["hairline"], colors["hairline-active"]
    tile = (
        f'<rect id="logo-tile" x="{x}" y="{y}" width="{side}" height="{side}" rx="76" '
        f'fill="{fill}" stroke="{outline}" stroke-width="4"/>'
        f'<rect id="logo-tile-inner" x="{x+14}" y="{y+14}" width="{side-28}" height="{side-28}" '
        f'rx="64" fill="none" stroke="{inner}" stroke-opacity="0.3" stroke-width="2"/>'
    )
    divider = (
        f'<path id="logo-divider" d="M{LOGO_DIVIDER_X} 70V350" '
        f'fill="none" stroke="{outline}" stroke-width="2"/>'
    )
    mark = (
        '<g transform="translate(210 210) scale(0.8) translate(-240 -261)">'
        f'{mark_body(palette, variant, "")}</g>'
    )
    body = tile + mark + divider + wordmark_body(palette, variant, wm, WORD_X, round(baseline, 1))
    return svg_doc(f"0 0 {width} {LOGO_HEIGHT}", width, LOGO_HEIGHT, mark_defs(palette, variant, ""), body)


# Ícone de aplicativo: placa escura arredondada + marca (cores do tema escuro).
ICON = {
    "forjaos-icon.svg": {"small": False, "inset": 6, "radius": 112, "scale": 0.94},
    "forjaos-icon-small.svg": {"small": True, "inset": 6, "radius": 104, "scale": 1.14},
}
MARK_CENTER = (240, 261)  # centro visual da marca (bigorna + chifre)
PNG_SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)


def png_source(size):
    return "forjaos-icon-small.svg" if size <= 32 else "forjaos-icon.svg"


def icon_svg(palette, name):
    cfg = ICON[name]
    dark = palette["themes"]["dark"]["colors"]
    i, size = cfg["inset"], 512 - 2 * cfg["inset"]
    tile = (
        f'<rect id="tile" x="{i}" y="{i}" width="{size}" height="{size}" rx="{cfg["radius"]}" '
        f'fill="{dark["void"]}" stroke="{dark["layer-3"]}" stroke-width="7"/>'
        f'<rect id="tile-inner" x="{i+16}" y="{i+16}" width="{size-32}" height="{size-32}" '
        f'rx="{cfg["radius"]-12}" fill="none" stroke="{dark["accent-cyan-deep"]}" '
        'stroke-opacity="0.35" stroke-width="2"/>'
    )
    mx, my = MARK_CENTER
    mark = (
        f'<g transform="translate(256 256) scale({cfg["scale"]}) translate({-mx} {-my})">'
        f'{mark_body(palette, "on-dark", "", small=cfg["small"])}</g>'
    )
    defs = mark_defs(palette, "on-dark", "", small=cfg["small"])
    return svg_doc("0 0 512 512", 512, 512, defs, tile + mark)


def write_pngs(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    for size in PNG_SIZES:
        target = out_dir / f"forjaos-{size}.png"
        subprocess.run(
            ["rsvg-convert", "-w", str(size), "-h", str(size), str(HERE / png_source(size)), "-o", str(target)],
            check=True,
        )
        print(f"escrito brand/logo/png/{target.name}")


def build(palette=None, wordmark=None):
    """Retorna {nome_do_arquivo: conteúdo} de cada SVG gerado."""
    palette = palette or load_palette()
    wm = wordmark or load_wordmark()
    out = {f"forjaos-mark-{v}.svg": mark_svg(palette, v) for v in VARIANTS}
    out.update({f"forjaos-logo-{v}.svg": logo_svg(palette, v, wm) for v in VARIANTS})
    out.update({name: icon_svg(palette, name) for name in ICON})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gera o logo ForjaOS (FR-053).")
    ap.add_argument("--png", action="store_true", help="exporta também os PNGs do ícone (rsvg-convert)")
    ap.add_argument("--check", action="store_true", help="falha se algum SVG versionado divergir do gerado")
    ap.add_argument("--dir", type=Path, default=HERE, help="diretório dos SVGs (padrão: brand/logo)")
    args = ap.parse_args(argv)
    files = build()
    if args.check:
        stale = [
            name for name, content in files.items()
            if not (args.dir / name).is_file() or (args.dir / name).read_text(encoding="utf-8") != content
        ]
        for name in stale:
            print(f"build_logo: {name} desatualizado — rode python3 brand/logo/build_logo.py")
        if not stale:
            print(f"build_logo: OK ({len(files)} SVGs)")
        return 1 if stale else 0
    for name, content in files.items():
        (args.dir / name).write_text(content, encoding="utf-8")
        print(f"escrito brand/logo/{name}")
    if args.png:
        write_pngs(args.dir / "png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
