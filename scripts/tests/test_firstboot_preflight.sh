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
grep -Fq 'BitLocker' "$qml"
grep -Fq 'somente leitura' "$qml"
grep -Fq 'Enroll MOK' "$qml"
grep -Fq 'Windows encontrado' "$qml"
grep -Fq 'Secure Boot' "$qml"
grep -Fq 'MOK' "$qml"
grep -Fq 'image/firstboot/Preflight.qml /usr/share/forjaos/firstboot/Preflight.qml' "$containerfile"

if grep -nE 'clearpart|autopart|ignoredisk|zerombr|mokutil --import|rm -rf|dd ' "$qml"; then
  echo 'preflight screen must not partition disks, enroll keys, or delete data' >&2
  exit 1
fi

echo 'firstboot preflight tests passed'
