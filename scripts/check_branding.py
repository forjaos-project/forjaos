#!/usr/bin/env python3
"""Inspect a ForjaOS rootfs for inherited branding on user-visible surfaces."""

import argparse
import configparser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


BRAND = re.compile(r"fedora|bazzite|bluefin|universal[ -]blue", re.IGNORECASE)
PACKAGE = re.compile(r"^(fedora-logos|fedora-release-identity-.*|bazzite-branding.*|bluefin-.*)$", re.IGNORECASE)
VISIBLE_PATHS = (
    "etc/motd",
    "etc/issue",
    "etc/sddm.conf.d",
    "etc/default/grub",
    "etc/xdg",
    "boot/grub2/themes",
    "usr/share/plymouth/themes/default.plymouth",
    "usr/share/wallpapers",
    "usr/share/ublue-os/motd",
    "usr/share/plasma/look-and-feel",
    "usr/share/kde-settings",
    "usr/share/icons/hicolor",
    "etc/flatpak/remotes.d",
    "usr/share/flatpak/remotes.d",
    "var/lib/flatpak/repo/config",
)
TEXT_SUFFIXES = {"", ".colors", ".conf", ".css", ".desktop", ".flatpakrepo", ".ini", ".js", ".json", ".layout", ".md", ".plymouth", ".qml", ".service", ".svg", ".theme", ".txt", ".xml"}
LEGAL_PARTS = {"licenses", "doc", "man"}


def finding(kind, path, value, line=None):
    item = {"kind": kind, "path": path, "value": value}
    if line is not None:
        item["line"] = line
    return item


def resolve_root_path(root, relative):
    """Resolve every component using rootfs semantics, including absolute links."""
    pending = list(Path(relative).parts)
    current = root
    hops = 0
    while pending:
        part = pending.pop(0)
        if part == "..":
            if current == root:
                raise OSError(f"symlink escapes rootfs: {relative}")
            current = current.parent
            continue
        current = current / part
        if current.is_symlink():
            hops += 1
            if hops > 40:
                raise OSError(f"symlink exceeds hop limit: {relative}")
            target = current.readlink()
            current = root if target.is_absolute() else current.parent
            pending = list(target.parts[1:] if target.is_absolute() else target.parts) + pending
    return current


def read_root_file(root, relative):
    return resolve_root_path(root, relative).read_bytes()


