# Host disk guard

**Goal:** Keep local ForjaOS builds and Docker Desktop from exhausting the Windows system SSD (ADR-0037, NFR-040, NFR-042).

**Architecture:** A Windows preflight rejects heavy local work below 160 GiB free on C:. A scheduled guard checks C: every minute and requests a graceful Docker Desktop stop below 120 GiB. Docker data remains on C:; D: is not a Docker data target. The monitor only runs while the Windows user is signed in. A dry run verifies the stop decision without stopping live services.

**Tech Stack:** PowerShell 5.1, Windows Task Scheduler, Docker Desktop CLI, Python unittest for source-level integration checks.

## File map

| File | Responsibility |
| --- | --- |
| `docs/adr/0037-host-ssd-reserve.md` | ADR-0037 decision, limits and residual risks |
| `AGENTS.md` | Mandatory local preflight and Docker storage rule |
| `scripts/host/check-disk.ps1` | Preflight and one-shot scheduled watch |
| `scripts/host/install-disk-guard.ps1` | Install the guard on C: and register Task Scheduler |
| `scripts/tests/test_host_disk_guard.py` | Threshold and installation contract tests |

## Tasks

1. **ADR-0037, NFR-040:** Add the written rule to the ADR and `AGENTS.md`. Test: inspect the documented thresholds and paths, run `scripts/check-agents-sync.sh`. Done when both specify C: SSD, 160 GiB preflight, 120 GiB stop, and no Docker data on D:. Commit: `docs(agents): require Windows SSD reserve for local builds`.
2. **ADR-0037, NFR-040:** Write threshold tests in `scripts/tests/test_host_disk_guard.py`, run them red, then implement `scripts/host/check-disk.ps1` and run them green. Done when preflight passes at 160 GiB, blocks below it, watch dry run requests stop below 120 GiB, and no live Docker stop occurs in tests. Commit: `feat(scripts): guard Windows SSD reserve`.
3. **ADR-0037, NFR-042:** Write installer contract test, run red, implement `scripts/host/install-disk-guard.ps1`, run green, then install and inspect the scheduled task on this host. Done when a per-minute task runs the copied script on C: for the signed-in user, avoids overlapping runs, and the live check reports safe with Docker running. Commit: `feat(scripts): schedule Docker disk guard on Windows`.
