"""VM lifecycle tests with a simulated guest and real status assertions."""

import importlib.util
import io
import json
import tempfile
import traceback
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "image/tests/run_bootc_vm_cycle.py"
OLD = "sha256:" + "a" * 64
NEW = "sha256:" + "b" * 64
BASE = "sha256:" + "c" * 64


def state(booted, staged=None, rollback=None, queued=False):
    def deployment(digest):
        return {"image": {"imageDigest": digest}} if digest else None

    return json.dumps({"status": {
        "booted": deployment(booted),
        "staged": deployment(staged),
        "rollback": deployment(rollback),
        "rollbackQueued": queued,
    }})


def load_controller():
    spec = importlib.util.spec_from_file_location("vm_cycle", CONTROLLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTransport:
    def __init__(self, statuses, fail_on=None):
        self.statuses = list(statuses)
        self.events = []
        self.fail_on = fail_on

    def _record(self, event):
        self.events.append(event)
        if event == self.fail_on:
            raise RuntimeError(f"simulated {event} failure")

    def verify_signature(self, image, digest):
        self._record(f"verify:{digest}")

    def publish_tag(self, image, digest, tag):
        self._record(f"publish:{digest}")

    def start_vm(self):
        self._record("start")

    def status(self):
        self._record("status")
        return self.statuses.pop(0)

    def bootc(self, *args):
        self._record("bootc:" + " ".join(args))

    def reboot(self):
        self._record("reboot")

    def close_vm(self):
        self._record("close")


GOOD_STATES = [
    state(BASE),
    state(BASE, staged=OLD),
    state(OLD, rollback=BASE),
    state(OLD, staged=NEW, rollback=BASE),
    state(NEW, rollback=OLD),
    state(NEW, rollback=OLD, queued=True),
    state(OLD, rollback=NEW),
]


class BootcVmCycleTests(unittest.TestCase):
    GUEST_SPACE = "Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/vda4 22020096 13631488 8388608 62% /var\n"

    def test_guest_preflight_reports_space_and_accepts_registry_auth_challenge(self):
        module = load_controller()
        for status in ("200", "401"):
            with self.subTest(status=status):
                transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
                transport.guest_exec = Mock(side_effect=[self.GUEST_SPACE, status])
                output = io.StringIO()
                with redirect_stdout(output):
                    transport.preflight()
                self.assertIn("8388608", output.getvalue())
                calls = transport.guest_exec.call_args_list
                self.assertEqual(calls[0].args, ("/usr/bin/df", "-Pk", "/var"))
                curl = calls[1]
                self.assertEqual(curl.args[0], "/usr/bin/curl")
                self.assertIn("https://ghcr.io/v2/", curl.args)
                self.assertIn("--max-time", curl.args)
                self.assertEqual(curl.args[curl.args.index("--max-time") + 1], "30")
                self.assertIn("--connect-timeout", curl.args)
                self.assertNotIn("--fail", curl.args)
                self.assertLessEqual(curl.kwargs["timeout"], 45)

    def test_guest_preflight_rejects_unreachable_or_unexpected_registry(self):
        module = load_controller()
        for failure in ("000", "500", RuntimeError("curl DNS resolution failed")):
            with self.subTest(failure=failure):
                transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
                transport.guest_exec = Mock(side_effect=[self.GUEST_SPACE, failure, "eth0 UP", "default via 10.0.2.2", "nameserver 10.0.2.3"])
                with patch.object(module.time, "monotonic", side_effect=[0, 120]):
                    with redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "registry preflight"):
                        transport.preflight()
                self.assertEqual(transport.guest_exec.call_count, 5)

    def test_guest_preflight_retries_dns_until_network_is_ready(self):
        module = load_controller()
        transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
        transport.guest_exec = Mock(side_effect=[self.GUEST_SPACE, RuntimeError("curl: (6) Could not resolve host"), "401"])
        with patch.object(module.time, "sleep") as sleep:
            with redirect_stdout(io.StringIO()):
                    transport.preflight()
        sleep.assert_called_once()
        self.assertEqual(transport.guest_exec.call_count, 3)

    def test_guest_preflight_rejects_insufficient_or_unreadable_space_before_network(self):
        module = load_controller()
        for output in (
            self.GUEST_SPACE.replace("8388608", "5242880"),
            "Filesystem 1024-blocks Used Available Capacity Mounted on\ninvalid\n",
        ):
            with self.subTest(output=output):
                transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
                transport.guest_exec = Mock(side_effect=[output, AssertionError("network must not be called")])
                with redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "guest.*space"):
                    transport.preflight()
                transport.guest_exec.assert_called_once_with("/usr/bin/df", "-Pk", "/var", timeout=30)

    def test_mutations_log_output_and_keep_arguments_out_of_shell_source(self):
        module = load_controller()
        for operation, timeout in (("switch", 3600), ("upgrade", 3600), ("rollback", 300)):
            with self.subTest(operation=operation):
                transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
                transport.guest_exec = Mock(return_value="")
                argument = 'image:tag;$(echo injected) "with spaces"'
                transport.bootc(operation, argument)
                call = transport.guest_exec.call_args
                self.assertEqual(call.args[:2], ("/usr/bin/bash", "-c"))
                self.assertEqual(call.args[2], 'exec /usr/bin/bootc "$@" > /run/forja-vm-bootc.log 2>&1')
                self.assertEqual(call.args[4:], (operation, argument))
                self.assertEqual(call.kwargs["timeout"], timeout)

    def test_mutation_failure_collects_bounded_tail_and_preserves_original_error(self):
        module = load_controller()
        for diagnostic in ("downloading layer 1/4", RuntimeError("diagnostic unavailable")):
            with self.subTest(diagnostic=diagnostic):
                transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
                failure = RuntimeError("original transfer timed out")
                transport.guest_exec = Mock(side_effect=[failure, diagnostic])
                with patch("sys.stderr", new_callable=io.StringIO) as output:
                    with self.assertRaises(RuntimeError) as caught:
                        transport.bootc("upgrade")
                self.assertIs(caught.exception, failure)
                tail = transport.guest_exec.call_args_list[1]
                self.assertEqual(tail.args, ("/usr/bin/tail", "-c", "16384", "/run/forja-vm-bootc.log"))
                self.assertLessEqual(tail.kwargs["timeout"], 30)
                self.assertIn(str(diagnostic), output.getvalue())

    def test_status_json_uses_direct_command_with_short_timeout(self):
        module = load_controller()
        transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
        expected = state(BASE)
        transport.guest_exec = Mock(return_value=expected)
        self.assertEqual(transport.status(), expected)
        transport.guest_exec.assert_called_once_with("/usr/bin/bootc", "status", "--json", timeout=60)

    def test_mutation_tail_redacts_signed_urls_and_authentication(self):
        module = load_controller()
        transport = module.LibvirtTransport("vm-cycle-test", "actor", "synthetic-token", "disk.qcow2")
        log = (
            'fetch https://pkg.example/blob/layer?signature=private-query&expires=123\n'
            'Authorization: Bearer private-header\nBearer private-bearer\nsynthetic-token\n'
        )
        transport.guest_exec = Mock(side_effect=[RuntimeError("transfer timed out"), log])
        with patch("sys.stderr", new_callable=io.StringIO) as output:
            with self.assertRaisesRegex(RuntimeError, "transfer timed out"):
                transport.bootc("upgrade")
        rendered = output.getvalue()
        self.assertIn("https://pkg.example/blob/layer", rendered)
        for secret in ("private-query", "expires=123", "private-header", "private-bearer", "synthetic-token"):
            self.assertNotIn(secret, rendered)

    def test_guest_exec_rpc_timeout_respects_remaining_command_budget(self):
        module = load_controller()
        transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
        transport.agent = Mock(side_effect=[{"pid": 1}, {"exited": True, "exitcode": 0}])
        with patch.object(module.time, "monotonic", side_effect=[0, 29]):
            transport.guest_exec("/usr/bin/true", timeout=30)
        self.assertEqual([call.kwargs["timeout"] for call in transport.agent.call_args_list], [30, 1])

    def test_registry_timeout_never_exposes_credentials_in_traceback(self):
        module = load_controller()
        token = "synthetic-review-token"
        transport = module.LibvirtTransport("vm-cycle-test", "actor", token, "disk.qcow2")

        def timed_out(args, **kwargs):
            raise module.subprocess.TimeoutExpired(
                args, kwargs["timeout"], output=token, stderr=token,
            )

        for operation in (
            lambda: transport.verify_signature("ghcr.io/forjaos-project/forjaos", OLD),
            lambda: transport.publish_tag("ghcr.io/forjaos-project/forjaos", OLD, "vm-cycle-test"),
        ):
            with self.subTest(operation=operation), patch.object(module.subprocess, "run", side_effect=timed_out):
                try:
                    operation()
                except Exception as failure:
                    rendered = "".join(traceback.format_exception(failure))
                    self.assertNotIn(token, rendered)
                    self.assertIsInstance(failure, RuntimeError)
                    self.assertIn("timed out", str(failure))
                else:
                    self.fail("registry timeout must stop the cycle")

    def test_libvirt_transport_imports_built_bazzite_disk(self):
        module = load_controller()
        with tempfile.TemporaryDirectory() as directory:
            disk = Path(directory) / "disk.qcow2"
            disk.write_bytes(b"qcow2")
            transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", disk=disk)
            transport.command = Mock(return_value="")
            transport.wait_agent = Mock()
            transport.preflight = Mock()
            transport.guest_read_file = Mock(side_effect=["1", "system_u:system_r:unconfined_service_t:s0"])
            transport.start_vm()
            command = transport.command.call_args_list[0].args[0]
            self.assertEqual(command[0], "virt-install")
            self.assertIn(str(disk), " ".join(command))
            self.assertIn("org.qemu.guest_agent.0", " ".join(command))
            self.assertIn("user,model=virtio", command)
            self.assertNotIn("bcvk", " ".join(command))
            transport.preflight.assert_called_once()

    def test_vm_rejects_disabled_selinux_before_bootc_cycle(self):
        module = load_controller()
        with tempfile.TemporaryDirectory() as directory:
            disk = Path(directory) / "disk.qcow2"
            disk.write_bytes(b"qcow2")
            transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", disk=disk)
            transport.command = Mock(return_value="")
            transport.wait_agent = Mock()
            transport.guest_read_file = Mock(return_value="0")
            with self.assertRaisesRegex(RuntimeError, "SELinux must remain enforcing"):
                transport.start_vm()

    def test_status_failure_preserves_error_and_reports_guest_agent_context(self):
        module = load_controller()
        transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")

        def guest_exec(path, *args, **_kwargs):
            if path == "/usr/bin/bootc":
                raise RuntimeError("Failed to execute child process /usr/bin/bootc (Permission denied)")
            if path == "/usr/bin/true":
                return ""
            raise RuntimeError("probe denied")

        transport.guest_exec = guest_exec
        transport.agent = Mock(side_effect=[7, {"buf-b64": "c3lzdGVtX3U6c3lzdGVtX3I6dmlydF9xZW11X2dhX3Q6czA=", "count": 38}, {}])
        with self.assertRaisesRegex(RuntimeError, "Permission denied") as caught:
            transport.status()
        self.assertIn("virt_qemu_ga_t", str(caught.exception))
        self.assertIn("/usr/bin/true: ok", str(caught.exception))
        self.assertIn("systemd-run bootc: probe denied", str(caught.exception))

    def test_diagnostic_failure_does_not_hide_original_bootc_error(self):
        module = load_controller()
        transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
        transport.guest_exec = Mock(side_effect=RuntimeError("Failed to execute child process /usr/bin/bootc (Permission denied)"))
        transport.agent = Mock(return_value=None)
        with self.assertRaisesRegex(RuntimeError, "Permission denied") as caught:
            transport.status()
        self.assertIn("guest agent SELinux context:", str(caught.exception))

    def test_bootc_uses_transient_service_when_guest_agent_denies_direct_exec(self):
        module = load_controller()
        transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
        expected = state(BASE)

        def guest_exec(path, *args, **_kwargs):
            if path == "/usr/bin/bootc":
                raise RuntimeError("Failed to execute child process /usr/bin/bootc (Permission denied)")
            if path == "/usr/bin/systemd-run":
                self.assertIn("--pipe", args)
                self.assertIn("--property=MemoryMax=3G", args)
                self.assertIn("--property=CPUQuota=200%", args)
                self.assertIn("--property=Nice=5", args)
                self.assertEqual(args[-3:], ("/usr/bin/bootc", "status", "--json"))
                return expected
            raise AssertionError(f"unexpected command {path}")

        transport.guest_exec = guest_exec
        self.assertEqual(transport.status(), expected)

    def test_bootc_command_failure_is_not_retried_as_a_second_mutation(self):
        module = load_controller()
        transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
        transport.guest_exec = Mock(side_effect=RuntimeError("guest bootc failed (1): registry timeout"))
        with self.assertRaisesRegex(RuntimeError, "registry timeout"):
            transport.bootc("switch", "ghcr.io/forjaos-project/forjaos:vm-cycle-f0-008")
        self.assertEqual([call.args[0] for call in transport.guest_exec.call_args_list], ["/usr/bin/bash", "/usr/bin/tail"])

    def test_reboot_reads_boot_id_through_guest_file_api(self):
        module = load_controller()
        transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")
        transport.guest_read_file = Mock(side_effect=["old-boot-id", "new-boot-id"])
        transport.virsh = Mock()
        transport.wait_agent = Mock()
        transport.guest_exec = Mock(side_effect=AssertionError("boot-id must not use guest-exec"))
        transport.reboot()
        transport.virsh.assert_called_once_with("reboot", "vm-cycle-test")

    def test_full_cycle_checks_three_booted_digests(self):
        module = load_controller()
        transport = FakeTransport(GOOD_STATES)
        with tempfile.TemporaryDirectory() as output:
            module.run_cycle(transport, "ghcr.io/forjaos-project/forjaos", OLD, NEW, "vm-cycle-1", Path(output))
            self.assertEqual(len(list(Path(output).glob("*.json"))), 7)
        self.assertEqual(transport.events[:3], [f"verify:{OLD}", f"verify:{NEW}", f"publish:{OLD}"])
        self.assertEqual(transport.events.count("reboot"), 3)
        self.assertEqual(transport.events[-1], "close")
        self.assertLess(transport.events.index(f"publish:{NEW}"), transport.events.index("bootc:upgrade"))

    def test_wrong_booted_digest_after_upgrade_fails_and_closes_vm(self):
        module = load_controller()
        statuses = GOOD_STATES.copy()
        statuses[4] = state(OLD, staged=NEW, rollback=BASE)
        transport = FakeTransport(statuses)
        with tempfile.TemporaryDirectory() as output:
            with self.assertRaisesRegex(RuntimeError, "booted"):
                module.run_cycle(transport, "ghcr.io/forjaos-project/forjaos", OLD, NEW, "vm-cycle-2", Path(output))
        self.assertEqual(transport.events[-1], "close")
        self.assertNotIn("bootc:rollback", transport.events)

    def test_wrong_booted_digest_after_rollback_fails(self):
        module = load_controller()
        statuses = GOOD_STATES.copy()
        statuses[6] = state(NEW, rollback=OLD)
        transport = FakeTransport(statuses)
        with tempfile.TemporaryDirectory() as output:
            with self.assertRaisesRegex(RuntimeError, "booted"):
                module.run_cycle(transport, "ghcr.io/forjaos-project/forjaos", OLD, NEW, "vm-cycle-3", Path(output))
        self.assertEqual(transport.events.count("reboot"), 3)

    def test_signature_failure_prevents_tag_write_and_vm_start(self):
        module = load_controller()
        transport = FakeTransport([], fail_on=f"verify:{NEW}")
        with tempfile.TemporaryDirectory() as output:
            with self.assertRaisesRegex(RuntimeError, "simulated"):
                module.run_cycle(transport, "ghcr.io/forjaos-project/forjaos", OLD, NEW, "vm-cycle-4", Path(output))
        self.assertFalse(any(event.startswith("publish") for event in transport.events))
        self.assertNotIn("start", transport.events)

    def test_same_digests_are_rejected_before_external_actions(self):
        module = load_controller()
        transport = FakeTransport([])
        with tempfile.TemporaryDirectory() as output:
            with self.assertRaisesRegex(ValueError, "distinct"):
                module.run_cycle(transport, "ghcr.io/forjaos-project/forjaos", OLD, OLD, "vm-cycle-5", Path(output))
        self.assertEqual(transport.events, [])

    def test_cleanup_failure_does_not_hide_start_failure(self):
        module = load_controller()

        class FailedStart(FakeTransport):
            def start_vm(self):
                raise RuntimeError("original VM start failure")

            def close_vm(self):
                raise RuntimeError("VM cleanup failure")

        with tempfile.TemporaryDirectory() as output:
            with self.assertRaisesRegex(RuntimeError, "original VM start failure"):
                module.run_cycle(FailedStart([]), "ghcr.io/forjaos-project/forjaos", OLD, NEW, "vm-cycle-6", Path(output))


if __name__ == "__main__":
    unittest.main()
