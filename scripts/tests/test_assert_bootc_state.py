"""Behavior checks for the VM bootc status assertion command."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "image/tests/assert_bootc_state.py"
OLD = "sha256:" + "a" * 64
NEW = "sha256:" + "b" * 64


def state(*, booted=OLD, staged=None, rollback=None, rollback_queued=False):
    def deployment(digest):
        return {"image": {"imageDigest": digest}} if digest else None

    return {
        "apiVersion": "org.containers.bootc/v1",
        "status": {
            "booted": deployment(booted),
            "staged": deployment(staged),
            "rollback": deployment(rollback),
            "rollbackQueued": rollback_queued,
        },
    }


def check(payload, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


class AssertBootcStateTests(unittest.TestCase):
    def test_container_policy_is_required_when_requested(self):
        signed = state(booted=OLD, staged=NEW)
        for slot in ("booted", "staged"):
            signed["status"][slot]["image"]["image"] = {"signature": "containerPolicy"}
        self.assertEqual(
            check(signed, "--booted", OLD, "--staged", NEW, "--require-container-policy").returncode,
            0,
        )
        del signed["status"]["staged"]["image"]["image"]["signature"]
        self.assertNotEqual(
            check(signed, "--booted", OLD, "--staged", NEW, "--require-container-policy").returncode,
            0,
        )

    def test_switch_requires_booted_digest_after_reboot(self):
        self.assertEqual(check(state(), "--booted", OLD, "--no-staged").returncode, 0)
        result = check(state(booted=NEW), "--booted", OLD)
        self.assertNotEqual(result.returncode, 0)

    def test_upgrade_requires_staged_then_booted_digest(self):
        self.assertEqual(check(state(staged=NEW), "--booted", OLD, "--staged", NEW).returncode, 0)
        result = check(state(staged=NEW), "--booted", NEW)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(check(state(booted=NEW, rollback=OLD), "--booted", NEW, "--rollback", OLD).returncode, 0)

    def test_rollback_requires_reboot_into_previous_digest(self):
        self.assertEqual(check(state(booted=NEW, rollback=OLD, rollback_queued=True), "--booted", NEW, "--rollback", OLD, "--rollback-queued").returncode, 0)
        self.assertNotEqual(check(state(booted=NEW, rollback=OLD), "--booted", OLD).returncode, 0)
        self.assertEqual(check(state(booted=OLD, rollback=NEW), "--booted", OLD, "--rollback", NEW).returncode, 0)

    def test_missing_or_invalid_digest_fails(self):
        self.assertNotEqual(check(state(booted=None), "--booted", OLD).returncode, 0)
        self.assertNotEqual(check(state(), "--booted", "sha256:short").returncode, 0)
        self.assertNotEqual(check({"status": {}}, "--booted", OLD).returncode, 0)

    def test_no_staged_rejects_pending_deployment(self):
        self.assertNotEqual(check(state(staged=NEW), "--booted", OLD, "--no-staged").returncode, 0)


if __name__ == "__main__":
    unittest.main()
