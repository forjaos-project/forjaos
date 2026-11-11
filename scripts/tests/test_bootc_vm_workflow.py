"""Guard the VM CI workflow's authority and real bootc execution path."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/bootc-vm.yml"
BASELINE = "sha256:cfe6a9791e5bd2226acc48c82cad0e3dcc887662bb9c9ba782a69b646a24f744"


class BootcVmWorkflowTests(unittest.TestCase):
    def test_vm_workflow_has_ci_and_weekly_triggers(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(source, r"(?m)^  pull_request:\s*$")
        self.assertRegex(source, r"(?m)^  workflow_dispatch:\s*$")
        self.assertRegex(source, r"(?m)^  schedule:\s*$")
        self.assertIn("cancel-in-progress: false", source)

    def test_fork_guard_and_scoped_permissions(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", source)
        self.assertIn("contents: read", source)
        self.assertIn("packages: write", source)
        self.assertNotIn("secrets.SIGNING_SECRET", source)
        self.assertNotIn("delete:packages", source)

    def test_pinned_tools_and_real_vm_cycle(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("runs-on: ubuntu-24.04", source)
        self.assertNotIn("bootc-host-setup@", source)
        self.assertIn("podman skopeo libvirt-daemon-system libvirt-clients", source)
        self.assertIn("uidmap fuse-overlayfs slirp4netns", source)
        self.assertIn("podman info", source)
        self.assertIn("podman run --rm --entrypoint /usr/bin/true ghcr.io/ublue-os/bazzite:stable", source)
        self.assertNotIn("CONTAINERS_CONF", source)
        self.assertNotIn("rm -rf", source)
        self.assertNotIn("/etc/", source)
        self.assertRegex(source, r"actions/checkout@[0-9a-f]{40}")
        self.assertRegex(source, r"sigstore/cosign-installer@[0-9a-f]{40}")
        self.assertRegex(source, r"actions/upload-artifact@[0-9a-f]{40}")
        self.assertIn("bcvk-x86_64-unknown-linux-gnu.tar.gz", source)
        self.assertIn("3135cc59b8971193b49be6cbaee12b789391ac6e6ab5ed3edf17082b03f144dd", source)
        self.assertIn("test -e /dev/kvm", source)
        self.assertIn(BASELINE, source)
        self.assertIn("image/tests/run_bootc_vm_cycle.py", source)
        self.assertIn("--variant forjaos", source)
        self.assertIn("--target", source)
        self.assertIn("--baseline", source)
        self.assertIn("--connect qemu:///session", source)
        self.assertIn("python3 image/tests/run_bootc_vm_cycle.py", source)
        self.assertNotIn("sudo --preserve-env=GH_TOKEN,GITHUB_ACTOR", source)
        self.assertIn("if: always()", source)
        self.assertNotRegex(source, re.compile(r"skopeo copy[^\n]*:stable"))


if __name__ == "__main__":
    unittest.main()
