# F0-004 Branding Check Implementation Plan

**Goal:** Replace the branding-check stub with a failing inspection of a built ForjaOS image or an extracted rootfs, as required by FR-002 and G4.

**Architecture:** Keep `check-branding.sh` as the public entry point. It runs a Python standard-library checker on a rootfs, or streams that checker into a local OCI image through Podman or Docker. The checker reads `/etc/os-release`, queries the RPM database, and scans only named user-visible surfaces. It emits deterministic human or JSON findings and exits nonzero on violations or inspection errors. It does not change image contents.

**Tech Stack:** Bash, Python 3 standard library, RPM available inside the image, Podman or Docker for image inspection, shell and Python tests.

**Source:** issue #17, FR-002, FR-003, G4, ADR-0032 and roadmap item F0-004. No screen is implemented.

## File map

- `scripts/check-branding.sh` — public `--rootfs` and `--image` interface and OCI runtime dispatch.
- `scripts/check_branding.py` — rootfs checks and deterministic result formatting.
- `scripts/tests/test_check_branding.py` — synthetic rootfs cases, package query, exceptions, output and errors.
- `scripts/tests/test_check_branding.sh` — shell entry point and image-dispatch cases with a fake OCI runtime.

## Task 1 — Inspect rootfs branding (FR-002, FR-003, G4)

- [ ] Write `scripts/tests/test_check_branding.py` first. Its synthetic rootfs contains `os-release`, an RPM command fixture, and the visible paths declared in the stub. Cases cover clean identity, every forbidden package family, visible brand text or path, legal-file exclusion, permitted `ID_LIKE=fedora`, missing or invalid identity, RPM failure, and deterministic JSON.
- [ ] Run the test and observe failure because `scripts/check_branding.py` is absent.
- [ ] Implement `scripts/check_branding.py` with explicit checks for `NAME`, `ID`, and `PRETTY_NAME`; RPM name queries; bounded scans of boot, login, desktop and settings surfaces; a precise exception for legal documents. Report findings with path and line where available. An unreadable required source is an inspection error.
- [ ] Run the test green and verify that restoring the stub behavior makes a test fail.
- [ ] Commit: `feat(scripts): inspect rootfs branding`.

## Task 2 — Wire image inspection (FR-002, G4)

- [ ] Write `scripts/tests/test_check_branding.sh` first. It checks `--rootfs`, `--image` dispatch using a fake runtime, `--json`, missing or conflicting arguments and propagation of the checker exit status. Run it and observe the stub fail.
- [ ] Replace `scripts/check-branding.sh` with a Bash entry point. For `--image`, prefer Podman and fall back to Docker, run Python inside the image with the checker streamed through stdin, and propagate its exit status. For `--rootfs`, invoke the local checker. Do not add an external package.
- [ ] Run the shell test green. Inspect the locally built `forjaos-nvidia-open:f0-002` and `forjaos:f0-002` images; record any real findings without weakening the check.
- [ ] Commit: `feat(scripts): check branding in OCI images`.

## Gate test and delivery

- [ ] Run the root verification and `scripts/run-shell-tests.sh`, including the new checker tests. Check `git diff --check`, conventional commits and roadmap branch validation.
- [ ] Open the PR with issue #17, command output, the observed image findings, and the explicit F1-011 rebranding boundary.
- [ ] Review under a new, clean Codex session per ADR-033; then deliver F0-004 only after `review: 8/8` and the required checks.
