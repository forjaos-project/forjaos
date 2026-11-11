"""Generate the ForjaOS Plasma 6 theme from the canonical palette."""

import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PALETTE = json.loads((ROOT / "brand/palette.json").read_text(encoding="utf-8"))


def rgb(value):
    return ",".join(str(int(value[index:index + 2], 16)) for index in (1, 3, 5))


def scheme(theme):
    colors = PALETTE["themes"][theme]["colors"]
    accent = colors["accent-cyan"]
    ai = colors["accent-violet" if theme == "dark" else "accent-indigo"]
    sections = ["# Generated from brand/palette.json by build_plasma.py", "[General]", f"Name=Forja {theme.title()}", "ColorScheme=Forja" + theme.title(), "shadeSortColumn=true"]
    backgrounds = {
        "Window": ("canvas", "layer-1"),
        "View": ("layer-1", "layer-2"),
        "Button": ("layer-2", "layer-3" if theme == "dark" else "layer-1"),
        "Selection": ("accent-cyan", "accent-cyan"),
        "Tooltip": ("layer-2", "layer-1"),
        "Complementary": ("layer-1", "layer-2"),
        "Header": ("layer-1", "layer-2"),
    }
    for section, (normal, alternate) in backgrounds.items():
        selected = section == "Selection"
        foreground = "on-primary" if selected else "on-surface"
        entries = {
            "BackgroundNormal": colors[normal],
            "BackgroundAlternate": colors[alternate],
            "ForegroundNormal": colors[foreground],
            "ForegroundInactive": colors["text-muted"],
            "ForegroundActive": accent,
            "ForegroundLink": ai,
            "ForegroundVisited": ai,
            "ForegroundNegative": colors["danger"],
            "ForegroundNeutral": colors["warning"],
            "ForegroundPositive": colors["success"],
            "DecorationFocus": accent,
            "DecorationHover": accent,
        }
        sections.extend(["", f"[Colors:{section}]"] + [f"{key}={rgb(value)}" for key, value in entries.items()])
    sections.extend(["", "[WM]", f"activeBackground={rgb(colors['layer-1'])}", f"activeForeground={rgb(colors['on-surface'])}", f"inactiveBackground={rgb(colors['layer-2'])}", f"inactiveForeground={rgb(colors['text-muted'])}"])
    return "\n".join(sections) + "\n"


