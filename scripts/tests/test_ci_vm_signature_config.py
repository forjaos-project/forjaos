"""The disposable Bazzite VM keeps upstream policy while trusting signed ForjaOS."""

import importlib.util
import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "image/tests/generate_ci_vm_config.py"
PRODUCTION_CONFIG = ROOT / "image/build_files/configure_image.py"
BASE_CONFIG = ROOT / "image/tests/ci-guest-agent.toml"
PUBLIC_KEY = "-----BEGIN PUBLIC KEY-----\nsynthetic-test-key\n-----END PUBLIC KEY-----\n"
BASE_POLICY = {
    "default": [{"type": "reject"}],
    "transports": {"docker": {
        "ghcr.io/ublue-os": [{"type": "sigstoreSigned", "keyPath": "/etc/pki/containers/ublue.pub"}],
    }},
}


def load_generator():
    spec = importlib.util.spec_from_file_location("ci_vm_config", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CiVmSignatureConfigTests(unittest.TestCase):
    def test_vm_trust_matches_published_image_trust(self):
        module = load_generator()
        spec = importlib.util.spec_from_file_location("production_image", PRODUCTION_CONFIG)
        production = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(production)
        self.assertEqual(module.REGISTRY, production.REGISTRY)
        self.assertEqual(module.KEY_PATH, production.KEY_DESTINATION)
        self.assertEqual(module.REGISTRY_CONFIG, production.REGISTRIES_D_CONTENT)
        self.assertEqual(module.REGISTRY_CONFIG_PATH, production.REGISTRIES_D)

    def test_preserves_bazzite_policy_and_adds_only_forja_namespace(self):
        module = load_generator()
        result = module.render(
            json.dumps(BASE_POLICY), PUBLIC_KEY, BASE_CONFIG.read_text(encoding="utf-8")
        )
        config = tomllib.loads(result)["customizations"]
        files = {item["path"]: item["data"] for item in config["files"]}
        self.assertEqual(len(files), 4)
        self.assertIn("/etc/systemd/system/qemu-guest-agent.service.d/90-forja-vm-ci.conf", files)
        self.assertEqual(files["/etc/pki/containers/forjaos.pub"], PUBLIC_KEY)
        self.assertEqual(
            files["/etc/containers/registries.d/forjaos-project.yaml"],
            "docker:\n  ghcr.io/forjaos-project:\n    use-sigstore-attachments: true\n",
        )
        policy = json.loads(files["/etc/containers/policy.json"])
        self.assertEqual(policy["default"], BASE_POLICY["default"])
        self.assertEqual(
            policy["transports"]["docker"]["ghcr.io/ublue-os"],
            BASE_POLICY["transports"]["docker"]["ghcr.io/ublue-os"],
        )
        self.assertEqual(policy["transports"]["docker"]["ghcr.io/forjaos-project"], [{
            "type": "sigstoreSigned",
            "keyPath": "/etc/pki/containers/forjaos.pub",
            "signedIdentity": {"type": "matchRepository"},
        }])

    def test_rejects_unsafe_or_conflicting_base_policy(self):
        module = load_generator()
        config = BASE_CONFIG.read_text(encoding="utf-8")
        for policy in (
            {"default": [{"type": "insecureAcceptAnything"}], "transports": {"docker": {}}},
            {"default": [{"type": "reject"}], "transports": {"docker": {
                "ghcr.io/forjaos-project": [{"type": "reject"}],
            }}},
        ):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                module.render(json.dumps(policy), PUBLIC_KEY, config)

    def test_rejects_invalid_public_key(self):
        module = load_generator()
        with self.assertRaises(ValueError):
            module.render(json.dumps(BASE_POLICY), "invalid", BASE_CONFIG.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
