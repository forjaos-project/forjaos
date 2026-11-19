#!/usr/bin/env python3
"""Infer a project-trained WeKws ONNX model from shared 80 ms PCM frames."""

import argparse
import math
import sys
from collections import deque
from pathlib import Path

import numpy as np

from features import FRAME_SAMPLES, MEL_BINS, StreamingFeatures


FRAME_BYTES = FRAME_SAMPLES * 2
VOICE_RMS = 400
VOICE_FRAMES_REQUIRED = 4
VOICE_WINDOW_FRAMES = 8


def regular_model(path: Path) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError(f"modelo local ausente: {path}")
    return path.resolve(strict=True)


def valid_threshold(value: str) -> float:
    threshold = float(value)
    if not math.isfinite(threshold) or not 0 < threshold < 1:
        raise argparse.ArgumentTypeError("sensibilidade deve estar entre 0 e 1")
    return threshold


class WeKwsModel:
    def __init__(self, path: Path):
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
        metadata = self.session.get_modelmeta().custom_metadata_map
        if metadata.get("feature_type") != "forja-logmel-v1":
            raise ValueError("extração de features ONNX incompatível")
        cache_dim = int(metadata["cache_dim"])
        cache_len = int(metadata["cache_len"])
        if not 0 < cache_dim <= 4096 or not 0 < cache_len <= 4096:
            raise ValueError("cache ONNX inválido")
        inputs = {item.name: item for item in self.session.get_inputs()}
        outputs = {item.name: item for item in self.session.get_outputs()}
        if set(inputs) != {"input", "cache"} or set(outputs) != {"output", "r_cache"}:
            raise ValueError("assinatura ONNX incompatível")
        if inputs["input"].shape[-1] != MEL_BINS:
            raise ValueError("dimensão das features incompatível")
        self.cache = np.zeros((1, cache_dim, cache_len), dtype=np.float32)

    def predict(self, features: np.ndarray) -> float:
        if features.ndim != 2 or features.shape[1] != MEL_BINS:
            raise ValueError("features inválidas")
        if features.shape[0] == 0:
            return 0.0
        scores, next_cache = self.session.run(
            ["output", "r_cache"],
            {"input": features[np.newaxis, :, :], "cache": self.cache},
        )
        if scores.ndim != 3 or scores.shape[0] != 1 or scores.shape[2] != 1:
            raise ValueError("saída ONNX incompatível")
        if next_cache.shape != self.cache.shape or not np.isfinite(next_cache).all():
            raise ValueError("cache ONNX inválido")
        if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
            raise ValueError("pontuação wake word inválida")
        self.cache = next_cache
        return float(scores.max(initial=0.0))


def run(model, source, destination, threshold: float) -> None:
    features = StreamingFeatures()
    armed = True
    recent_voice = deque(maxlen=VOICE_WINDOW_FRAMES)
    while frame := source.read(FRAME_BYTES):
        if len(frame) != FRAME_BYTES:
            raise ValueError("quadro PCM incompleto")
        samples = np.frombuffer(frame, dtype="<i2")
        recent_voice.append(np.mean(samples.astype(np.float64) ** 2) > VOICE_RMS ** 2)
        score = model.predict(features.accept(samples))
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("pontuação wake word inválida")
        if score >= threshold and armed and sum(recent_voice) >= VOICE_FRAMES_REQUIRED:
            destination.write(b"wake\n")
            destination.flush()
            armed = False
        elif score < threshold * 0.5:
            armed = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Detecta wake word WeKws local em PCM mono 16 kHz")
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--threshold", type=valid_threshold, default=0.5)
    args = parser.parse_args()
    run(WeKwsModel(regular_model(args.model)), sys.stdin.buffer, sys.stdout.buffer, args.threshold)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, ImportError, KeyError) as error:
        print(f"HERO wake word: {error}", file=sys.stderr)
        raise SystemExit(1)
