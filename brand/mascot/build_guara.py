#!/usr/bin/env python3
"""Build the five palette-driven static Guará SVG states (FR-054)."""

import argparse
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PALETTE = HERE.parent / "palette.json"


def render(state, palette):
    colors = palette["themes"]["dark"]["colors"]
    orange = colors["accent-orange"]
    orange_soft = colors["accent-orange-soft"]
    dark = colors["void"]
    cream = colors["tertiary"]
    muted = colors["text-muted"]
    body = f"""<g id="body">
  <path d="M256 148 C218 150 182 171 160 213 L121 236 148 260 108 285 145 300 119 330 158 345 150 366 191 383 216 431 Q256 456 296 431 L321 383 362 366 354 345 393 330 367 300 404 285 364 260 391 236 352 213 C330 171 294 150 256 148Z" fill="url(#fur)" stroke="{dark}" stroke-width="8" stroke-linejoin="round"/>
  <path d="M256 168 L224 282 256 368 288 282Z" fill="{orange_soft}" opacity="0.58"/>
  <path d="M147 338 L208 324 242 368 256 407 216 421Z M365 338 L304 324 270 368 256 407 296 421Z" fill="{cream}"/>
  <path d="M207 357 Q256 329 305 357 L312 411 Q256 451 200 411Z" fill="{cream}"/>
  <path d="M228 390 Q256 379 284 390 L271 411 Q256 421 241 411Z" fill="{dark}"/>
</g>"""
    ears = f"""<g id="ears">
  <path d="M157 226 C136 174 122 119 108 46 L178 108 221 207Z M355 226 C376 174 390 119 404 46 L334 108 291 207Z" fill="{orange}" stroke="{dark}" stroke-width="8" stroke-linejoin="round"/>
  <path d="M160 187 L132 91 181 132 199 201Z M352 187 L380 91 331 132 313 201Z" fill="{cream}"/>
  <path d="M108 46 149 81 130 119Z M404 46 363 81 382 119Z" fill="{dark}"/>
</g>"""
    eyes = f"""<g id="eyes">
  <path d="M181 299 Q209 280 237 298 Q209 313 181 299Z M331 299 Q303 280 275 298 Q303 313 331 299Z" fill="{dark}"/>
  <circle cx="214" cy="296" r="4" fill="{cream}"/><circle cx="298" cy="296" r="4" fill="{cream}"/>
</g>"""
    mouth = f'<g id="mouth"><path d="M230 423 Q256 435 282 423" fill="none" stroke="{dark}" stroke-width="8" stroke-linecap="round"/></g>'
    glow = f'<g id="glow"><circle cx="256" cy="252" r="235" fill="none" stroke="{muted}" stroke-width="8" opacity="0.7"/></g>'
    badge = f'<g id="badge"><circle cx="416" cy="110" r="15" fill="{muted}" stroke="{dark}" stroke-width="5"/></g>'
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" '
        f'viewBox="0 0 512 512" data-state="{state}">\n'
        '<defs><linearGradient id="fur" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{orange_soft}"/><stop offset="1" stop-color="{orange}"/>'
        '</linearGradient></defs>\n'
        + "\n".join((body, ears, eyes, mouth, glow, badge))
        + "\n</svg>\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated SVGs drift")
    args = parser.parse_args()
    palette = json.loads(PALETTE.read_text(encoding="utf-8"))
    stale = []
    for state in palette["mascot"]["states"]:
        path = HERE / f"guara-{state}.svg"
        expected = render(state, palette)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                stale.append(path.name)
        else:
            path.write_text(expected, encoding="utf-8", newline="\n")
    if stale:
        print("Guará SVGs out of date: " + ", ".join(stale), file=sys.stderr)
        return 1
    print("Guará SVGs: OK" if args.check else "Guará SVGs generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
