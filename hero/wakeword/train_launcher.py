#!/usr/bin/env python3
"""Install the optional, hash-locked trainer and run it outside the image."""

import fcntl
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def data_home() -> Path:
    home = Path.home()
    root = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
    if not root.is_absolute():
        raise ValueError("XDG_DATA_HOME deve ser absoluto")
    return root / "hero"


def ensure_runtime() -> Path:
    source = Path("/usr/share/forjaos/wakeword-training-runtime")
    if not (source / "pyproject.toml").is_file() or not (source / "uv.lock").is_file():
        raise RuntimeError("arquivos do runtime de treino ausentes")
    parent = data_home() / "wakeword-training" / "runtime"
    target = parent / "python-3.14"
    python = target / "bin/python"
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(parent, 0o700)
    with (parent / ".install.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if python.is_file():
            return python
        uv = shutil.which("uv")
        if not uv:
            raise RuntimeError("uv não está instalado")
        stage = parent / f".python-3.14.stage-{os.getpid()}-{time.monotonic_ns()}"
        subprocess.run(
            [uv, "venv", "--python", "/usr/bin/python3.14", str(stage)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        environment = os.environ.copy()
        environment["UV_PROJECT_ENVIRONMENT"] = str(stage)
        subprocess.run(
            [uv, "sync", "--locked", "--no-dev", "--project", str(source)],
            check=True,
            env=environment,
            stdout=subprocess.DEVNULL,
        )
        stage.rename(target)
        fcntl.flock(lock, fcntl.LOCK_UN)
    return python


if __name__ == "__main__":
    trainer = Path("/usr/share/forjaos/wakeword/train.py")
    if not trainer.is_file():
        raise SystemExit("treinador de wake word não está instalado")
    try:
        python = ensure_runtime()
        os.execv(python, [str(python), str(trainer), *sys.argv[1:]])
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as error:
        print(f"Treino de wake word: {error}", file=sys.stderr)
        raise SystemExit(1)
