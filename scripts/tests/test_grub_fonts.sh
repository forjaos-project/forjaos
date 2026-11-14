#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUILDER="$ROOT/brand/themes/build_grub_fonts.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/fonts" "$TMP/grub/forja-dark" "$TMP/grub/forja-light"
printf 'ui source\n' > "$TMP/fonts/ui.ttf"
printf 'mono source\n' > "$TMP/fonts/mono.otf"

cat > "$TMP/bin/grub2-mkfont" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
family=''
size=''
output=''
for argument in "$@"; do
  case "$argument" in
    --name=*) family=${argument#--name=} ;;
    --size=*) size=${argument#--size=} ;;
    --output=*) output=${argument#--output=} ;;
  esac
done
[[ -n "$family" && -n "$size" && -n "$output" ]]
printf '%s Regular %s\n' "$family" "$size" > "$output"
EOF
chmod +x "$TMP/bin/grub2-mkfont"

PATH="$TMP/bin:$PATH" bash "$BUILDER" "$TMP/grub" "$TMP/fonts/ui.ttf" "$TMP/fonts/mono.otf"
for theme in dark light; do
  grep -Fxq 'Plus Jakarta Sans Regular 24' "$TMP/grub/forja-$theme/PlusJakartaSans24.pf2"
  grep -Fxq 'JetBrains Mono Regular 12' "$TMP/grub/forja-$theme/JetBrainsMono12.pf2"
done

echo 'PASS test_grub_fonts'
