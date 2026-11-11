#!/usr/bin/env python3
"""Exercise signed bootc switch, upgrade, and rollback in a disposable VM."""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
IMAGE = re.compile(r"ghcr\.io/forjaos-project/forjaos(?:-nvidia-open)?\Z")
TAG = re.compile(r"vm-cycle-[a-z0-9-]+\Z")
ASSERT_SCRIPT = Path(__file__).with_name("assert_bootc_state.py")


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

    def __init__(self, vm_name, actor, token, disk, connect="qemu:///session"):
        self.vm_name = vm_name
        self.actor = actor
        self.token = token
        self.connect = connect
        self.disk = Path(disk)

    def redact_diagnostic(self, text):
        text = text.replace(self.token, "***")
        text = re.sub(r'''(?i)(https?://[^\s?<>"']+)\?[^\s<>"']+''', r"\1?***", text)
        text = re.sub(r"(?im)(authorization\s*[:=]\s*)[^\r\n]+", r"\1***", text)
        return re.sub(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+", "Bearer ***", text)

    def command(self, args, *, timeout=1800):
        try:
            result = subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            # TimeoutExpired includes argv, which can contain registry credentials.
            raise RuntimeError(f"{Path(args[0]).name} timed out after {timeout} seconds") from None
        if result.returncode:
            detail = self.redact_diagnostic(result.stderr or result.stdout).strip()
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
        deadline = time.monotonic() + timeout
        response = self.agent({
            "execute": "guest-exec",
            "arguments": {"path": path, "arg": list(args), "capture-output": True},
        }, timeout=min(60, timeout))
        if not isinstance(response, dict) or not isinstance(response.get("pid"), int):
            raise RuntimeError("guest-exec did not return a process ID")
        pid = response["pid"]
        while (remaining := deadline - time.monotonic()) > 0:
            status = self.agent({"execute": "guest-exec-status", "arguments": {"pid": pid}}, timeout=min(60, remaining))
            if status.get("exited"):
                stdout = base64.b64decode(status.get("out-data", "")).decode("utf-8", errors="replace")
                stderr = base64.b64decode(status.get("err-data", "")).decode("utf-8", errors="replace")
                if status.get("exitcode") != 0:
                    detail = self.redact_diagnostic(stderr)[:1000]
                    raise RuntimeError(f"guest {Path(path).name} failed ({status.get('exitcode')}): {detail}")
                return stdout
            time.sleep(max(0, min(3, deadline - time.monotonic())))
        raise RuntimeError(f"guest {Path(path).name} timed out")

    def guest_read_file(self, path):
        handle = self.agent({"execute": "guest-file-open", "arguments": {"path": path, "mode": "r"}})
        if not isinstance(handle, int):
            raise RuntimeError("guest-file-open did not return a handle")
        try:
            data = self.agent({"execute": "guest-file-read", "arguments": {"handle": handle, "count": 256}})
            return base64.b64decode(data["buf-b64"]).decode("utf-8", errors="replace").strip("\x00\r\n")
        finally:
            self.agent({"execute": "guest-file-close", "arguments": {"handle": handle}})

    def bootc_command(self, *args):
        try:
            return self.guest_exec("/usr/bin/bootc", *args, timeout=60)
        except RuntimeError as failure:
            if "Failed to execute child process" not in str(failure) or "Permission denied" not in str(failure):
                raise
            try:
                return self.guest_exec(
                    "/usr/bin/systemd-run", "--system", "--wait", "--pipe", "--collect", "--quiet",
                    "--property=MemoryMax=3G", "--property=CPUQuota=200%", "--property=Nice=5",
                    "--", "/usr/bin/bootc", *args, timeout=60,
                )
            except (RuntimeError, subprocess.TimeoutExpired) as service_failure:
                diagnostics = [f"systemd-run bootc: {str(service_failure)[:200]}"]
            for label, probe in (
                ("guest agent SELinux context", lambda: self.guest_read_file("/proc/self/attr/current")),
                ("/usr/bin/true", lambda: self.guest_exec("/usr/bin/true", timeout=15)),
                ("/usr/bin/id", lambda: self.guest_exec("/usr/bin/id", timeout=15)),
                ("/usr/bin/cat", lambda: self.guest_exec("/usr/bin/cat", "/proc/self/attr/current", timeout=15)),
            ):
                try:
                    value = probe()
                    diagnostics.append(f"{label}: {(value or 'ok')[:200]}")
                except Exception as probe_failure:
                    diagnostics.append(f"{label}: {str(probe_failure)[:200]}")
            raise RuntimeError(f"{failure}; guest diagnostics: {'; '.join(diagnostics)}") from failure

    def start_vm(self):
        if not self.disk.is_file():
            raise RuntimeError(f"Bazzite VM disk missing: {self.disk}")
        self.command([
            "virt-install", "--connect", self.connect, "--name", self.vm_name,
            "--memory", "4096", "--vcpus", "4", "--import",
            "--disk", f"path={self.disk},format=qcow2,bus=virtio",
            "--osinfo", "detect=off,require=off", "--boot", "uefi,firmware.feature0.name=secure-boot,firmware.feature0.enabled=no",
            "--network", "user,model=virtio", "--graphics", "none", "--noautoconsole",
            "--channel", "unix,target.type=virtio,target.name=org.qemu.guest_agent.0",
        ], timeout=300)
        self.wait_agent()
        if self.guest_read_file("/sys/fs/selinux/enforce") != "1":
            raise RuntimeError("SELinux must remain enforcing in the Bazzite test VM")
        if self.guest_read_file("/proc/self/attr/current") != "system_u:system_r:unconfined_service_t:s0":
            raise RuntimeError("test-only guest agent SELinux context was not applied")
        self.preflight()

    def preflight(self):
        usage = self.guest_exec("/usr/bin/df", "-h", "/", "/var", timeout=30)
        print(f"vm-cycle: guest disk usage:\n{self.redact_diagnostic(usage).strip()}", flush=True)
        deadline = time.monotonic() + 120
        while True:
            try:
                status = self.guest_exec(
                    "/usr/bin/curl", "--silent", "--show-error", "--output", "/dev/null",
                    "--write-out", "%{http_code}", "--connect-timeout", "10", "--max-time", "30",
                    "https://ghcr.io/v2/", timeout=45,
                ).strip()
                if status in ("200", "401"):
                    print(f"vm-cycle: guest registry preflight: HTTP {status}", flush=True)
                    return
                last_error = f"unexpected HTTP {status}"
            except (RuntimeError, subprocess.TimeoutExpired) as failure:
                last_error = str(failure)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(10, remaining))

        diagnostics = []
        for name, path, args in (
            ("interfaces", "/usr/bin/ip", ("-brief", "addr")),
            ("routes", "/usr/bin/ip", ("-4", "route")),
            ("resolver", "/usr/bin/cat", ("/etc/resolv.conf",)),
        ):
            try:
                value = self.guest_exec(path, *args, timeout=15)
                diagnostics.append(f"{name}: {self.redact_diagnostic(value).strip()[:300]}")
            except (RuntimeError, subprocess.TimeoutExpired) as failure:
                diagnostics.append(f"{name}: {self.redact_diagnostic(str(failure))[:150]}")
        raise RuntimeError(
            f"guest registry preflight failed: {self.redact_diagnostic(last_error)[:300]}; "
            + "; ".join(diagnostics)
        )

    def status(self):
        return self.bootc_command("status", "--json")

    def bootc(self, *args):
        if not args or args[0] not in ("switch", "upgrade", "rollback"):
            raise ValueError("expected a bootc switch, upgrade, or rollback mutation")
        timeout = 300 if args[0] == "rollback" else 3600
        print(f"vm-cycle: bootc {args[0]} started (timeout={timeout}s)", flush=True)
        try:
            self.guest_exec(
                "/usr/bin/bash", "-c", 'exec /usr/bin/bootc "$@" > /run/forja-vm-bootc.log 2>&1',
                "bootc-vm", *args, timeout=timeout,
            )
        except Exception:
            try:
                tail = self.guest_exec("/usr/bin/tail", "-c", "16384", "/run/forja-vm-bootc.log", timeout=30)
                print(f"vm-cycle: bootc log tail:\n{self.redact_diagnostic(tail)}", file=sys.stderr, flush=True)
            except Exception as diagnostic_failure:
                detail = self.redact_diagnostic(str(diagnostic_failure))
                print(f"vm-cycle: bootc log unavailable: {detail}", file=sys.stderr, flush=True)
            raise
        print(f"vm-cycle: bootc {args[0]} completed", flush=True)

    def reboot(self):
        previous = self.guest_read_file("/proc/sys/kernel/random/boot_id")
        self.virsh("reboot", self.vm_name)
        deadline = time.monotonic() + 1200
        while time.monotonic() < deadline:
            try:
                self.wait_agent(timeout=15)
                current = self.guest_read_file("/proc/sys/kernel/random/boot_id")
                if current and current != previous:
                    return
            except (RuntimeError, subprocess.TimeoutExpired):
                pass
            time.sleep(3)
        raise RuntimeError("VM did not boot a new kernel session")

    def close_vm(self):
        try:
            state = self.virsh("domstate", self.vm_name).strip()
        except RuntimeError as exc:
            if "not found" in str(exc) or "failed to get domain" in str(exc):
                return
            raise
        if state != "shut off":
            self.virsh("destroy", self.vm_name)
        self.virsh("undefine", self.vm_name, "--nvram")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("forjaos", "forjaos-nvidia-open"), required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--connect", default="qemu:///session")
    parser.add_argument("--disk", type=Path, required=True)
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
    transport = LibvirtTransport(tag, actor, token, args.disk, connect=args.connect)
    run_cycle(transport, f"ghcr.io/forjaos-project/{args.variant}", args.baseline, args.target, tag, args.output)


if __name__ == "__main__":
    main()
