# F0-008 Bootc VM Cycle Implementation Plan

**Goal:** Prove a signed ForjaOS image can replace the Bazzite base in a VM, boot a newer image through `bootc upgrade`, and return to the previous digest through `bootc rollback` (FR-001, FR-008).

**Architecture:** Keep image publication and VM validation separate. The validation controller creates a dedicated mutable GHCR test tag from two already signed ForjaOS digests, runs a Bazzite VM, executes bootc through the QEMU guest agent, and checks the booted digest after every reboot. A manual Hyper-V run records the same transitions. The CI test tag is never a release channel. `:stable` remains subject to the weekly promotion gates in PRD 5.4 and NFR-040.

**Tech Stack:** Python standard library for status assertions and VM orchestration, GitHub Actions, official Ubuntu Podman/Skopeo/libvirt/QEMU/virtinst packages, and the pinned official `bootc-image-builder` container (Apache-2.0) on an ephemeral runner. No package or repository is added to the ForjaOS image (ADR-002, G4). The upstream host-setup action is excluded because it performs broad cleanup and direct `/etc` edits that conflict with the repository's destructive-action rule. The runner uses a rootful, short-lived image-builder container to create a Bazzite QCOW2, then an unprivileged libvirt session to boot it. This replaces `bcvk` after repeated CI failures while preparing its ephemeral installation VM, including on Ubuntu 26.04; a detached Podman exec probe passed on the same runner.

**Entry:** Issue #44 states the FR-001/FR-008 acceptance criteria; roadmap F0-008 is claimed on `feat/F0-008-bootc-vm-validation`. Issue #43 tracks the latest daily build failure and must be resolved before a current image is used as a successful upgrade target.

## File map

- `image/tests/assert_bootc_state.py` — validate the booted, staged, and rollback digest from `bootc status --json`.
- `scripts/tests/test_assert_bootc_state.py` — success and failure cases for each transition.
- `image/tests/run_bootc_vm_cycle.py` — host-side VM, registry tag, reboot, and guest-agent controller.
- `scripts/tests/test_bootc_vm_cycle.py` — fake external commands to prove order and fail-closed behavior.
- `.github/workflows/bootc-vm.yml` — manual and weekly VM job with pinned tools, limited permissions, and archived evidence.
- `scripts/tests/test_bootc_vm_workflow.py` — workflow structure and security checks.
- `docs/evidence/f0-008/vm-cycle-2026-11-11.md` — observed local and CI digests, commands, and limits.
- `docs/roadmap/roadmap.json` — only F0-008 moves from the published claim to `done` at ship.

## Task 1 — Validate bootc deployment states (FR-001, FR-008)

- Write `scripts/tests/test_assert_bootc_state.py` first and observe failures against the absent assertion script. Cover missing booted digest, mismatched staged/booted/rollback digests, and the successful three-reboot cycle.
- Implement `image/tests/assert_bootc_state.py` with explicit expected digest and state arguments. Reject equal baseline and upgrade digests; never infer success from a staged deployment alone.
- Run the tests green and remove a digest comparison temporarily to prove the test fails. DoD: each transition can only pass when `status.booted.image.imageDigest` equals the expected full digest.
- Commit `feat(image): assert bootc VM deployment states`.

## Task 2 — Drive the real VM cycle (FR-001, FR-008, ADR-030)

