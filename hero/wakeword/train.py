#!/usr/bin/env python3
"""Train and gate one private WeKws wake-word model from a local WAV manifest."""

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import wave
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from features import FRAME_SAMPLES, MEL_BINS, SAMPLE_RATE, StreamingFeatures


WEKWS_REVISION = "6a45aeb994dd81c0969ff877a5a7c46d60ed0c86"
WEKWS_URL = "https://github.com/wenet-e2e/wekws.git"
PHRASES = ("Guará", "Tupã", "Jaci", "Iara", "Ipê", "Boto", "Curió", "Arara")
SPLITS = ("train", "dev", "test")
REQUIRED_COLUMNS = {"split", "label", "path", "source", "phrase", "speaker_code"}
FALSE_POSITIVE_LIMIT_PER_HOUR = 1 / 8
LATENCY_LIMIT_MS = 300
FRAME_BYTES = FRAME_SAMPLES * 2


@dataclass(frozen=True)
class Example:
    path: Path
    split: str
    label: str
    source: str
    speaker_code: str


def slug(name: str) -> str:
    folded = unicodedata.normalize("NFD", name.casefold())
    ascii_name = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    value = re.sub(r"[^a-z0-9]+", "", ascii_name)
    if not value:
        raise ValueError("nome sem caracteres utilizáveis")
    return value


def read_manifest(manifest: Path, name: str) -> list[Example]:
    root = manifest.resolve(strict=True).parent
    examples: list[Example] = []
    speakers: dict[str, str] = {}
    with manifest.open(newline="", encoding="utf-8-sig") as source:
        rows = csv.DictReader(source, delimiter="\t")
        missing = REQUIRED_COLUMNS - set(rows.fieldnames or ())
        if missing:
            raise ValueError(f"colunas ausentes no manifesto: {', '.join(sorted(missing))}")
        for line, row in enumerate(rows, start=2):
            split = (row.get("split") or "").strip()
            label = (row.get("label") or "").strip()
            source_name = (row.get("source") or "").strip()
            speaker = (row.get("speaker_code") or "").strip()
            relative = Path((row.get("path") or "").strip())
            phrase = (row.get("phrase") or "").strip()
            if split not in SPLITS or label not in {"wake", "negative"}:
                raise ValueError(f"linha {line}: split/label inválido")
            if source_name not in {"human", "piper", "common_voice", "noise"}:
                raise ValueError(f"linha {line}: origem inválida")
            if label == "wake" and phrase != name:
                raise ValueError(f"linha {line}: frase não corresponde ao nome treinado")
            if source_name != "noise" and not speaker:
                raise ValueError(f"linha {line}: áudio de fala sem código de locutor")
            if relative.is_absolute() or not relative.parts or ".." in relative.parts:
                raise ValueError(f"linha {line}: path deve ser relativo ao manifesto")
            candidate = root / relative
            if candidate.is_symlink() or not candidate.is_file():
                raise ValueError(f"linha {line}: arquivo ausente ou link simbólico")
            audio = candidate.resolve(strict=True)
            if not audio.is_relative_to(root):
                raise ValueError(f"linha {line}: arquivo fora da pasta privada")
            if source_name != "noise" and speaker:
                speaker_key = f"{source_name}:{speaker}"
                previous = speakers.setdefault(speaker_key, split)
                if previous != split:
                    raise ValueError(f"linha {line}: participante aparece em mais de uma divisão")
            examples.append(Example(audio, split, label, source_name, speaker))

    for split in SPLITS:
        split_examples = [example for example in examples if example.split == split]
        if not any(example.label == "wake" for example in split_examples):
            raise ValueError(f"manifesto sem exemplos positivos em {split}")
        if not any(example.label == "negative" for example in split_examples):
            raise ValueError(f"manifesto sem exemplos negativos em {split}")
    return examples


def load_features(example: Example) -> np.ndarray:
    try:
        with wave.open(str(example.path), "rb") as audio:
            if (
                audio.getnchannels() != 1
                or audio.getframerate() != SAMPLE_RATE
                or audio.getsampwidth() != 2
                or audio.getcomptype() != "NONE"
                or audio.getnframes() == 0
            ):
                raise ValueError("WAV deve ser PCM mono 16 kHz/16 bits e não vazio")
            samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").copy()
    except (OSError, EOFError, wave.Error) as error:
        raise ValueError(f"WAV inválido: {example.path.name}") from error
    output = StreamingFeatures().accept(samples)
    if output.shape[0] == 0 or not np.isfinite(output).all():
        raise ValueError(f"features vazias ou inválidas: {example.path.name}")
    return output


