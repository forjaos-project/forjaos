#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo 'usage: build_branding_rpm.sh SPEC SOURCES OUTPUT' >&2
  exit 2
fi

spec=$1
sources=$2
output=$3
base_identity_evr=$(rpm -q --qf '%{VERSION}-%{RELEASE}' fedora-release-identity-basic)
base_logos_evr=$(rpm -q --qf '%{VERSION}-%{RELEASE}' fedora-logos)
base_release_evr=$(rpm -q --qf '%{VERSION}-%{RELEASE}' fedora-release)
workdir=$(mktemp -d)
mkdir -p "$workdir/RPMS"
rpmbuild -bb "$spec" \
  --define "_topdir $workdir" \
  --define "_sourcedir $sources" \
  --define "base_identity_evr $base_identity_evr" \
  --define "base_logos_evr $base_logos_evr" \
  --define "base_release_evr $base_release_evr"
rpm_file=$(find "$workdir/RPMS" -type f -name 'forjaos-branding-*.rpm' -print -quit)
test -n "$rpm_file"
cp "$rpm_file" "$output"
