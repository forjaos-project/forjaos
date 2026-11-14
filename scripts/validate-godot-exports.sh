#!/usr/bin/env bash
set -euo pipefail

output=${1:?usage: validate-godot-exports.sh OUTPUT_DIRECTORY}
root=$(cd "$(dirname "$0")/.." && pwd)
project="$root/image/tests/godot-smoke"
mkdir -p "$output/linux" "$output/web"
output=$(cd "$output" && pwd)

flatpak run org.godotengine.Godot --headless --path "$project" --import
flatpak run org.godotengine.Godot --headless --path "$project" \
  --export-release Linux "$output/linux/forjaos-smoke.x86_64"
flatpak run org.godotengine.Godot --headless --path "$project" \
  --export-release Web "$output/web/index.html"

test -s "$output/linux/forjaos-smoke.x86_64"
test -s "$output/web/index.html"
test -s "$output/web/index.wasm"
printf 'Godot Linux and Web exports: ok\n'