def ensure_wekws(cache_root: Path, override: Path | None) -> Path:
    if override:
        source = override.resolve(strict=True)
        actual = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if actual != WEKWS_REVISION:
            raise ValueError(f"WeKws deve estar fixado em {WEKWS_REVISION}")
        return source

    target = cache_root / "wekws" / WEKWS_REVISION
    if target.is_dir():
        actual = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if actual == WEKWS_REVISION:
            return target
        raise ValueError("código WeKws em cache diverge da revisão fixada")

    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    stage = target.parent / f".{WEKWS_REVISION}.stage-{os.getpid()}"
    subprocess.run(
        ["git", "clone", "--filter=blob:none", "--no-checkout", WEKWS_URL, str(stage)],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(stage), "checkout", "--detach", WEKWS_REVISION],
        check=True,
    )
    stage.rename(target)
    return target


def split_data(examples: list[Example], split: str):
    import torch
    from torch.nn.utils.rnn import pad_sequence

    selected = [example for example in examples if example.split == split]
    features = [torch.from_numpy(load_features(example)) for example in selected]
    lengths = torch.tensor([item.shape[0] for item in features], dtype=torch.long)
    padded = pad_sequence(features, batch_first=True)
    targets = torch.tensor([0 if item.label == "wake" else -1 for item in selected], dtype=torch.long)
    target_lengths = torch.ones(len(selected), dtype=torch.long)
    return padded, lengths, targets, target_lengths, selected


def model_config() -> dict:
    return {
        "input_dim": MEL_BINS,
        "output_dim": 1,
        "hidden_dim": 32,
        "preprocessing": {"type": "linear"},
        "backbone": {
            "type": "mdtc",
            "num_stack": 3,
            "stack_size": 4,
            "kernel_size": 5,
            "hidden_dim": 32,
            "causal": True,
        },
    }


def train_model(examples: list[Example], wekws_root: Path, workdir: Path):
    import torch

    sys.path.insert(0, str(wekws_root))
    from wekws.model.kws_model import init_model
    from wekws.model.loss import criterion

    torch.manual_seed(82002)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    config = model_config()
    model = init_model(config).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=0.00005)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=3, min_lr=1e-6, threshold=0.01
    )
    train = split_data(examples, "train")
    validation = split_data(examples, "dev")
    best_loss = float("inf")
    best_state = None
    stale_epochs = 0
    epochs = 100

    for epoch in range(epochs):
        model.train()
        order = torch.randperm(train[0].shape[0])
        for indices in order.split(32):
            x = train[0][indices].to(device)
            lengths = train[1][indices].to(device)
            targets = train[2][indices].to(device)
            target_lengths = train[3][indices].to(device)
            logits, _ = model(x)
            loss, _ = criterion(
                "max_pooling", logits, targets, lengths,
                target_lengths=target_lengths, min_duration=0, validation=False,
            )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()

        model.eval()
        with torch.no_grad():
            logits, _ = model(validation[0].to(device))
            validation_loss, _ = criterion(
                "max_pooling", logits, validation[2].to(device), validation[1].to(device),
                target_lengths=validation[3].to(device), min_duration=0, validation=True,
            )
        score = float(validation_loss.item())
        scheduler.step(score)
        if score < best_loss:
            best_loss = score
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= 12:
                break

    if best_state is None:
        raise RuntimeError("treino não produziu checkpoint finito")
    model.load_state_dict(best_state)
    model.to(device).eval()
    torch.save(best_state, workdir / "best-checkpoint.pt")
    return model, config, device, best_loss, epoch + 1


def export_model(model, config: dict, device, output: Path, name: str) -> None:
    import onnx
    import onnxruntime as ort
    import torch

    hidden = model.hdim
    cache_len = model.backbone.padding
    samples = torch.zeros((1, 64, MEL_BINS), dtype=torch.float32, device=device)
    cache = torch.zeros((1, hidden, cache_len), dtype=torch.float32, device=device)
    stage = output.with_suffix(".onnx.stage")
    torch.onnx.export(
        model,
        (samples, cache),
        str(stage),
        input_names=["input", "cache"],
        output_names=["output", "r_cache"],
        dynamic_axes={"input": {1: "T"}, "output": {1: "T"}},
        opset_version=13,
        dynamo=False,
        do_constant_folding=True,
    )
    graph = onnx.load(str(stage))
    onnx.checker.check_model(graph)
    metadata = {
        "cache_dim": str(hidden),
        "cache_len": str(cache_len),
        "feature_type": "forja-logmel-v1",
        "phrase": name,
        "wekws_revision": WEKWS_REVISION,
    }
    existing = {item.key for item in graph.metadata_props}
    for key, value in metadata.items():
        if key not in existing:
            entry = graph.metadata_props.add()
            entry.key = key
            entry.value = value
    onnx.save(graph, str(stage))

    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(stage), options, providers=["CPUExecutionProvider"])
    cpu_samples = samples.detach().cpu().numpy()
    cpu_cache = cache.detach().cpu().numpy()
    expected, expected_cache = model(samples, cache)
    actual, actual_cache = session.run(
        ["output", "r_cache"], {"input": cpu_samples, "cache": cpu_cache}
    )
    if not np.allclose(expected.detach().cpu().numpy(), actual, atol=1e-4):
        raise RuntimeError("export ONNX diverge do modelo PyTorch")
    if not np.allclose(expected_cache.detach().cpu().numpy(), actual_cache, atol=1e-4):
        raise RuntimeError("cache ONNX diverge do modelo PyTorch")
    stage.replace(output)


