#!/usr/bin/env python3
"""Apply the minimal ForjaOS identity and signature policy to a bootc rootfs."""

import argparse
import json
from pathlib import Path


REGISTRY = "ghcr.io/forjaos-project"
KEY_DESTINATION = "/etc/pki/containers/forjaos.pub"
PROJECT_URL = "https://github.com/forjaos-project/forjaos"
ISSUES_URL = f"{PROJECT_URL}/issues"
REGISTRIES_D = "/etc/containers/registries.d/forjaos-project.yaml"
# cosign guarda a assinatura como anexo OCI; sem isto a regra sigstoreSigned não a encontra.
REGISTRIES_D_CONTENT = f"docker:\n  {REGISTRY}:\n    use-sigstore-attachments: true\n"


def update_os_release(source: str, image_name: str) -> str:
    """Replace project identity, keeping unrelated base and bootc metadata."""
    replacements = {
        "NAME": '"ForjaOS"',
        "VERSION": '"0.1"',
        "ID": "forjaos",
        "ID_LIKE": "fedora",
        "VERSION_ID": "0.1",
        "PRETTY_NAME": '"ForjaOS 0.1"',
        "HOME_URL": f'"{PROJECT_URL}"',
        "DOCUMENTATION_URL": f'"{PROJECT_URL}"',
        "SUPPORT_URL": f'"{ISSUES_URL}"',
        "BUG_REPORT_URL": f'"{ISSUES_URL}"',
        "DEFAULT_HOSTNAME": '"forjaos"',
        "BOOTLOADER_NAME": '"ForjaOS 0.1"',
        "VARIANT_ID": image_name,
        "IMAGE_ID": f'"{image_name}-0.1"',
    }
    removed = {"LOGO", "CPE_NAME"}
    result = []
    seen = set()
    for line in source.splitlines():
        key = line.partition("=")[0]
        if key in removed:
            continue
        if key in replacements:
            if key not in seen:
                result.append(f"{key}={replacements[key]}")
                seen.add(key)
            continue
        result.append(line)
    result.extend(f"{key}={value}" for key, value in replacements.items() if key not in seen)
    return "\n".join(result) + "\n"


def configure(root: Path, public_key: Path, image_name: str) -> None:
    release_path = root / "usr/lib/os-release"
    policy_path = root / "etc/containers/policy.json"
    release = release_path.read_text(encoding="utf-8")
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    key_data = public_key.read_bytes()
    if not (key_data.startswith(b"-----BEGIN PUBLIC KEY-----") and b"-----END PUBLIC KEY-----" in key_data):
        raise ValueError("public key is not a PEM public key")
    if not isinstance(policy, dict) or not isinstance(policy.get("default"), list):
        raise ValueError("base signature policy is missing its default rules")
    transports = policy.get("transports")
    if not isinstance(transports, dict) or not isinstance(transports.get("docker"), dict):
        raise ValueError("base signature policy is missing docker transport rules")

    # Escopo de namespace: cobre todas as variantes ForjaOS; matchRepository ainda exige
    # que a assinatura seja do repositório efetivamente baixado.
    transports["docker"][REGISTRY] = [
        {
            "type": "sigstoreSigned",
            "keyPath": KEY_DESTINATION,
            "signedIdentity": {"type": "matchRepository"},
        }
    ]
    destination = root / KEY_DESTINATION.lstrip("/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(key_data)
    registries = root / REGISTRIES_D.lstrip("/")
    registries.parent.mkdir(parents=True, exist_ok=True)
    registries.write_text(REGISTRIES_D_CONTENT, encoding="utf-8")
    release_path.write_text(update_os_release(release, image_name), encoding="utf-8")
    policy_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--image-name", choices=("forjaos", "forjaos-nvidia-open"), required=True)
    args = parser.parse_args()
    try:
        configure(args.root, args.public_key, args.image_name)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"configure-image: {exc}\n")


if __name__ == "__main__":
    main()
