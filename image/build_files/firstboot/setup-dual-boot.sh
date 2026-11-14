#!/usr/bin/env bash
set -euo pipefail

state_dir="${FORJAOS_STATE_DIR:-/var/lib/forjaos}"
completion_file="$state_dir/dual-boot-setup.complete"
efibootmgr_bin="${EFIBOOTMGR_BIN:-efibootmgr}"
efi_sysfs_root="${FORJAOS_EFI_SYSFS_ROOT:-/sys/firmware/efi}"
grub_theme_source_dir="${FORJAOS_GRUB_THEME_SOURCE_DIR:-/usr/share/grub/themes/forja-dark}"
grub_theme_boot_dir="${FORJAOS_GRUB_THEME_BOOT_DIR:-/boot/grub2/themes/forja-dark}"
grub_defaults="${FORJAOS_GRUB_DEFAULTS:-/etc/default/grub}"
grub_config="${FORJAOS_GRUB_CONFIG:-/etc/grub2-efi.cfg}"
grub_mkconfig_bin="${GRUB2_MKCONFIG_BIN:-grub2-mkconfig}"
boot_remount_helper="${FORJAOS_BOOT_REMOUNT_HELPER:-/usr/libexec/bazzite-boot-remount}"
boot_remount_loaded=false
boot_remount_active=false

cleanup_boot_remount() {
  local exit_code=$?
  trap - EXIT
  if [[ "$boot_remount_active" == true && "$boot_remount_loaded" == true ]]; then
    remount_boot_ro || true
  fi
  exit "$exit_code"
}
trap cleanup_boot_remount EXIT

activate_grub_theme() {
  [[ -d "$efi_sysfs_root" ]] || return 0

  if [[ ! -f "$grub_theme_source_dir/theme.txt" ]]; then
    echo "ForjaOS GRUB theme is missing: $grub_theme_source_dir/theme.txt" >&2
    return 1
  fi
  if [[ ! -f "$grub_defaults" ]]; then
    echo "GRUB defaults file is missing: $grub_defaults" >&2
    return 1
  fi
  if [[ ! -r "$boot_remount_helper" ]]; then
    echo "Bazzite boot remount helper is missing: $boot_remount_helper" >&2
    return 1
  fi

  # GRUB reads its theme from the boot filesystem, not from the deployed /usr.
  source "$boot_remount_helper"
  boot_remount_loaded=true
  remount_boot_rw
  boot_remount_active=true
  install -d -m 0755 "${grub_theme_boot_dir%/*}"
  cp -a "$grub_theme_source_dir/." "$grub_theme_boot_dir/"

  if grep -q '^GRUB_THEME=' "$grub_defaults"; then
    sed -i '/^GRUB_THEME=/d' "$grub_defaults"
  fi
  printf 'GRUB_THEME="%s/theme.txt"\n' "$grub_theme_boot_dir" >> "$grub_defaults"
  "$grub_mkconfig_bin" -o "$grub_config"
  remount_boot_ro
  boot_remount_active=false
}

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

  activate_grub_theme
fi

install -d -m 0755 "$state_dir"
touch "$completion_file"
