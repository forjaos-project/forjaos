#!/usr/bin/env python3
"""Install Microsoft's optional VS Code tarball and the Dev Containers extension for one user."""

import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import urlopen


DOWNLOAD = "https://update.code.visualstudio.com/latest/linux-x64/stable"
EXTENSION = "ms-vscode-remote.remote-containers"
HOME = Path.home()
INSTALL_ROOT = HOME / ".local/opt/vscode"
BIN_DIR = HOME / ".local/bin"


def validate_archive(archive: tarfile.TarFile) -> None:
    roots = set()
    for member in archive.getmembers():
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("O arquivo VS Code contém um caminho inseguro.")
        roots.add(path.parts[0])
        if member.isdev() or member.isfifo():
            raise ValueError("O arquivo VS Code contém um tipo de arquivo não permitido.")
        if member.issym() or member.islnk():
            target = PurePosixPath(member.linkname)
            if target.is_absolute() or ".." in target.parts:
                raise ValueError("O arquivo VS Code contém um link inseguro.")
    if roots != {"VSCode-linux-x64"}:
        raise ValueError("O pacote baixado não tem a estrutura Linux x64 esperada.")


def download_archive(path: Path) -> None:
    with urlopen(DOWNLOAD, timeout=60) as response, path.open("wb") as target:
        shutil.copyfileobj(response, target)


def install() -> Path:
    INSTALL_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    if INSTALL_ROOT.is_symlink():
        raise ValueError("O diretório do VS Code não pode ser um link simbólico.")
    with tempfile.TemporaryDirectory(prefix=".download-", dir=INSTALL_ROOT) as temporary:
        temporary = Path(temporary)
        archive_path = temporary / "vscode.tar.gz"
        download_archive(archive_path)
        with tarfile.open(archive_path, "r:gz") as archive:
            validate_archive(archive)
            try:
                archive.extractall(temporary, filter="data")
            except TypeError:
                # validate_archive enforces traversal and link safety on Python < 3.12.
                archive.extractall(temporary)
        extracted = temporary / "VSCode-linux-x64"
        metadata = json.loads((extracted / "resources/app/package.json").read_text(encoding="utf-8"))
        version = metadata.get("version", "")
        if not version or any(character not in "0123456789.-" for character in version):
            raise ValueError("A versão do pacote VS Code é inválida.")
        installed = INSTALL_ROOT / version
        if installed.exists():
            if installed.is_symlink() or not (installed / "code").is_file():
                raise ValueError("A instalação existente do VS Code não é válida.")
        else:
            shutil.move(str(extracted), str(installed))

    code = installed / "code"
    if not code.is_file():
        raise ValueError("O pacote VS Code não contém o executável code.")
    BIN_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    launcher = BIN_DIR / "code"
    if launcher.exists() and not launcher.is_symlink():
        raise ValueError("~/.local/bin/code já existe e não será substituído.")
    if launcher.is_symlink():
        previous = launcher.resolve(strict=False)
        if INSTALL_ROOT.resolve() not in previous.parents:
            raise ValueError("~/.local/bin/code aponta para um destino alheio; não será substituído.")
    temporary_link = BIN_DIR / f".code-{os.getpid()}.tmp"
    temporary_link.symlink_to(code)
    os.replace(temporary_link, launcher)
    result = subprocess.run([str(code), "--install-extension", EXTENSION], check=False)
    if result.returncode:
        raise RuntimeError("O VS Code foi instalado, mas o Marketplace não instalou a extensão Dev Containers.")
    return code


def main() -> int:
    if os.geteuid() == 0:
        print("O VS Code deve ser instalado pelo usuário, nunca como root.", file=sys.stderr)
        return 1
    try:
        code = install()
    except Exception as error:
        print(f"Instalação opcional do VS Code falhou: {error}", file=sys.stderr)
        return 1
    print(f"VS Code e extensão Dev Containers instalados para o usuário: {code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
