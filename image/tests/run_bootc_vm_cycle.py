#!/usr/bin/env python3
"""Exercise signed bootc switch, upgrade, and rollback in a disposable VM."""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
IMAGE = re.compile(r"ghcr\.io/forjaos-project/forjaos(?:-nvidia-open)?\Z")
TAG = re.compile(r"vm-cycle-[a-z0-9-]+\Z")
ASSERT_SCRIPT = Path(__file__).with_name("assert_bootc_state.py")
BASE_IMAGE = "ghcr.io/ublue-os/bazzite:stable"


def digest_at(status_text, slot):
    try:
        digest = json.loads(status_text)["status"][slot]["image"]["imageDigest"]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"missing {slot} digest in bootc status") from exc
    if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
        raise RuntimeError(f"invalid {slot} digest in bootc status")
    return digest


def check_status(status_text, *, booted, staged=None, rollback=None, no_staged=False, queued=False):
    command = [sys.executable, str(ASSERT_SCRIPT), "--booted", booted]
    if staged:
        command += ["--staged", staged]
    if rollback:
        command += ["--rollback", rollback]
    if no_staged:
        command.append("--no-staged")
    if queued:
        command.append("--rollback-queued")
    result = subprocess.run(command, input=status_text, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "bootc status assertion failed")


def run_cycle(transport, image, baseline, target, tag, output):
    """Run the lifecycle, saving every status before its assertion."""
    if not IMAGE.fullmatch(image) or not TAG.fullmatch(tag):
        raise ValueError("image or VM test tag is outside the ForjaOS test scope")
    if not DIGEST.fullmatch(baseline) or not DIGEST.fullmatch(target) or baseline == target:
        raise ValueError("baseline and target must be distinct full sha256 digests")
    output.mkdir(parents=True, exist_ok=True)

    def observe(name, **expected):
        status_text = transport.status()
        (output / f"{name}.json").write_text(status_text.rstrip() + "\n", encoding="utf-8")
        check_status(status_text, **expected)
        print(f"vm-cycle: {name}: booted={digest_at(status_text, 'booted')}", flush=True)
        return status_text

    transport.verify_signature(image, baseline)
    transport.verify_signature(image, target)
    transport.publish_tag(image, baseline, tag)
    started = False
    try:
        started = True
        transport.start_vm()
        initial = transport.status()
        (output / "01-base.json").write_text(initial.rstrip() + "\n", encoding="utf-8")
        base_digest = digest_at(initial, "booted")
        check_status(initial, booted=base_digest, no_staged=True)
        print(f"vm-cycle: 01-base: booted={base_digest}", flush=True)

        transport.bootc("switch", f"{image}:{tag}")
        observe("02-switch-staged", booted=base_digest, staged=baseline)
        transport.reboot()
        observe("03-switch-booted", booted=baseline, rollback=base_digest, no_staged=True)

        transport.publish_tag(image, target, tag)
        transport.bootc("upgrade")
        observe("04-upgrade-staged", booted=baseline, staged=target)
        transport.reboot()
        observe("05-upgrade-booted", booted=target, rollback=baseline, no_staged=True)

        transport.bootc("rollback")
        observe("06-rollback-queued", booted=target, rollback=baseline, queued=True)
        transport.reboot()
        observe("07-rollback-booted", booted=baseline, rollback=target, no_staged=True)
    finally:
        if started:
            original_failure = sys.exc_info()[1]
            try:
                transport.close_vm()
            except Exception as cleanup_failure:
                if original_failure is None:
                    raise
                print(f"vm-cycle: cleanup also failed: {cleanup_failure}", file=sys.stderr)


