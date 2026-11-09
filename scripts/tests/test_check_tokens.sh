#!/usr/bin/env bash
# Testa scripts/check-tokens.sh com uma árvore temporária.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/hero/ui"

# caso 1: cor presente no palette -> passa
printf 'Rectangle { color: "#00e5ff" }\n' > "$TMP/hero/ui/ok.qml"
if ! "$ROOT/scripts/check-tokens.sh" "$TMP" >/dev/null; then
  echo "FAIL: cor válida reprovada"; exit 1
fi

# caso 2: cor fora do palette -> falha
printf 'Rectangle { color: "#ff00aa" }\n' > "$TMP/hero/ui/bad.qml"
if "$ROOT/scripts/check-tokens.sh" "$TMP" >/dev/null; then
  echo "FAIL: cor inválida aprovada"; exit 1
fi
rm "$TMP/hero/ui/bad.qml"

# caso 3: maiúsculas e formato #rrggbbaa são normalizados
printf '.x{color:#00E5FF;border-color:#0F131D80}\n' > "$TMP/hero/ui/ok.css"
if ! "$ROOT/scripts/check-tokens.sh" "$TMP" >/dev/null; then
  echo "FAIL: #RRGGBB maiúsculo ou #rrggbbaa do palette reprovado"; exit 1
fi

# caso 4: docs/telas (protótipos) é ignorado
mkdir -p "$TMP/docs/telas/x"
printf '<div style="color:#ff00aa">' > "$TMP/docs/telas/x/code.html"
if ! "$ROOT/scripts/check-tokens.sh" "$TMP" >/dev/null; then
  echo "FAIL: docs/telas não foi ignorado"; exit 1
fi

echo "PASS test_check_tokens"
