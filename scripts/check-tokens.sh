#!/usr/bin/env bash
# check-tokens.sh — ADR-027 / FR-051
# Falha se encontrar cor hex (#rgb, #rrggbb, #rrggbbaa) fora de brand/palette.json
# em arquivos próprios do projeto (.qml .css .scss .svg .html .colors .colorscheme .toml .rs .py).
#
# Ignorados: docs/telas (protótipos históricos), .git, node_modules, target,
#            brand/palette.json (a própria fonte), docs/roadmap/index.html e
#            scripts/roadmap_template.html (gerados a partir do palette; cobertos pelo teste do roadmap.py).
#
# Uso: scripts/check-tokens.sh [RAIZ]   (padrão: raiz do repositório)
set -euo pipefail

ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
PALETTE="$(cd "$(dirname "$0")/.." && pwd)/brand/palette.json"

if [[ ! -f "$PALETTE" ]]; then
  echo "check-tokens: palette não encontrado em $PALETTE" >&2
  exit 2
fi

# Lista de cores permitidas (minúsculas), uma por linha.
allowed="$(grep -oiE '#[0-9a-f]{8}|#[0-9a-f]{6}|#[0-9a-f]{3}\b' "$PALETTE" | tr 'A-F' 'a-f' | sort -u)"

status=0
count=0
while IFS= read -r -d '' f; do
  while IFS= read -r hex; do
    [[ -z "$hex" ]] && continue
    h="$(printf '%s' "$hex" | tr 'A-F' 'a-f')"
    # #rrggbbaa: a cor base precisa estar no palette; o canal alfa é livre.
    if [[ ${#h} -eq 9 ]]; then h="${h:0:7}"; fi
    if ! grep -qxF "$h" <<<"$allowed"; then
      echo "check-tokens: ${f#"$ROOT"/}: cor fora do palette: $hex"
      status=1
    fi
  done < <(grep -oiE '#[0-9a-f]{8}\b|#[0-9a-f]{6}\b|#[0-9a-f]{3}\b' "$f" || true)
  count=$((count + 1))
done < <(find "$ROOT" \
  \( -path '*/.git' -o -path '*/docs/telas' -o -path '*/node_modules' -o -path '*/target' \
     -o -path '*/brand/palette.json' -o -path '*/docs/roadmap/index.html' -o -path '*/scripts/roadmap_template.html' \) -prune \
  -o -type f \( -name '*.qml' -o -name '*.css' -o -name '*.scss' -o -name '*.svg' -o -name '*.html' \
     -o -name '*.colors' -o -name '*.colorscheme' -o -name '*.toml' -o -name '*.rs' -o -name '*.py' \) -print0)

if [[ $status -eq 0 ]]; then
  echo "check-tokens: OK ($count arquivos verificados)"
fi
exit $status
