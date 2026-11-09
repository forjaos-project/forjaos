#!/usr/bin/env bash
# Confirms that the private key in $SIGNING_SECRET matches the committed cosign.pub (ADR-030).
# Usage: SIGNING_SECRET=... scripts/check-signing-key.sh [path/to/cosign.pub]
# Exit: 0 match, 2 mismatch or missing input. Never prints the secret.
set -uo pipefail
pub="${1:-$(cd "$(dirname "$0")/.." && pwd)/cosign.pub}"
if [ -z "${SIGNING_SECRET:-}" ]; then
  echo "check-signing-key: SIGNING_SECRET vazio ou ausente" >&2; exit 2
fi
if [ ! -s "$pub" ]; then
  echo "check-signing-key: $pub não encontrado" >&2; exit 2
fi
# Secrets pasted from Windows may carry CRLF, which breaks PEM parsing.
CHECK_SIGNING_KEY=$(printf '%s' "$SIGNING_SECRET" | tr -d '\r'); export CHECK_SIGNING_KEY
err=$(mktemp); trap 'rm -f "$err"' EXIT
derived=$(cosign public-key --key env://CHECK_SIGNING_KEY 2>"$err") || {
  echo "check-signing-key: cosign não conseguiu ler a chave de SIGNING_SECRET: $(tail -n 1 "$err")" >&2; exit 2; }
norm() { tr -d '\r' | sed '/^[[:space:]]*$/d'; }
if [ "$(printf '%s\n' "$derived" | norm)" != "$(norm < "$pub")" ]; then
  echo "check-signing-key: a chave de SIGNING_SECRET não corresponde a $pub" >&2; exit 2
fi
echo "check-signing-key: OK"
