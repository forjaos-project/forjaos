# F1-001 — Image package and service contract

**Goal:** Remove confirmed unwanted base packages and verify the inherited developer and gaming RPMs and system service defaults without introducing new dependencies or repositories (FR-004, FR-005, FR-006, FR-007, ADR-0034).

**Architecture:** Keep an explicit removal manifest under `image/build_files/`. A build helper applies it against the current RPM database, so the two Bazzite variants may differ without hiding failed transactions. A separate contract checker runs inside each built image before publication and records inherited package and service states. The daily image job supplies real-image evidence for both variants.

**Tech Stack:** Containerfile, Bash, Python standard library, RPM/DNF, systemd, unittest, Bash integration tests, Podman CI.

**Entry:** ADR-0034 accepted on 2026-11-12. Issue #47 records the original dependency conflict. The `daily-image` run 43201943595 license artifacts establish the starting RPM inventories; `forjaos` contains `waydroid` and `waydroid-selinux`, while `forjaos-nvidia-open` contains neither. Both contain `podman`, `distrobox`, `steam`, `firewalld`, `audit`, `btop`, `nvtop`, and `forjaos-branding`. The audit artifacts do not establish systemd enablement or non-RPM installations.

## File map

| File | Responsibility |
| --- | --- |
| `image/build_files/remove.txt` | Exact unwanted RPMs confirmed in the base image. |
| `image/build_files/apply_package_policy.sh` | Apply manifests safely to both image variants and fail on transaction errors. |
| `image/Containerfile` | Run the package policy before final identity and bootc lint; include the contract checker in each variant. |
| `scripts/tests/test_image_package_policy.sh` | Prove installed-only removal, install transaction failure, and preservation of gaming packages. |
| `image/build_files/check_image_contract.py` | Read real RPM and systemctl results, enforce the F1-001 package and service subset. |
| `scripts/tests/test_image_contract.py` | Prove failures for missing packages, retained unwanted packages, and wrong service states. |
| `.github/scripts/daily-image.sh` | Run the contract checker on each built variant before publishing. |
| `scripts/tests/test_daily_image.sh` | Prove the contract gate runs before push for both variants. |

## Task 1 — Apply the approved RPM removal policy (FR-004, FR-007, ADR-0034)

**Files:** `image/build_files/remove.txt`, `image/build_files/apply_package_policy.sh`, `image/Containerfile`, `scripts/tests/test_image_package_policy.sh`.

1. Write a Bash test with fake RPM/DNF binaries: installed `waydroid` and `waydroid-selinux` are removed with `--no-autoremove`; absent names are skipped; a removal transaction failure stops the build; `steam` and `steam-devices` are never removed. Run it and observe failure before writing the helper.
2. List only `waydroid` and `waydroid-selinux` in `remove.txt`, the confirmed unwanted RPMs in the generic variant. The helper must reject blank or malformed manifest entries and never invoke DNF when a listed RPM is absent. Run the test, refactor, and commit.

**DoD:** Both Bazzite variants can apply the same manifest; no Waydroid RPM remains where present; Steam remains installed; a failed RPM transaction fails the build. Commit: `feat(image): apply base package policy`.

## Task 2 — Verify package and service defaults (FR-005, FR-006, FR-007, ADR-0034)

**Files:** `image/build_files/check_image_contract.py`, `scripts/tests/test_image_contract.py`.

1. Write tests using captured command outputs for missing `podman`, `distrobox`, `steam`, `steam-devices`, `firewalld`, `audit`, `btop`, `nvtop`, or `forjaos-branding`; retained Waydroid RPMs; enabled `sshd` or `cockpit.socket`; and disabled `firewalld` or `auditd`. Observe failure before implementation.
2. Implement a checker that queries the image's RPM database and `systemctl is-enabled` without changing `/etc`, firewall, or SELinux. Distinguish `disabled` from missing units and fail closed on query errors. Run the tests and commit.

**DoD:** The checker produces actionable errors and passes only when all scoped package and system service conditions hold. `docker.socket`, `herod`, and `memd` remain assigned to their component deliveries by ADR-0034. Commit: `feat(image): verify image package and service contract`.

## Task 3 — Gate both published variants (FR-004, FR-005, FR-006, FR-007, ADR-0034)

**Files:** `image/Containerfile`, `.github/scripts/daily-image.sh`, `scripts/tests/test_daily_image.sh`.

1. Extend the existing fake-Podman test to require the image contract checker after build and before any push; observe failure against the current script.
2. Run the checker in the built container with its own entrypoint. Preserve the existing license inventory, branding, and signature gates. Run the test and commit.

**DoD:** The daily workflow refuses publication when either variant violates the scoped package/service contract; evidence from the real CI matrix is attached to the PR. Commit: `feat(image): gate daily images on package contract`.

## Gate checks (FR-004, FR-005, FR-006, FR-007)

- Run root checks, image shell tests, branding check, roadmap branch validation, and `bootc container lint` through the daily image workflow.
- Prove a new test fails when its implementation is reverted, then restore the implementation.
- Keep FR-004 ISO size, FR-005 full `forja doctor` inventory, and FR-006 user daemons in their ADR-0034 dependent cards; do not mark them as tested in F1-001.
