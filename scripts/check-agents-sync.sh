#!/usr/bin/env bash
# check-agents-sync.sh — o bloco <!-- flow:start --> … <!-- flow:end --> de AGENTS.md deve ser
# idêntico à concatenação de .claude/commands/{plan,code,test,review,ship}.md, nessa ordem.
#
# Uso: scripts/check-agents-sync.sh [RAIZ]        verifica (exit 1 se divergir)
#      scripts/check-agents-sync.sh --fix [RAIZ]  regenera o bloco em AGENTS.md
set -euo pipefail

FIX=0
if [[ "${1:-}" == "--fix" ]]; then FIX=1; shift; fi
ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
AGENTS="$ROOT/AGENTS.md"
CMDS="$ROOT/.claude/commands"

for c in plan code test review ship; do
  [[ -f "$CMDS/$c.md" ]] || { echo "check-agents-sync: falta $CMDS/$c.md" >&2; exit 2; }
done
[[ -f "$AGENTS" ]] || { echo "check-agents-sync: falta $AGENTS" >&2; exit 2; }

expected="$(for c in plan code test review ship; do cat "$CMDS/$c.md"; echo; done)"
expected="${expected%$'\n'}"

if [[ $FIX -eq 1 ]]; then
  tmp="$(mktemp)"; blockfile="$(mktemp)"
  printf '%s\n' "$expected" > "$blockfile"
  # getline não interpreta escapes (diferente de -v), preservando "\|", "\(" etc. dos comandos.
  awk -v bf="$blockfile" '
    /<!-- flow:start -->/ { print; while ((getline line < bf) > 0) print line; close(bf); skip=1; next }
    /<!-- flow:end -->/   { skip=0 }
    !skip { print }
  ' "$AGENTS" > "$tmp"
  mv "$tmp" "$AGENTS"; rm -f "$blockfile"
  echo "check-agents-sync: bloco Fluxo regenerado em AGENTS.md"
  exit 0
fi

actual="$(awk '/<!-- flow:start -->/{f=1;next} /<!-- flow:end -->/{f=0} f' "$AGENTS")"
actual="${actual%$'\n'}"

if [[ "$expected" == "$actual" ]]; then
  echo "check-agents-sync: OK"
  exit 0
fi
echo "check-agents-sync: AGENTS.md (bloco Fluxo) difere de .claude/commands/*.md — rode scripts/check-agents-sync.sh --fix"
diff <(printf '%s\n' "$expected") <(printf '%s\n' "$actual") | head -40 || true
exit 1
