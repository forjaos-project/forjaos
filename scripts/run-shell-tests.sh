#!/usr/bin/env bash
# Runs every scripts/tests/*.sh, one bash per file; fails if any fails.
set -u
cd "$(dirname "$0")/.."
rc=0
for t in scripts/tests/*.sh; do
  [ -e "$t" ] || continue
  bash "$t" || { echo "FAIL: $t" >&2; rc=1; }
done
exit "$rc"
