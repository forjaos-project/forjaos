#!/usr/bin/env python3
"""Validate installer ISO size and create/check a sha256sum-compatible manifest."""

import argparse
import hashlib
import re
import sys
from pathlib import Path


MAX_ISO_BYTES = 6_000_000_000  # NFR-011 uses decimal GB.
ISO_NAMES = {"forjaos.iso", "forjaos-nvidia-open.iso"}
MANIFEST_LINE = re.compile(r"([0-9a-f]{64})  (forjaos(?:-nvidia-open)?\.iso)")


def digest_iso(path: Path) -> str:
    if path.name not in ISO_NAMES or not path.is_file():
        raise ValueError(f"missing or unexpected ISO: {path}")
    size = path.stat().st_size
    if size == 0 or size > MAX_ISO_BYTES:
        raise ValueError(f"ISO size must be greater than zero and at most 6 GB: {size} bytes")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create(iso: Path) -> None:
    checksum = digest_iso(iso)
    manifest = iso.parent / "SHA256SUMS"
    manifest.write_text(f"{checksum}  {iso.name}\n", encoding="ascii")
    check(manifest)
    print(f"verify-iso: {iso.name}: {iso.stat().st_size} bytes, sha256:{checksum}")


def check(manifest: Path) -> None:
    if not manifest.is_file():
        raise ValueError(f"missing SHA256SUMS: {manifest}")
    lines = manifest.read_text(encoding="ascii").splitlines()
    if not lines or len(lines) > len(ISO_NAMES):
        raise ValueError("SHA256SUMS must list one or two ForjaOS ISOs")
    seen = set()
    for line in lines:
        match = MANIFEST_LINE.fullmatch(line)
        if not match or match.group(2) in seen:
            raise ValueError(f"invalid SHA256SUMS line: {line}")
        expected, name = match.groups()
        seen.add(name)
        if digest_iso(manifest.parent / name) != expected:
            raise ValueError(f"SHA-256 mismatch: {name}")
        print(f"verify-iso: {name}: OK")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "check"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "create":
            create(args.path)
        else:
            check(args.path)
    except (OSError, ValueError) as error:
        print(f"verify-iso: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
