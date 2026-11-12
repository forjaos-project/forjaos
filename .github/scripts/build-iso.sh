#!/usr/bin/env bash
# Build one network Anaconda ISO for a signed, immutable testing digest.
set -euo pipefail

variant="${1:-}"
case "$variant" in
  forjaos|forjaos-nvidia-open) ;;
  *) echo 'build-iso: expected forjaos or forjaos-nvidia-open' >&2; exit 2 ;;
esac
if [[ $# -lt 2 || $# -gt 3 || -z "$2" ]]; then
  echo 'build-iso: expected variant, output directory, and optional testing/stable channel' >&2
  exit 2
fi
channel="${3:-testing}"
case "$channel" in
  testing|stable) ;;
  *) echo 'build-iso: expected testing or stable channel' >&2; exit 2 ;;
esac

repo="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$2"
output="$(cd "$2" && pwd -P)"
image="ghcr.io/forjaos-project/$variant"
digest="$(skopeo inspect --format '{{.Digest}}' "docker://$image:$channel")"
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
  --build-arg "TARGET_REF=$image:$channel" \
  --tag "$installer_image" "$repo"
sudo bash "$repo/scripts/check-branding.sh" --image "$installer_image"
installer_id="$(sudo podman image inspect --format '{{.Id}}' "$installer_image")"
sudo podman run --rm --entrypoint /usr/bin/rpm "$installer_image" -qa \
  --queryformat 'P\t%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\t%{LICENSE}\t%{SOURCERPM}\n[F\t%{FILENAMES}\t%{FILEFLAGS:fflags}\n]' \
  | python3 "$repo/.github/scripts/generate_third_party_licenses.py" \
    --variant "$variant" --image-id "$installer_id" \
    --output "$output/THIRD_PARTY_LICENSES.md"
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
sudo podman run --rm \
  --volume "$output:/output" \
  --entrypoint /usr/bin/xorriso "$installer_image" \
  -indev "/output/$variant.iso" -osirrox on \
  -extract /boot/grub2/grub.cfg "/output/$variant-grub.cfg" >/dev/null
sudo chown "$(id -u):$(id -g)" "$output/$variant-grub.cfg"
grep -qF "menuentry 'Instalar ForjaOS'" "$output/$variant-grub.cfg"
grep -qF 'root=live:CDLABEL=ForjaOS-Installer rd.live.image inst.graphical' \
  "$output/$variant-grub.cfg"
if grep -qE '(^|[[:space:]])(enforcing=0|selinux=0)([[:space:]]|$)' \
  "$output/$variant-grub.cfg"; then
  echo 'build-iso: installer boot disables SELinux' >&2
  exit 1
fi
printf 'build-iso: %s from %s\n' "$iso" "$ref"