class LibvirtTransport:
    """Run VM operations without changing the host or image configuration."""

    def __init__(self, vm_name, actor, token, connect="qemu:///session"):
        self.vm_name = vm_name
        self.actor = actor
        self.token = token
        self.connect = connect

    def command(self, args, *, timeout=1800):
        result = subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)
        if result.returncode:
            detail = (result.stderr or result.stdout).replace(self.token, "***").strip()
            raise RuntimeError(f"{Path(args[0]).name} failed ({result.returncode}): {detail[:1000]}")
        return result.stdout

    def verify_signature(self, image, digest):
        self.command([
            "cosign", "verify", "--new-bundle-format=false", "--key", "cosign.pub",
            "--registry-username", self.actor, "--registry-password", self.token,
            f"{image}@{digest}",
        ], timeout=120)

    def publish_tag(self, image, digest, tag):
        credentials = f"{self.actor}:{self.token}"
        self.command([
            "skopeo", "copy", "--preserve-digests", "--src-creds", credentials,
            "--dest-creds", credentials, f"docker://{image}@{digest}", f"docker://{image}:{tag}",
        ])
        actual = self.command([
            "skopeo", "inspect", "--creds", credentials, "--format", "{{.Digest}}",
            f"docker://{image}:{tag}",
        ]).strip()
        if actual != digest:
            raise RuntimeError(f"test tag digest mismatch: expected {digest}, got {actual}")

    def virsh(self, *args, timeout=60):
        return self.command(["virsh", "-c", self.connect, *args], timeout=timeout)

    def agent(self, payload, timeout=60):
        response = self.virsh("qemu-agent-command", self.vm_name, json.dumps(payload), timeout=timeout)
        try:
            result = json.loads(response)
        except json.JSONDecodeError as exc:
            raise RuntimeError("invalid QEMU guest agent response") from exc
        if "error" in result:
            raise RuntimeError(f"QEMU guest agent: {result['error']}")
        return result.get("return")

    def wait_agent(self, timeout=900):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                self.agent({"execute": "guest-ping"}, timeout=15)
                return
            except (RuntimeError, subprocess.TimeoutExpired):
                time.sleep(3)
        raise RuntimeError("QEMU guest agent did not become ready")

    def guest_exec(self, path, *args, timeout=1800):
        response = self.agent({
            "execute": "guest-exec",
            "arguments": {"path": path, "arg": list(args), "capture-output": True},
        })
        if not isinstance(response, dict) or not isinstance(response.get("pid"), int):
            raise RuntimeError("guest-exec did not return a process ID")
        pid = response["pid"]
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = self.agent({"execute": "guest-exec-status", "arguments": {"pid": pid}})
            if status.get("exited"):
                stdout = base64.b64decode(status.get("out-data", "")).decode("utf-8", errors="replace")
                stderr = base64.b64decode(status.get("err-data", "")).decode("utf-8", errors="replace")
                if status.get("exitcode") != 0:
                    raise RuntimeError(f"guest {Path(path).name} failed ({status.get('exitcode')}): {stderr[:1000]}")
                return stdout
            time.sleep(3)
        raise RuntimeError(f"guest {Path(path).name} timed out")

    def start_vm(self):
        self.command(["podman", "pull", BASE_IMAGE])
        self.command([
            "bcvk", "libvirt", "run", "--connect", self.connect, "--name", self.vm_name,
            "--memory", "4G", "--cpus", "4", "--disk-size", "70G",
            "--firmware", "uefi-insecure", "--disable-tpm", "--detach", BASE_IMAGE,
        ], timeout=3600)
        xml = self.virsh("dumpxml", self.vm_name)
        if "org.qemu.guest_agent.0" not in xml:
            channel = (
                "<channel type='unix'><source mode='bind'/>"
                "<target type='virtio' name='org.qemu.guest_agent.0'/></channel>"
            )
            with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", encoding="utf-8") as source:
                source.write(channel)
                source.flush()
                self.virsh("attach-device", self.vm_name, source.name, "--live", "--config")
        self.wait_agent()

    def status(self):
        return self.guest_exec("/usr/bin/bootc", "status", "--json")

    def bootc(self, *args):
        self.guest_exec("/usr/bin/bootc", *args)

    def reboot(self):
        previous = self.guest_exec("/usr/bin/cat", "/proc/sys/kernel/random/boot_id").strip()
        self.virsh("reboot", self.vm_name)
        deadline = time.monotonic() + 1200
        while time.monotonic() < deadline:
            try:
                self.wait_agent(timeout=15)
                current = self.guest_exec("/usr/bin/cat", "/proc/sys/kernel/random/boot_id", timeout=15).strip()
                if current and current != previous:
                    return
            except (RuntimeError, subprocess.TimeoutExpired):
                pass
            time.sleep(3)
        raise RuntimeError("VM did not boot a new kernel session")

    def close_vm(self):
        self.command(["bcvk", "libvirt", "rm", "--connect", self.connect, "-f", self.vm_name], timeout=180)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("forjaos", "forjaos-nvidia-open"), required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--connect", default="qemu:///session")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    actor = os.environ.get("GITHUB_ACTOR")
    token = os.environ.get("GH_TOKEN")
    if not actor or not token:
        parser.error("GITHUB_ACTOR and GH_TOKEN are required")
    run_id = re.sub(r"[^a-z0-9-]", "-", args.run_id.lower()).strip("-")
    if not run_id:
        parser.error("invalid run ID")
    tag = f"vm-cycle-{run_id}"
    transport = LibvirtTransport(tag, actor, token, connect=args.connect)
    run_cycle(transport, f"ghcr.io/forjaos-project/{args.variant}", args.baseline, args.target, tag, args.output)


if __name__ == "__main__":
    main()
