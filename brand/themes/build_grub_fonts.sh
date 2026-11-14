#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  printf 'usage: %s GRUB_THEME_ROOT UI_FONT MONO_FONT\n' "$0" >&2
  exit 2
fi

theme_root=$1
ui_font=$2
mono_font=$3
[[ -s "$ui_font" ]] || { echo "missing UI font: $ui_font" >&2; exit 1; }
[[ -s "$mono_font" ]] || { echo "missing mono font: $mono_font" >&2; exit 1; }

for theme in dark light; do
  output_dir="$theme_root/forja-$theme"
  [[ -d "$output_dir" ]] || { echo "missing GRUB theme directory: $output_dir" >&2; exit 1; }
  grub2-mkfont --size=24 --name="Plus Jakarta Sans" \
    --output="$output_dir/PlusJakartaSans24.pf2" "$ui_font"
  grub2-mkfont --size=12 --name="JetBrains Mono" \
    --output="$output_dir/JetBrainsMono12.pf2" "$mono_font"
done
