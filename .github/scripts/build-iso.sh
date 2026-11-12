#!/usr/bin/env bash
# Build one Anaconda installer ISO from a signed, immutable testing digest.
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

# The builder reads the rootful Podman store mounted from the host. Keep the
# builder digest identical to the one already used by the VM CI workflow.
builder='quay.io/centos-bootc/bootc-image-builder@sha256:dab86ee6b46dcade411b37f4e70b07d93b6a06da0dbfec6fe89247a220e0d9f8'
sudo podman pull "$ref"
sudo podman run --rm --privileged --network host \
  --security-opt label=disable \
  --volume "$output:/output" \
  --volume /var/lib/containers/storage:/var/lib/containers/storage \
  "$builder" --type anaconda-iso --rootfs btrfs \
  --chown "$(id -u):$(id -g)" "$ref"

iso="$output/bootiso/install.iso"
if [[ ! -s "$iso" ]]; then
  echo 'build-iso: builder did not produce bootiso/install.iso' >&2
  exit 1
fi
mv "$iso" "$output/$variant.iso"
printf 'build-iso: %s from %s\n' "$output/$variant.iso" "$ref"
