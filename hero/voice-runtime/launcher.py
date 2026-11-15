#!/usr/bin/env python3
"""Install the pinned local speech runtime and STT model on first use."""

import argparse
import fcntl
import hashlib
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


MODEL_REVISION = "536b0662742c02347bc0e980a01041f333bce120"
MODEL_REPOSITORY = "Systran/faster-whisper-small"
MODEL_FILES = {
    "config.json": (2370, "b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828"),
    "model.bin": (483_546_902, "3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671"),
    "tokenizer.json": (2_203_239, "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"),
    "vocabulary.txt": (459_861, "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913"),
}


def data_home() -> Path:
    home = Path.home()
    root = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
    if not root.is_absolute():
        raise ValueError("XDG_DATA_HOME deve ser absoluto")
    return root / "hero"


def matches(path: Path, size: int, digest: str) -> bool:
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
        return False
    hash_value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hash_value.update(block)
    return hash_value.hexdigest() == digest


def locked_directory(path: Path):
    import contextlib

    @contextlib.contextmanager
    def lock():
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock_file = path / ".install.lock"
        with lock_file.open("a+b") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    return lock()


def ensure_runtime() -> Path:
    source = Path(__file__).resolve().parent
    requirements = source / "requirements.txt"
    version = hashlib.sha256(requirements.read_bytes()).hexdigest()[:16]
    parent = data_home() / "voice-runtime"
    target = parent / version
    python = target / "bin/python"
    if python.is_file():
        return python
    with locked_directory(parent):
        if python.is_file():
            return python
        uv = shutil.which("uv")
        if not uv:
            raise RuntimeError("uv não está instalado")
        stage = parent / f".{version}.stage-{os.getpid()}-{time.monotonic_ns()}"
        try:
            subprocess.run([uv, "venv", "--python", "/usr/bin/python3.14", str(stage)], check=True, stdout=subprocess.DEVNULL)
            subprocess.run([
                uv, "pip", "sync", "--python", str(stage / "bin/python"),
                "--require-hashes", str(requirements),
            ], check=True, stdout=subprocess.DEVNULL)
            stage.rename(target)
        except Exception:
            if stage.exists():
                shutil.rmtree(stage)
            raise
    return python


def download_file(directory: Path, name: str, size: int, digest: str) -> None:
    target = directory / name
    if matches(target, size, digest):
        return
    if target.exists() or target.is_symlink():
        raise ValueError(f"modelo local divergente: {name}")
    partial = directory / f".{name}.part"
    if partial.is_symlink() or (partial.exists() and not partial.is_file()):
        raise ValueError(f"download parcial inválido: {name}")
    url = f"https://huggingface.co/{MODEL_REPOSITORY}/resolve/{MODEL_REVISION}/{name}"
    for attempt in range(3):
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"User-Agent": "ForjaOS-HERO/0.1"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                append = offset > 0 and response.status == 206
                with partial.open("ab" if append else "wb") as destination:
                    while block := response.read(1024 * 1024):
                        destination.write(block)
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            continue
        if matches(partial, size, digest):
            partial.chmod(0o600)
            partial.rename(target)
            return
        if partial.stat().st_size >= size:
            raise ValueError(f"SHA-256 do modelo divergente: {name}")
    raise RuntimeError(f"download do modelo incompleto: {name}")


def ensure_stt_model() -> Path:
    directory = data_home() / "models" / f"stt-small-{MODEL_REVISION[:12]}"
    with locked_directory(directory):
        for name, (size, digest) in MODEL_FILES.items():
            download_file(directory, name, size, digest)
    return directory


def main() -> int:
    parser = argparse.ArgumentParser(description="Inicia o worker local de voz do HERO")
    parser.add_argument("mode", choices=("tts", "stt-server"))
    parser.add_argument("--model", type=Path, help="Modelo Piper local para TTS")
    args = parser.parse_args()
    if args.mode == "tts" and not args.model:
        parser.error("--model é obrigatório para TTS")
    python = ensure_runtime()
    worker = Path(__file__).resolve().parent / "worker.py"
    model = args.model if args.mode == "tts" else ensure_stt_model()
    os.execv(str(python), [str(python), str(worker), args.mode, "--model", str(model)])
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"HERO voice: {error}", file=sys.stderr)
        raise SystemExit(1)
