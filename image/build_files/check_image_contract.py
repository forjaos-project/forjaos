#!/usr/bin/env python3
"""Check scoped F1-001 package and service defaults inside a built image."""

import os
import subprocess
import sys
from pathlib import Path


REQUIRED_RPMS = frozenset({
    "audit",
    "btop",
    "bluez",
    "cockpit-bridge",
    "cockpit-system",
    "distrobox",
    "firewalld",
    "forjaos-branding",
    "git-core",
    "gamescope",
    "mangohud",
    "nvtop",
    "podman",
    "python3",
    "steam",
    "steam-devices",
})
REMOVED_RPMS = frozenset({"waydroid", "waydroid-selinux"})
PACKAGE_ALIASES = {
    "bluez": frozenset({"bluez", "terra-bluez"}),
    "gamescope": frozenset({"gamescope", "terra-gamescope"}),
    "mangohud": frozenset({"mangohud", "terra-mangohud"}),
}
REQUIRED_UNIT_STATES = {
    "firewalld.service": "enabled",
    "auditd.service": "enabled",
    "sshd.service": "disabled",
    "cockpit.socket": "disabled",
}
REQUIRED_EXECUTABLES = (
    "/usr/bin/forja",
    "/usr/libexec/forjaos/herod",
    "/usr/libexec/forjaos/memd",
)


def read_packages() -> set[str]:
    result = subprocess.run(
        ["rpm", "-qa", "--qf", "%{NAME}\n"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(f"RPM query failed: {result.stderr.strip() or result.returncode}")
    packages = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    if not packages:
        raise ValueError("RPM query returned no packages")
    return packages


def read_unit_state(unit: str) -> str:
    result = subprocess.run(
        ["systemctl", "is-enabled", unit],
        capture_output=True,
        text=True,
        check=False,
    )
    state = result.stdout.strip()
    if result.returncode in (0, 1) and state in ("enabled", "disabled", "masked", "static", "indirect", "enabled-runtime"):
        return state
    if result.returncode == 4 and state == "not-found":
        return state
    raise ValueError(f"systemctl query failed for {unit}: {result.stderr.strip() or state or result.returncode}")


def check_contract(packages: set[str], unit_states: dict[str, str]) -> list[str]:
    errors = []
    missing = {
        package
        for package in REQUIRED_RPMS
        if not PACKAGE_ALIASES.get(package, frozenset({package})) & packages
    }
    for package in sorted(missing):
        errors.append(f"required RPM missing: {package}")
    for package in sorted(REMOVED_RPMS & packages):
        errors.append(f"unwanted RPM retained: {package}")
    for unit, expected in REQUIRED_UNIT_STATES.items():
        actual = unit_states.get(unit, "not-found")
        if unit == "cockpit.socket" and actual == "not-found":
            continue  # Cockpit components are present, but no listening socket exists.
        if actual != expected:
            errors.append(f"{unit}: expected {expected}, got {actual}")
    for executable in REQUIRED_EXECUTABLES:
        path = Path(executable)
        if not path.is_file() or path.is_symlink() or not os.access(path, os.X_OK):
            errors.append(f"required executable missing or invalid: {executable}")
    return errors


def main() -> int:
    try:
        packages = read_packages()
        states = {unit: read_unit_state(unit) for unit in REQUIRED_UNIT_STATES}
    except (OSError, ValueError) as exc:
        print(f"image-contract: {exc}", file=sys.stderr)
        return 1
    errors = check_contract(packages, states)
    if errors:
        for error in errors:
            print(f"image-contract: {error}", file=sys.stderr)
        return 1
    print("image-contract: package and service defaults OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
