#!/usr/bin/env python3
"""Generate platform theme files from brand/palette.json (FR-051, ADR-027)."""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
PALETTE_PATH = ROOT / "brand/palette.json"
PALETTE = json.loads(PALETTE_PATH.read_text(encoding="utf-8"))


def _plasma_outputs():
    module_path = ROOT / "brand/plasma/build_plasma.py"
    spec = importlib.util.spec_from_file_location("forjaos_plasma_generator", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {path.relative_to(ROOT).as_posix(): content for path, content in module.expected().items()}


def _colors(theme):
    colors = PALETTE["themes"][theme]["colors"]
    return {
        "canvas": colors["canvas"],
        "surface": colors["layer-1"],
        "surface_alt": colors["layer-2"],
        "surface_high": colors.get("layer-3", colors["layer-2"]),
        "text": colors["on-surface"],
        "text_muted": colors["text-muted"],
        "accent": colors["accent-cyan"],
        "accent_alt": colors.get("accent-violet", colors["accent-indigo"]),
        "success": colors["success"],
        "warning": colors["warning"],
        "danger": colors["danger"],
        "on_accent": colors.get("on-primary", colors["on-surface"]),
        "selection": colors.get("selection", colors["primary-container"] if "primary-container" in colors else colors["accent-cyan"]),
        "border": colors.get("outline-variant", colors.get("hairline", colors["layer-2"])),
    }


def _rgba(hex_color):
    return tuple(int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5))


def _konsole_rgb(hex_color):
    return ",".join(str(int(hex_color[index:index + 2], 16)) for index in (1, 3, 5))


def _header():
    return "/* Generated from brand/palette.json by build_themes.py. Do not edit. */\n"


def _qml(theme):
    c = _colors(theme)
    return f'''// Generated from brand/palette.json by build_themes.py. Do not edit.
import QtQuick

QtObject {{
    readonly property color canvas: "{c["canvas"]}"
    readonly property color surface: "{c["surface"]}"
    readonly property color surfaceAlt: "{c["surface_alt"]}"
    readonly property color text: "{c["text"]}"
    readonly property color textMuted: "{c["text_muted"]}"
    readonly property color accent: "{c["accent"]}"
    readonly property color success: "{c["success"]}"
    readonly property color warning: "{c["warning"]}"
    readonly property color danger: "{c["danger"]}"
    readonly property color border: "{c["border"]}"
}}
'''


def _plymouth_script(theme):
    dimensions = PALETTE["dimensions"]
    canvas = _colors(theme)["canvas"]
    red, green, blue = _rgba(canvas)
    return f'''# Generated from brand/palette.json by build_themes.py. Do not edit.
# Canvas token: {canvas}
Window.SetBackgroundTopColor({red:.6f}, {green:.6f}, {blue:.6f});
Window.SetBackgroundBottomColor({red:.6f}, {green:.6f}, {blue:.6f});

logo_image = Image("special://logo");
logo_sprite = Sprite(logo_image);
logo_sprite.SetX(Window.GetWidth() / 2 - logo_image.GetWidth() / 2);
logo_sprite.SetY(Window.GetHeight() / 2 - logo_image.GetHeight() / 2 - {dimensions['plymouth_logo_vertical_offset']});

bar_width = Math.Min({dimensions['plymouth_progress_max_width']}, Window.GetWidth() - {2 * dimensions['plymouth_progress_side_margin']});
bar_y = Window.GetHeight() / 2 + logo_image.GetHeight() / 2 + {dimensions['plymouth_progress_vertical_gap']};
bar_background_image = Image("progress-background.svg").Scale(bar_width, {dimensions['plymouth_progress_height']});
bar_fill_image = Image("progress-fill.svg").Scale(bar_width, {dimensions['plymouth_progress_height']});
bar_background = Sprite(bar_background_image);
bar_background.SetX(Window.GetWidth() / 2 - bar_width / 2);
bar_background.SetY(bar_y);
bar_fill = Sprite(bar_fill_image);
bar_fill.SetX(Window.GetWidth() / 2 - bar_width / 2);
bar_fill.SetY(bar_y);
bar_fill.SetImage(bar_fill_image.Scale({dimensions['plymouth_progress_min_width']}, {dimensions['plymouth_progress_height']}));

fun boot_progress_callback(duration, progress)
{{
    width = Math.Max({dimensions['plymouth_progress_min_width']}, Math.Int(bar_width * Math.Clamp(progress, 0, 1)));
    bar_fill.SetImage(bar_fill_image.Scale(width, {dimensions['plymouth_progress_height']}));
}}

Plymouth.SetBootProgressFunction(boot_progress_callback);
'''


