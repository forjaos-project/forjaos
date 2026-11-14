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
ALIASES = {"guara": "Guará", "tupa": "Tupã", "jaci": "Jaci", "iara": "Iara",
           "ipe": "Ipê", "boto": "Boto", "curio": "Curió", "arara": "Arara"}
CONFIG = Path.home() / ".config" / "forjaos"
BREW = Path.home() / ".brew" / "bin" / "brew"


def run(command, *, input_text=None):
    try:
        return subprocess.run(command, input=input_text, text=True, check=False)
    except OSError:
        return None


def configure_git_credentials():
    result = run(["git", "config", "--global", "--replace-all", "credential.helper", "libsecret"])
    if result is None or result.returncode:
        return False
    CONFIG.mkdir(mode=0o700, parents=True, exist_ok=True)
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    ssh_config = ssh_dir / "config"
    include = "Include ~/.config/forjaos/ssh.conf"
    existing = ssh_config.read_text(encoding="utf-8") if ssh_config.exists() else ""
    if include not in existing.splitlines():
        ssh_config.write_text(include + "\n" + existing, encoding="utf-8")
        os.chmod(ssh_config, 0o600)
    ssh_settings = CONFIG / "ssh.conf"
    ssh_settings.write_text(
        "Host *\n    AddKeysToAgent yes\n    IdentityAgent "
        f"/run/user/{os.getuid()}/forjaos-ssh-agent.sock\n",
        encoding="utf-8",
    )
    os.chmod(ssh_settings, 0o600)
    agent_unit = Path.home() / ".config/systemd/user/forjaos-ssh-agent.service"
    agent_unit.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    agent_unit.write_text(
        "[Unit]\nDescription=ForjaOS SSH agent\n\n[Service]\nType=simple\n"
        "Environment=SSH_AUTH_SOCK=%t/forjaos-ssh-agent.sock\n"
        "ExecStart=/usr/bin/ssh-agent -D -a %t/forjaos-ssh-agent.sock\n"
        "Restart=on-failure\n\n[Install]\nWantedBy=default.target\n",
        encoding="utf-8",
    )
    os.chmod(agent_unit, 0o600)
    result = run(["systemctl", "--user", "daemon-reload"])
    if result is None or result.returncode:
        return False
    result = run(["systemctl", "--user", "enable", "--now", "forjaos-ssh-agent.service"])
    return result is not None and result.returncode == 0


def configure_github_credential():
    username = subprocess.run(["gh", "api", "user", "--jq", ".login"],
                              capture_output=True, text=True, check=False)
    token = subprocess.run(["gh", "auth", "token"], capture_output=True,
                           text=True, check=False)
    if username.returncode or token.returncode or not username.stdout.strip() or not token.stdout.strip():
        return False
    credential = ("protocol=https\nhost=github.com\nusername=" + username.stdout.strip()
                  + "\npassword=" + token.stdout.strip() + "\n\n")
    stored = subprocess.run(["git", "credential", "approve"], input=credential,
                            text=True, capture_output=True, check=False)
    credential = ""
    return stored.returncode == 0


def configure_shell():
    zshrc = Path.home() / ".zshrc"
    block = "\n".join((
        "# ForjaOS developer shell",
        "command -v starship >/dev/null && eval \"$(starship init zsh)\"",
        "command -v zoxide >/dev/null && eval \"$(zoxide init zsh)\"",
        "command -v atuin >/dev/null && eval \"$(atuin init zsh)\"",
        "command -v fzf >/dev/null && source <(fzf --zsh)",
        "export SSH_AUTH_SOCK=\"$XDG_RUNTIME_DIR/forjaos-ssh-agent.sock\"",
        "export SSH_ASKPASS=/usr/bin/ksshaskpass",
        "export SSH_ASKPASS_REQUIRE=prefer",
    ))
    existing = zshrc.read_text(encoding="utf-8") if zshrc.exists() else ""
    if "# ForjaOS developer shell" not in existing:
        separator = "" if not existing or existing.endswith("\n") else "\n"
        zshrc.write_text(existing + separator + block + "\n", encoding="utf-8")
        os.chmod(zshrc, 0o600)
    profile = Path.home() / ".config/konsolerc"
    profile.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lines = profile.read_text(encoding="utf-8").splitlines() if profile.exists() else []
    try:
        section = lines.index("[Desktop Entry]")
        end = next((index for index in range(section + 1, len(lines))
                    if lines[index].startswith("[")), len(lines))
        setting = next((index for index in range(section + 1, end)
                        if lines[index].startswith("DefaultProfile=")), None)
        if setting is None:
            lines.insert(end, "DefaultProfile=ForjaOS.profile")
        else:
            lines[setting] = "DefaultProfile=ForjaOS.profile"
    except ValueError:
        lines = ["[Desktop Entry]", "DefaultProfile=ForjaOS.profile", *lines]
    profile.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(profile, 0o600)


def private_json(path, data):
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False)
    os.chmod(temp, 0o600)
    temp.replace(path)


