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

cat > "$TMP/bin/efibootmgr" <<'EOF'
#!/usr/bin/env bash
cat "$EFI_ENTRIES"
EOF
cat > "$TMP/bin/timedatectl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$RTC_CALLS"
EOF
chmod +x "$TMP/bin/efibootmgr" "$TMP/bin/timedatectl"

export PATH="$TMP/bin:$PATH"
export EFI_ENTRIES="$TMP/entries"
export RTC_CALLS="$TMP/rtc-calls"
export FORJAOS_STATE_DIR="$TMP/state-windows"
export FORJAOS_EFI_SYSFS_ROOT="$TMP/efi"
printf 'Boot0001* Windows Boot Manager HD(1,GPT,...)\n' > "$EFI_ENTRIES"

bash "$SCRIPT"
bash "$SCRIPT"
[[ "$(cat "$RTC_CALLS")" == 'set-local-rtc 1' ]]
[[ -f "$FORJAOS_STATE_DIR/dual-boot-setup.complete" ]]

export FORJAOS_STATE_DIR="$TMP/state-no-windows"
printf 'Boot0000* Fedora HD(1,GPT,...)\n' > "$EFI_ENTRIES"
bash "$SCRIPT"
[[ ! -s "$RTC_CALLS" || "$(cat "$RTC_CALLS")" == 'set-local-rtc 1' ]]
[[ -f "$FORJAOS_STATE_DIR/dual-boot-setup.complete" ]]

grep -Fx 'SUBSYSTEM=="block", ENV{ID_FS_TYPE}=="ntfs", ENV{UDISKS_MOUNT_OPTIONS_DEFAULTS}="ro"' "$RULE"
grep -Fx 'ConditionPathExists=!/var/lib/forjaos/dual-boot-setup.complete' "$SERVICE"
grep -F 'MemoryMax=' "$SERVICE"
grep -F 'CPUQuota=' "$SERVICE"
grep -F 'Nice=' "$SERVICE"
grep -F 'COPY image/build_files/firstboot/ /tmp/forjaos-firstboot/' "$CONTAINERFILE"
grep -F '/usr/lib/udev/rules.d/90-forjaos-ntfs-readonly.rules' "$CONTAINERFILE"
grep -F '/usr/lib/systemd/system/forjaos-setup-dual-boot.service' "$CONTAINERFILE"

echo 'PASS test_firstboot_dual_boot'
