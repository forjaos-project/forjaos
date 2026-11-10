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
cp "$brand_root/shortcuts/org.forjaos.terminal.desktop" "$workdir/SOURCES/shortcuts/"
cp "$brand_root/LICENSES.md" "$brand_root/fonts/OFL.txt" "$workdir/SOURCES/licenses/"
rpmbuild -bb "$build_files/forjaos-plasma.spec" \
  --define "_topdir $workdir" \
  --define "base_look_evr $base_look_evr" \
  --define "base_wallpaper_evr $base_wallpaper_evr"
rpm_file=$(find "$workdir/RPMS" -type f -name 'forjaos-plasma-*.rpm' -print -quit)
test -n "$rpm_file"
cp "$rpm_file" "$output_rpm"
