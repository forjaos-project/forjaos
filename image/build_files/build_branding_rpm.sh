#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  printf 'usage: %s BUILD_FILES ICONS_DIR OUTPUT_RPM IMAGE_NAME\n' "$0" >&2
  exit 2
fi

build_files=$1
icons_dir=$2
output_rpm=$3
image_name=$4
brand_root=$(cd "$icons_dir/../.." && pwd)
base_identity_evr=$(rpm -q --qf '%{VERSION}-%{RELEASE}' fedora-release-identity-kinoite)
base_logos_evr=$(rpm -q --qf '%{VERSION}-%{RELEASE}' fedora-logos)
workdir=$(mktemp -d)
trap 'rm -rf -- "$workdir"' EXIT
mkdir -p "$workdir/SOURCES/icons" "$workdir/SOURCES/svg" "$workdir/SOURCES/licenses" "$workdir/RPMS"
cp "$icons_dir"/forjaos-*.png "$workdir/SOURCES/icons/"
cp "$brand_root/logo/forjaos-icon.svg" "$workdir/SOURCES/svg/"
cp "$brand_root/LICENSES.md" "$workdir/SOURCES/licenses/"
cp "$build_files/80-kde-desktop.preset" "$workdir/SOURCES/"
python3 - "$build_files/configure_image.py" "$image_name" "$workdir/SOURCES/os-release" <<'PY'
import importlib.util
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("configure_image", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
source = Path("/usr/lib/os-release").read_text(encoding="utf-8")
Path(sys.argv[3]).write_text(module.update_os_release(source, sys.argv[2]), encoding="utf-8")
PY
rpmbuild -bb "$build_files/forjaos-branding.spec" \
  --define "_topdir $workdir" \
  --define "base_identity_evr $base_identity_evr" \
  --define "base_logos_evr $base_logos_evr"
rpm_file=$(find "$workdir/RPMS" -type f -name 'forjaos-branding-*.rpm' -print -quit)
test -n "$rpm_file"
cp "$rpm_file" "$output_rpm"
