#!/usr/bin/env bash
set -euo pipefail

efi_root="${1:-/sys/firmware/efi}"
cert="${2:-/usr/share/forjaos/secure_boot.der}"
target_efi="${3:-/mnt/sysroot/boot/efi/EFI}"

if [[ ! -d "$efi_root" ]]; then
    echo 'MOK_STAGE_SKIPPED_NON_EFI'
    exit 0
fi
if [[ ! -s "$cert" ]]; then
    echo "MOK_STAGE_MISSING_CERT: $cert" >&2
    exit 1
fi

# bootc/Anaconda can mount /boot again after mounting the ESP, hiding the
# EFI directory in this process namespace. Mount the ESP device separately.
if [[ ! -s "$target_efi/fedora/mmx64.efi" ]]; then
    esp_mountpoint="$(dirname "$target_efi")"
    esp_entry="$(findmnt -nro SOURCE,FSTYPE -M "$esp_mountpoint" | sed -n '1p')"
    read -r esp_device esp_fstype <<< "$esp_entry"
    if [[ "$esp_fstype" != vfat || "$esp_device" != /dev/* ]]; then
        echo "MOK_STAGE_ESP_NOT_FOUND: $esp_mountpoint" >&2
        exit 1
    fi
    esp_temporary="$(mktemp -d "${TMPDIR:-/run}/forjaos-mok-esp.XXXXXX")"
    mount "$esp_device" "$esp_temporary"
    trap 'umount "$esp_temporary"; rmdir "$esp_temporary"' EXIT
    target_efi="$esp_temporary/EFI"
    echo 'MOK_STAGE_ESP_REMOUNTED'
fi

# The first boot can use EFI/BOOT/BOOTX64.EFI before the Fedora UEFI entry is
# created. Its shim needs MokManager beside it, not only in EFI/fedora.
manager="$target_efi/fedora/mmx64.efi"
shim="$target_efi/fedora/shimx64.efi"
fallback="$target_efi/BOOT/BOOTX64.EFI"
if [[ ! -s "$manager" || ! -s "$shim" ]]; then
    echo "MOK_STAGE_MISSING_TARGET_MANAGER_OR_SHIM: $target_efi" >&2
    exit 1
fi
if cmp -s "$shim" "$fallback"; then
    install -m 0644 "$manager" "$target_efi/BOOT/mmx64.efi"
    cmp -s "$manager" "$target_efi/BOOT/mmx64.efi"
    echo 'MOK_FALLBACK_MANAGER_INSTALLED'
else
    # Preserve a fallback bootloader supplied by another OS or vendor.
    echo 'MOK_FALLBACK_UNCHANGED'
fi

# The public Universal Blue MOK password is confirmed physically in MokManager.
# Fedora 45 mokutil --test-key can return 0 while printing "is not enrolled".
# Import is safe to repeat: mokutil skips an enrolled or pending certificate.
mokutil --timeout -1
printf 'universalblue\nuniversalblue\n' | mokutil --import "$cert" >/dev/null
echo 'MOK_STAGE_IMPORT_OK'
