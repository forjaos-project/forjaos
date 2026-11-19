"""Deterministic 16 kHz log-mel features shared by training and inference."""

import numpy as np


SAMPLE_RATE = 16_000
FRAME_SAMPLES = SAMPLE_RATE * 80 // 1_000
WINDOW_SAMPLES = SAMPLE_RATE * 25 // 1_000
HOP_SAMPLES = SAMPLE_RATE * 10 // 1_000
FFT_SIZE = 512
MEL_BINS = 80


def _mel_bank() -> np.ndarray:
    def hz_to_mel(value):
        return 2595.0 * np.log10(1.0 + value / 700.0)

    def mel_to_hz(value):
        return 700.0 * (10.0 ** (value / 2595.0) - 1.0)

    edges = mel_to_hz(np.linspace(hz_to_mel(20), hz_to_mel(8000), MEL_BINS + 2))
    frequencies = np.fft.rfftfreq(FFT_SIZE, 1.0 / SAMPLE_RATE)
    bank = np.zeros((MEL_BINS, frequencies.size), dtype=np.float32)
    for index in range(MEL_BINS):
        left, center, right = edges[index : index + 3]
        rising = (frequencies - left) / (center - left)
        falling = (right - frequencies) / (right - center)
        bank[index] = np.maximum(0, np.minimum(rising, falling))
    return bank


MEL_BANK = _mel_bank()
WINDOW = np.hanning(WINDOW_SAMPLES).astype(np.float32)


class StreamingFeatures:
    def __init__(self):
        self._pending = np.empty(0, dtype=np.int16)

    def accept(self, samples: np.ndarray) -> np.ndarray:
        if samples.dtype != np.dtype("<i2") or samples.ndim != 1:
            raise ValueError("PCM deve ser mono s16le")
        data = np.concatenate((self._pending, samples))
        if data.size < WINDOW_SAMPLES:
            self._pending = data
            return np.empty((0, MEL_BINS), dtype=np.float32)
        windows = np.lib.stride_tricks.sliding_window_view(data, WINDOW_SAMPLES)[::HOP_SAMPLES]
        frames = np.asarray(windows, dtype=np.float32)
        frames = (frames - frames.mean(axis=1, keepdims=True)) * WINDOW
        spectrum = np.fft.rfft(frames, n=FFT_SIZE, axis=1)
        power = (spectrum.real ** 2 + spectrum.imag ** 2).astype(np.float32)
        features = np.log(np.maximum(power @ MEL_BANK.T, 1e-10)).astype(np.float32)
        self._pending = data[windows.shape[0] * HOP_SAMPLES :].copy()
        return features


def extract(samples: np.ndarray) -> np.ndarray:
    """Use the same feature extraction for offline training samples."""
    return StreamingFeatures().accept(samples)
