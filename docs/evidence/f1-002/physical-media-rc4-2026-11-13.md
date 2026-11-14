# RC4 physical installer media results — F1-002

Date: 2026-11-13

## Test image and hardware

- ISO: `forjaos.iso` (RC4, generic variant), built locally at `D:\ForjaOS-local-test-rc4\forjaos.iso`.
- Length: 2,085,693,440 bytes.
- Expected SHA-256: `706e455295c71227091e41a81dbef6b7d1a0539768b142b7076899e91115c9a4`.
- Notebook: Dell Inspiron 15; Intel WiFi Link 5100 AGN (`wlp12s0`). Exact Inspiron model and Secure Boot state were not recorded.
- Test USB: SanDisk Cruzer Blade, 15.7 GB. No installation was started and no internal disk was modified.

## Results by writing method

| Method | Media write and integrity | Physical boot | Result |
| --- | --- | --- | --- |
| Fedora Media Writer | RC4 written directly to the SanDisk USB | Reached Anaconda welcome; Intel Wi-Fi networks appeared and connected without Ethernet | Pass for this notebook and ISO |
| Ventoy 1.1.18 | Ventoy checksum against `forjaos.iso.sha256` reported success | Normal and GRUB2 boot attempts failed. The initramfs report showed repeated `/dev/sr0` sector 128 read errors, then failure to mount `/dev/mapper/live-rw` | Fail on this notebook; do not claim Ventoy compatibility |
| GNU `dd` in Ubuntu WSL2 | WSL device `/dev/sdg`, mapped from Windows Disk 2 / SanDisk Cruzer Blade after verifying model, size, USB bus ID, and that partitions were unmounted. `dd` wrote exactly 2,085,693,440 bytes with `conv=fsync` in 387.353 s (5.4 MB/s). Reading the same byte range back produced the expected SHA-256 above. | Reached Anaconda welcome on the Dell Inspiron 15 | Pass for this notebook and ISO |

## Limits

- The physical evidence covers the generic RC4 ISO on one Dell notebook. It does not cover the NVIDIA variant, desktop reference hardware, Secure Boot, disk installation, or Windows dual boot.
- The Ventoy failure is a recorded incompatibility on this test setup; the checksum passing does not establish successful boot.
- The screenshots were supplied during the test conversation. They are not stored here; the Wi-Fi screenshot exposed home-network identifiers and was intentionally not committed.

## Acceptance status

The Fedora Media Writer and `dd` paths booted to Anaconda. FR-014 is not fully accepted: Ventoy failed on the tested notebook, and the desktop/Secure Boot hardware checks remain outstanding.
