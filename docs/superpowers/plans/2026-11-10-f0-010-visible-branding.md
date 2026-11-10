# F0-010 Visible Branding Gate

**Goal:** Close issue #25 by replacing inherited Fedora/Bazzite desktop art and visible application metadata, then publish both signed `:testing` images with a checker that covers the menu and the installed application catalog.

**Architecture:** Ship the approved ForjaOS wallpaper and Guara art in a small Plasma RPM. Preserve the Fedora KDE dependency graph through exact base RPM capabilities and a narrow `/usr/share` overlay. Remove the unneeded Bazzite Portal package; hide or remove branded launcher and AppStream records without changing `/etc` or gaming functionality. Extend the checker to inspect user-visible desktop entries and application metadata. Keep the fuller panel layout, theme switching and HERO shortcuts in F1-006.

**Tech Stack:** Python 3 standard library, SVG/PNG, Plasma 6 KPackage, RPM, Docker/Podman, GitHub Actions and Cosign. Plus Jakarta Sans uses upstream OFL-1.1; the existing Fedora JetBrains Mono RPM supplies the mono font. FR-002, FR-055, ADR-027, ADR-028, G4 and NFR-024 govern this change.

## Tasks

### 1. Approved ForjaOS art (FR-002, FR-055, ADR-027, G4)

- Files: `brand/mascot/`, `brand/wallpapers/`, `brand/LICENSES.md`, `brand/tests/test_plasma_assets.py`.
- Test first: four 3840x2160 images, palette-bound SVG waves, embedded approved Guara source, recorded art ownership. Run red before restoring assets.
- Implement the previously approved Guara head and dark/light abstract/Guara wallpapers. Run the tests and mutate one dimension to prove sensitivity.
- DoD: the four renders are self-contained, sharp, and contain no inherited brand. Commit `feat(brand): add ForjaOS wallpapers` and the approved refinement `fix(brand): refine Guara wallpaper artwork`.

### 2. Minimal Forja desktop identity (FR-002, ADR-027/028, G4)

- Files: `brand/plasma/`, `brand/fonts/`, `brand/shortcuts/`, `docs/shortcuts.md`, `brand/tests/test_plasma_assets.py`.
- Test first: Forja look-and-feel and dark/light resources resolve from the palette; first-login defaults point to Forja wallpaper; font license and available terminal action are valid.
- Install the existing tested theme and font assets. The F1-006 layout remains a provisional base and is not accepted as FR-052; reserved shortcuts remain explicitly unavailable until their feature item lands.
- DoD: KPackage loads, `fc-match` resolves Plus Jakarta Sans and JetBrains Mono, tokens pass. Commit `feat(brand): add Forja Plasma layout` and `feat(brand): set desktop fonts and shortcuts`.

### 3. Image package and profile cleanup (FR-002, G4)

- Files: `image/Containerfile`, `image/build_files/forjaos-plasma.spec`, `image/build_files/build_plasma_rpm.sh`, `image/build_files/configure_plasma.py`, `image/build_files/forjaos-branding.spec`, `scripts/tests/test_plasma_image.py`.
- Test first: exact base capabilities, explicit DNF removal without deleting Plasma, profile cleanup confined to `/usr/share`, no Fedora icon aliases. Run red before copying implementation.
- Build both image variants and run `dnf check`, `rpm -V forjaos-plasma`, `bootc container lint`, and unchanged checker. Mutate a disposable image to prove checker failure.
- DoD: zero inherited brand findings under existing scanned paths in both images. Commit `feat(image): install Forja desktop branding`.

### 4. Menu and application catalog gap from clean review (FR-002, NFR-024)

- Files: `scripts/check_branding.py`, `scripts/tests/test_check_branding.py`, `image/build_files/configure_plasma.py`, `image/Containerfile`, `scripts/tests/test_plasma_image.py`.
- Test first: a visible `.desktop` with branded Name/Comment/Icon and an AppStream desktop-application or operating-system entry with branded Name/Summary fail, while hidden/internal command names do not create false positives. Run red.
- Remove the unneeded Bazzite Portal RPM, remove unowned documentation/forum launchers, and remove Bazzite Updater AppStream metadata while keeping the CLI and Steam/Deck scripts. No `/etc` changes.
- DoD: menu/AppStream metadata no longer advertises Fedora/Bazzite/Bluefin/Universal Blue; checker passes on both images and fails against disposable brand regression. Remove the unused Fira Code font and Fedora OS catalog component. Commit `fix(image): remove visible inherited applications` and `fix(review): remove inherited OS metadata and font`.

### 5. Visual proof, review and ship (FR-002, ADR-033)

- Files: `docs/evidence/f0-010/`, `docs/roadmap/roadmap.json` (only F0-010).
- Run root tests, brand tests, image build/checker, token and spec checks. Publish signed candidate images on the feature branch. In the disposable `ForjaOS-Test` VM, inspect desktop launcher and the installed application catalog, capturing actual ForjaOS wallpaper and no visible Bazzite entries; record the exact image digest. Do not claim hardware acceptance from this VM. The PRD's Discover-vs-Bazaar divergence is tracked in issue #40; the current base installs Bazaar.
- Open the PR with command outputs, obtain independent clean-context `review: 8/8` and visual evidence, require green CI, mark F0-010 done, squash merge, then run `daily-image` on main and confirm both signed `:testing` digests before closing #25.

### 6. Boot splash regression found in VM (FR-002, ADR-033)

- Files: `scripts/check_branding.py`, `scripts/tests/test_check_branding.py`, `image/Containerfile`, `image/build_files/rebuild_initramfs.sh`.
- Test first: a rootfs with a ForjaOS logo but a stale Bazzite logo inside `initramfs.img` must fail the checker; the same logo in both must pass. Verify the current published candidate fails before changing the build.
- Regenerate each installed kernel initramfs after the branding RPM replaces `/usr/share/pixmaps/system-logo-white.png`; do not change the kernel or Secure Boot settings in the distributed image. Compare the embedded and rootfs logo bytes in both rebuilt image variants.
- DoD: the boot image contains the ForjaOS logo, the checker is green on both variants, and a fresh VM boot no longer shows Bazzite Plymouth artwork. Commit `fix(image): rebuild branded initramfs`.

### 7. Plasma Login wallpaper regression found in VM (FR-002, FR-055, ADR-033)

- Files: `image/build_files/configure_plasma.py`, `scripts/check_branding.py`, `scripts/tests/test_plasma_image.py`, `scripts/tests/test_check_branding.py`.
- Test first: a rootfs whose Plasma Login default resolves through `default.jxl` to inherited `convergence.jxl` fails; a rootfs whose login and lock-screen wallpaper links resolve to the ForjaOS artwork passes. Confirm the published candidate fails before the image fix.
- Replace the unowned legacy `convergence.jxl` artwork with a JPEG XL conversion of the approved ForjaOS dark wallpaper, preserve the existing `/etc/xdg/kscreenlockerrc` path without editing `/etc`, and remove the unowned legacy PNG. Keep Plasma Login's packaged default setting valid; add a checker invariant for its resolved wallpaper.
- DoD: the login and lock-screen wallpaper paths resolve to ForjaOS artwork in both image variants, the checker detects the previous candidate, and a fresh VM login no longer shows Bazzite art. Commit `fix(image): replace inherited login wallpaper`.

## Scope boundary

F1-006 still owns the complete FR-050/052/058 DoD: instant light/dark switching, all required panel/dock items, all five shortcuts, and matching desktop comparisons. This F0 item only removes the visible inherited brand that blocks the phase-0 image pipeline.
