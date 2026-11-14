#!/usr/bin/env python3
"""Apply first-boot profile choices without persisting credentials."""

import argparse
import json
import os
from pathlib import Path
import subprocess


PROFILES = {
    "minimal": ([], []),
    "web": (["node", "pnpm"], []),
    "backend": (["openjdk", "go", "python"], ["io.dbeaver.DBeaverCommunity"]),
    "gamedev": ([], ["org.godotengine.Godot", "org.blender.Blender", "org.kde.krita"]),
    "devops": (["kubectl", "k9s", "helm", "ansible"], []),
    "ai": (["ollama"], []),
}
NAMES = {"Guará", "Tupã", "Jaci", "Iara", "Ipê", "Boto", "Curió", "Arara"}
CONFIG = Path.home() / ".config" / "forjaos"


def private_json(path, data):
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False)
    os.chmod(temp, 0o600)
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--mascot", choices=sorted(NAMES), required=True)
    parser.add_argument("--language", choices=["pt-BR", "en-US"], default="pt-BR")
    parser.add_argument("--keyboard", choices=["br", "us"], default="br")
    parser.add_argument("--unity", action="store_true")
    args = parser.parse_args()
    CONFIG.mkdir(mode=0o700, parents=True, exist_ok=True)
    state = CONFIG / "firstboot-state.json"
    private_json(state, {"status": "running", "profile": args.profile})
    persona_dir = Path.home() / ".config" / "hero"
    persona_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    persona = persona_dir / "persona.toml"
    persona.write_text(f'name = "{args.mascot}"\n', encoding="utf-8")
    os.chmod(persona, 0o600)
    brew, flatpaks = PROFILES[args.profile]
    commands = []
    if brew:
        commands.append(["brew", "install", *brew])
    if flatpaks:
        commands.append(["flatpak", "install", "--user", "--noninteractive", "flathub", *flatpaks])
    if args.unity:
        commands.append(["forja", "install", "unity", "--yes"])
    for command in commands:
        private_json(state, {"status": "running", "profile": args.profile, "step": command[0]})
        try:
            result = subprocess.run(command, check=False)
        except OSError:
            result = None
        if result is None or result.returncode:
            private_json(state, {"status": "failed", "profile": args.profile, "step": command[0]})
            return 1
    private_json(CONFIG / "firstboot.json", {"profile": args.profile, "mascot": args.mascot,
                                              "language": args.language, "keyboard": args.keyboard})
    private_json(state, {"status": "complete", "profile": args.profile})
    (CONFIG / "firstboot-complete").touch(mode=0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