def panel_svg(theme):
    colors = PALETTE["themes"][theme]["colors"]
    fill = colors["layer-1"]
    edge = colors["outline-variant"] if theme == "dark" else colors["hairline"]
    radius = PALETTE["radius"]["usage"]["dock"]
    margin = PALETTE["dimensions"]["dock_bottom_offset"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <defs><rect id="panel-shape" x="4" y="4" width="56" height="56" rx="{radius}"/></defs>
  <use href="#panel-shape" fill="{fill}" fill-opacity="0.84" stroke="{edge}" stroke-width="1"/>
  <rect id="top" x="24" y="4" width="16" height="20" fill="{fill}" fill-opacity="0.84"/>
  <rect id="bottom" x="24" y="40" width="16" height="20" fill="{fill}" fill-opacity="0.84"/>
  <rect id="left" x="4" y="24" width="20" height="16" fill="{fill}" fill-opacity="0.84"/>
  <rect id="right" x="40" y="24" width="20" height="16" fill="{fill}" fill-opacity="0.84"/>
  <rect id="topleft" x="4" y="4" width="20" height="20" fill="{fill}" fill-opacity="0.84"/>
  <rect id="topright" x="40" y="4" width="20" height="20" fill="{fill}" fill-opacity="0.84"/>
  <rect id="bottomleft" x="4" y="40" width="20" height="20" fill="{fill}" fill-opacity="0.84"/>
  <rect id="bottomright" x="40" y="40" width="20" height="20" fill="{fill}" fill-opacity="0.84"/>
  <rect id="center" x="24" y="24" width="16" height="16" fill="{fill}" fill-opacity="0.84"/>
  <rect id="floating-center" x="24" y="24" width="16" height="16" fill="{fill}" fill-opacity="0.84"/>
  <rect id="hint-top-margin" width="1" height="{margin}" fill="{fill}"/>
  <rect id="hint-bottom-margin" width="1" height="{margin}" fill="{fill}"/>
  <rect id="hint-left-margin" width="{margin}" height="1" fill="{fill}"/>
  <rect id="hint-right-margin" width="{margin}" height="1" fill="{fill}"/>
  <rect id="floating-hint-top-margin" width="1" height="{margin}" fill="{fill}"/>
  <rect id="floating-hint-bottom-margin" width="1" height="{margin}" fill="{fill}"/>
  <rect id="floating-hint-left-margin" width="{margin}" height="1" fill="{fill}"/>
  <rect id="floating-hint-right-margin" width="{margin}" height="1" fill="{fill}"/>
</svg>\n'''


def metadata(theme):
    return json.dumps({"KPlugin": {"Id": f"forja-{theme}", "Name": f"Forja {theme.title()}", "Description": "ForjaOS Plasma theme", "License": "CC BY-SA 4.0", "Authors": [{"Name": "ForjaOS project"}]}}, indent=2, ensure_ascii=False) + "\n"


def expected():
    files = {}
    for theme in ("dark", "light"):
        files[HERE / "color-schemes" / f"Forja{theme.title()}.colors"] = scheme(theme)
        base = HERE / "desktoptheme" / f"forja-{theme}"
        files[base / "metadata.json"] = metadata(theme)
        files[base / "widgets" / "panel-background.svg"] = panel_svg(theme)
    look = HERE / "look-and-feel" / "org.forjaos.desktop"
    files[look / "metadata.json"] = json.dumps({"KPackageStructure": "Plasma/LookAndFeel", "KPlugin": {"Id": "org.forjaos.desktop", "Name": "ForjaOS", "Description": "ForjaOS desktop", "License": "CC BY-SA 4.0", "Authors": [{"Name": "ForjaOS project"}]}}, indent=2, ensure_ascii=False) + "\n"
    files[look / "contents" / "defaults"] = """[kdeglobals][General]
ColorScheme=ForjaDark

[kdeglobals][Icons]
Theme=breeze

[plasmarc][Theme]
name=forja-dark

[Wallpaper]
Image=/usr/share/wallpapers/ForjaOS/dark-abstract.png

[ksplashrc][KSplash]
Theme=org.forjaos.desktop
"""
    dark = PALETTE["themes"]["dark"]["colors"]
    files[look / "contents" / "splash" / "Splash.qml"] = f'''import QtQuick

Rectangle {{
    id: root
    color: "{dark["canvas"]}"
    property int stage

    Image {{
        id: mark
        anchors.centerIn: parent
        width: 128
        height: 128
        source: "file:///usr/share/pixmaps/system-logo-white.png"
        fillMode: Image.PreserveAspectFit
        opacity: root.stage >= 5 ? 0 : 1
        Behavior on opacity {{ NumberAnimation {{ duration: 320 }} }}
    }}
    Rectangle {{
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: mark.bottom
        anchors.topMargin: 32
        width: root.stage >= 2 ? 64 : 0
        height: 3
        radius: 1
        color: "{dark["accent-cyan"]}"
        Behavior on width {{ NumberAnimation {{ duration: 320 }} }}
    }}
}}
'''
    files[look / "contents" / "layouts" / "org.kde.plasma.desktop-layout.js"] = f'''// First-login layout for FR-052. Optional launchers are added by their feature packages.
var top = new Panel;
top.location = "top";
top.height = {PALETTE["dimensions"]["topbar_height"]};
top.floating = false;
top.lengthMode = "fill";
top.addWidget("org.kde.plasma.kickoff");
top.addWidget("org.kde.plasma.pager");
top.addWidget("org.kde.plasma.panelspacer");
top.addWidget("org.kde.plasma.digitalclock");
top.addWidget("org.kde.plasma.panelspacer");
top.addWidget("org.kde.plasma.systemtray");

var dock = new Panel;
dock.location = "bottom";
dock.height = {PALETTE["dimensions"]["dock_height"]};
dock.floating = true;
dock.lengthMode = "fit";
dock.alignment = "center";
var tasks = dock.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "applications:org.kde.konsole.desktop",
    "applications:org.kde.dolphin.desktop",
    "applications:org.kde.plasma-systemmonitor.desktop",
    "preferred://browser"
]);
tasks.reloadConfig();
dock.addWidget("org.kde.plasma.kickoff");

var desktops = desktopsForActivity(currentActivity());
for (var i = 0; i < desktops.length; ++i) {{
    desktops[i].wallpaperPlugin = "org.kde.image";
    desktops[i].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    desktops[i].writeConfig("Image", "file:///usr/share/wallpapers/ForjaOS/dark-abstract.png");
}}
'''
    return files


def main():
    check = sys.argv[1:] == ["--check"]
    stale = []
    for path, content in expected().items():
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale:
        raise SystemExit("stale Plasma assets: " + ", ".join(str(path) for path in stale))


if __name__ == "__main__":
    main()
