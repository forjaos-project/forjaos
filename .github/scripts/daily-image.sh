#!/usr/bin/env bash
# F0-003: build and publish one tested, signed ForjaOS bootc image.
set -euo pipefail

variant="${1:-}"
case "$variant" in
  forjaos-nvidia-open) ;;
  forjaos) ;;
  *) echo 'daily-image: expected forjaos or forjaos-nvidia-open' >&2; exit 2 ;;
esac

for required in GITHUB_ACTOR GH_TOKEN SIGNING_SECRET LICENSE_REPORT_DIR; do
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
case "$variant" in
  forjaos-nvidia-open) base_image=ghcr.io/ublue-os/bazzite-nvidia-open:stable ;;
  forjaos) base_image=ghcr.io/ublue-os/bazzite:stable ;;
esac
base_digest="$(skopeo inspect --format '{{.Digest}}' "docker://$base_image")"
if [[ ! "$base_digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo 'daily-image: base registry returned an invalid digest' >&2
  exit 1
fi
base_ref="${base_image%:*}@$base_digest"
report_root="${TRIVY_REPORT_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/forjaos-trivy}"
report_dir="$report_root/$variant"
mkdir -p "$report_dir"

podman build --pull=always --file image/Containerfile \
  --build-arg "BASE_IMAGE=$base_ref" \
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
image_id="$(podman image inspect --format '{{.Id}}' "$local_image")"
podman run --rm --entrypoint /usr/bin/rpm "$local_image" -qa \
  --queryformat 'P\t%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\t%{LICENSE}\t%{SOURCERPM}\n[F\t%{FILENAMES}\t%{FILEFLAGS:fflags}\n]' \
  | python3 .github/scripts/generate_third_party_licenses.py \
    --variant "$variant" --image-id "$image_id" \
    --output "$LICENSE_REPORT_DIR/$variant/THIRD_PARTY_LICENSES.md"
podman run --rm --entrypoint /usr/bin/python3 "$local_image" \
  /usr/libexec/forjaos/check_image_contract.py
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

# Scan both the exact candidate digest and its declared upstream base before
# signing or updating :testing. New critical CVEs stop promotion; base findings
# are retained for the isolated issue-reporting job.
trivy image --timeout 15m --scanners vuln --severity CRITICAL --exit-code 0 \
  --platform linux/amd64 --format json --output "$report_dir/base.json" "$base_ref"
TRIVY_USERNAME="$GITHUB_ACTOR" TRIVY_PASSWORD="$GH_TOKEN" \
  trivy image --timeout 15m --scanners vuln --severity CRITICAL --exit-code 0 \
  --platform linux/amd64 --format json --output "$report_dir/image.json" "$image@$digest"
python3 scripts/classify_trivy_report.py \
  --image-report "$report_dir/image.json" \
  --base-report "$report_dir/base.json" \
  --output "$report_dir/classified.json"

# containers/image's use-sigstore-attachments policy reads the legacy
# sha256-<digest>.sig attachment, not Cosign 3's default OCI 1.1 bundle.
cosign sign --yes --new-bundle-format=false --use-signing-config=false \
  --registry-referrers-mode=legacy --key env://CHECK_SIGNING_KEY \
  --registry-username "$GITHUB_ACTOR" --registry-password "$GH_TOKEN" \
  "$image@$digest"
cosign verify --new-bundle-format=false --key cosign.pub \
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
cosign verify --new-bundle-format=false --key cosign.pub \
  --registry-username "$GITHUB_ACTOR" --registry-password "$GH_TOKEN" \
  "$image:testing" >/dev/null
printf 'daily-image: published and verified %s@%s as :testing\n' "$image" "$digest"