def notify(message):
    try:
        subprocess.run(["notify-send", "ForjaOS", message], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--mascot", required=True)
    parser.add_argument("--language", choices=["pt-BR", "en-US"], default="pt-BR")
    parser.add_argument("--keyboard", choices=["br", "us"], default="br")
    parser.add_argument("--unity", action="store_true")
    parser.add_argument("--claude-code", action="store_true")
    parser.add_argument("--github", action="store_true")
    parser.add_argument("--devcontainers", action="store_true")
    parser.add_argument("--vscode-devcontainers", action="store_true")
    parser.add_argument("--api-key", action="append", choices=["anthropic", "openai", "openrouter", "nous"], default=[])
    args = parser.parse_args()
    os.environ["PATH"] = str(BREW.parent) + os.pathsep + os.environ.get("PATH", "")
    args.mascot = ALIASES.get(args.mascot.lower(), args.mascot)
    if not 2 <= len(args.mascot) <= 24 or not all(ch.isalpha() or ch in " -'" for ch in args.mascot):
        parser.error("invalid mascot name")
    wakeword = "model_pending" if args.mascot in NAMES else "training_pending"
    CONFIG.mkdir(mode=0o700, parents=True, exist_ok=True)
    state = CONFIG / "firstboot-state.json"
    private_json(CONFIG / "firstboot.json", {"profile": args.profile, "mascot": args.mascot,
                                              "language": args.language, "keyboard": args.keyboard,
                                              "unity": args.unity, "claude_code": args.claude_code,
                                              "wakeword": wakeword})
    (CONFIG / "firstboot-complete").touch(mode=0o600)
    private_json(state, {"status": "running", "profile": args.profile, "done": 0, "total": 0})
    persona_dir = Path.home() / ".config" / "hero"
    persona_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    persona = persona_dir / "persona.toml"
    persona.write_text("name = " + json.dumps(args.mascot, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(persona, 0o600)
    if not configure_git_credentials():
        private_json(state, {"status": "failed", "profile": args.profile, "step": "git-keyring"})
        notify("Git/KWallet indisponível. Execute forja setup novamente.")
        return 1
    if args.github:
        auth = run(["gh", "auth", "status"])
        if auth is None or auth.returncode:
            auth = run(["gh", "auth", "login"])
        if auth is None or auth.returncode or not configure_github_credential():
            private_json(state, {"status": "failed", "profile": args.profile, "step": "github"})
            notify("Autenticação GitHub pendente. Execute forja setup novamente.")
            return 1
    for provider in args.api_key:
        try:
            stored = subprocess.run(["/usr/bin/python3", "/usr/libexec/forjaos/keys.py", provider], check=False)
        except OSError:
            stored = None
        if stored is None or stored.returncode:
            private_json(state, {"status": "failed", "profile": args.profile, "step": "kwallet"})
            notify("Chave não salva no KWallet. Execute forja setup novamente.")
            return 1
    brew, flatpaks = PROFILES[args.profile]
    commands = [["/usr/bin/python3", "/usr/libexec/forjaos/install_homebrew.py"]]
    commands.append(["brew", "install", "starship", "zoxide", "fzf", "atuin"])
    if brew:
        commands.append(["brew", "install", *brew])
    if args.devcontainers or args.vscode_devcontainers:
        commands.extend([
            ["brew", "install", "node"],
            ["npm", "install", "--global", "@devcontainers/cli"],
        ])
    if args.vscode_devcontainers:
        commands.append(["/usr/bin/python3", "/usr/libexec/forjaos/install_vscode_devcontainers.py"])
    if flatpaks:
        commands.append(["flatpak", "remote-add", "--user", "--if-not-exists",
                         "flathub", "https://flathub.org/repo/flathub.flatpakrepo"])
        commands.append(["flatpak", "install", "--user", "--noninteractive", "flathub", *flatpaks])
    if args.profile == "web":
        commands.append(["/usr/bin/python3", "/usr/libexec/forjaos/install_chrome.py"])
        commands.append(["/usr/bin/python3", "/usr/libexec/forjaos/install_postman.py"])
    if args.profile == "backend":
        commands.append(["podman", "pull", "docker.io/library/postgres:17"])
    if args.profile == "gamedev":
        commands.append(["/usr/bin/python3", "/usr/libexec/forjaos/install_godot_templates.py"])
    if args.profile == "devops":
        commands.append(["brew", "install", "hashicorp/tap/terraform", "awscli"])
        commands.append(["brew", "install", "--cask", "gcloud-cli", "azure-cli"])
    if args.profile == "ai":
        commands.extend([
            ["brew", "install", "node", "jupyterlab"],
            ["npm", "install", "--global", "@openai/codex"],
            ["/usr/bin/python3", "/usr/libexec/forjaos/install_hermes.py"],
        ])
    if args.unity:
        commands.append(["forja", "install", "unity", "--yes"])
    if args.claude_code:
        commands.append(["forja", "install", "claude-code", "--yes"])
    events = []
    for index, command in enumerate(commands):
        events.append({"step": command[0], "status": "running"})
        private_json(state, {"status": "running", "profile": args.profile,
                             "step": command[0], "done": index, "total": len(commands),
                             "events": events})
        try:
            result = subprocess.run(command, check=False)
        except OSError:
            result = None
        if result is None or result.returncode:
            events[-1]["status"] = "failed"
            private_json(state, {"status": "failed", "profile": args.profile,
                                 "step": command[0], "done": index, "total": len(commands),
                                 "events": events})
            notify(f"Instalação pendente em {command[0]}. Execute forja setup novamente.")
            return 1
        events[-1]["status"] = "done"
    configure_shell()
    private_json(state, {"status": "complete",
                         "profile": args.profile, "wakeword": wakeword,
                         "done": len(commands), "total": len(commands), "events": events})
    notify("Configuração concluída.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
