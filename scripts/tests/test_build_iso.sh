#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -r "$tmp"' EXIT
mkdir -p "$tmp/bin"
export TEST_LOG="$tmp/log"
export TEST_DIGEST="sha256:$(printf 'a%.0s' {1..64})"
export PATH="$tmp/bin:$PATH"

cat > "$tmp/bin/skopeo" <<'FAKE'
#!/usr/bin/env bash
printf 'skopeo %s\n' "$*" >> "$TEST_LOG"
printf '%s\n' "${TEST_BAD_DIGEST:-$TEST_DIGEST}"
FAKE
cat > "$tmp/bin/cosign" <<'FAKE'
#!/usr/bin/env bash
printf 'cosign %s\n' "$*" >> "$TEST_LOG"
[[ "${TEST_BAD_SIGNATURE:-}" != 1 ]]
FAKE
cat > "$tmp/bin/sudo" <<'FAKE'
#!/usr/bin/env bash
printf 'sudo %s\n' "$*" >> "$TEST_LOG"
if [[ "$1" == podman && "$2" == image && "$3" == inspect ]]; then
  printf 'sha256:%064d\n' 0
  exit 0
fi
if [[ "$1" == podman && "$2" == run && "$*" == *'--entrypoint /usr/bin/rpm'* ]]; then
  printf 'P\tanaconda\t1-1\tx86_64\tGPL-2.0-or-later\tanaconda-1-1.src.rpm\nF\t/usr/share/licenses/anaconda/LICENSE\tl\n'
  exit 0
fi
if [[ "$1" == podman && "$2" == run ]]; then
  while (($#)); do
    if [[ "$1" == --volume && "$2" == *:/output ]]; then
      mkdir -p "${2%:/output}"
      printf 'ISO fixture' > "${2%:/output}/$TEST_VARIANT.iso"
      break
    fi
    shift
  done
fi
FAKE
chmod +x "$tmp/bin/"*

for variant in forjaos forjaos-nvidia-open; do
  export TEST_VARIANT="$variant"
  : > "$TEST_LOG"
  bash "$repo/.github/scripts/build-iso.sh" "$variant" "$tmp/$variant"
  test -s "$tmp/$variant/$variant.iso"
  test -s "$tmp/$variant/THIRD_PARTY_LICENSES.md"
  grep -qF "docker://ghcr.io/forjaos-project/$variant:testing" "$TEST_LOG"
  grep -qF "cosign verify --new-bundle-format=false --key $repo/cosign.pub ghcr.io/forjaos-project/$variant@$TEST_DIGEST" "$TEST_LOG"
  grep -qF "sudo podman build --file $repo/image/build_files/installer/Containerfile --build-arg PAYLOAD_REF=ghcr.io/forjaos-project/$variant@$TEST_DIGEST" "$TEST_LOG"
  grep -qF -- "--build-arg TARGET_REF=ghcr.io/forjaos-project/$variant:testing" "$TEST_LOG"
  grep -qF -- '--bootc-default-fs ext4' "$TEST_LOG"
  grep -qF -- '--output-name' "$TEST_LOG"
  grep -qF -- 'generic-iso' "$TEST_LOG"
  grep -qF "sudo bash $repo/scripts/check-branding.sh --image localhost/$variant-installer:ci" "$TEST_LOG"
  grep -qF -- '--entrypoint /usr/bin/rpm' "$TEST_LOG"
  if grep -qE -- '--installer-payload-ref|--bootc-installer-payload-ref|--type bootc-installer' "$TEST_LOG"; then
    echo 'FAIL: network installer embeds the payload' >&2; exit 1
  fi
  if grep -qF -- '--type anaconda-iso' "$TEST_LOG"; then
    echo 'FAIL: legacy anaconda-iso may install to the first disk without prompting' >&2; exit 1
  fi
  verify_line="$(grep -n 'cosign verify' "$TEST_LOG" | head -1 | cut -d: -f1)"
  build_line="$(grep -n 'sudo podman build' "$TEST_LOG" | head -1 | cut -d: -f1)"
  run_line="$(grep -n 'sudo podman run' "$TEST_LOG" | head -1 | cut -d: -f1)"
  brand_line="$(grep -n 'sudo bash.*check-branding.sh' "$TEST_LOG" | head -1 | cut -d: -f1)"
  [[ "$verify_line" -lt "$build_line" && "$build_line" -lt "$brand_line" && "$brand_line" -lt "$run_line" ]]
done

export TEST_VARIANT=forjaos
: > "$TEST_LOG"
bash "$repo/.github/scripts/build-iso.sh" forjaos "$tmp/stable" stable
grep -qF 'docker://ghcr.io/forjaos-project/forjaos:stable' "$TEST_LOG"
grep -qF -- '--build-arg TARGET_REF=ghcr.io/forjaos-project/forjaos:stable' "$TEST_LOG"
if bash "$repo/.github/scripts/build-iso.sh" forjaos "$tmp/invalid-channel" arbitrary >/dev/null 2>&1; then
  echo 'FAIL: accepted arbitrary release channel' >&2; exit 1
fi

: > "$TEST_LOG"
export TEST_BAD_SIGNATURE=1
if bash "$repo/.github/scripts/build-iso.sh" forjaos "$tmp/unsigned" >/dev/null 2>&1; then
  echo 'FAIL: accepted unsigned image' >&2; exit 1
fi
! grep -q 'sudo podman' "$TEST_LOG"
unset TEST_BAD_SIGNATURE

: > "$TEST_LOG"
export TEST_BAD_DIGEST='sha256:invalid'
if bash "$repo/.github/scripts/build-iso.sh" forjaos "$tmp/bad-digest" >/dev/null 2>&1; then
  echo 'FAIL: accepted invalid digest' >&2; exit 1
fi
! grep -q 'cosign\|sudo podman' "$TEST_LOG"
unset TEST_BAD_DIGEST

if bash "$repo/.github/scripts/build-iso.sh" arbitrary "$tmp/invalid" >/dev/null 2>&1; then
  echo 'FAIL: accepted invalid variant' >&2; exit 1
fi
echo 'test_build_iso: OK'
