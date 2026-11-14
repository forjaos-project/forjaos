#!/usr/bin/env python3
"""Prepare licensed ForjaOS branding sources for the installer RPM."""

import argparse
import json
import shutil
from pathlib import Path


def generate(sources: Path, brand: Path) -> None:
    colors = json.loads((brand / "palette.json").read_text(encoding="utf-8"))["themes"]["dark"]["colors"]
    sources.mkdir(parents=True, exist_ok=True)
    (sources / "os-release").write_text(
        'NAME="ForjaOS"\nPRETTY_NAME="ForjaOS 0.1"\nID=forjaos\n'
        'ID_LIKE=fedora\nVERSION_ID=0.1\nLOGO=forjaos-icon\n'
        'HOME_URL="https://github.com/forjaos-project/forjaos"\n'
        'DOCUMENTATION_URL="https://github.com/forjaos-project/forjaos"\n'
        'SUPPORT_URL="https://github.com/forjaos-project/forjaos/issues"\n'
        'BUG_REPORT_URL="https://github.com/forjaos-project/forjaos/issues"\n',
        encoding="utf-8",
    )
    (sources / "forjaos.conf").write_text(
        "[Profile]\nprofile_id = forjaos\nbase_profile = fedora\n\n"
        "[Profile Detection]\nos_id = forjaos\n\n"
        "[User Interface]\ncustom_stylesheet = /usr/share/anaconda/pixmaps/forjaos.css\n",
        encoding="utf-8",
    )
    (sources / "forjaos.css").write_text(
        "/* GTK Anaconda chrome uses canonical ForjaOS dark tokens. */\n"
        f"@define-color forja_canvas {colors['canvas']};\n"
        f"@define-color forja_accent {colors['accent-cyan']};\n"
        f"@define-color forja_text {colors['on-surface']};\n"
        "* { font-family: 'Plus Jakarta Sans'; }\n"
        ".logo-sidebar { background-color: @forja_canvas; background-image: none; }\n"
        ".logo { background-image: url('/usr/share/anaconda/pixmaps/forjaos-logo.png'); "
        "background-position: 50% 20px; background-repeat: no-repeat; "
        "background-color: transparent; }\n"
        ".product-logo { background-image: none; background-color: transparent; }\n"
        "AnacondaSpokeWindow #nav-box { background-color: @forja_canvas; "
        "background-image: none; color: @forja_text; }\n"
        "AnacondaSpokeWindow #nav-box button { color: @forja_accent; }\n",
        encoding="utf-8",
    )
    (sources / "branding.css").write_text(
        "/* Cockpit and Anaconda Web UI branding from the ForjaOS palette. */\n"
        "#badge { inline-size: 96px; block-size: 96px; "
        "background-image: url('logo.png'); background-size: contain; "
        "background-repeat: no-repeat; }\n"
        "#brand::before { content: 'ForjaOS'; }\n"
        ".anaconda {\n"
        f"  --brand-default-light: {colors['accent-cyan']};\n"
        f"  --brand-default: {colors['accent-cyan-deep']};\n"
        f"  --brand-default-dark: {colors['on-primary-container']};\n"
        "  font-family: 'Plus Jakarta Sans';\n"
        "  .logo { background-image: url('logo.png'); }\n"
        "}\n"
        ":not(.pf-v6-theme-dark) .anaconda {\n"
        "  --pf-t--global--color--brand--default: var(--brand-default);\n"
        "  --pf-t--global--color--brand--hover: var(--brand-default-dark);\n"
        "}\n"
        ".pf-v6-theme-dark .anaconda {\n"
        "  --pf-t--global--color--brand--default: var(--brand-default-light);\n"
        "  --pf-t--global--color--brand--hover: var(--brand-default);\n"
        "}\n",
        encoding="utf-8",
    )
    for source, destination in (
        (brand / "logo/png/forjaos-256.png", sources / "forjaos-logo.png"),
        (brand / "logo/forjaos-icon.svg", sources / "forjaos-icon.svg"),
        (brand / "fonts/PlusJakartaSans-VF.ttf", sources / "PlusJakartaSans-VF.ttf"),
        (brand / "fonts/OFL.txt", sources / "OFL.txt"),
        (brand / "LICENSES.md", sources / "LICENSES.md"),
    ):
        shutil.copyfile(source, destination)
    for icon in (brand / "logo/png").glob("forjaos-*.png"):
        shutil.copyfile(icon, sources / icon.name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--brand", required=True, type=Path)
    args = parser.parse_args()
    generate(args.sources, args.brand)


if __name__ == "__main__":
    main()
