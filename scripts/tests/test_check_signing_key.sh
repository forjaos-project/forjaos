#!/usr/bin/env bash
# Testa scripts/check-signing-key.sh com um `cosign` falso no PATH.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/repo"

# cosign falso: `cosign public-key --key env://SIGNING_SECRET` imprime "PUB:<secret>"
cat > "$TMP/bin/cosign" <<'FAKE'
#!/usr/bin/env bash
[ "$1" = "public-key" ] && [ "$2" = "--key" ] && [ "$3" = "env://SIGNING_SECRET" ] || exit 9
printf -- '-----BEGIN PUBLIC KEY-----\nPUB:%s\n-----END PUBLIC KEY-----\n' "$SIGNING_SECRET"
FAKE
chmod +x "$TMP/bin/cosign"
run() { PATH="$TMP/bin:$PATH" "$ROOT/scripts/check-signing-key.sh" "$TMP/repo/cosign.pub" 2>&1; }

printf -- '-----BEGIN PUBLIC KEY-----\nPUB:s3cr3t-A\n-----END PUBLIC KEY-----\n' > "$TMP/repo/cosign.pub"

# caso 1: chave do secret corresponde -> 0
out=$(SIGNING_SECRET='s3cr3t-A' run) || { echo "FAIL: par correspondente reprovado: $out"; exit 1; }

# caso 2: chave diferente -> 2, sem vazar o secret
set +e; out=$(SIGNING_SECRET='s3cr3t-B' run); rc=$?; set -e
[ "$rc" -eq 2 ] || { echo "FAIL: par divergente deveria sair 2 (saiu $rc)"; exit 1; }
case "$out" in *s3cr3t-B*) echo "FAIL: saída vazou o secret"; exit 1;; esac

# caso 3: secret vazio -> 2
set +e; out=$(SIGNING_SECRET='' run); rc=$?; set -e
[ "$rc" -eq 2 ] || { echo "FAIL: secret vazio deveria sair 2 (saiu $rc)"; exit 1; }

# caso 4: cosign.pub ausente -> 2
rm "$TMP/repo/cosign.pub"
set +e; out=$(SIGNING_SECRET='s3cr3t-A' run); rc=$?; set -e
[ "$rc" -eq 2 ] || { echo "FAIL: cosign.pub ausente deveria sair 2 (saiu $rc)"; exit 1; }

echo "PASS test_check_signing_key"
