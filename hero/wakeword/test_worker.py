import argparse
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from features import FRAME_SAMPLES, MEL_BINS, StreamingFeatures, extract
from worker import FRAME_BYTES, WeKwsModel, regular_model, run, valid_threshold


class SequenceModel:
    def __init__(self, scores):
        self.scores = iter(scores)
        self.frames = []

    def predict(self, features):
        assert features.dtype == np.float32
        assert features.ndim == 2 and features.shape[1] == MEL_BINS
        self.frames.append(features.shape[0])
        return next(self.scores)


class WakeWorkerTests(unittest.TestCase):
    @staticmethod
    def speech_frame():
        return np.full(FRAME_SAMPLES, 2000, dtype="<i2").tobytes()

    def test_streaming_features_match_offline_extraction(self):
        samples = (np.sin(np.arange(FRAME_SAMPLES * 5) * 0.07) * 10_000).astype("<i2")
        streaming = StreamingFeatures()
        chunks = [streaming.accept(samples[index : index + FRAME_SAMPLES])
                  for index in range(0, samples.size, FRAME_SAMPLES)]
        np.testing.assert_allclose(np.concatenate(chunks), extract(samples), rtol=1e-5)
        self.assertEqual(chunks[0].shape, (6, MEL_BINS))
        self.assertTrue(all(chunk.shape == (8, MEL_BINS) for chunk in chunks[1:]))

    def test_stream_emits_once_until_score_resets(self):
        model = SequenceModel([0.1, 0.1, 0.1, 0.8, 0.2, 0.75])
        output = io.BytesIO()
        run(model, io.BytesIO(self.speech_frame() * 6), output, 0.5)
        self.assertEqual(output.getvalue(), b"wake\nwake\n")
        self.assertEqual(model.frames, [6, 8, 8, 8, 8, 8])

    def test_silence_and_short_noise_cannot_trigger_wake(self):
        output = io.BytesIO()
        pcm = bytes(FRAME_BYTES * 8) + self.speech_frame() * 3 + bytes(FRAME_BYTES * 8)
        run(SequenceModel([0.99] * 19), io.BytesIO(pcm), output, 0.5)
        self.assertEqual(output.getvalue(), b"")

    def test_incomplete_frame_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "incompleto"):
            run(SequenceModel([0.9]), io.BytesIO(bytes(FRAME_BYTES + 1)), io.BytesIO(), 0.5)

    def test_nonfinite_score_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "inválida"):
            run(SequenceModel([float("nan")]), io.BytesIO(bytes(FRAME_BYTES)), io.BytesIO(), 0.5)

    def test_model_must_be_absolute_regular_local_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertRaises(ValueError, regular_model, root / "missing.onnx")
            target = root / "model.onnx"
            target.write_bytes(b"model")
            self.assertEqual(regular_model(target), target.resolve())
            self.assertRaises(ValueError, regular_model, Path("model.onnx"))
            link = root / "link.onnx"
            try:
                link.symlink_to(target)
            except OSError:
                pass
            else:
                self.assertRaises(ValueError, regular_model, link)

    def test_threshold_rejects_out_of_range_values(self):
        for invalid in ("0", "1", "nan", "inf"):
            with self.subTest(invalid=invalid), self.assertRaises(argparse.ArgumentTypeError):
                valid_threshold(invalid)

    def test_cli_loads_only_explicit_model_and_streams_pcm(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "onnxruntime.py").write_text(
                "import numpy as np\n"
                "class SessionOptions:\n"
                "    pass\n"
                "class InferenceSession:\n"
                "    def __init__(self, path, options, providers):\n"
                "        assert providers == ['CPUExecutionProvider']\n"
                "        assert path.endswith('wake.onnx')\n"
                "    def get_modelmeta(self):\n"
                "        return type('Meta', (), {'custom_metadata_map': "
                "{'cache_dim':'4','cache_len':'3','feature_type':'forja-logmel-v1'}})()\n"
                "    def get_inputs(self):\n"
                "        return [type('Tensor', (), {'name':'input','shape':[1,'T',80]})(), "
                "type('Tensor', (), {'name':'cache','shape':[1,4,3]})()]\n"
                "    def get_outputs(self):\n"
                "        return [type('Tensor', (), {'name':name})() for name in ('output','r_cache')]\n"
                "    def run(self, names, inputs):\n"
                "        return [np.full((1,inputs['input'].shape[1],1),.8,dtype=np.float32), "
                "inputs['cache']]\n"
            )
            model = root / "wake.onnx"
            model.write_bytes(b"local fixture")
            environment = dict(os.environ, PYTHONPATH=str(root))
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("worker.py")), "--model", str(model)],
                input=self.speech_frame() * 4, capture_output=True, env=environment,
                timeout=5, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stdout, b"wake\n")

    @unittest.skipUnless(importlib.util.find_spec("onnx"), "ONNX authoring package unavailable")
    def test_real_onnx_session_uses_streaming_feature_and_cache_shapes(self):
        import onnx
        from onnx import TensorProto, helper

        graph = helper.make_graph(
            [helper.make_node("ReduceMean", ["input"], ["mean"], axes=[2], keepdims=1),
             helper.make_node("Sigmoid", ["mean"], ["output"]),
             helper.make_node("Identity", ["cache"], ["r_cache"])],
            "synthetic_wekws_contract",
            [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, "T", MEL_BINS]),
             helper.make_tensor_value_info("cache", TensorProto.FLOAT, [1, 4, 3])],
            [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, "T", 1]),
             helper.make_tensor_value_info("r_cache", TensorProto.FLOAT, [1, 4, 3])],
        )
        model = helper.make_model(graph, opset_imports=[helper.make_operatorsetid("", 13)])
        model.ir_version = 10
        for key, value in (("cache_dim", "4"), ("cache_len", "3"),
                           ("feature_type", "forja-logmel-v1")):
            item = model.metadata_props.add()
            item.key, item.value = key, value
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.onnx"
            onnx.save(model, path)
            detector = WeKwsModel(path)
            self.assertAlmostEqual(detector.predict(np.ones((6, MEL_BINS), dtype=np.float32)),
                                   0.7310586, places=5)
            self.assertEqual(detector.cache.shape, (1, 4, 3))
            del model.metadata_props[-1]
            onnx.save(model, path)
            with self.assertRaisesRegex(ValueError, "features ONNX incompatível"):
                WeKwsModel(path)


if __name__ == "__main__":
    unittest.main()
