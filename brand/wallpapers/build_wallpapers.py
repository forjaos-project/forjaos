#!/usr/bin/env python3
"""Generate deterministic 4K ForjaOS wallpaper SVG sources from palette.json."""

import argparse
import json
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PALETTE = ROOT / "brand/palette.json"
MASCOT = ROOT / "brand/mascot/guara-idle.svg"
OUTPUT = HERE / "ForjaOS"
STEMS = ("dark-abstract", "dark-guara", "light-abstract", "light-guara")


def mascot_fragment():
    source = MASCOT.read_text(encoding="utf-8")
    gradient = re.search(r'<linearGradient id="fur".*?</linearGradient>', source, re.DOTALL)
    groups = [re.search(fr'<g id="{layer}">.*?</g>', source, re.DOTALL) for layer in ("body", "ears", "eyes", "mouth")]
    if gradient is None or any(group is None for group in groups):
        raise ValueError("approved Guará SVG is missing a required vector component")
    return gradient.group(), "\n".join(group.group() for group in groups)


def render(stem, palette):
    theme, kind = stem.split("-", 1)
    colors = palette["themes"][theme]["colors"]
    background = colors["canvas"]
    layer = colors["layer-2"]
    cyan = colors["accent-cyan"]
    violet = colors["accent-violet" if theme == "dark" else "accent-indigo"]
    orange = colors["accent-orange"]
    mascot_defs, mascot_body = mascot_fragment() if kind == "guara" else ("", "")
    mascot = (
        f'<g id="mascot" transform="translate(2460 320) scale(2.8)" opacity="0.92">{mascot_body}</g>'
        if kind == "guara" else ""
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="3840" height="2160" viewBox="0 0 3840 2160" data-theme="{theme}" data-kind="{kind}">
<defs>
  <linearGradient id="wall-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{background}"/><stop offset="1" stop-color="{layer}"/></linearGradient>
  {mascot_defs}
</defs>
<rect width="3840" height="2160" fill="url(#wall-bg)"/>
<path d="M-200 1610 C680 1060 1180 1880 2160 1290 S3410 900 4050 1270 L4050 2250 H-200Z" fill="{violet}" opacity="0.13"/>
<path d="M-200 1910 C670 1340 1340 2200 2310 1590 S3550 1300 4050 1710 L4050 2250 H-200Z" fill="{cyan}" opacity="0.16"/>
<path d="M-200 2080 C750 1730 1520 2360 2520 1880 S3500 1680 4050 1940 L4050 2250 H-200Z" fill="{orange}" opacity="0.08"/>
<path d="M-100 1530 C760 980 1300 1760 2220 1200 S3480 820 3970 1100" fill="none" stroke="{cyan}" stroke-width="10" opacity="0.28"/>
<path d="M-100 1770 C740 1230 1430 2020 2370 1480 S3500 1180 3970 1480" fill="none" stroke="{violet}" stroke-width="8" opacity="0.24"/>
{mascot}
</svg>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if vector sources have drifted")
    args = parser.parse_args()
    palette = json.loads(PALETTE.read_text(encoding="utf-8"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stale = []
    for stem in STEMS:
        path = OUTPUT / f"{stem}.svg"
        expected = render(stem, palette)
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                stale.append(path.name)
        else:
            path.write_text(expected, encoding="utf-8", newline="\n")
    if stale:
        print("ForjaOS wallpapers out of date: " + ", ".join(stale), file=sys.stderr)
        return 1
    print("ForjaOS wallpapers: OK" if args.check else "ForjaOS wallpaper sources generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
