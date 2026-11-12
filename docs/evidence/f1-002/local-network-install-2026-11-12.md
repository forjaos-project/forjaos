# F1-002 local network installation probe — 2026-11-12

Requirements: FR-010, NFR-020, ADR-0035. This is a diagnostic VM probe, not physical USB or Secure Boot acceptance.

## Input and environment

- Diagnostic installer ISO: SHA-256 `9218205a8e74772010e13b4b888a741d3222977bd72d4bfff8d917721f425f7c`. It was reconstructed locally from the earlier installer build and includes the ForjaOS product identity fix. A disposable Kickstart and command-line boot arguments were injected for unattended VM testing. It is **not** the `v0.1.0-rc.1` Release asset.
- Payload source: `registry:ghcr.io/forjaos-project/forjaos@sha256:aedee6c3c67487ed610b3e9a067278d285474d855758ed3382ac79291a92189a`.
- QEMU/KVM, UEFI OVMF, 32 GiB disposable virtual disk, 6 GiB RAM, 4 vCPUs, user-mode network. The guest had no access to host disks.
- A separate negative check replaced the installer's trusted key with another valid P-256 public key. `skopeo copy` rejected the payload with `cryptographic signature verification failed` before copying layers.

## Observed result

1. Anaconda partitioned the disposable disk, then reported `layers needed: 271 (4.9 GB)` for the signed payload.
2. The installer reported `Installation complete!`, `Bootc deployment complete` with the source digest above, and `Complete!`.
3. The virtual disk booted without the ISO. Initial system setup triggered one reboot. The second disk-only boot reached `ForjaOS 0.1` and `forjaos login:` on the serial console; [capture](installed-login-2026-11-12.png).
4. The installed kernel loaded SELinux policy. No SELinux or firewall setting was relaxed for this probe.

This proves the network installation path in a local VM. The exact Release candidate ISO, the interactive disk selection, physical USB methods, hardware boot and Secure Boot remain separate gates.
