#!/usr/bin/env bash
# Inspect a ForjaOS rootfs or built OCI image for user-visible inherited branding.
set -euo pipefail

usage() {
  echo "usage: scripts/check-branding.sh (--rootfs DIR | --image IMAGE) [--json]" >&2
  exit 2
}

mode=""
target=""
json_args=()
while (($#)); do
  case "$1" in
    --rootfs|--image)
      [[ -z "$mode" && $# -ge 2 && -n "$2" && "$2" != --* ]] || usage
      mode="$1"
      target="$2"
      shift 2
      ;;
    --json)
      ((${#json_args[@]} == 0)) || usage
      json_args=(--json)
      shift
      ;;
    *) usage ;;
  esac
done
[[ -n "$mode" ]] || usage

checker="$(cd "$(dirname "$0")" && pwd)/check_branding.py"
if [[ "$mode" == --rootfs ]]; then
  exec python3 "$checker" --rootfs "$target" "${json_args[@]}"
fi

if command -v podman >/dev/null 2>&1; then
  runtime=podman
elif command -v docker >/dev/null 2>&1; then
  runtime=docker
else
  echo "check-branding: Podman or Docker is required for --image" >&2
  exit 2
fi
exec "$runtime" run --rm -i --entrypoint /usr/bin/python3 "$target" - --rootfs / "${json_args[@]}" < "$checker"
