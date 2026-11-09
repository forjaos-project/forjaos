#!/usr/bin/env bash
# F0-003: build and publish one tested, signed ForjaOS bootc image.
set -euo pipefail

variant="${1:-}"
case "$variant" in
  forjaos-nvidia-open) base=bazzite-nvidia-open ;;
  forjaos) base=bazzite ;;
  *) echo 'daily-image: expected forjaos or forjaos-nvidia-open' >&2; exit 2 ;;
esac

for required in GITHUB_ACTOR GH_TOKEN SIGNING_SECRET; do
  if [[ -z "${!required:-}" ]]; then
    echo "daily-image: $required is required" >&2
    exit 2
  fi
done

repo="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo"
image="ghcr.io/forjaos-project/$variant"
local_image="localhost/$variant:daily-build"
credentials="$GITHUB_ACTOR:$GH_TOKEN"

podman build --pull=always --file image/Containerfile \
  --build-arg "BASE_IMAGE=ghcr.io/ublue-os/$base:stable" \
  --build-arg "IMAGE_NAME=$variant" --tag "$local_image" .
podman run --rm --entrypoint /usr/bin/bootc "$local_image" container lint
podman run --rm --entrypoint /usr/bin/python3 "$local_image" -c '
from pathlib import Path
values = {}
for line in Path("/etc/os-release").read_text().splitlines():
    key, sep, value = line.partition("=")
    if sep:
        values[key] = value.strip("\"")
required = {"NAME": "ForjaOS", "ID": "forjaos", "ID_LIKE": "fedora"}
for key, expected in required.items():
    if values.get(key) != expected:
        raise SystemExit(f"invalid os-release {key}")
for key in ("PRETTY_NAME", "HOME_URL", "BUG_REPORT_URL"):
    if not values.get(key):
        raise SystemExit(f"missing os-release {key}")
'
bash scripts/check-branding.sh --image "$local_image"
bash scripts/check-signing-key.sh cosign.pub

# Keep the private key in the process environment; the existing preflight
# normalizes CRLF as well, but an env:// key must be normalized again here.
CHECK_SIGNING_KEY="${SIGNING_SECRET//$'\r'/}"
export CHECK_SIGNING_KEY COSIGN_PASSWORD=""
digest_file="$(mktemp)"
trap 'rm -f "$digest_file"' EXIT
podman push --creds "$credentials" --digestfile "$digest_file" \
  "$local_image" "docker://$image:candidate"
digest="$(cat "$digest_file")"
if [[ ! "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo 'daily-image: registry returned an invalid digest' >&2
  exit 1
fi

cosign sign --yes --key env://CHECK_SIGNING_KEY \
  --registry-username "$GITHUB_ACTOR" --registry-password "$GH_TOKEN" \
  "$image@$digest"
cosign verify --key cosign.pub \
  --registry-username "$GITHUB_ACTOR" --registry-password "$GH_TOKEN" \
  "$image@$digest" >/dev/null

# Preserve the signed manifest exactly; a conversion must fail before :testing
# points to a digest that the key did not sign.
skopeo copy --preserve-digests --src-creds "$credentials" \
  --dest-creds "$credentials" \
  "docker://$image@$digest" "docker://$image:testing"
remote_digest="$(skopeo inspect --creds "$credentials" \
  --format '{{.Digest}}' "docker://$image:testing")"
if [[ "$remote_digest" != "$digest" ]]; then
  echo 'daily-image: :testing digest differs from the signed digest' >&2
  exit 1
fi
cosign verify --key cosign.pub \
  --registry-username "$GITHUB_ACTOR" --registry-password "$GH_TOKEN" \
  "$image:testing" >/dev/null
printf 'daily-image: published and verified %s@%s as :testing\n' "$image" "$digest"
