#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/../.." && pwd)
qml="$root/image/firstboot/Preflight.qml"
containerfile="$root/image/Containerfile"

test -f "$qml"
grep -Fq 'signal continueRequested()' "$qml"
grep -Fq 'property string windowsState: "unknown"' "$qml"
grep -Fq 'property string secureBootState: "unknown"' "$qml"
grep -Fq 'property string mokState: "unknown"' "$qml"

grep -Fq 'Inicialização Rápida' "$qml"
grep -Fq 'Por padrão, o ForjaOS monta NTFS em somente leitura' "$qml"
grep -Fq 'BitLocker' "$qml"
grep -Fq 'somente leitura' "$qml"
grep -Fq 'Enroll MOK' "$qml"
grep -Fq 'Windows encontrado' "$qml"
grep -Fq 'Secure Boot' "$qml"
grep -Fq 'MOK' "$qml"
grep -Fq 'A detecção de sistema ainda não está conectada' "$qml"
grep -Fq 'image/firstboot/Preflight.qml /usr/share/forjaos/firstboot/Preflight.qml' "$containerfile"

if grep -Fq 'font.family: "Inter"' "$qml"; then
  echo 'preflight explanatory copy must use the UI typeface' >&2
  exit 1
fi

for content in stateNote footer; do
  line=$(grep -F "text: copy.$content" "$qml")
  if [[ "$line" != *'font.family: "Plus Jakarta Sans"'* || "$line" != *'font.pixelSize: 12'* ]]; then
    echo "preflight $content must use the 12px UI body style" >&2
    exit 1
  fi
done

if grep -nE 'clearpart|autopart|ignoredisk|zerombr|mokutil --import|rm -rf|dd ' "$qml"; then
  echo 'preflight screen must not partition disks, enroll keys, or delete data' >&2
  exit 1
fi

echo 'firstboot preflight tests passed'
