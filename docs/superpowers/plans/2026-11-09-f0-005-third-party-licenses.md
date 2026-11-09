# F0-005 Third-Party License Inventory Implementation Plan

> **For agentic workers:** Execute the two tasks in order, with a red test before each implementation and one commit per task.

**Goal:** Generate and upload one `THIRD_PARTY_LICENSES.md` inventory from each freshly built ForjaOS image in daily CI (G4, ADR-007).

**Architecture:** Query the image's RPM database for package identity, license metadata, source RPM, and license-file flags. A Python standard-library renderer validates the stream and atomically writes a stable Markdown report. The daily image script generates the report before the existing branding gate, and the workflow uploads a per-variant artifact even when that gate rejects publication. This is an inventory of RPM metadata and declared license-file paths, not a legal conclusion or a copy of every license text.

**Tech Stack:** RPM already present in the bootc image, Python 3 standard library, Bash, Podman, GitHub Actions, pinned `actions/upload-artifact` (MIT). No image package or runtime dependency is added (G4, ADR-007).

**Entry:** Issue #26 states the G4/ADR-007 DoD. F0-005 is claimed at `942ab81` on `feat/F0-005-third-party-licenses`; F0-003 is complete. Issue #25 separately tracks the inherited branding gate failure.

---

## File map

- `.github/scripts/generate_third_party_licenses.py` — parse a tagged RPM query stream, reject missing/malformed metadata, sort packages and license files, render Markdown, and replace the destination atomically.
- `scripts/tests/test_third_party_licenses.py` — exercise parsing, ordering, escaping, absence of packages or license tags, license-file flags, and no partial output on failure.
- `.github/scripts/daily-image.sh` — query RPM inside the built image and invoke the renderer before branding, writing under `LICENSE_REPORT_DIR/<variant>/THIRD_PARTY_LICENSES.md`.
- `scripts/tests/test_daily_image.sh` — fake RPM output, assert a report for both variants and that generation precedes branding and push; fail before publication when RPM fails.
- `.github/workflows/daily-image.yml` — give the build step a runner-temp report directory and upload a uniquely named artifact per variant with `if-no-files-found: error` after failures.
- `scripts/tests/test_daily_image_workflow.py` — assert the artifact step, pin, path, permissions, and failure behavior.
- `docs/roadmap/roadmap.json` — only F0-005 changes from claim to done during ship.

## Task 1 — Render an accurate inventory (G4, ADR-007)

**Files:** create `.github/scripts/generate_third_party_licenses.py`; create `scripts/tests/test_third_party_licenses.py`.

- [ ] Write tests that feed `P\tname\tversion-release\tarch\tlicense\tsource` package records followed by `F\t/path\tflags` file records. Check two packages sort deterministically, `l`-flagged files appear, non-license files do not, Markdown metacharacters are escaped, and `--variant`/`--image-id` identify the build.
- [ ] Run `python3 -m unittest scripts.tests.test_third_party_licenses` and observe failure because the renderer does not exist.
- [ ] Implement `argparse` with `--variant`, `--image-id`, and `--output`; require one or more package records, nonempty name/version/arch/license/source, no conflicting duplicate package, absolute license paths, and no orphan file records. Use a temporary file next to the output and `os.replace` only after complete parsing. Keep the report an inventory of RPM metadata and paths, without asserting every component's legal compatibility.
- [ ] Run the test green; remove the renderer temporarily and verify the test fails, then restore it. Run the renderer against a real `forjaos:f0-002` RPM query and inspect package count and header.
- [ ] DoD: deterministic nonempty report from the real image; malformed or empty input leaves no report. Commit `feat(scripts): generate image license inventory`.

## Task 2 — Publish the report from daily CI (G4, ADR-007, ADR-002, NFR-024)

**Files:** modify `.github/scripts/daily-image.sh`, `scripts/tests/test_daily_image.sh`, `.github/workflows/daily-image.yml`, and `scripts/tests/test_daily_image_workflow.py`.

- [ ] Extend the shell test's fake `podman run --entrypoint /usr/bin/rpm` to emit a package and an `l`-flagged license file. Set `LICENSE_REPORT_DIR` to the test's temporary directory. Assert a report for each variant, generation before `scripts/check-branding.sh` and any push, and no push if the fake RPM command fails. Extend the workflow test to require a pinned artifact action, variant-specific name/path, `if-no-files-found: error`, and an explicit status condition that uploads after the build step fails.
- [ ] Run `bash scripts/tests/test_daily_image.sh` and `python3 -m unittest scripts.tests.test_daily_image_workflow`; observe red before editing production files.
- [ ] In the daily script, after local image identity checks and before branding, run `podman image inspect --format '{{.Id}}'` and `podman run --rm --entrypoint /usr/bin/rpm "$local_image" -qa --queryformat 'P\t%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\t%{LICENSE}\t%{SOURCERPM}\n[F\t%{FILENAMES}\t%{FILEFLAGS:fflags}\n]' | python3 .github/scripts/generate_third_party_licenses.py --variant "$variant" --image-id "$image_id" --output "$LICENSE_REPORT_DIR/$variant/THIRD_PARTY_LICENSES.md"`. Preserve `set -o pipefail` so failed RPM queries fail the job.
- [ ] In the workflow, set `LICENSE_REPORT_DIR` to `${{ runner.temp }}/licenses` on the build step. Add a post-build `actions/upload-artifact` step pinned to its verified commit SHA (MIT), with `if: ${{ always() }}`, `name: third-party-licenses-${{ matrix.variant }}`, `path: ${{ runner.temp }}/licenses/${{ matrix.variant }}/THIRD_PARTY_LICENSES.md`, and `if-no-files-found: error`. Do not grant extra token permission.
- [ ] Run both tests green; mutate the generation call or artifact path to prove the corresponding test fails, then restore. Validate YAML using actionlint.
- [ ] DoD: both variants produce separate artifacts from their own image; branding remains a publication blocker but its failure does not discard an already generated report. Commit `feat(image): upload per-variant license reports` (body records the pinned action's MIT license).

## Gate test and delivery (G4, ADR-033)

- [ ] Run the root suite and scripts-folder suite: Python unittests, shell tests, token check, agent sync, roadmap branch validation, and tela spec check. Run `actionlint` for the workflow. Recheck a real image report independently from test fixtures.
- [ ] Open a PR linked to issue #26 with exact outputs and the branding limit. Review from a clean Codex context, post `review: 8/8` only with all eight items met, and ship after green CI and current-main rebase.