def _plymouth_theme(theme):
    label = f"ForjaOS {theme.title()}"
    return f'''# Generated from brand/palette.json by build_themes.py. Do not edit.
[Plymouth Theme]
Name={label}
Description={label} boot splash
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/forjaos-{theme}
ScriptFile=/usr/share/plymouth/themes/forjaos-{theme}/forjaos.script
'''


def _grub_theme(theme):
    dimensions = PALETTE["dimensions"]
    colors = PALETTE["themes"][theme]["colors"]
    background = colors.get("void", colors["canvas"])
    return f'''# Generated from brand/palette.json by build_themes.py. Do not edit.
title-text: "ForjaOS"
title-color: "{colors['on-surface']}"
title-font: "Plus Jakarta Sans Regular 24"
message-color: "{colors['text-muted']}"
message-bg-color: "{background}"
desktop-color: "{background}"

+ boot_menu {{
  left = {dimensions['grub_menu_left_percent']}%
  top = {dimensions['grub_menu_top_percent']}%
  width = {dimensions['grub_menu_width_percent']}%
  height = {dimensions['grub_menu_height_percent']}%
  item_font = "JetBrains Mono Regular 12"
  item_color = "{colors['on-surface']}"
  selected_item_color = "{colors['on-primary']}"
  item_height = {PALETTE['dimensions']['button_dialog']}
  item_padding = {dimensions['grub_menu_item_padding']}
  item_spacing = {dimensions['grub_menu_item_spacing']}
}}
'''


def _progress_svg(color, name):
    width = PALETTE["dimensions"]["plymouth_progress_max_width"]
    height = PALETTE["dimensions"]["plymouth_progress_height"]
    return f'''<!-- Generated from brand/palette.json by build_themes.py. Do not edit. -->
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect id="{name}" width="{width}" height="{height}" fill="{color}"/>
</svg>
'''


def _konsole(theme):
    c = _colors(theme)
    ansi = [c["canvas"], c["danger"], c["success"], c["warning"], c["accent"], c["accent_alt"], c["selection"], c["text"]]
    entries = [
        "# Generated from brand/palette.json by build_themes.py. Do not edit.",
        "[Background]", f"Color={_konsole_rgb(c['canvas'])}",
        "[BackgroundFaint]", f"Color={_konsole_rgb(c['canvas'])}",
        "[BackgroundIntense]", f"Color={_konsole_rgb(c['surface_alt'])}",
        "[Foreground]", f"Color={_konsole_rgb(c['text'])}",
        "[ForegroundFaint]", f"Color={_konsole_rgb(c['text_muted'])}",
        "[ForegroundIntense]", f"Color={_konsole_rgb(c['text'])}",
    ]
    for index, color in enumerate(ansi):
        entries.extend([f"[Color{index}]", f"Color={_konsole_rgb(color)}", f"[Color{index}Faint]", f"Color={_konsole_rgb(color)}", f"[Color{index}Intense]", f"Color={_konsole_rgb(color)}"])
    entries.extend([
        "[General]", "Blur=false", "ColorRandomization=false", f"Description=ForjaOS {theme.title()}",
        "Opacity=1", "Wallpaper=",
    ])
    return "\n".join(entries) + "\n"


