#!/usr/bin/env python3
"""Add ForjaOS signature trust to a disposable Bazzite VM disk config."""

import argparse
import json
import tomllib
from pathlib import Path


REGISTRY = "ghcr.io/forjaos-project"
KEY_PATH = "/etc/pki/containers/forjaos.pub"
POLICY_PATH = "/etc/containers/policy.json"
REGISTRY_CONFIG_PATH = "/etc/containers/registries.d/forjaos-project.yaml"
REGISTRY_CONFIG = (
    "docker:\n"
    f"  {REGISTRY}:\n"
    "    use-sigstore-attachments: true\n"
)
BASE_CONFIG = Path(__file__).with_name("ci-guest-agent.toml")


def render(base_policy_text: str, public_key: str, base_config_text: str) -> str:
    """Preserve upstream rules and add a single signed ForjaOS namespace."""
    policy = json.loads(base_policy_text)
    default = policy.get("default") if isinstance(policy, dict) else None
    transports = policy.get("transports") if isinstance(policy, dict) else None
    docker = transports.get("docker") if isinstance(transports, dict) else None
    if not isinstance(default, list) or not default or any(
        not isinstance(rule, dict) or rule.get("type") != "reject" for rule in default
    ):
        raise ValueError("Bazzite default signature policy must reject unsigned images")
    if not isinstance(docker, dict) or REGISTRY in docker:
        raise ValueError("Bazzite docker policy is missing or already owns the ForjaOS namespace")
    if not (
        public_key.startswith("-----BEGIN PUBLIC KEY-----\n")
        and "-----END PUBLIC KEY-----" in public_key
    ):
        raise ValueError("ForjaOS public key is not a PEM public key")

    config = tomllib.loads(base_config_text)
    files = config.get("customizations", {}).get("files")
    if not isinstance(files, list) or [file.get("path") for file in files] != [
        "/etc/systemd/system/qemu-guest-agent.service.d/90-forja-vm-ci.conf"
    ]:
        raise ValueError("unexpected disposable VM base config")

    docker[REGISTRY] = [{
        "type": "sigstoreSigned",
        "keyPath": KEY_PATH,
        "signedIdentity": {"type": "matchRepository"},
    }]
    additions = []
    for path in ("/etc/pki/containers", "/etc/containers/registries.d"):
        additions.append(f"[[customizations.directories]]\npath = {json.dumps(path)}")
    for path, data in (
        (POLICY_PATH, json.dumps(policy, indent=2) + "\n"),
        (KEY_PATH, public_key),
        (REGISTRY_CONFIG_PATH, REGISTRY_CONFIG),
    ):
        additions.append(
            f"[[customizations.files]]\npath = {json.dumps(path)}\n"
            f"data = {json.dumps(data)}"
        )
    return base_config_text.rstrip() + "\n\n" + "\n\n".join(additions) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-policy", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        render(
            args.base_policy.read_text(encoding="utf-8"),
            args.public_key.read_text(encoding="utf-8"),
            BASE_CONFIG.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
