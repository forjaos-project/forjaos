#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/../.." && pwd)
helper="$repo/image/build_files/apply_package_policy.sh"
manifest="$repo/image/build_files/remove.txt"
test -f "$helper"
test -f "$manifest"
test "$(cat "$manifest")" = $'waydroid\nwaydroid-selinux'

tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
mkdir -p "$tmp/bin"
cat > "$tmp/bin/rpm" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
test "$1" = -q && test "$2" = --quiet
for package in $installed_packages; do
  if [[ "$package" == "$3" ]]; then exit 0; fi
done
exit 1
EOF
cat > "$tmp/bin/dnf" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$dnf_log"
if [[ "${fail_dnf:-0}" == 1 ]]; then exit 7; fi
EOF
chmod +x "$tmp/bin/rpm" "$tmp/bin/dnf"
export PATH="$tmp/bin:$PATH" dnf_log="$tmp/dnf.log"

export installed_packages='waydroid waydroid-selinux steam steam-devices'
bash "$helper" "$manifest"
test "$(cat "$dnf_log")" = 'remove -y --no-autoremove waydroid waydroid-selinux'

: > "$dnf_log"
export installed_packages='steam steam-devices'
bash "$helper" "$manifest"
test ! -s "$dnf_log"

export installed_packages='waydroid steam steam-devices' fail_dnf=1
if bash "$helper" "$manifest"; then
  echo 'failed removal transaction was accepted' >&2
  exit 1
fi
unset fail_dnf

printf 'waydroid\nsteam\n' > "$tmp/bad.txt"
if bash "$helper" "$tmp/bad.txt"; then
  echo 'gaming package was accepted for removal' >&2
  exit 1
fi
printf 'waydroid\ninvalid name\n' > "$tmp/bad.txt"
if bash "$helper" "$tmp/bad.txt"; then
  echo 'invalid package name was accepted' >&2
  exit 1
fi

echo 'image package policy: ok'
