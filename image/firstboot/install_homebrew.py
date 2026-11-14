#!/usr/bin/env python3
"""Install the official Homebrew bootstrap into a user-owned Linux prefix."""

import os
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen


INSTALLER = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
HOME = Path.home()
PREFIX = HOME / ".brew"
BREW = PREFIX / "bin/brew"
INIT = 'eval "$("$HOME/.brew/bin/brew" shellenv)"'


def add_shell_init(path: Path) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if INIT not in current.splitlines():
        separator = "" if not current or current.endswith("\n") else "\n"
        path.write_text(current + separator + INIT + "\n", encoding="utf-8")
        os.chmod(path, 0o600)


def main() -> int:
    if os.geteuid() == 0:
        print("Homebrew deve ser instalado pelo usuário, nunca como root.", file=sys.stderr)
        return 1
    if len(os.fsencode(PREFIX)) > 26:
        print("O caminho do Homebrew excede o limite de 26 bytes para prefixos Linux compatíveis.",
              file=sys.stderr)
        return 1
    if PREFIX.is_symlink() or (PREFIX.exists() and not PREFIX.is_dir()):
        print("O prefixo do Homebrew existe e não é um diretório seguro.", file=sys.stderr)
        return 1
    if not BREW.exists():
        try:
            with urlopen(INSTALLER, timeout=30) as response:
                script = response.read().decode("utf-8")
        except Exception as error:  # network and TLS errors are reported without credentials
            print(f"Não foi possível baixar o instalador oficial do Homebrew: {error}", file=sys.stderr)
            return 1
        env = os.environ.copy()
        env.update({"NONINTERACTIVE": "1", "HOMEBREW_NO_SUDO": "1",
                    "HOMEBREW_NO_ANALYTICS": "1", "HOMEBREW_NO_AUTO_UPDATE": "1"})
        result = subprocess.run(["/usr/bin/bash", "-s", "--", "--path", str(PREFIX)],
                                input=script, text=True, env=env, check=False)
        if result.returncode:
            return result.returncode
    if not BREW.is_file():
        print("O instalador terminou sem criar o executável brew esperado.", file=sys.stderr)
        return 1
    add_shell_init(HOME / ".zshrc")
    add_shell_init(HOME / ".bashrc")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