- Write `scripts/tests/test_bootc_vm_cycle.py` first with fake registry, libvirt, and guest-agent command responses. Observe red before the controller exists. Assert signature verification occurs before tag publication and that any guest command or digest mismatch stops the cycle.
- Implement `image/tests/run_bootc_vm_cycle.py`: verify two distinct signed digests, create one dedicated test tag, boot a Bazzite VM, switch, reboot, advance the tag, upgrade, reboot, rollback, reboot, and collect `bootc status --json` at each state. Keep credentials in process memory and mask them from logs (NFR-024).
- After the real switch exceeded 30 minutes in run 43085084234, add a bounded guest registry preflight and print guest filesystem capacity before transfer. Keep status reads short; allow up to 3600 seconds for switch/upgrade and 300 seconds for rollback. The workflow retains its independent 180-minute ceiling, which can reject a run before a combination of worst-case operation deadlines. Redirect mutating commands to a guest-only temporary `/run` log and collect a sanitized tail on failure, without losing the original error or repeating the mutation. Redact credential values and signed URL queries before emitting diagnostics (NFR-024). Tests must first reproduce missing connectivity checks, absent timeout diagnostics, diagnostic failures masking the original failure, and disclosure of synthetic signed URLs.
- Run the fake tests green and remove the rollback assertion temporarily to prove the test fails. DoD: no successful exit without three observed booted digests and an actual rollback reboot.
- Commit `feat(image): exercise bootc switch upgrade and rollback in VM`.

## Task 3 — Run the VM test in CI (FR-008, NFR-040, G4)

- Write `scripts/tests/test_bootc_vm_workflow.py` first; observe red before the workflow exists. Check manual and weekly triggers, exact branch/ref guard, pinned external actions and image-builder container digest, narrow permissions, and evidence upload.
- Add `.github/workflows/bootc-vm.yml` to run the controller on a GitHub-hosted Ubuntu VM with nested KVM preflight, official Ubuntu VM packages, libvirt, QEMU guest agent, and adequate disk checks. Generate a fresh Bazzite QCOW2 with `bootc-image-builder`, import it using `virt-install`, and pass its path to the controller. Use the last known signed baseline and a newly published `:testing` digest. A failed preflight is a failed gate, not a skipped test. Keep `:stable` untouched.
- The stock Bazzite guest confines QEMU guest agent to `virt_qemu_ga_t`, which denies `bootc` execution and transient systemd units. Subject to the maintainer's explicit AGENTS.md rule-7 approval, apply `image/tests/ci-guest-agent.toml` only while building the disposable Bazzite disk. Its single service drop-in selects `unconfined_service_t` for this VM's guest agent. Start through `/usr/bin/env`, a generic binary entrypoint permitted for that domain, because the specialized QEMU executable cannot be the initial entrypoint (confirmed by the journal in run 43079234668). Pass the explicit virtio-serial channel to QEMU. Before running `bootc`, assert that SELinux remains enforcing and the expected service context is active. No ForjaOS container layer or runner-host policy is changed (FR-008, ADR-022, NFR-020).
- Run structural tests green and mutate the ref guard to prove failure. DoD: a completed CI run contains `switch`, `upgrade`, and `rollback` evidence with distinct digests and no unverified promotion.
- Commit `feat(image): verify bootc lifecycle in CI`.

## Task 4 — Record Hyper-V and CI evidence (FR-001, FR-008, ADR-033)

- On `ForjaOS-Test`, capture `bootc status --json` before and after each command and reboot. Verify the running image digest, not only the staged entry; include the exact GHCR digests and Secure Boot state in `docs/evidence/f0-008/vm-cycle-2026-11-11.md`.
- Run the root and image test gates, plus the CI VM workflow. Record the CI run URL, result, and any objective limitation in the evidence file. DoD: the evidence lets the reviewer reproduce the three transitions and distinguish local VM proof from CI proof.
- Commit `docs(image): record bootc VM cycle evidence`.

## Test, review, and ship (FR-001, FR-008, ADR-033)

- Run root Python tests, shell tests, token and agent checks, branch roadmap validation, tela spec check, branding check on the tested image, and the applicable image build/lint. Paste exact results in the PR.
- Open a PR linked to #44; use a fresh-context Codex reviewer for all eight checks. Fix each finding in a separate `fix(review):` commit. Ship only with `review: 8/8` and green CI.
- Record the `:stable` limitation explicitly. PRD 5.4 and NFR-040 require the broader weekly VM/performance gate before release promotion; F0-008 does not bypass it.