def check_identity(root, findings):
    try:
        lines = read_root_file(root, "etc/os-release").decode("utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        findings.append(finding("inspection", "/etc/os-release", str(error)))
        return
    fields = {}
    for number, line in enumerate(lines, 1):
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            fields[key] = value.strip().strip('"\'')
            match = BRAND.search(value)
            if key != "ID_LIKE" and match:
                findings.append(finding("text", "/etc/os-release", match.group(), number))
    expected = {"NAME": "ForjaOS", "ID": "forjaos", "ID_LIKE": "fedora"}
    for key, value in expected.items():
        if fields.get(key) != value:
            findings.append(finding("identity", "/etc/os-release", f"{key}={fields.get(key, '<missing>')}"))
    pretty = fields.get("PRETTY_NAME", "")
    if not re.fullmatch(r"ForjaOS \d+\.\d+(?:\.\d+)?", pretty):
        findings.append(finding("identity", "/etc/os-release", f"PRETTY_NAME={pretty or '<missing>'}"))
    for key in ("HOME_URL", "BUG_REPORT_URL"):
        if not re.fullmatch(r"https?://[^\s/]+(?:/[^\s]*)?", fields.get(key, "")):
            findings.append(finding("identity", "/etc/os-release", f"{key}={fields.get(key) or '<missing>'}"))


def check_packages(root, findings):
    try:
        result = subprocess.run(
            ["rpm", "--root", str(root), "-qa", "--qf", "%{NAME}\n"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        findings.append(finding("inspection", "/usr/lib/sysimage/rpm", str(error)))
        return
    if result.returncode:
        findings.append(finding("inspection", "/usr/lib/sysimage/rpm", result.stderr.strip() or f"rpm exited {result.returncode}"))
        return
    packages = {name.strip() for name in result.stdout.splitlines() if name.strip()}
    for name in sorted(packages):
        if PACKAGE.fullmatch(name):
            findings.append(finding("package", "/usr/lib/sysimage/rpm", name))
    if "forjaos-branding" not in packages:
        findings.append(finding("package", "/usr/lib/sysimage/rpm", "forjaos-branding missing"))


def visible_files(root, findings):
    def walk(relative, ancestors, optional=False):
        try:
            resolved = resolve_root_path(root, relative)
            if resolved.is_dir():
                if resolved in ancestors:
                    return  # A directory alias must not expand an ancestor indefinitely.
                for child in sorted(resolved.iterdir()):
                    yield from walk(relative / child.name, ancestors | {resolved})
            elif resolved.is_file():
                yield root / relative
            elif not optional or (root / relative).is_symlink():
                raise OSError(f"missing visible link target: {relative}")
        except OSError as error:
            findings.append(finding("inspection", "/" + relative.as_posix(), str(error)))

    for relative in VISIBLE_PATHS:
        yield from walk(Path(relative), set(), optional=True)


def check_visible(root, findings):
    try:
        identity = resolve_root_path(root, "etc/os-release")
    except OSError:
        identity = None  # check_identity already recorded this inspection error.
    for path in visible_files(root, findings):
        relative = path.relative_to(root)
        if LEGAL_PARTS.intersection(relative.parts):
            continue
        display = "/" + relative.as_posix()
        if BRAND.search(display):
            findings.append(finding("path", display, "inherited brand in visible path"))
        resolved = resolve_root_path(root, relative)
        # Identity and its ID_LIKE exception were already checked, even via aliases.
        if resolved == identity:
            continue
        if LEGAL_PARTS.intersection(resolved.relative_to(root).parts):
            continue
        target = "/" + resolved.relative_to(root).as_posix()
        if resolved != path and BRAND.search(target):
            findings.append(finding("path", display, f"inherited brand in link target: {target}"))
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            data = read_root_file(root, relative.as_posix())
        except OSError as error:
            findings.append(finding("inspection", display, str(error)))
            continue
        if b"\0" in data[:4096]:
            continue
        try:
            content = data.decode("utf-8")
        except UnicodeError:
            continue
        for number, line in enumerate(content.splitlines(), 1):
            match = BRAND.search(line)
            if match:
                findings.append(finding("text", display, match.group(), number))


def application_files(root, directory, suffix, findings):
    """Yield metadata files through the same rootfs link resolution as visible assets."""
    try:
        path = resolve_root_path(root, directory)
        if not path.exists():
            return
        if not path.is_dir():
            raise OSError("application metadata path is not a directory")
        for child in sorted(path.iterdir()):
            if child.suffix == suffix:
                yield Path(directory) / child.name
    except OSError as error:
        findings.append(finding("inspection", "/" + directory, str(error)))


def check_applications(root, findings):
    """Inspect labels/icons shown by the launcher and Discover, not internal Exec paths."""
    for relative in application_files(root, "usr/share/applications", ".desktop", findings):
        display = "/" + relative.as_posix()
        try:
            lines = read_root_file(root, relative).decode("utf-8").splitlines()
        except (OSError, UnicodeError) as error:
            findings.append(finding("inspection", display, str(error)))
            continue
        in_entry = False
        hidden = False
        labels = []
        for number, line in enumerate(lines, 1):
            if line.startswith("[") and line.endswith("]"):
                in_entry = line == "[Desktop Entry]"
                continue
            if not in_entry or "=" not in line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            if key in ("NoDisplay", "Hidden") and value.strip().lower() == "true":
                hidden = True
            if key.split("[", 1)[0] in ("Name", "GenericName", "Comment", "Keywords", "Icon"):
                match = BRAND.search(value)
                if match:
                    labels.append(finding("text", display, match.group(), number))
        if not hidden:
            findings.extend(labels)

    for relative in application_files(root, "usr/share/metainfo", ".xml", findings):
        display = "/" + relative.as_posix()
        try:
            component = ET.fromstring(read_root_file(root, relative))
        except (OSError, ET.ParseError) as error:
            findings.append(finding("inspection", display, str(error)))
            continue
        if component.tag != "component" or component.get("type") not in (
            "desktop", "desktop-application", "operating-system"
        ):
            continue
        for element in component.iter():
            if element.tag not in ("name", "summary", "description", "icon"):
                continue
            match = BRAND.search(" ".join(element.itertext()))
            if match:
                findings.append(finding("text", display, match.group()))
                break


def check_initramfs_logo(root, findings):
    """The boot splash uses a copy of the logo baked into each initramfs."""
    modules = resolve_root_path(root, "usr/lib/modules")
    if not modules.exists():
        return
    try:
        logo = read_root_file(root, "usr/share/pixmaps/system-logo-white.png")
        images = sorted(modules.glob("*/initramfs.img"))
    except OSError as error:
        findings.append(finding("inspection", "/usr/share/pixmaps/system-logo-white.png", str(error)))
        return
    for image in images:
        display = "/" + image.relative_to(root).as_posix()
        try:
            result = subprocess.run(
                ["lsinitrd", "-f", "usr/share/pixmaps/system-logo-white.png", str(image)],
                capture_output=True,
                check=False,
            )
        except OSError as error:
            findings.append(finding("inspection", display, str(error)))
            continue
        if result.returncode:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            findings.append(finding("inspection", display, detail or f"lsinitrd exited {result.returncode}"))
        elif result.stdout != logo:
            findings.append(finding("image", display, "boot splash logo differs from ForjaOS rootfs logo"))


def check_login_wallpapers(root, findings):
    """Plasma Login and the lock screen must resolve to project-owned artwork."""
    section = "Greeter][Wallpaper][org.kde.image][General"
    owned = root / "usr/share/wallpapers/ForjaOS"
    for relative in ("usr/lib/plasmalogin/defaults.conf", "etc/xdg/kscreenlockerrc"):
        display = "/" + relative
        try:
            path = resolve_root_path(root, relative)
            if not path.exists():
                continue
            config = configparser.ConfigParser(interpolation=None)
            config.read_string(read_root_file(root, relative).decode("utf-8"))
            for key in ("Image", "PreviewImage"):
                value = config.get(section, key)
                uri = urlparse(value)
                if uri.scheme not in ("", "file") or uri.netloc or not uri.path.startswith("/"):
                    raise ValueError(f"unsupported {key} path: {value}")
                target = resolve_root_path(root, uri.path.lstrip("/"))
                if not target.is_file() or not target.is_relative_to(owned):
                    findings.append(finding("image", display, f"{key} resolves outside ForjaOS artwork: {value}"))
                    break
        except (OSError, UnicodeError, ValueError, configparser.Error) as error:
            findings.append(finding("inspection", display, str(error)))


def check_first_login_launcher(root, findings):
    """The selected look-and-feel can override the kickoff icon on a new account."""
    config_path = resolve_root_path(root, "etc/xdg/kdeglobals")
    if not config_path.is_file():
        return
    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read_string(read_root_file(root, "etc/xdg/kdeglobals").decode("utf-8"))
        package = config.get("KDE", "LookAndFeelPackage", fallback="")
        if not package:
            return
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", package):
            raise ValueError(f"unexpected look-and-feel package: {package}")
        relative = f"usr/share/plasma/look-and-feel/{package}/contents/plasmoidsetupscripts/org.kde.plasma.kickoff.js"
        setup = resolve_root_path(root, relative)
        if not setup.is_file():
            return
        content = read_root_file(root, relative).decode("utf-8")
        icon = re.search(r'writeConfig\s*\(\s*["\']icon["\']\s*,\s*["\']([^"\']+)["\']', content)
        if icon and icon.group(1) != "start-here":
            findings.append(finding("image", "/" + relative, f"first-login launcher icon: {icon.group(1)}"))
    except (OSError, UnicodeError, ValueError, configparser.Error) as error:
        findings.append(finding("inspection", "/etc/xdg/kdeglobals", str(error)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.rootfs.resolve()
    findings = []
    if not root.is_dir():
        findings.append(finding("inspection", str(root), "rootfs is not a directory"))
    else:
        check_identity(root, findings)
        check_packages(root, findings)
        check_visible(root, findings)
        check_applications(root, findings)
        check_initramfs_logo(root, findings)
        check_login_wallpapers(root, findings)
        check_first_login_launcher(root, findings)
    findings.sort(key=lambda item: (item["path"], item.get("line", 0), item["kind"], item["value"]))
    status = "error" if any(item["kind"] == "inspection" for item in findings) else "fail" if findings else "ok"
    report = {"status": status, "findings": findings}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(f"check-branding: {status} ({len(findings)} finding(s))")
        for item in findings:
            location = item["path"] + (f":{item['line']}" if "line" in item else "")
            print(f"{location}: {item['kind']}: {item['value']}")
    return {"ok": 0, "fail": 1, "error": 2}[status]


if __name__ == "__main__":
    raise SystemExit(main())
