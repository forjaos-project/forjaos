# F1-002 candidate `v0.1.0-rc.1` — local VM installation

Requirements: FR-010, NFR-011, NFR-020, ADR-0035 and ADR-0036. This is installation evidence for the exact draft Release assets. It does not replace FR-014 physical media or Secure Boot tests.

## Assets and integrity

| Asset | Bytes | SHA-256 | Signed payload source |
| --- | ---: | --- | --- |
| `forjaos.iso` | 2,066,470,912 | `abb545ae49676cd08cf06412f67f798732d9f78df91af12bbe1e68ebb971b6c2` | `ghcr.io/forjaos-project/forjaos@sha256:aedee6c3c67487ed610b3e9a067278d285474d855758ed3382ac79291a92189a` |
| `forjaos-nvidia-open.iso` | 2,066,475,008 | `519738fa465f1adab173f0b59304d9c039437ec090ee92bfcebefc26a737f048` | `ghcr.io/forjaos-project/forjaos-nvidia-open@sha256:4581ab7b592662ae8aa7424aed566e4dedb506b9d5a87f6f75caffeecdc5210b` |

The draft Release workflow [43299447486](https://github.com/forjaos-project/forjaos/actions/runs/43299447486) built both ISOs, verified both bundles, downloaded the Release assets and verified them again. After downloading each asset locally, SHA-256 matched the combined `SHA256SUMS` and `cosign verify-blob --key cosign.pub --bundle <asset>.sigstore.json <asset>` returned `Verified OK`. The rebuilt PR workflow [43307401153](https://github.com/forjaos-project/forjaos/actions/runs/43307401153) passed both build and boot jobs. The candidate uses `:testing`; it is not a stable release.

## Reproduction procedure

Use a Linux host or an isolated Linux container with KVM, QEMU, OVMF, xorriso and Python 3. Only attach a newly created disposable virtual disk. The ISO itself remains unchanged. Its kernel and initramfs are extracted to a scratch directory and the live root is read from the ISO. The CI separately exercises the ISO's UEFI bootloader; direct kernel boot here only supplies the unattended test arguments.

1. Verify the downloaded ISO against `SHA256SUMS` and its cosign bundle. Select the source digest from the table above.
2. Extract the kernel and initramfs from that ISO. Confirm the ISO's volume label is `ForjaOS-Installer`:

   ```bash
   xorriso -osirrox on -indev "$iso" \
     -extract /images/pxeboot/vmlinuz "$scratch/vmlinuz" \
     -extract /images/pxeboot/initrd.img "$scratch/initrd.img"
   ```
3. Write this disposable Kickstart in the scratch directory, replacing `<SOURCE>` and `<TARGET>` with the matching variant from the table (`<TARGET>` is the corresponding `ghcr.io/forjaos-project/<variant>:testing`):

   ```kickstart
   #version=RHEL10
   lang en_US.UTF-8
   keyboard us
   timezone UTC --utc
   network --bootproto=dhcp --device=link --activate
   rootpw --lock
   user --name=validation --lock
   zerombr
   clearpart --all --initlabel
   autopart --type=plain
   bootc --source-imgref registry:<SOURCE> --target-imgref <TARGET>
   reboot
   ```

4. Save the rendered Kickstart as `$scratch/install.ks`. Inside the isolated VM host/container, start `python3 -m http.server 8000 --bind 0.0.0.0 --directory "$scratch"` without publishing the port. QEMU user networking provides `10.0.2.2` to reach this server. Create and boot the disposable disk:

   ```bash
   cp /usr/share/OVMF/OVMF_VARS_4M.fd "$scratch/OVMF_VARS.fd"
   qemu-img create -f qcow2 "$scratch/disk.qcow2" 32G
   qemu-system-x86_64 -accel kvm -machine q35 -m 6144 -smp 4 \
     -drive if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
     -drive "if=pflash,format=raw,unit=1,file=$scratch/OVMF_VARS.fd" \
     -kernel "$scratch/vmlinuz" -initrd "$scratch/initrd.img" \
     -append 'root=live:CDLABEL=ForjaOS-Installer rd.live.image inst.cmdline inst.notmux inst.nokill inst.ks=http://10.0.2.2:8000/install.ks console=ttyS0' \
     -cdrom "$iso" -drive "file=$scratch/disk.qcow2,format=qcow2,if=virtio" \
     -netdev user,id=net0 -device virtio-net-pci,netdev=net0 \
     -vga std -display none -serial "file:$scratch/install-serial.log" -no-reboot
   ```

5. Require the serial log to show `Bootc deployment in progress` with the exact source digest, `Installation complete!`, `Bootc deployment complete` and `Complete!`. Stop the installer VM after completion. Boot the virtual disk alone using the same OVMF drives, `-boot order=c`, the QCOW2 disk, the network and `-serial file:$scratch/installed-serial.log`; omit `-kernel`, `-initrd` and `-cdrom`. Initial setup may trigger one reboot; boot the same disk again and require `ForjaOS 0.1` and `forjaos login:`.

The test Kickstart is deliberately different from the interactive default: it selects only the disposable virtual disk and locks both accounts. The initial NVIDIA probe used a disposable local test account; the locked-account Kickstart above was used for the generic probe and is the credential-free reproduction path. No host disk or signing key is passed to the guest. The installer still uses its packaged signed-image policy; a separate negative test with another valid P-256 key rejected the payload before copying any layers.

## Observed results

- **NVIDIA open:** source digest `4581ab7b592662ae8aa7424aed566e4dedb506b9d5a87f6f75caffeecdc5210b`; Anaconda reported `Complete!` after about 1,091 seconds. The first disk-only boot performed initial setup and restarted. The second reached [ForjaOS login on VT3](candidate-nvidia-installed-login-2026-11-12.png). The QCOW2 file reached about 27 GB during installation.
- **Generic:** source digest `aedee6c3c67487ed610b3e9a067278d285474d855758ed3382ac79291a92189a`; Anaconda reported `Complete!` after about 1,135 seconds using the locked-account Kickstart above. The first disk-only boot performed initial setup and restarted. The second reached [ForjaOS login on VT2](candidate-generic-installed-login-2026-11-12.png). The QCOW2 file reached about 24 GB during installation.

The installer serial logs contain these completion records (elapsed seconds):

```text
NVIDIA 1084.778621  Deploying image: Installation complete!
NVIDIA 1084.820566  Bootc deployment complete: registry:ghcr.io/forjaos-project/forjaos-nvidia-open@sha256:4581ab7b592662ae8aa7424aed566e4dedb506b9d5a87f6f75caffeecdc5210b
NVIDIA 1090.963669  Complete!
Generic 1126.604881 Deploying image: Installation complete!
Generic 1126.645521 Bootc deployment complete: registry:ghcr.io/forjaos-project/forjaos@sha256:aedee6c3c67487ed610b3e9a067278d285474d855758ed3382ac79291a92189a
Generic 1134.678417 Complete!
```

UEFI Secure Boot was not enabled in these disposable QEMU guests. The results do not establish boot or installation on physical hardware.
