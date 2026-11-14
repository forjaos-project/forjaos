#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  printf 'usage: %s BUILD_FILES BRAND_ROOT OUTPUT_RPM\n' "$0" >&2
  exit 2
fi

build_files=$1
brand_root=$2
output_rpm=$3
base_look_evr=$(rpm -q --qf '%{VERSION}-%{RELEASE}' plasma-lookandfeel-fedora)
base_wallpaper_evr=$(rpm -q --qf '%{VERSION}-%{RELEASE}' f45-backgrounds-kde)
workdir=$(mktemp -d)
mkdir -p "$workdir/SOURCES" "$workdir/RPMS"
cp -a "$brand_root/plasma" "$workdir/SOURCES/"
find "$workdir/SOURCES/plasma" -type f -exec chmod 0644 {} +
mkdir -p "$workdir/SOURCES/wallpapers" "$workdir/SOURCES/fonts" \
  "$workdir/SOURCES/shortcuts" "$workdir/SOURCES/licenses"
cp "$brand_root/wallpapers/ForjaOS/"*.png "$workdir/SOURCES/wallpapers/"
cp "$brand_root/fonts/PlusJakartaSans-VF.ttf" "$workdir/SOURCES/fonts/"
cp /usr/share/fonts/jetbrains-mono-fonts/JetBrainsMono-Regular.otf "$workdir/SOURCES/fonts/"
cp "$brand_root/shortcuts/"*.desktop "$workdir/SOURCES/shortcuts/"
mkdir -p "$workdir/SOURCES/plymouth" "$workdir/SOURCES/grub" "$workdir/SOURCES/konsole"
cp -a "$brand_root/plymouth/." "$workdir/SOURCES/plymouth/"
cp -a "$brand_root/grub/." "$workdir/SOURCES/grub/"
cp -a "$brand_root/konsole/." "$workdir/SOURCES/konsole/"
find "$workdir/SOURCES/plymouth" "$workdir/SOURCES/grub" "$workdir/SOURCES/konsole" -type f -exec chmod 0644 {} +
for theme in dark light; do
  grub_theme="$workdir/SOURCES/grub/forja-$theme"
  grub2-mkfont --size=24 --name="Plus Jakarta Sans" \
    --output="$grub_theme/PlusJakartaSans24.pf2" \
    "$workdir/SOURCES/fonts/PlusJakartaSans-VF.ttf"
  grub2-mkfont --size=12 --name="JetBrains Mono" \
    --output="$grub_theme/JetBrainsMono12.pf2" \
    "$workdir/SOURCES/fonts/JetBrainsMono-Regular.otf"
done
cp "$brand_root/LICENSES.md" "$brand_root/fonts/OFL.txt" "$workdir/SOURCES/licenses/"
rpmbuild -bb "$build_files/forjaos-plasma.spec" \
  --define "_topdir $workdir" \
  --define "base_look_evr $base_look_evr" \
  --define "base_wallpaper_evr $base_wallpaper_evr"
rpm_file=$(find "$workdir/RPMS" -type f -name 'forjaos-plasma-*.rpm' -print -quit)
test -n "$rpm_file"
cp "$rpm_file" "$output_rpm"
