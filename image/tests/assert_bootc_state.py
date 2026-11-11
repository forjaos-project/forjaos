#!/usr/bin/env python3
"""Assert the actual bootc deployment state from status JSON on stdin."""

import argparse
import json
import re
import sys


DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


def deployment_digest(status, slot):
    deployment = status.get(slot)
    if deployment is None:
        return None
    if not isinstance(deployment, dict):
        raise ValueError(f"{slot} is not a deployment")
    image = deployment.get("image")
    if not isinstance(image, dict):
        raise ValueError(f"{slot}.image is missing")
    digest = image.get("imageDigest")
    if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
        raise ValueError(f"{slot}.image.imageDigest is invalid")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--booted", required=True, help="expected booted OCI digest")
    parser.add_argument("--staged", help="expected staged OCI digest")
    parser.add_argument("--rollback", help="expected rollback OCI digest")
    parser.add_argument("--no-staged", action="store_true", help="require no staged deployment")
    parser.add_argument("--rollback-queued", action="store_true", help="require rollback to be queued")
    args = parser.parse_args()
    if args.no_staged and args.staged:
        parser.error("--no-staged and --staged are mutually exclusive")
    for expected in (args.booted, args.staged, args.rollback):
        if expected is not None and not DIGEST.fullmatch(expected):
            parser.error("expected digests must be full lowercase sha256 values")
    try:
        payload = json.load(sys.stdin)
        status = payload["status"]
        if not isinstance(status, dict):
            raise ValueError("status is not an object")
        actual = {slot: deployment_digest(status, slot) for slot in ("booted", "staged", "rollback")}
        for slot in ("booted", "staged", "rollback"):
            expected = getattr(args, slot)
            if expected is not None and actual[slot] != expected:
                raise ValueError(f"{slot}: expected {expected}, got {actual[slot]}")
        if args.no_staged and actual["staged"] is not None:
            raise ValueError(f"staged deployment remains: {actual['staged']}")
        if args.rollback_queued and status.get("rollbackQueued") is not True:
            raise ValueError("rollback is not queued")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"bootc-state: {exc}\n")
    print(" ".join(f"{slot}={actual[slot] or '-'}" for slot in ("booted", "staged", "rollback")))


if __name__ == "__main__":
    main()
