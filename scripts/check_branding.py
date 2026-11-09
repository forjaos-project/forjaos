#!/usr/bin/env python3
"""Inspect a ForjaOS rootfs for inherited branding on user-visible surfaces."""

import argparse
import json
from pathlib import Path
import re
import subprocess


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
    "usr/share/plasma/look-and-feel",
    "usr/share/kde-settings",
    "usr/share/icons/hicolor",
    "etc/flatpak/remotes.d",
    "usr/share/flatpak/remotes.d",
    "var/lib/flatpak/repo/config",
)
TEXT_SUFFIXES = {"", ".conf", ".desktop", ".ini", ".json", ".plymouth", ".qml", ".svg", ".theme", ".txt", ".xml"}
LEGAL_PARTS = {"licenses", "doc", "man"}


def finding(kind, path, value, line=None):
    item = {"kind": kind, "path": path, "value": value}
    if line is not None:
        item["line"] = line
    return item


def read_root_file(root, relative):
    """Follow absolute rootfs symlinks inside the selected root, not on the host."""
    current = root / relative
    for _ in range(8):
        if not current.is_symlink():
            break
        target = current.readlink()
        current = root / str(target).lstrip("/") if target.is_absolute() else current.parent / target
    return current.read_bytes()


def check_identity(root, findings):
    try:
        lines = read_root_file(root, "etc/os-release").decode("utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        findings.append(finding("inspection", "/etc/os-release", str(error)))
        return
    fields = {}
    for line in lines:
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            fields[key] = value.strip().strip('"\'')
    expected = {"NAME": "ForjaOS", "ID": "forjaos"}
    for key, value in expected.items():
        if fields.get(key) != value:
            findings.append(finding("identity", "/etc/os-release", f"{key}={fields.get(key, '<missing>')}"))
    pretty = fields.get("PRETTY_NAME", "")
    if not (pretty == "ForjaOS" or pretty.startswith("ForjaOS ")):
        findings.append(finding("identity", "/etc/os-release", f"PRETTY_NAME={pretty or '<missing>'}"))


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


def visible_files(root):
    for relative in VISIBLE_PATHS:
        path = root / relative
        if path.is_file() or path.is_symlink():
            yield path
        elif path.is_dir():
            yield from (candidate for candidate in path.rglob("*") if candidate.is_file() or candidate.is_symlink())


def check_visible(root, findings):
    for path in visible_files(root):
        relative = path.relative_to(root)
        if LEGAL_PARTS.intersection(relative.parts):
            continue
        display = "/" + relative.as_posix()
        if BRAND.search(display):
            findings.append(finding("path", display, "inherited brand in visible path"))
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