def _vscode(theme):
    c = _colors(theme)
    dark = theme == "dark"
    data = {
        "name": f"ForjaOS {theme.title()}",
        "type": "dark" if dark else "light",
        "colors": {
            "editor.background": c["canvas"], "editor.foreground": c["text"],
            "editorLineNumber.foreground": c["text_muted"], "editorLineNumber.activeForeground": c["accent"],
            "editor.selectionBackground": c["selection"], "editorCursor.foreground": c["accent"],
            "sideBar.background": c["surface"], "sideBar.foreground": c["text"],
            "activityBar.background": c["canvas"], "activityBar.foreground": c["accent"],
            "statusBar.background": c["surface_alt"], "statusBar.foreground": c["text"],
            "titleBar.activeBackground": c["surface"], "titleBar.activeForeground": c["text"],
            "panel.background": c["canvas"], "panel.border": c["border"],
            "focusBorder": c["accent"], "button.background": c["accent"],
            "button.foreground": c["on_accent"], "list.activeSelectionBackground": c["selection"],
            "errorForeground": c["danger"], "editorError.foreground": c["danger"],
            "editorWarning.foreground": c["warning"], "testing.iconPassed": c["success"],
        },
        "tokenColors": [
            {"name": "Comments", "scope": ["comment", "punctuation.definition.comment"], "settings": {"foreground": c["text_muted"], "fontStyle": "italic"}},
            {"name": "Strings", "scope": ["string", "constant.other.symbol"], "settings": {"foreground": c["success"]}},
            {"name": "Keywords", "scope": ["keyword", "storage.type", "storage.modifier"], "settings": {"foreground": c["accent_alt"]}},
            {"name": "Functions", "scope": ["entity.name.function", "support.function"], "settings": {"foreground": c["accent"]}},
            {"name": "Numbers", "scope": ["constant.numeric"], "settings": {"foreground": c["warning"]}},
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _gtk(theme):
    c = _colors(theme)
    names = {
        "window_bg_color": c["canvas"], "view_bg_color": c["surface"], "view_fg_color": c["text"],
        "headerbar_bg_color": c["surface"], "headerbar_fg_color": c["text"],
        "card_bg_color": c["surface_alt"], "accent_bg_color": c["accent"],
        "accent_fg_color": c["canvas"], "success_color": c["success"],
        "warning_color": c["warning"], "error_color": c["danger"],
    }
    values = "\n".join(f"@define-color {name} {value};" for name, value in names.items())
    return _header() + values + "\n\n* { font-family: '" + PALETTE["typography"]["families"]["ui"] + "'; }\n"


def _tokens_css():
    sections = [_header()]
    for theme in ("dark", "light"):
        colors = PALETTE["themes"][theme]["colors"]
        sections.append(f'[data-forja-theme="{theme}"] {{')
        for name, value in colors.items():
            if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", value):
                sections.append(f"  --fj-{name}: {value};")
        sections.append("}\n")
    return "\n".join(sections)


def expected(include_firefox=False):
    outputs = _plasma_outputs()
    outputs["brand/tokens.css"] = _tokens_css()
    for theme in ("dark", "light"):
        c = _colors(theme)
        outputs[f"brand/sddm/ForjaTheme-{theme}.qml"] = _qml(theme)
        outputs[f"brand/qml/{theme}/ForjaTheme.qml"] = _qml(theme)
        outputs[f"brand/grub/forja-{theme}/theme.txt"] = _grub_theme(theme)
        outputs[f"brand/plymouth/forjaos-{theme}/forjaos.plymouth"] = _plymouth_theme(theme)
        outputs[f"brand/plymouth/forjaos-{theme}/forjaos.script"] = _plymouth_script(theme)
        outputs[f"brand/plymouth/forjaos-{theme}/progress-background.svg"] = _progress_svg(c["surface_alt"], "background")
        outputs[f"brand/plymouth/forjaos-{theme}/progress-fill.svg"] = _progress_svg(c["accent"], "fill")
        outputs[f"brand/konsole/Forja {theme.title()}.colorscheme"] = _konsole(theme)
        outputs[f"brand/vscode/forja-{theme}-color-theme.json"] = _vscode(theme)
        outputs[f"brand/gtk/forja-{theme}.css"] = _gtk(theme)
        if include_firefox:
            firefox = _header() + f'''@-moz-document url(chrome://browser/content/browser.xhtml) {{
  #navigator-toolbox {{ background-color: {c["surface"]} !important; color: {c["text"]} !important; }}
  #TabsToolbar {{ background-color: {c["canvas"]} !important; }}
  #urlbar-background {{ background-color: {c["surface_alt"]} !important; border-color: {c["border"]} !important; }}
  #urlbar[focused="true"] > #urlbar-background {{ border-color: {c["accent"]} !important; }}
}}
'''
            outputs[f"brand/firefox/userChrome-{theme}.css"] = firefox
    return outputs


def run(output_dir, check=False, include_firefox=False):
    destination_root = Path(output_dir).resolve() if output_dir else ROOT
    stale = []
    for relative_path, content in expected(include_firefox).items():
        path = destination_root / relative_path
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(relative_path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    if stale:
        raise SystemExit("stale theme assets: " + ", ".join(stale))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated files are missing or stale")
    parser.add_argument("--firefox", action="store_true", help="also generate optional Firefox userChrome.css")
    parser.add_argument("--output-dir", help="write under a temporary root instead of the repository")
    args = parser.parse_args(argv)
    run(args.output_dir, args.check, args.firefox)


if __name__ == "__main__":
    main()
