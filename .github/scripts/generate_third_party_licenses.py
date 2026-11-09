#!/usr/bin/env python3
"""Render an inventory from RPM package and license-file query records."""

import argparse
import html
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath


@dataclass
class Package:
    name: str
    version: str
    arch: str
    license: str
    source: str
    license_files: set[str] = field(default_factory=set)


def parse_records(lines):
    packages = {}
    current = None
    for number, raw in enumerate(lines, start=1):
        fields = raw.rstrip("\n").split("\t")
        if fields[0] == "P":
            if len(fields) != 6 or any(not value.strip() for value in fields[1:]):
                raise ValueError(f"line {number}: incomplete RPM package record")
            _, name, version, arch, license_expression, source = fields
            key = (name, version, arch)
            if key in packages:
                raise ValueError(f"line {number}: duplicate RPM package {name}")
            current = Package(name, version, arch, license_expression, source)
            packages[key] = current
        elif fields[0] == "F":
            if current is None or len(fields) != 3:
                raise ValueError(f"line {number}: orphan or incomplete RPM file record")
            _, path, flags = fields
            if not path.startswith("/") or ".." in PurePosixPath(path).parts:
                raise ValueError(f"line {number}: invalid RPM file path")
            if "l" in flags:
                current.license_files.add(path)
        else:
            raise ValueError(f"line {number}: unexpected RPM record")
    if not packages:
        raise ValueError("RPM query returned no installed packages")
    return sorted(packages.values(), key=lambda item: (item.name, item.version, item.arch))


def cell(value):
    return html.escape(value, quote=False).replace("|", "\\|").replace("`", "\\`")


def render(variant, image_id, packages):
    rows = [
        f"# Third-party licenses — {variant}",
        "",
        f"Image ID: `{image_id}`  ",
        f"Inventory: {len(packages)} installed RPM packages.",
        "",
        "This report reproduces RPM license metadata and paths marked as license files in the built image. "
        "It does not copy license texts or certify legal compatibility. "
        "License files are available at the listed paths inside the image.",
        "",
        "| Package | Version-release | Arch | License metadata | Source RPM | License files in image |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for package in packages:
        files = "<br>".join(cell(path) for path in sorted(package.license_files)) or "—"
        rows.append(
            "| " + " | ".join(
                [
                    cell(package.name),
                    cell(package.version),
                    cell(package.arch),
                    cell(package.license),
                    cell(package.source),
                    files,
                ]
            ) + " |"
        )
    return "\n".join(rows) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, choices=("forjaos", "forjaos-nvidia-open"))
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    image_id = args.image_id
    if re.fullmatch(r"[0-9a-f]{64}", image_id):
        image_id = f"sha256:{image_id}"
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        parser.error("--image-id must be a sha256 image ID")

    temporary = None
    try:
        packages = parse_records(sys.stdin)
        report = render(args.variant, image_id, packages)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=args.output.parent,
            prefix=".third-party-licenses-", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(report)
        os.replace(temporary, args.output)
        print(f"third-party-licenses: wrote {len(packages)} packages to {args.output}")
    except (OSError, ValueError) as error:
        print(f"third-party-licenses: {error}", file=sys.stderr)
        return 1
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
