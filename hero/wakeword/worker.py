#!/usr/bin/env python3
"""Read 80 ms PCM frames and report local wake-word detections on stdout."""

import argparse
import math
import sys
from pathlib import Path


FRAME_BYTES = 16_000 * 2 * 80 // 1000


def regular_model(path: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"modelo local ausente: {path}")
    return path.resolve(strict=True)


def valid_threshold(value: str) -> float:
    threshold = float(value)
    if not math.isfinite(threshold) or not 0 < threshold < 1:
        raise argparse.ArgumentTypeError("sensibilidade deve estar entre 0 e 1")
    return threshold


def run(model, source, destination, threshold: float) -> None:
    import numpy as np

    armed = True
    while frame := source.read(FRAME_BYTES):
        if len(frame) != FRAME_BYTES:
            raise ValueError("quadro PCM incompleto")
        scores = model.predict(np.frombuffer(frame, dtype="<i2"))
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in scores.values()):
            raise ValueError("pontuação wake word inválida")
        score = max(scores.values(), default=0)
        if score >= threshold and armed:
            destination.write(b"wake\n")
            destination.flush()
            armed = False
        elif score < threshold * 0.5:
            armed = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Detecta wake word local em PCM mono 16 kHz")
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--melspec", required=True, type=Path)
    parser.add_argument("--embedding", required=True, type=Path)
    parser.add_argument("--threshold", type=valid_threshold, default=0.5)
    args = parser.parse_args()
    model_path = regular_model(args.model)
    melspec_path = regular_model(args.melspec)
    embedding_path = regular_model(args.embedding)

    from openwakeword.model import Model

    model = Model(
        wakeword_models=[str(model_path)],
        inference_framework="onnx",
        melspec_model_path=str(melspec_path),
        embedding_model_path=str(embedding_path),
    )
    run(model, sys.stdin.buffer, sys.stdout.buffer, args.threshold)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, ImportError) as error:
        print(f"HERO wake word: {error}", file=sys.stderr)
        raise SystemExit(1)
