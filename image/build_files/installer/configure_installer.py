#!/usr/bin/env python3
"""Configure an interactive Anaconda ISO for a signed remote ForjaOS digest."""

import argparse
import json
import re
from pathlib import Path


SOURCE_RE = re.compile(r"ghcr\.io/forjaos-project/(forjaos|forjaos-nvidia-open)@sha256:[0-9a-f]{64}\Z")
TARGET_RE = re.compile(r"ghcr\.io/forjaos-project/(forjaos|forjaos-nvidia-open):(testing|stable)\Z")
KEY_PATH = "/etc/pki/containers/forjaos.pub"


def write(root: Path, path: str, content: str) -> None:
    destination = root / path.lstrip("/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def configure(root: Path, source: str, target: str, public_key: Path) -> None:
    source_match = SOURCE_RE.fullmatch(source)
    target_match = TARGET_RE.fullmatch(target)
    if source_match is None or target_match is None or source_match.group(1) != target_match.group(1):
        raise ValueError("source and target must name the same ForjaOS variant; source must use sha256")
    key = public_key.read_text(encoding="utf-8")
    if not key.startswith("-----BEGIN PUBLIC KEY-----\n") or "-----END PUBLIC KEY-----" not in key:
        raise ValueError("invalid ForjaOS public key")

    policy = {
        "default": [{"type": "reject"}],
        "transports": {"docker": {"ghcr.io/forjaos-project": [{
            "type": "sigstoreSigned",
            "keyPath": KEY_PATH,
            "signedIdentity": {"type": "matchRepository"},
        }]}},
    }
    write(root, "/etc/containers/policy.json", json.dumps(policy, indent=2) + "\n")
    write(root, KEY_PATH, key)
    write(root, "/etc/containers/registries.d/forjaos-project.yaml",
          "docker:\n  ghcr.io/forjaos-project:\n    use-sigstore-attachments: true\n")
    write(root, "/usr/lib/bootc/install/90-forjaos-signature.toml",
          "[install]\nenforce-container-sigpolicy = true\n")
    write(root, "/usr/share/anaconda/interactive-defaults.ks",
          "# Interactive install: storage and user choices remain in Anaconda.\n"
          f"bootc --source-imgref registry:{source} --target-imgref {target}\n")
    # Fedora's default ExecStart invokes tmux directly from init_t, which is
    # denied for screen_exec_t under enforcing. The shell enters initrc_t.
    write(root, "/usr/lib/systemd/system/anaconda.service.d/10-forjaos-tmux.conf",
          "[Service]\nExecStart=\n"
          "ExecStart=/usr/bin/sh -c '/usr/bin/tmux -u -f /usr/share/anaconda/tmux.conf start'\n")
    write(root, "/usr/lib/image-builder/bootc/iso.yaml",
          'label: "ForjaOS-Installer"\n'
          'grub2:\n  timeout: 5\n  entries:\n    - name: "Instalar ForjaOS"\n'
          '      linux: ${kernelpath} root=live:CDLABEL=ForjaOS-Installer rd.live.image inst.graphical\n'
          '      initrd: ${initrdpath}\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    args = parser.parse_args()
    configure(args.root, args.source, args.target, args.public_key)


if __name__ == "__main__":
    main()
