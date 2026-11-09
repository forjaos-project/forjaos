#!/usr/bin/env bash
# F0-003: exercise the production entry point without network or private keys.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -r "$TMP"' EXIT
mkdir -p "$TMP/bin"
export PATH="$TMP/bin:$PATH"
export TEST_LOG="$TMP/commands"
export TEST_DIGEST="sha256:$(printf 'a%.0s' {1..64})"
export TEST_PUBLIC_KEY="$REPO/cosign.pub"
export GH_TOKEN=synthetic-token GITHUB_ACTOR=synthetic-actor SIGNING_SECRET=synthetic-key GITHUB_RUN_ID=123

cat > "$TMP/bin/podman" <<'FAKE_PODMAN'
#!/usr/bin/env bash
printf 'podman %s\n' "$*" >> "$TEST_LOG"
case "$1" in
  run)
    if [[ "$*" == *'--rootfs /'* && "${TEST_FAIL_BRANDING:-}" == 1 ]]; then exit 1; fi
    if [[ "$*" == *'os-release'* && "${TEST_FAIL_IDENTITY:-}" == 1 ]]; then exit 1; fi
    ;;
  push)
    while (($#)); do
      if [[ "$1" == --digestfile ]]; then printf '%s\n' "$TEST_DIGEST" > "$2"; break; fi
      shift
    done
    ;;
esac
FAKE_PODMAN
cat > "$TMP/bin/cosign" <<'FAKE_COSIGN'
#!/usr/bin/env bash
printf 'cosign %s\n' "$*" >> "$TEST_LOG"
case "$1" in
  public-key) cat "$TEST_PUBLIC_KEY" ;;
  sign) [[ "${TEST_FAIL_SIGN:-}" != 1 ]] ;;
  verify) [[ "${TEST_FAIL_VERIFY:-}" != 1 ]] ;;
esac
FAKE_COSIGN
cat > "$TMP/bin/skopeo" <<'FAKE_SKOPEO'
#!/usr/bin/env bash
printf 'skopeo %s\n' "$*" >> "$TEST_LOG"
case "$1" in
  inspect)
    if [[ "${TEST_BAD_REMOTE_DIGEST:-}" == 1 ]]; then
      printf 'sha256:%064d\n' 0
    else
      printf '%s\n' "$TEST_DIGEST"
    fi
    ;;
esac
FAKE_SKOPEO
chmod +x "$TMP/bin/"*

assert_order() {
  local first="$1" second="$2" a b
  a="$(grep -nF -- "$first" "$TEST_LOG" | head -n1 | cut -d: -f1)"
  b="$(grep -nF -- "$second" "$TEST_LOG" | head -n1 | cut -d: -f1)"
  [[ -n "$a" && -n "$b" && "$a" -lt "$b" ]] || {
    echo "FAIL: '$first' must precede '$second'" >&2; cat "$TEST_LOG" >&2; exit 1;
  }
}

for variant in forjaos-nvidia-open forjaos; do
  : > "$TEST_LOG"
  bash "$REPO/.github/scripts/daily-image.sh" "$variant"
  if [[ "$variant" == forjaos-nvidia-open ]]; then base=bazzite-nvidia-open; else base=bazzite; fi
  grep -qF -- "--build-arg BASE_IMAGE=ghcr.io/ublue-os/$base:stable" "$TEST_LOG" || {
    echo "FAIL: wrong base for $variant" >&2; exit 1;
  }
  grep -qF -- "--build-arg IMAGE_NAME=$variant" "$TEST_LOG"
  assert_order 'container lint' 'os-release'
  assert_order 'os-release' '--rootfs /'
  assert_order '--rootfs /' 'podman push'
  assert_order 'podman push' 'cosign sign'
  assert_order 'cosign sign' 'cosign verify'
  assert_order 'cosign verify' 'skopeo copy'
  grep -qF "docker://ghcr.io/forjaos-project/$variant:testing" "$TEST_LOG"
  grep -qF -- '--preserve-digests' "$TEST_LOG"
  grep -qF "ghcr.io/forjaos-project/$variant@$TEST_DIGEST" "$TEST_LOG"
done

: > "$TEST_LOG"
export TEST_FAIL_BRANDING=1
if bash "$REPO/.github/scripts/daily-image.sh" forjaos >/dev/null 2>&1; then echo 'FAIL: accepted branded image' >&2; exit 1; fi
if grep -qE 'podman push|cosign sign|skopeo copy' "$TEST_LOG"; then echo 'FAIL: published branded image' >&2; exit 1; fi
unset TEST_FAIL_BRANDING

: > "$TEST_LOG"
export TEST_FAIL_IDENTITY=1
if bash "$REPO/.github/scripts/daily-image.sh" forjaos >/dev/null 2>&1; then echo 'FAIL: accepted invalid identity' >&2; exit 1; fi
if grep -qE 'podman push|cosign sign|skopeo copy' "$TEST_LOG"; then echo 'FAIL: published invalid identity' >&2; exit 1; fi
unset TEST_FAIL_IDENTITY

: > "$TEST_LOG"
export TEST_FAIL_SIGN=1
if bash "$REPO/.github/scripts/daily-image.sh" forjaos >/dev/null 2>&1; then echo 'FAIL: accepted failed signature' >&2; exit 1; fi
if grep -q 'skopeo copy' "$TEST_LOG"; then echo 'FAIL: promoted unsigned candidate' >&2; exit 1; fi
unset TEST_FAIL_SIGN

: > "$TEST_LOG"
export TEST_FAIL_VERIFY=1
if bash "$REPO/.github/scripts/daily-image.sh" forjaos >/dev/null 2>&1; then echo 'FAIL: accepted unverified signature' >&2; exit 1; fi
if grep -q 'skopeo copy' "$TEST_LOG"; then echo 'FAIL: promoted unverified candidate' >&2; exit 1; fi
unset TEST_FAIL_VERIFY

: > "$TEST_LOG"
export TEST_BAD_REMOTE_DIGEST=1
if bash "$REPO/.github/scripts/daily-image.sh" forjaos >/dev/null 2>&1; then echo 'FAIL: accepted digest mismatch' >&2; exit 1; fi
unset TEST_BAD_REMOTE_DIGEST

for variant in arbitrary '' ; do
  if bash "$REPO/.github/scripts/daily-image.sh" "$variant" >/dev/null 2>&1; then
    echo "FAIL: accepted invalid variant: $variant" >&2; exit 1
  fi
done
echo 'PASS test_daily_image'
