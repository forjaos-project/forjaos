# F0-002 Minimal Image Implementation Plan

> **For agentic workers:** Execute these tasks inline, in order. Each task ends with its own commit; image changes use red, green, refactor.

**Goal:** Build a minimal ForjaOS bootc image from the published Bazzite desktop base, with the ForjaOS identity and image-signature policy.

**Architecture:** ADR-0032 replaces only the two unavailable or unsuitable base references in ADR-001. One `Containerfile` uses the NVIDIA base by default and accepts the AMD/Intel base as a build argument. A small Python build helper updates the base's `os-release` and adds a narrowly scoped signature rule while preserving its other policy entries.

**Tech Stack:** bootc OCI image, Containerfile, Python 3 already present in the base, `unittest`, `skopeo` and Docker/Podman.

**Source:** issue #6, FR-001, FR-003, ADR-001, ADR-002, ADR-003, ADR-030, ADR-031; direct human decision of 2026-11-09. No screen is involved.

## File map

- `docs/adr/0032-bazzite-desktop-base.md` — records the base correction and verification evidence.
- `docs/PRD.md` — aligns ADR-001, the architecture drawing, variant table, FR-001, and phase 0 with ADR-0032.
- `docs/roadmap/roadmap.json` — corrects F0-002's title and adds one deferred DX item with scope `image/` and `depends_on: ["F0-002"]`.
- `image/build_files/configure_image.py` — changes only the image rootfs identity and signature-policy files.
- `scripts/tests/test_configure_image.py` — tests the helper against isolated rootfs fixtures.
- `image/Containerfile` — selects the published base, applies the helper, and runs `bootc container lint`.

## Task 1 — Record the base decision (ADR-001, ADR-003, FR-001)

- [ ] Create `docs/adr/0032-bazzite-desktop-base.md` with the exact public image references, their `skopeo inspect` digests, `containers.bootc=1`, the `modinfo` result `license: Dual MIT/GPL`, and the official Bazzite DX pipeline URL. State that only ADR-001's base-image choice is revoked; the ForjaOS image names remain `forjaos` and `forjaos-nvidia-open`.
- [ ] Modify only the base references in `docs/PRD.md`: ADR-001, drawing line 133, variant rows 158–159, FR-001 and phase-0 line 471. Keep `PRETTY_NAME="ForjaOS X.Y"` from ADR-031.
- [ ] Verify: `rg -n 'bazzite-dx-nvidia-open|bazzite-dx:stable' docs/PRD.md` returns no matches; `rg -n 'Dual MIT/GPL|bazzite-nvidia-open:stable|bazzite:stable' docs/adr/0032-bazzite-desktop-base.md` finds the evidence and both bases; `git diff --check` passes.
- [ ] Commit: `adr(docs): correct Bazzite desktop base images`.

## Task 2 — Schedule the DX layer separately (FR-001, FR-005, ADR-0032)

- [ ] Update the F0-002 title in `docs/roadmap/roadmap.json` to the actual NVIDIA base. Add item `F1-010` with phase `1`, status `todo`, scope `image/`, `depends_on: ["F0-002"]`, and a title requiring reproduction of Bazzite DX components from upstream scripts with compatible-license verification. The new item does not install any DX component in F0-002.
- [ ] Verify: `python3 scripts/roadmap.py validate --branch` passes; a Python assertion over `roadmap.json` confirms the new item's dependency, scope, and status; `git diff origin/main -- docs/roadmap/roadmap.json` shows only F0-002 and the new item.
- [ ] Commit: `docs(roadmap): schedule Bazzite DX layer`.

## Task 3 — Configure identity and signature trust (FR-003, ADR-030, ADR-031)

- [ ] Create `scripts/tests/test_configure_image.py` first. Its temporary rootfs has `/etc/os-release` linked to `/usr/lib/os-release`, a base policy containing other registry rules, and a public key fixture. Assert `NAME="ForjaOS"`, `PRETTY_NAME="ForjaOS 0.1"`, `VERSION_ID=0.1`, `ID=forjaos`, `ID_LIKE=fedora`, the project URLs, and preservation of unrelated base fields and policy rules. Assert the `ghcr.io/forjaos-project/forjaos-nvidia-open` rule is `sigstoreSigned` with `matchRepository` and `/etc/pki/containers/forjaos.pub`. Assert missing key/policy fails without silently weakening trust.
- [ ] Run `python3 -m unittest scripts.tests.test_configure_image -v` and observe the missing-helper failure.
- [ ] Create `image/build_files/configure_image.py` using only Python stdlib. It accepts `--root`, `--public-key`, and `--image-name`; changes the `os-release` target inside that root, copies the public key, and loads then extends the existing `policy.json` instead of replacing its defaults or other registry rules. `--image-name` accepts exactly `forjaos` or `forjaos-nvidia-open`. Keep the base's nonidentity metadata and do not add packages, services, or privacy rules.
- [ ] Run the same unittest and observe it pass; run the helper again on the fixture to confirm idempotence.
- [ ] Commit: `feat(image): configure ForjaOS identity and image trust`.

## Task 4 — Wire the bootc image (FR-001, FR-003, ADR-0032)

- [ ] Add an integration assertion to `scripts/tests/test_configure_image.py` that checks the `Containerfile` has a published NVIDIA default, a build argument for the non-NVIDIA base, invokes the helper with `cosign.pub`, and finishes with `bootc container lint`. Run it and observe failure because the file is absent.
- [ ] Create `image/Containerfile` with `ARG BASE_IMAGE=ghcr.io/ublue-os/bazzite-nvidia-open:stable` before `FROM ${BASE_IMAGE}`, plus `ARG IMAGE_NAME=forjaos-nvidia-open` after `FROM`; the AMD/Intel build overrides the base with `ghcr.io/ublue-os/bazzite:stable`. Copy only the helper and public key from the repository-root build context; execute the helper and `bootc container lint`.
- [ ] Run the unittest. Build locally with `docker build -f image/Containerfile -t forjaos:f0-002 .` and inspect the resulting `/etc/os-release`, public key, and scoped policy. `docker build --build-arg BASE_IMAGE=ghcr.io/ublue-os/bazzite:stable --build-arg IMAGE_NAME=forjaos` is run when disk space permits; the already verified upstream `skopeo inspect` is the minimum proof for that base in this slice.
- [ ] Commit: `feat(image): build minimal bootc image`.

## Gate test and handoff

- [ ] Run `python3 -m unittest discover -s scripts/tests -p 'test_*.py'`, `scripts/run-shell-tests.sh`, `scripts/check-tokens.sh`, `scripts/check-agents-sync.sh`, `python3 scripts/roadmap.py validate --branch`, `python3 scripts/gen_tela_specs.py --check`, and `scripts/check-branding.sh` (currently a documented stub for F0-004). Record the distinction between static tests, real image build, and deferred VM `bootc switch`.
- [ ] Prove the new tests fail when the helper is temporarily reverted, then restore it. Run `git diff --check` and check that `docs/STATUS.md` and `docs/roadmap/index.html` are absent from the diff.
- [ ] Open a PR using the repository template with command output and `Implementado por: Codex`; request review from Claude Code. Codex does not execute its own review or ship gate.
