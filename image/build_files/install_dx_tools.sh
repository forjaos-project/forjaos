#!/usr/bin/env bash
set -euo pipefail

# Adapted from ublue-os/bazzite-dx build_files/20-install-apps.sh (Apache-2.0):
# https://github.com/ublue-os/bazzite-dx/blob/main/build_files/20-install-apps.sh
# The desktop base already supplies the login manager, gaming stack and Podman.
packages=(
  android-tools bcc bpftop bpftrace ccache flatpak-builder git-subtree
  google-noto-sans-fonts nicstat numactl podman-machine podman-tui
  python3-ramalama restic rclone sysprof tiptop usbmuxd waypipe zsh
  rocm-hip rocm-opencl rocm-clinfo rocm-smi
  qemu libvirt qemu-kvm virt-manager edk2-ovmf guestfs-tools
)

dnf install -y --setopt=install_weak_deps=False "${packages[@]}"

# Fail the image build if a selected RPM has no declared license or reports a
# proprietary/EULA license. The complete RPM inventory is exported by the
# existing THIRD_PARTY_LICENSES generator in the image pipeline.
for package in "${packages[@]}"; do
  license=$(rpm -q --qf '%{LICENSE}' "$package")
  if [[ -z "$license" || "$license" =~ [Pp]roprietary|EULA|Commercial|Redistributable ]]; then
    echo "DX RPM license requires review: $package ($license)" >&2
    exit 1
  fi
done
