import argparse
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from worker import FRAME_BYTES, regular_model, run, valid_threshold


class SequenceModel:
    def __init__(self, scores):
        self.scores = iter(scores)
        self.frames = 0

    def predict(self, frame):
        assert frame.dtype.str == "<i2"
        assert frame.size == FRAME_BYTES // 2
        self.frames += 1
        return {"guara": next(self.scores)}


class WakeWorkerTests(unittest.TestCase):
    def run_with_fake_numpy(self, model, source, destination, threshold):
        def frombuffer(frame, dtype):
            self.assertEqual(dtype, "<i2")
            return SimpleNamespace(dtype=SimpleNamespace(str="<i2"), size=len(frame) // 2)

        with patch.dict(sys.modules, {"numpy": SimpleNamespace(frombuffer=frombuffer)}):
            run(model, source, destination, threshold)

    def test_stream_emits_once_until_score_resets(self):
        model = SequenceModel([0.1, 0.8, 0.9, 0.2, 0.75])
        output = io.BytesIO()
        self.run_with_fake_numpy(model, io.BytesIO(bytes(FRAME_BYTES * 5)), output, 0.5)
        self.assertEqual(output.getvalue(), b"wake\nwake\n")
        self.assertEqual(model.frames, 5)

    def test_incomplete_frame_fails_closed(self):
        model = SequenceModel([0.9])
        with self.assertRaisesRegex(ValueError, "incompleto"):
            self.run_with_fake_numpy(model, io.BytesIO(bytes(FRAME_BYTES + 1)), io.BytesIO(), 0.5)

    def test_nonfinite_score_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "inválida"):
            self.run_with_fake_numpy(
                SequenceModel([float("nan")]), io.BytesIO(bytes(FRAME_BYTES)), io.BytesIO(), 0.5
            )

    def test_model_must_be_a_regular_local_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertRaises(ValueError, regular_model, root / "missing.onnx")
            target = root / "model.onnx"
            target.write_bytes(b"model")
            self.assertEqual(regular_model(target), target.resolve())
            link = root / "link.onnx"
            try:
                link.symlink_to(target)
            except OSError:
                pass  # Windows may disallow symlink creation without developer mode.
            else:
                self.assertRaises(ValueError, regular_model, link)

    def test_threshold_rejects_out_of_range_values(self):
        for invalid in ("0", "1", "nan", "inf"):
            with self.subTest(invalid=invalid), self.assertRaises(argparse.ArgumentTypeError):
                valid_threshold(invalid)

    def test_cli_loads_only_explicit_assets_and_streams_pcm(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "openwakeword"
            package.mkdir()
            (package / "__init__.py").write_text("")
            (package / "model.py").write_text(
                "class Model:\n"
                "    def __init__(self, **kwargs):\n"
                "        assert kwargs['inference_framework'] == 'onnx'\n"
                "        assert len(kwargs['wakeword_models']) == 1\n"
                "        assert all(path.startswith('" + str(root).replace("\\", "\\\\") + "') "
                "for key in ('wakeword_models', 'melspec_model_path', 'embedding_model_path') "
                "for path in (kwargs[key] if isinstance(kwargs[key], list) else [kwargs[key]]))\n"
                "    def predict(self, frame):\n"
                "        return {'guara': 0.8}\n"
            )
            (root / "numpy.py").write_text("def frombuffer(frame, dtype): return frame\n")
            assets = [root / name for name in ("wake.onnx", "mel.onnx", "embedding.onnx")]
            for asset in assets:
                asset.write_bytes(b"local fixture")
            environment = dict(os.environ, PYTHONPATH=str(root))
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("worker.py")),
                 "--model", str(assets[0]), "--melspec", str(assets[1]),
                 "--embedding", str(assets[2])],
                input=bytes(FRAME_BYTES * 2), capture_output=True, env=environment,
                timeout=5, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stdout, b"wake\n")


if __name__ == "__main__":
    unittest.main()
