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
    state_color = colors[palette["mascot"]["state_colors"][state]]
    if state == "idle":
        eye_shape = f'<path d="M181 299 Q209 280 237 298 Q209 313 181 299Z M331 299 Q303 280 275 298 Q303 313 331 299Z" fill="{dark}"/><circle cx="214" cy="296" r="4" fill="{cream}"/><circle cx="298" cy="296" r="4" fill="{cream}"/>'
        mouth_shape = f'<path d="M230 423 Q256 435 282 423" fill="none" stroke="{dark}" stroke-width="8" stroke-linecap="round"/>'
        badge_shape = f'<circle cx="416" cy="110" r="15" fill="{state_color}" stroke="{dark}" stroke-width="5"/>'
    elif state == "listening":
        eye_shape = f'<ellipse cx="209" cy="296" rx="21" ry="15" fill="{dark}"/><ellipse cx="303" cy="296" rx="21" ry="15" fill="{dark}"/><circle cx="213" cy="291" r="5" fill="{cream}"/><circle cx="307" cy="291" r="5" fill="{cream}"/>'
        mouth_shape = f'<path d="M237 423 Q256 431 275 423" fill="none" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>'
        badge_shape = f'<circle cx="416" cy="110" r="11" fill="{state_color}"/><path d="M394 91 Q379 110 394 129 M438 91 Q453 110 438 129" fill="none" stroke="{state_color}" stroke-width="7" stroke-linecap="round"/>'
    elif state == "thinking":
        eye_shape = f'<path d="M185 301 Q209 282 235 298 Q211 315 185 301Z M327 301 Q303 282 277 298 Q301 315 327 301Z" fill="{dark}"/><circle cx="205" cy="292" r="5" fill="{cream}"/><circle cx="297" cy="292" r="5" fill="{cream}"/><path d="M186 271 Q210 263 230 275 M282 275 Q302 263 326 271" fill="none" stroke="{dark}" stroke-width="6"/>'
        mouth_shape = f'<path d="M240 427 Q256 419 272 427" fill="none" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>'
        badge_shape = f'<circle cx="416" cy="110" r="10" fill="{state_color}"/><path d="M394 87 Q418 72 440 94" fill="none" stroke="{state_color}" stroke-width="6" stroke-linecap="round"/><circle cx="443" cy="96" r="5" fill="{state_color}"/>'
    elif state == "speaking":
        eye_shape = f'<path d="M183 299 Q209 285 237 301 Q209 309 183 299Z M329 299 Q303 285 275 301 Q303 309 329 299Z" fill="{dark}"/><circle cx="211" cy="296" r="4" fill="{cream}"/><circle cx="301" cy="296" r="4" fill="{cream}"/>'
        mouth_shape = f'<ellipse cx="256" cy="425" rx="22" ry="14" fill="{dark}"/><path d="M243 430 Q256 423 269 430" fill="none" stroke="{orange_soft}" stroke-width="5"/>'
        badge_shape = f'<circle cx="416" cy="110" r="10" fill="{state_color}"/><path d="M393 99 V121 M385 104 V116 M439 99 V121 M447 104 V116" fill="none" stroke="{state_color}" stroke-width="6" stroke-linecap="round"/>'
    elif state == "error":
        eye_shape = f'<path d="M190 286 228 312 M228 286 190 312 M284 286 322 312 M322 286 284 312" fill="none" stroke="{state_color}" stroke-width="9" stroke-linecap="round"/>'
        mouth_shape = f'<path d="M235 431 248 421 260 431 276 421" fill="none" stroke="{dark}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
        badge_shape = f'<circle cx="416" cy="110" r="15" fill="{state_color}" stroke="{dark}" stroke-width="5"/><path d="M410 104 422 116 M422 104 410 116" stroke="{cream}" stroke-width="4"/>'
    else:
        raise ValueError(f"unknown Guará state: {state}")
    eyes = f'<g id="eyes">{eye_shape}</g>'
    mouth = f'<g id="mouth">{mouth_shape}</g>'
    glow = f'<g id="glow"><circle cx="256" cy="252" r="235" fill="none" stroke="{state_color}" stroke-width="8" opacity="0.7"/></g>'
    badge = f'<g id="badge">{badge_shape}</g>'
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
