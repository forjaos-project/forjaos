#!/usr/bin/env python3
"""Replace inherited visible KDE branding inside a disposable bootc rootfs."""

import argparse
from pathlib import Path
import subprocess


WALLPAPER = "file:///usr/share/wallpapers/ForjaOS/dark-abstract.png"
PROFILE = "usr/share/kde-settings/kde-profile/default"
VISIBLE_WALLPAPERS = (
    "usr/share/wallpapers/bazzite-blue.png",
    "usr/share/wallpapers/bazzite-glass.png",
)


def within_root(root: Path, relative: str) -> Path:
    """Reject a changed base path that resolves outside the selected image root."""
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"path escapes image root: {relative}")
    return path


def replace(root: Path, relative: str, replacements: dict[str, str]) -> None:
    path = within_root(root, relative)
    source = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        if old not in source:
            raise ValueError(f"expected KDE value missing in {relative}: {old}")
        source = source.replace(old, new)
    path.write_text(source, encoding="utf-8")


def remove_file(root: Path, relative: str) -> None:
    path = within_root(root, relative)
    if path.exists() or path.is_symlink():
        path.unlink()


def remove_directory(root: Path, relative: str) -> None:
    path = within_root(root, relative)
    if not path.exists():
        return
    if not path.is_dir():
        raise ValueError(f"expected directory: {relative}")
    for child in sorted(path.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        within_root(root, child.relative_to(root).as_posix())
        if child.is_dir() and not child.is_symlink():
            child.rmdir()
        else:
            child.unlink()
    path.rmdir()


def remove_inherited_apps(root: Path) -> None:
    """Drop unowned branded launchers and updater catalog data, retaining executables."""
    for relative in (
        "usr/share/applications/bazzite-documentation.desktop",
        "usr/share/applications/discourse.desktop",
        "usr/share/metainfo/io.github.rfrench3.bazzite-updater.metainfo.xml",
    ):
        remove_file(root, relative)


def rebrand_first_login_launcher(root: Path) -> None:
    """Vapor is still the base's active first-login preset; give its launcher our icon."""
    setup = "usr/share/plasma/look-and-feel/com.valve.vapor.desktop/contents/plasmoidsetupscripts/org.kde.plasma.kickoff.js"
    replace(root, setup, {
        'applet.writeConfig("icon", "distributor-logo-steamdeck")':
        'applet.writeConfig("icon", "start-here")',
    })
    icons = "usr/share/icons/hicolor/scalable/places"
    forja = within_root(root, f"{icons}/start-here.svg")
    inherited = within_root(root, f"{icons}/distributor-logo.svg")
    alias = within_root(root, f"{icons}/distributor-logo-steamdeck.svg")
    if (not forja.is_file() or not inherited.is_file() or inherited.is_symlink()
            or not alias.is_symlink() or alias.readlink() != Path("distributor-logo.svg")):
        raise ValueError("expected ForjaOS launcher icon and unowned inherited icon")
    inherited.unlink()
    inherited.symlink_to("start-here.svg")


def rebrand_login_art(root: Path) -> None:
    """Keep the inherited login paths while replacing their unowned artwork."""
    source = within_root(root, "usr/share/wallpapers/ForjaOS/dark-abstract.png")
    legacy = within_root(root, "usr/share/wallpapers/convergence.jxl")
    output = within_root(root, "usr/share/wallpapers/ForjaOS/dark-abstract.jxl")
    if not source.is_file() or not legacy.is_file() or legacy.is_symlink() or output.exists():
        raise ValueError("expected original Plasma Login art and ForjaOS PNG")
    for name in ("default.jxl", "default-dark.jxl"):
        link = root / "usr/share/backgrounds" / name
        if not link.is_symlink() or link.readlink() != Path("/usr/share/wallpapers/convergence.jxl"):
            raise ValueError(f"unexpected Plasma Login default: {link}")
    subprocess.run(["magick", str(source), "-strip", "-quality", "100", str(output)], check=True)
    if not output.is_file() or not output.stat().st_size:
        raise ValueError("ForjaOS login wallpaper conversion failed")
    legacy.unlink()
    legacy.symlink_to("ForjaOS/dark-abstract.jxl")
    remove_file(root, "usr/share/wallpapers/convergence.png")


def configure(root: Path) -> None:
    share = f"{PROFILE}/share"
    xdg = f"{PROFILE}/xdg"
    replace(root, f"{xdg}/kdeglobals", {
        "LookAndFeelPackage=org.fedoraproject.fedora.desktop": "LookAndFeelPackage=org.forjaos.desktop",
        "ColorScheme=BreezeLight": "ColorScheme=ForjaDark",
        "Noto Sans Mono": "JetBrains Mono",
        "Noto Sans": "Plus Jakarta Sans",
    })
    replace(root, f"{share}/config/kdeglobals", {
        "Noto Sans Mono": "JetBrains Mono",
        "Noto Sans": "Plus Jakarta Sans",
    })
    replace(root, f"{xdg}/kscreenlockerrc", {
        "file:///usr/share/wallpapers/Fedora/": WALLPAPER,
    })
    replace(root, f"{share}/config/konquerorrc", {
        "http://start.fedoraproject.org/": "https://github.com/forjaos-project/forjaos",
    })
    # Fedora-only recommendations and bookmarks are not useful in a Forja profile.
    for relative in (
        f"{xdg}/neochatrc",
        f"{share}/apps/konqueror/bookmarks.xml",
        f"{share}/apps/konqueror/profiles/webbrowsing",
        f"{share}/apps/konqueror/profiles/tabbedbrowsing",
    ):
        remove_file(root, relative)

    # Preserve Steam/Deck functionality while replacing only the inherited splash art.
    for style in ("com.valve.vapor.desktop", "com.valve.vgui.desktop"):
        base = f"usr/share/plasma/look-and-feel/{style}/contents/splash"
        replace(root, f"{base}/Splash.qml", {
            'source: "images/bazzite_logo.svgz"':
            'source: "file:///usr/share/pixmaps/system-logo-white.png"',
        })
        remove_file(root, f"{base}/images/bazzite_logo.svgz")

    # kde-settings-plasma keeps a few Fedora menu scripts after the look-and-feel RPM is removed.
    for style in ("fedora", "fedoradark", "fedoralight"):
        remove_directory(root, f"usr/share/plasma/look-and-feel/org.fedoraproject.{style}.desktop")

    # desktop-backgrounds-kde owns compatibility links independently of f45-backgrounds-kde.
    remove_file(root, "usr/share/wallpapers/Fedora")
    default_wallpaper = within_root(root, "usr/share/wallpapers/Default")
    if default_wallpaper.is_symlink():
        default_wallpaper.unlink()
    elif default_wallpaper.exists():
        raise ValueError("expected Default wallpaper link")
    default_wallpaper.symlink_to("ForjaOS")
    rebrand_login_art(root)
    rebrand_first_login_launcher(root)

    # The inherited updater is retained for CLI compatibility but hidden from the menu.
    updater = "usr/share/applications/io.github.rfrench3.bazzite-updater.desktop"
    updater_path = within_root(root, updater)
    source = updater_path.read_text(encoding="utf-8")
    if "NoDisplay=true" not in source:
        updater_path.write_text(source.replace("[Desktop Entry]", "[Desktop Entry]\nNoDisplay=true", 1), encoding="utf-8")
    remove_file(root, "usr/share/icons/hicolor/scalable/apps/io.github.rfrench3.bazzite-updater.svg")

    icons = within_root(root, "usr/share/icons/hicolor")
    for path in icons.rglob("*"):
        if path.is_file() and path.name.startswith("bazzite-logo"):
            remove_file(root, path.relative_to(root).as_posix())
    for relative in VISIBLE_WALLPAPERS:
        remove_file(root, relative)
    remove_directory(root, "usr/share/wallpapers/bazzite")
    remove_inherited_apps(root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    configure(args.root.resolve())


if __name__ == "__main__":
    main()
