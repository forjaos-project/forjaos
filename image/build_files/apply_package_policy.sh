#!/usr/bin/env bash
set -euo pipefail

manifest=${1:?usage: apply_package_policy.sh remove.txt}
test -f "$manifest"

packages=()
while IFS= read -r package || [[ -n "$package" ]]; do
  if [[ ! "$package" =~ ^[a-z0-9][a-z0-9+._-]*$ ]]; then
    echo "invalid RPM name in removal manifest: $package" >&2
    exit 2
  fi
  case "$package" in
    steam*|gamescope*|mangohud*|proton*|*gamepad*|*controller*)
      echo "gaming package cannot be removed: $package" >&2
      exit 2
      ;;
  esac
  packages+=("$package")
done < "$manifest"

if (( ${#packages[@]} == 0 )); then
  echo 'empty removal manifest' >&2
  exit 2
fi

installed=()
for package in "${packages[@]}"; do
  if rpm -q --quiet "$package"; then
    installed+=("$package")
  else
    status=$?
    if (( status != 1 )); then
      echo "RPM query failed for $package: $status" >&2
      exit "$status"
    fi
  fi
done

if (( ${#installed[@]} )); then
  dnf remove -y --no-autoremove "${installed[@]}"
fi
