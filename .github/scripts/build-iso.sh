#!/usr/bin/env bash
# Build one network Anaconda ISO for a signed, immutable testing digest.
set -euo pipefail

variant="${1:-}"
case "$variant" in
  forjaos|forjaos-nvidia-open) ;;
  *) echo 'build-iso: expected forjaos or forjaos-nvidia-open' >&2; exit 2 ;;
esac
if [[ $# -ne 2 || -z "$2" ]]; then
  echo 'build-iso: expected variant and output directory' >&2
  exit 2
fi

repo="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$2"
output="$(cd "$2" && pwd -P)"
image="ghcr.io/forjaos-project/$variant"
digest="$(skopeo inspect --format '{{.Digest}}' "docker://$image:testing")"
if [[ ! "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo 'build-iso: registry returned an invalid digest' >&2
  exit 1
fi
ref="$image@$digest"
cosign verify --new-bundle-format=false --key "$repo/cosign.pub" "$ref" >/dev/null

# ADR-0035: the installer environment is Fedora bootc; only its Kickstart
# refers to the verified ForjaOS payload. Do not embed the large payload.
builder='ghcr.io/osbuild/image-builder-cli@sha256:8bfc9884838edb070372827f9b3f94a86a5900ccdceb15c6920cc6a4095d51ae'
installer_image="localhost/$variant-installer:ci"
sudo podman build \
  --file "$repo/image/build_files/installer/Containerfile" \
  --build-arg "PAYLOAD_REF=$ref" \
  --build-arg "TARGET_REF=$image:testing" \
  --tag "$installer_image" "$repo"
sudo podman run --rm --privileged --network host \
  --security-opt label=disable \
  --volume "$output:/output" \
  --volume /var/lib/containers/storage:/var/lib/containers/storage \
  "$builder" build --bootc-ref "$installer_image" \
  --bootc-default-fs ext4 --output-dir /output --output-name "$variant" \
  generic-iso

iso="$output/$variant.iso"
if [[ ! -s "$iso" ]]; then
  echo "build-iso: builder did not produce $variant.iso" >&2
  exit 1
fi
sudo chown "$(id -u):$(id -g)" "$iso"
printf 'build-iso: %s from %s\n' "$iso" "$ref"
