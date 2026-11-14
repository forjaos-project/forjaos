#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$ROOT/image/build_files/firstboot/setup-dual-boot.sh"
RULE="$ROOT/image/build_files/firstboot/90-forjaos-ntfs-readonly.rules"
SERVICE="$ROOT/image/build_files/firstboot/setup-dual-boot.service"
CONTAINERFILE="$ROOT/image/Containerfile"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
mkdir -p "$TMP/efi"
mkdir -p "$TMP/theme-source/forja-dark"
printf 'theme contents\n' > "$TMP/theme-source/forja-dark/theme.txt"
printf 'GRUB_TIMEOUT=5\nGRUB_THEME="/boot/old/theme.txt"\n' > "$TMP/grub-defaults"

cat > "$TMP/bin/efibootmgr" <<'EOF'
#!/usr/bin/env bash
cat "$EFI_ENTRIES"
EOF
cat > "$TMP/bin/timedatectl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$RTC_CALLS"
EOF
cat > "$TMP/bin/grub2-mkconfig" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$GRUB_MKCONFIG_CALLS"
EOF
cat > "$TMP/boot-remount" <<'EOF'
remount_boot_rw() { printf 'rw\n' >> "$BOOT_REMOUNT_CALLS"; }
remount_boot_ro() { printf 'ro\n' >> "$BOOT_REMOUNT_CALLS"; }
EOF
chmod +x "$TMP/bin/efibootmgr" "$TMP/bin/timedatectl" "$TMP/bin/grub2-mkconfig"

export PATH="$TMP/bin:$PATH"
export EFI_ENTRIES="$TMP/entries"
export RTC_CALLS="$TMP/rtc-calls"
export GRUB_MKCONFIG_CALLS="$TMP/grub-mkconfig-calls"
export BOOT_REMOUNT_CALLS="$TMP/boot-remount-calls"
export FORJAOS_BOOT_REMOUNT_HELPER="$TMP/boot-remount"
export FORJAOS_GRUB_THEME_SOURCE_DIR="$TMP/theme-source/forja-dark"
export FORJAOS_GRUB_THEME_BOOT_DIR="$TMP/boot/grub2/themes/forja-dark"
export FORJAOS_GRUB_DEFAULTS="$TMP/grub-defaults"
export FORJAOS_GRUB_CONFIG="$TMP/grub2-efi.cfg"
export FORJAOS_STATE_DIR="$TMP/state-windows"
export FORJAOS_EFI_SYSFS_ROOT="$TMP/efi"
printf 'Boot0001* Windows Boot Manager HD(1,GPT,...)\n' > "$EFI_ENTRIES"

bash "$SCRIPT"
bash "$SCRIPT"
[[ "$(cat "$RTC_CALLS")" == 'set-local-rtc 1' ]]
[[ -f "$FORJAOS_STATE_DIR/dual-boot-setup.complete" ]]
[[ "$(grep -c '^GRUB_THEME=' "$FORJAOS_GRUB_DEFAULTS")" == '1' ]]
grep -Fx "GRUB_THEME=\"$FORJAOS_GRUB_THEME_BOOT_DIR/theme.txt\"" "$FORJAOS_GRUB_DEFAULTS"
grep -Fx 'GRUB_TIMEOUT=5' "$FORJAOS_GRUB_DEFAULTS"
[[ -f "$FORJAOS_GRUB_THEME_BOOT_DIR/theme.txt" ]]
[[ "$(cat "$GRUB_MKCONFIG_CALLS")" == "-o $FORJAOS_GRUB_CONFIG" ]]
[[ "$(cat "$BOOT_REMOUNT_CALLS")" == $'rw\nro' ]]

export FORJAOS_STATE_DIR="$TMP/state-no-windows"
printf 'Boot0000* Fedora HD(1,GPT,...)\n' > "$EFI_ENTRIES"
bash "$SCRIPT"
[[ ! -s "$RTC_CALLS" || "$(cat "$RTC_CALLS")" == 'set-local-rtc 1' ]]
[[ -f "$FORJAOS_STATE_DIR/dual-boot-setup.complete" ]]
[[ "$(grep -c '^GRUB_THEME=' "$FORJAOS_GRUB_DEFAULTS")" == '1' ]]
[[ "$(wc -l < "$GRUB_MKCONFIG_CALLS")" -eq 2 ]]

export FORJAOS_EFI_SYSFS_ROOT="$TMP/no-efi"
export FORJAOS_STATE_DIR="$TMP/state-bios"
bash "$SCRIPT"
[[ "$(wc -l < "$GRUB_MKCONFIG_CALLS")" -eq 2 ]]
[[ "$(wc -l < "$BOOT_REMOUNT_CALLS")" -eq 4 ]]

grep -Fx 'SUBSYSTEM=="block", ENV{ID_FS_TYPE}=="ntfs", ENV{UDISKS_MOUNT_OPTIONS_DEFAULTS}="ro"' "$RULE"
grep -Fx 'ConditionPathExists=!/var/lib/forjaos/dual-boot-setup.complete' "$SERVICE"
grep -F 'MemoryMax=' "$SERVICE"
grep -F 'CPUQuota=' "$SERVICE"
grep -F 'Nice=' "$SERVICE"
grep -F 'COPY image/build_files/firstboot/ /tmp/forjaos-firstboot/' "$CONTAINERFILE"
grep -F '/usr/lib/udev/rules.d/90-forjaos-ntfs-readonly.rules' "$CONTAINERFILE"
grep -F '/usr/lib/systemd/system/forjaos-setup-dual-boot.service' "$CONTAINERFILE"

echo 'PASS test_firstboot_dual_boot'
