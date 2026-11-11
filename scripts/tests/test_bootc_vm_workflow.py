"""Guard the VM CI workflow's authority and real bootc execution path."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/bootc-vm.yml"
GUEST_CONFIG = ROOT / "image/tests/ci-guest-agent.toml"
BASELINE = "sha256:cfe6a9791e5bd2226acc48c82cad0e3dcc887662bb9c9ba782a69b646a24f744"


class BootcVmWorkflowTests(unittest.TestCase):
    def test_guest_agent_override_is_confined_to_disposable_vm_disk(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        config = GUEST_CONFIG.read_text(encoding="utf-8")
        self.assertIn('image/tests/ci-guest-agent.toml:/config.toml:ro', workflow)
        self.assertNotIn('--config /config.toml', workflow)
        self.assertIn('/etc/systemd/system/qemu-guest-agent.service.d/', config)
        self.assertIn('SELinuxContext=system_u:system_r:unconfined_service_t:s0', config)
        self.assertIn('MemoryMax=3G', config)
        self.assertIn('CPUQuota=200%', config)
        self.assertIn('Nice=5', config)
        self.assertNotIn('SELINUX=disabled', config)

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
        self.assertIn("podman skopeo libvirt-daemon-system libvirt-clients virtinst", source)
        self.assertIn('source_file="$RUNNER_TEMP/forja-ubuntu.sources"', source)
        self.assertIn('URIs: https://archive.ubuntu.com/ubuntu', source)
        self.assertIn('URIs: https://security.ubuntu.com/ubuntu', source)
        self.assertIn('Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg', source)
        self.assertIn('Dir::Etc::sourcelist=$source_file', source)
        self.assertIn('Dir::Etc::sourceparts=/dev/null', source)
        self.assertNotIn('azure.archive.ubuntu.com', source)
        self.assertIn('getent hosts archive.ubuntu.com', source)
        self.assertIn('getent hosts security.ubuntu.com', source)
        self.assertIn('sudo resolvectl dns "$dns_iface" 1.1.1.1', source)
        self.assertIn('trap \'sudo resolvectl revert "$dns_iface"\' EXIT', source)
        self.assertIn('APT::Update::Error-Mode=any', source)
        self.assertIn('timeout 300s sudo apt-get "${apt_opts[@]}" update', source)
        self.assertIn('timeout 600s sudo apt-get "${apt_opts[@]}" install', source)
        self.assertIn("uidmap fuse-overlayfs slirp4netns", source)
        self.assertIn("Diagnose guest boot after cycle failure", source)
        self.assertIn("sudo qemu-nbd --read-only --connect=/dev/nbd0", source)
        self.assertIn("sudo partx -a /dev/nbd0", source)
        self.assertIn("sudo udevadm settle", source)
        self.assertIn("sudo journalctl --file", source)
        self.assertIn('path = "/var/log/journal"', (ROOT / "image/tests/ci-guest-agent.toml").read_text())
        self.assertIn("podman info", source)
        self.assertIn("podman run --rm --entrypoint /usr/bin/true ghcr.io/ublue-os/bazzite:stable", source)
        self.assertIn('podman exec "$probe_id" /usr/bin/true', source)
        self.assertNotIn("CONTAINERS_CONF", source)
        self.assertNotIn("rm -rf", source)
        self.assertNotIn("sudo tee /etc/", source)
        self.assertNotIn("sudo sed -i", source)
        self.assertRegex(source, r"actions/checkout@[0-9a-f]{40}")
        self.assertRegex(source, r"sigstore/cosign-installer@[0-9a-f]{40}")
        self.assertRegex(source, r"actions/upload-artifact@[0-9a-f]{40}")
        self.assertIn("quay.io/centos-bootc/bootc-image-builder@sha256:dab86ee6b46dcade411b37f4e70b07d93b6a06da0dbfec6fe89247a220e0d9f8", source)
        self.assertIn("--rootfs btrfs", source)
        self.assertNotIn("customizations.filesystem", source)
        self.assertNotIn("bcvk-x86_64-unknown-linux-gnu.tar.gz", source)
        self.assertIn("test -e /dev/kvm", source)
        self.assertIn(BASELINE, source)
        self.assertIn("image/tests/run_bootc_vm_cycle.py", source)
        self.assertIn("--variant forjaos", source)
        self.assertIn("--target", source)
        self.assertIn("--baseline", source)
        self.assertIn("--connect qemu:///session", source)
        self.assertIn("--disk \"$RUNNER_TEMP/bazzite-qcow2/qcow2/disk.qcow2\"", source)
        self.assertIn("python3 image/tests/run_bootc_vm_cycle.py", source)
        self.assertNotIn("sudo --preserve-env=GH_TOKEN,GITHUB_ACTOR", source)
        self.assertIn("if: always()", source)
        self.assertNotRegex(source, re.compile(r"skopeo copy[^\n]*:stable"))


if __name__ == "__main__":
    unittest.main()
