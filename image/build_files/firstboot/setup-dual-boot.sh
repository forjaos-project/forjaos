#!/usr/bin/env bash
set -euo pipefail

state_dir="${FORJAOS_STATE_DIR:-/var/lib/forjaos}"
completion_file="$state_dir/dual-boot-setup.complete"
efibootmgr_bin="${EFIBOOTMGR_BIN:-efibootmgr}"
efi_sysfs_root="${FORJAOS_EFI_SYSFS_ROOT:-/sys/firmware/efi}"

if [[ -e "$completion_file" ]]; then
  exit 0
fi

if [[ -d "$efi_sysfs_root" ]]; then
  if ! command -v "$efibootmgr_bin" >/dev/null 2>&1; then
    echo "efibootmgr is required to detect Windows Boot Manager" >&2
    exit 1
  fi

  if ! entries="$("$efibootmgr_bin" --verbose)"; then
    echo "Unable to read UEFI boot entries" >&2
    exit 1
  fi

  if grep -Fqi 'Windows Boot Manager' <<< "$entries"; then
    timedatectl set-local-rtc 1
  fi
fi

install -d -m 0755 "$state_dir"
touch "$completion_file"