def activation_time(session, path: Path, threshold: float) -> tuple[int, int, float | None]:
    features = StreamingFeatures()
    cache_dim = int(session.get_modelmeta().custom_metadata_map["cache_dim"])
    cache_len = int(session.get_modelmeta().custom_metadata_map["cache_len"])
    cache = np.zeros((1, cache_dim, cache_len), dtype=np.float32)
    recent_voice = deque(maxlen=8)
    armed = True
    cursor_samples = 0
    first_voice_ms = None
    triggers = 0
    first_latency = None
    with wave.open(str(path), "rb") as audio:
        while frame := audio.readframes(FRAME_SAMPLES):
            if len(frame) != FRAME_BYTES:
                break
            samples = np.frombuffer(frame, dtype="<i2")
            is_voice = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))) > 400
            recent_voice.append(is_voice)
            if is_voice and first_voice_ms is None:
                first_voice_ms = round(cursor_samples * 1000 / SAMPLE_RATE)
            mel = features.accept(samples)
            if mel.size:
                scores, cache = session.run(
                    ["output", "r_cache"], {"input": mel[np.newaxis, :, :], "cache": cache}
                )
                score = float(scores.max(initial=0.0))
                elapsed = round((cursor_samples + FRAME_SAMPLES) * 1000 / SAMPLE_RATE)
                if score >= threshold and armed and sum(recent_voice) >= 4:
                    triggers += 1
                    armed = False
                    if first_latency is None and first_voice_ms is not None:
                        first_latency = max(0, elapsed - first_voice_ms)
                elif score < threshold * 0.5:
                    armed = True
            cursor_samples += FRAME_SAMPLES
    duration_seconds = cursor_samples / SAMPLE_RATE
    return triggers, round(duration_seconds * 1000), first_latency


def evaluate(session, examples: list[Example], threshold: float, split: str = "test") -> dict:
    positive = [item for item in examples if item.split == split and item.label == "wake"]
    negative = [item for item in examples if item.split == split and item.label == "negative"]
    if not positive or not negative:
        raise ValueError("teste precisa de exemplos positivos e negativos")
    hits = 0
    latencies: list[int] = []
    for item in positive:
        triggers, _, latency = activation_time(session, item.path, threshold)
        if triggers:
            hits += 1
        if latency is not None:
            latencies.append(latency)
    false_positives = 0
    negative_ms = 0
    for item in negative:
        triggers, duration_ms, _ = activation_time(session, item.path, threshold)
        false_positives += triggers
        negative_ms += duration_ms
    hours = negative_ms / 3_600_000
    rate = false_positives / hours if hours else None
    return {
        "threshold": threshold,
        "positive_samples": len(positive),
        "positive_detected": hits,
        "positive_recall": hits / len(positive),
        "latency_p95_ms": int(np.percentile(latencies, 95)) if latencies else None,
        "negative_duration_hours": round(hours, 4),
        "false_positives": false_positives,
        "false_positives_per_hour": rate,
    }


def choose_threshold(session, examples: list[Example]) -> tuple[float, dict]:
    best = None
    for threshold in np.arange(0.1, 0.951, 0.05):
        metrics = evaluate(session, examples, float(threshold), split="dev")
        if metrics["false_positives_per_hour"] is None:
            continue
        if metrics["positive_detected"] == 0:
            continue
        if metrics["false_positives_per_hour"] <= FALSE_POSITIVE_LIMIT_PER_HOUR:
            candidate = (metrics["positive_recall"], float(threshold), metrics)
            if best is None or candidate[:2] > best[:2]:
                best = candidate
    if best is None:
        raise RuntimeError("nenhum threshold atende ao FAR de desenvolvimento")
    return best[1], best[2]


