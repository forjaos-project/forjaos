"""The live installer tree must be SELinux-labeled after container deployment."""

import runpy
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / ".github/scripts/osbuild"


class PatchISOManifestTests(unittest.TestCase):
    def setUp(self):
        self.patch = runpy.run_path(str(SCRIPT))["patch_manifest"]

    def test_relabels_the_live_tree_after_container_deploy(self):
        manifest = {
            "version": "2",
            "pipelines": [
                {"name": "build", "stages": [{"type": "org.osbuild.selinux"}]},
                {"name": "os-tree", "stages": [{"type": "org.osbuild.container-deploy"}]},
                {"name": "bootiso-tree", "stages": [{"type": "org.osbuild.squashfs"}]},
            ],
        }
        patched = self.patch(manifest)
        self.assertEqual(
            patched["pipelines"][1]["stages"][-1],
            {
                "type": "org.osbuild.selinux",
                "options": {
                    "file_contexts": "etc/selinux/targeted/contexts/files/file_contexts",
                    "exclude_paths": ["sysroot/ostree/repo"],
                },
            },
        )
        self.assertEqual(manifest["pipelines"][1]["stages"], [{"type": "org.osbuild.container-deploy"}])

    def test_rejects_an_unexpected_pipeline(self):
        with self.assertRaises(ValueError):
            self.patch({"version": "2", "pipelines": [{"name": "os-tree", "stages": []}]})

    def test_rejects_duplicate_os_tree(self):
        tree = {"name": "os-tree", "stages": [{"type": "org.osbuild.container-deploy"}]}
        with self.assertRaises(ValueError):
            self.patch({"version": "2", "pipelines": [tree, tree]})


if __name__ == "__main__":
    unittest.main()
