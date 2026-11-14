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
# These selections are intentionally reported as partial until their full
# product recipes are delivered. A successful Flatpak/Brew command alone is
# not evidence that the PRD profile is complete.
PENDING = {
    "web": ["Chrome", "Postman"],
    "backend": ["Postgres container"],
    "gamedev": ["Godot export templates", "Aseprite license check"],
    "devops": ["Terraform", "AWS CLI", "GCP CLI", "Azure CLI"],
    "ai": ["Codex CLI", "Hermes Agent", "Jupyter", "model downloads"],
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
    parser.add_argument("--mascot", required=True)
    parser.add_argument("--language", choices=["pt-BR", "en-US"], default="pt-BR")
    parser.add_argument("--keyboard", choices=["br", "us"], default="br")
    parser.add_argument("--unity", action="store_true")
    args = parser.parse_args()
    if not 2 <= len(args.mascot) <= 24 or not all(ch.isalpha() or ch in " -'" for ch in args.mascot):
        parser.error("invalid mascot name")
    CONFIG.mkdir(mode=0o700, parents=True, exist_ok=True)
    state = CONFIG / "firstboot-state.json"
    private_json(state, {"status": "running", "profile": args.profile})
    persona_dir = Path.home() / ".config" / "hero"
    persona_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    persona = persona_dir / "persona.toml"
    persona.write_text("name = " + json.dumps(args.mascot, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(persona, 0o600)
    brew, flatpaks = PROFILES[args.profile]
    commands = []
    if brew:
        commands.append(["brew", "install", *brew])
    if flatpaks:
        commands.append(["flatpak", "install", "--user", "--noninteractive", "flathub", *flatpaks])
    if args.unity:
        commands.append(["forja", "install", "unity", "--yes"])
    for index, command in enumerate(commands):
        private_json(state, {"status": "running", "profile": args.profile,
                             "step": command[0], "done": index, "total": len(commands)})
        try:
            result = subprocess.run(command, check=False)
        except OSError:
            result = None
        if result is None or result.returncode:
            private_json(state, {"status": "failed", "profile": args.profile,
                                 "step": command[0], "done": index, "total": len(commands)})
            return 1
    wakeword = "model_pending" if args.mascot in NAMES else "training_pending"
    private_json(CONFIG / "firstboot.json", {"profile": args.profile, "mascot": args.mascot,
                                              "language": args.language, "keyboard": args.keyboard,
                                              "wakeword": wakeword})
    pending = PENDING.get(args.profile, [])
    private_json(state, {"status": "partial" if pending else "complete",
                         "profile": args.profile, "wakeword": wakeword, "pending": pending,
                         "done": len(commands), "total": len(commands)})
    (CONFIG / "firstboot-complete").touch(mode=0o600)
    return 2 if pending else 0


if __name__ == "__main__":
    raise SystemExit(main())