def promote(model_path: Path, metrics: dict, name: str, threshold: float) -> str:
    home = Path.home()
    model_dir = home / ".local/share/hero/wakewords"
    config_dir = home / ".config/hero"
    model_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(model_dir, 0o700)
    os.chmod(config_dir, 0o700)
    slug_name = slug(name)
    destination = model_dir / f"{slug_name}.onnx"
    if destination.is_symlink():
        raise ValueError("modelo de destino é link simbólico")
    staged = model_dir / f".{slug_name}.onnx.stage-{os.getpid()}"
    shutil.copyfile(model_path, staged)
    os.chmod(staged, 0o600)
    staged.replace(destination)

    config = config_dir / "wakeword.toml"
    config_stage = config_dir / f".wakeword.toml.stage-{os.getpid()}"
    if config.is_symlink() or (config.exists() and not config.is_file()):
        raise ValueError("configuração local de wake word inválida")
    model_quoted = json.dumps(str(destination.resolve()), ensure_ascii=False)
    config_stage.write_text(f"model = {model_quoted}\nthreshold = {threshold:.2f}\n", encoding="utf-8")
    os.chmod(config_stage, 0o600)
    config_stage.replace(config)

    result = subprocess.run(
        [
            "busctl", "--user", "call", "org.forjaos.Hero", "/org/forjaos/Hero",
            "org.forjaos.Hero.Trigger", "ReloadWakeWord", "",
        ], capture_output=True, text=True, timeout=5,
    )
    if result.returncode == 0 and '"active"' in result.stdout:
        return "active"
    return "installed_reload_pending"


def main() -> int:
    parser = argparse.ArgumentParser(description="Treina um classificador local de wake word WeKws")
    parser.add_argument("--name", required=True, help="nome a treinar")
    parser.add_argument(
        "--manifest", type=Path,
        help="manifesto privado TSV; padrão: XDG_DATA_HOME/hero/wakeword-training/manifest.tsv",
    )
    parser.add_argument("--wekws-source", type=Path, help="checkout WeKws já fixado na revisão aprovada")
    args = parser.parse_args()
    name = args.name.strip()
    if not 2 <= len(name) <= 24:
        parser.error("nome deve ter entre 2 e 24 caracteres")
    if not all(char.isalpha() or char in " -'" for char in name):
        parser.error("nome aceita letras, espaços, hífen e apóstrofo")
    data_root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "hero"
    manifest = args.manifest or data_root / "wakeword-training" / "manifest.tsv"
    training_root = data_root / "wakeword-training"
    private_work = training_root / slug(name)
    private_work.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        examples = read_manifest(manifest, name)
        human_speakers = {
            example.speaker_code
            for example in examples
            if example.label == "wake" and example.source == "human" and example.speaker_code
        }
        if name in PHRASES and len(human_speakers) < 20:
            raise ValueError(
                f"FR-081 pendente: {name} tem {len(human_speakers)} locutores humanos distintos; requer 20"
            )
        wekws_root = ensure_wekws(training_root, args.wekws_source)
        model, config, device, validation_loss, epochs = train_model(examples, wekws_root, private_work)
        candidate = private_work / f"{slug(name)}.candidate.onnx"
        export_model(model, config, device, candidate, name)
        import onnxruntime as ort

        session = ort.InferenceSession(str(candidate), providers=["CPUExecutionProvider"])
        threshold, dev_metrics = choose_threshold(session, examples)
        test_metrics = evaluate(session, [item for item in examples if item.split == "test"], threshold)
        ready = (
            test_metrics["negative_duration_hours"] >= 8
            and test_metrics["false_positives_per_hour"] is not None
            and test_metrics["false_positives_per_hour"] <= FALSE_POSITIVE_LIMIT_PER_HOUR
            and test_metrics["latency_p95_ms"] is not None
            and test_metrics["latency_p95_ms"] <= LATENCY_LIMIT_MS
        )
        report = {
            "phrase": name,
            "status": "ready" if ready else "validation_pending",
            "model_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            "wekws_revision": WEKWS_REVISION,
            "training_device": str(device),
            "epochs": epochs,
            "best_validation_loss": validation_loss,
            "human_speaker_count": len(human_speakers),
            "dev": dev_metrics,
            "test": test_metrics,
            "criteria": {
                "false_positives_per_hour_max": FALSE_POSITIVE_LIMIT_PER_HOUR,
                "negative_test_hours_min": 8,
                "latency_p95_ms_max": LATENCY_LIMIT_MS,
            },
            "limit": "A origem humana e a autorização das gravações exigem revisão manual.",
        }
        (private_work / "metrics.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if not ready:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2
        report["activation"] = promote(candidate, test_metrics, name, threshold)
        (private_work / "metrics.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Treino de wake word: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
