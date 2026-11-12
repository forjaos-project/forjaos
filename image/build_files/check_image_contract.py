#!/usr/bin/env python3
"""Check scoped F1-001 package and service defaults inside a built image."""

import subprocess
import sys


REQUIRED_RPMS = frozenset({
    "audit",
    "btop",
    "cockpit-bridge",
    "cockpit-system",
    "distrobox",
    "firewalld",
    "forjaos-branding",
    "git-core",
    "nvtop",
    "podman",
    "python3",
    "steam",
    "steam-devices",
})
REMOVED_RPMS = frozenset({"waydroid", "waydroid-selinux"})
REQUIRED_UNIT_STATES = {
    "firewalld.service": "enabled",
    "auditd.service": "enabled",
    "sshd.service": "disabled",
    "cockpit.socket": "disabled",
}


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
    for package in sorted(REQUIRED_RPMS - packages):
        errors.append(f"required RPM missing: {package}")
    for package in sorted(REMOVED_RPMS & packages):
        errors.append(f"unwanted RPM retained: {package}")
    for unit, expected in REQUIRED_UNIT_STATES.items():
        actual = unit_states.get(unit, "not-found")
        if unit == "cockpit.socket" and actual == "not-found":
            continue  # Cockpit components are present, but no listening socket exists.
        if actual != expected:
            errors.append(f"{unit}: expected {expected}, got {actual}")
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
