#!/usr/bin/env bash
# Exercise the public F0-004 entry point with a synthetic rootfs and OCI runtime.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -r "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/rootfs/etc"
cat > "$TMP/rootfs/etc/os-release" <<'RELEASE'
NAME="ForjaOS"
ID=forjaos
ID_LIKE=fedora
PRETTY_NAME="ForjaOS 0.1"
RELEASE

cat > "$TMP/bin/rpm" <<'FAKE_RPM'
#!/usr/bin/env bash
printf 'forjaos-branding\n'
FAKE_RPM
cat > "$TMP/bin/podman" <<'FAKE_PODMAN'
#!/usr/bin/env bash
printf '%s\n' "$*" > "$TEST_RUNTIME_ARGS"
cat > "$TEST_STREAMED_CHECKER"
python3 "$TEST_STREAMED_CHECKER" --rootfs "$TEST_ROOTFS" --json
FAKE_PODMAN
chmod +x "$TMP/bin/rpm" "$TMP/bin/podman"
export PATH="$TMP/bin:$PATH"
export TEST_RUNTIME_ARGS="$TMP/runtime-args"
export TEST_STREAMED_CHECKER="$TMP/streamed-checker.py"
export TEST_ROOTFS="$TMP/rootfs"

out="$(bash "$REPO/scripts/check-branding.sh" --rootfs "$TMP/rootfs" --json)"
[[ "$out" == *'"status": "ok"'* ]] || { echo "FAIL: clean rootfs rejected: $out"; exit 1; }

printf 'Bazzite boot\n' > "$TMP/rootfs/etc/issue"
set +e
out="$(bash "$REPO/scripts/check-branding.sh" --rootfs "$TMP/rootfs" --json)"; rc=$?
set -e
[ "$rc" -eq 1 ] && [[ "$out" == *'"status": "fail"'* ]] || {
  echo "FAIL: visible brand did not fail: rc=$rc $out"; exit 1;
}

set +e
out="$(bash "$REPO/scripts/check-branding.sh" --image forjaos:test --json)"; rc=$?
set -e
[ "$rc" -eq 1 ] && [[ "$out" == *'"status": "fail"'* ]] || {
  echo "FAIL: image checker status not propagated: rc=$rc $out"; exit 1;
}
grep -q -- '--rm -i --entrypoint /usr/bin/python3 forjaos:test - --rootfs / --json' "$TEST_RUNTIME_ARGS" || {
  echo "FAIL: OCI dispatch arguments differ"; exit 1;
}

for args in '--rootfs' '--image' '--rootfs /tmp --image forjaos:test' '--bogus'; do
  if bash "$REPO/scripts/check-branding.sh" $args >/dev/null 2>&1; then
    echo "FAIL: invalid arguments accepted: $args"; exit 1
  fi
done
echo "PASS test_check_branding"
