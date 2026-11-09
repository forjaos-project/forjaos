#!/usr/bin/env bash
# Testa scripts/check-agents-sync.sh (verificação e --fix) em árvore temporária.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/.claude/commands"
printf '# /plan\nA\ngrep -L '"'"'FR-\\|NFR-'"'"' "$f"  # escapes devem sobreviver ao --fix\n' > "$TMP/.claude/commands/plan.md"
printf '# /code\nB\n' > "$TMP/.claude/commands/code.md"
for c in test review ship; do printf '# /%s\nX\n' "$c" > "$TMP/.claude/commands/$c.md"; done

# AGENTS.md com bloco vazio -> --fix preenche -> verificação passa
printf '# AGENTS\n\n## Fluxo\n\n<!-- flow:start -->\n<!-- flow:end -->\n\n## Depois\nfim\n' > "$TMP/AGENTS.md"
"$ROOT/scripts/check-agents-sync.sh" --fix "$TMP" >/dev/null
"$ROOT/scripts/check-agents-sync.sh" "$TMP" >/dev/null || { echo "FAIL: após --fix deveria estar sincronizado"; exit 1; }
grep -q '^## Depois$' "$TMP/AGENTS.md" || { echo "FAIL: --fix apagou conteúdo fora do bloco"; exit 1; }
grep -q '^fim$' "$TMP/AGENTS.md" || { echo "FAIL: --fix apagou conteúdo após o bloco"; exit 1; }

# comando muda -> verificação falha
printf '# /plan\nMUDOU\n' > "$TMP/.claude/commands/plan.md"
if "$ROOT/scripts/check-agents-sync.sh" "$TMP" >/dev/null 2>&1; then
  echo "FAIL: divergência aprovada"; exit 1
fi

# --fix de novo -> volta a passar e não duplica o bloco
"$ROOT/scripts/check-agents-sync.sh" --fix "$TMP" >/dev/null
"$ROOT/scripts/check-agents-sync.sh" "$TMP" >/dev/null || { echo "FAIL: segundo --fix não sincronizou"; exit 1; }
[[ "$(grep -c 'flow:start' "$TMP/AGENTS.md")" == "1" ]] || { echo "FAIL: marcador duplicado"; exit 1; }

echo "PASS test_check_agents_sync"
