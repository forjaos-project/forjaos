"""VM lifecycle tests with a simulated guest and real status assertions."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock


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
    def test_libvirt_transport_imports_built_bazzite_disk(self):
        module = load_controller()
        with tempfile.TemporaryDirectory() as directory:
            disk = Path(directory) / "disk.qcow2"
            disk.write_bytes(b"qcow2")
            transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", disk=disk)
            transport.command = Mock(return_value="")
            transport.wait_agent = Mock()
            transport.start_vm()
            command = transport.command.call_args_list[0].args[0]
            self.assertEqual(command[0], "virt-install")
            self.assertIn(str(disk), " ".join(command))
            self.assertIn("org.qemu.guest_agent.0", " ".join(command))
            self.assertNotIn("bcvk", " ".join(command))

    def test_status_failure_preserves_error_and_reports_guest_agent_context(self):
        module = load_controller()
        transport = module.LibvirtTransport("vm-cycle-test", "actor", "token", "disk.qcow2")

        def guest_exec(path, *args, **_kwargs):
            if path == "/usr/bin/bootc":
                raise RuntimeError("bootc execution denied")
            if path == "/usr/bin/true":
                return ""
            raise RuntimeError("probe denied")

        transport.guest_exec = guest_exec
        transport.agent = Mock(side_effect=[{"handle": 7}, {"buf-b64": "c3lzdGVtX3U6c3lzdGVtX3I6dmlydF9xZW11X2dhX3Q6czA=", "count": 38}, {}])
        with self.assertRaisesRegex(RuntimeError, "bootc execution denied") as caught:
            transport.status()
        self.assertIn("virt_qemu_ga_t", str(caught.exception))
        self.assertIn("/usr/bin/true: ok", str(caught.exception))

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
