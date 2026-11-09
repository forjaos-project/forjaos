# F1-011 Image Identity Implementation Plan

**Goal:** Give both bootc variants their own ForjaOS icon and image reference so the OS identity and update metadata no longer point at the Bazzite base (FR-002, FR-003, FR-053).

**Architecture:** Extend the existing image configuration helper to replace the inherited Universal Blue image metadata and set the freedesktop `LOGO` icon name. Copy the already approved ForjaOS PNG sizes from `brand/logo/png` into hicolor `apps/` during the image build. Keep the bootc signature policy and base-specific metadata unchanged. Run the real branding checker after building both variants to measure the remaining inherited surfaces for issue #25; do not change the checker (ADR-002, FR-002).

**Tech Stack:** Python standard library, Containerfile, existing CC BY-SA 4.0 logo assets, Python unit tests, Docker/Podman image build. No new runtime package or repository (G4).

**Entry:** Issue #30 defines objective F1-011 acceptance. The user explicitly asked to resolve issue #25; this authorizes taking the phase-1 roadmap item early while phase 0 continues. The branch has a published claim. No UI screen implementation is part of this item.

## File map

- `image/build_files/configure_image.py` — `LOGO` icon name, ForjaOS image-info fields, icon installation.
- `image/Containerfile` — copy the existing PNG assets into the build and pass their directory to the helper.
- `scripts/tests/test_configure_image.py` — synthetic rootfs behavior for both variants and failure atomicity.
- `scripts/tests/test_image_containerfile.py` — Containerfile passes the icon assets and variant to the helper.
- `docs/roadmap/roadmap.json` — only F1-011 transitions `claim` → `done` at ship.

## Task 1 — Correct published image identity (FR-002, FR-003, ADR-002)

- [ ] Extend `scripts/tests/test_configure_image.py` first with inherited `image-info.json` fixtures for each variant. Assert `image-name`, `image-vendor`, signed `image-ref`, `image-tag` and `image-branch` point to the variant's `:testing` stream while unrelated base metadata is preserved. Assert missing or malformed metadata prevents identity writes. Run red against the old helper.
- [ ] Extend `image/build_files/configure_image.py` to read and validate metadata before writing; update only the required identity fields. The reference uses `ostree-image-signed:docker://ghcr.io/forjaos-project/<variant>` and the current `testing` stream. DoD: both variants point to their own signed reference, never the inherited Bazzite reference.
- [ ] Run the focused tests green; demonstrate that removing the image-info update makes the new test red. Commit: `feat(image): point metadata to ForjaOS images`.

## Task 2 — Install the ForjaOS icon (FR-002, FR-003, FR-053)

- [ ] Add tests first to `scripts/tests/test_configure_image.py` and `scripts/tests/test_image_containerfile.py`. Assert `LOGO=forjaos-icon`, byte-for-byte PNG installation into hicolor for every size in `brand/logo/png`, rejection of a missing icon source, and Containerfile `COPY` plus `--icons-dir` wiring. Observe red.
- [ ] Extend the helper with an `--icons-dir` input and install the approved PNGs. Extend `image/Containerfile` to copy the assets and pass the input; remove build-only copies afterward. No image generation or palette edit. DoD: `LOGO` resolves to installed own icon and all published PNG sizes match source.
- [ ] Run tests green and demonstrate a missing COPY breaks the structural test. Commit: `feat(image): install ForjaOS logo in hicolor`.

## Gate test and delivery (FR-002, ADR-033)

- [ ] Run root and image-area checks: Python unittest, shell suite, tokens, agents sync, branch roadmap validation, tela spec check, both real image builds, `bootc container lint`, and `check-branding.sh --image` on both. Record the remaining finding count in issue #25 without weakening the checker.
- [ ] Open the PR with issue #30, exact outputs and the issue #25 residual. Review in a clean context; ship only after `review: 8/8` and CI green. The broader visual rebranding remains tracked until the daily image run actually publishes both `:testing` tags.
