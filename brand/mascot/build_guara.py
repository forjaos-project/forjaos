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
    amber = colors["warning"]
    body = f"""<g id="body">
  <path d="M256 129 C185 119 119 155 106 222 Q77 258 94 283 L72 302 104 305 Q75 336 94 352 L74 379 Q108 375 121 354 C100 407 139 449 182 464 Q222 489 256 495 Q290 489 330 464 C373 449 412 407 391 354 Q404 375 438 379 L418 352 Q437 336 408 305 L440 302 418 283 Q435 258 406 222 C393 155 327 119 256 129Z" fill="{dark}"/>
  <path d="M256 128 C203 125 155 153 139 197 Q112 208 102 232 L130 224 Q107 246 100 268 L135 253 Q106 291 114 309 L141 297 Q116 331 130 355 L153 338 Q138 381 164 411 Q176 383 191 369 C207 405 229 434 256 448 C283 434 305 405 321 369 Q336 383 348 411 Q374 381 359 338 L382 355 Q396 331 371 297 L398 309 Q406 291 377 253 L412 268 Q405 246 382 224 L410 232 Q400 208 373 197 C357 153 309 125 256 128Z" fill="{orange}"/>
  <path d="M256 145 Q233 179 223 231 Q246 205 256 217 Q266 205 289 231 Q279 179 256 145Z" fill="{orange_soft}"/>
  <path d="M125 325 Q164 304 194 323 Q225 336 246 378 Q219 365 195 378 Q171 386 145 368 Q163 367 178 354 Q152 347 125 354Z M387 325 Q348 304 318 323 Q287 336 266 378 Q293 365 317 378 Q341 386 367 368 Q349 367 334 354 Q360 347 387 354Z" fill="{cream}"/>
  <path d="M216 353 Q234 362 256 380 Q278 362 296 353 Q318 394 301 429 Q279 451 256 454 Q233 451 211 429 Q194 394 216 353Z" fill="{cream}"/>
  <path d="M221 386 Q234 374 256 376 Q278 374 291 386 Q285 410 256 413 Q227 410 221 386Z" fill="{dark}"/>
  <path d="M256 414 L256 426" fill="none" stroke="{dark}" stroke-width="6" stroke-linecap="round"/>
</g>"""
    ears = f"""<g id="ears">
  <path d="M163 208 C119 175 93 108 101 22 Q157 43 214 161 L225 216Z M349 208 C393 175 419 108 411 22 Q355 43 298 161 L287 216Z" fill="{dark}"/>
  <path d="M159 178 Q121 134 120 67 Q154 91 189 179Z M353 178 Q391 134 392 67 Q358 91 323 179Z" fill="{cream}"/>
  <path d="M172 180 Q177 141 164 106 Q205 149 213 195Z M340 180 Q335 141 348 106 Q307 149 299 195Z" fill="{orange}"/>
</g>"""
    state_color = colors[palette["mascot"]["state_colors"][state]]
    if state == "idle":
        eye_shape = f'<path d="M171 284 Q203 257 240 282 Q219 310 184 299Z M341 284 Q309 257 272 282 Q293 310 328 299Z" fill="{dark}"/><ellipse cx="207" cy="286" rx="13" ry="11" fill="{amber}"/><ellipse cx="305" cy="286" rx="13" ry="11" fill="{amber}"/><circle cx="208" cy="284" r="6" fill="{dark}"/><circle cx="304" cy="284" r="6" fill="{dark}"/><circle cx="213" cy="280" r="3" fill="{cream}"/><circle cx="299" cy="280" r="3" fill="{cream}"/>'
        mouth_shape = f'<path d="M235 428 Q256 443 277 428" fill="none" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>'
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
