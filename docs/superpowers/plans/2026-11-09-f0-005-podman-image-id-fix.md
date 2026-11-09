# F0-005 Podman Image ID Fix Implementation Plan

> **For agentic workers:** Execute this correction in order, observing red and green tests before committing.

**Goal:** Make the F0-005 CI inventory accept the image ID format emitted by Podman while keeping the report's ID canonical (G4, ADR-007).

**Architecture:** Podman emitted a bare 64-character hex image ID in run 42714375576; Docker and the shell fixture emitted `sha256:` plus the hex. Normalize either form in the renderer before rendering, and reject every other form. The daily workflow's existing artifact and branding gates stay intact.

**Tech Stack:** Python 3 standard library, Bash fixtures, GitHub Actions. No new dependency (G4, ADR-007).

**Entry:** Issue #26 was reopened after the merged PR #27 failed the real CI run before producing artifacts. The roadmap already records F0-005 as done in main; this is a correction to that delivered item, so this follow-up PR does not change another roadmap item or generated status file.

---

## File map

- `scripts/tests/test_third_party_licenses.py` — prove prefixed and bare Podman IDs produce the same canonical report; invalid IDs still fail.
- `scripts/tests/test_daily_image.sh` — make fake `podman image inspect` return a bare ID, matching the runner observed in run 42714375576.
- `.github/scripts/generate_third_party_licenses.py` — normalize the bare ID and retain strict validation.

## Task 1 — Normalize Podman image IDs (G4, ADR-007)

- [ ] Extend the Python test helper with an optional image-ID argument. Add a test that passes `"a" * 64` and checks the report contains ``sha256:`` followed by the same hex, while an ID of 63 characters fails without writing a file. In the shell fixture, change `podman image inspect` from `sha256:` plus 64 hex to only 64 hex.
- [ ] Run `python3 -m unittest discover -s scripts/tests -p test_third_party_licenses.py` and `bash scripts/tests/test_daily_image.sh`; both must fail against the current renderer's prefixed-only validation.
- [ ] In the renderer, accept `sha256:[0-9a-f]{64}` unchanged or `[0-9a-f]{64}` prefixed with `sha256:`; reject anything else with `argparse.error`. Render only the normalized value.
- [ ] Run both tests green and the full root suite, plus `actionlint` and `roadmap.py validate --branch`. DoD: the same image ID emitted by the runner can produce an artifact; malformed IDs still fail closed. Commit `fix(scripts): accept bare Podman image IDs`.

## Gate test and delivery (G4, ADR-033)

- [ ] Open the correction PR linked to reopened issue #26, with the failed run and new test output. Use a clean Codex context for all eight review items and require `review: 8/8` plus green CI before squash merge.
- [ ] Dispatch the daily workflow from the corrected `main` and verify both license artifacts upload. The inherited branding failure remains tracked by issue #25; it must still prevent `:testing` publication.
