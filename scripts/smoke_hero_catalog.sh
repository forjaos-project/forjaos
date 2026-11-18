#!/usr/bin/env bash
set -euo pipefail

runtime_dir="$(mktemp -d)"
export XDG_RUNTIME_DIR="$runtime_dir"
export HOME="$runtime_dir/home"
mkdir -m 700 -- "$HOME"
export SMOKE_PROJECT="$HOME/proj/hero-smoke"
mkdir -p -- "$SMOKE_PROJECT"
git -C "$SMOKE_PROJECT" init -q
cleanup() {
  if [[ -n "${hero_pid:-}" ]]; then
    kill "$hero_pid" 2>/dev/null || true
    wait "$hero_pid" 2>/dev/null || true
  fi
  rm -r -- "$runtime_dir"
}
trap cleanup EXIT

/usr/libexec/forjaos/herod &
hero_pid=$!
for _ in {1..30}; do
  if gdbus introspect --session --dest org.forjaos.Hero --object-path /org/forjaos/Hero >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

python3 - <<'PY'
import ast
import json
import os
import subprocess

cases = [
    ("status da CPU", "system.status", "livre", False),
    ("mostre gpu", "gpu.status", "livre", False),
    ("liste serviços", "services.list", "livre", False),
    ("status do serviço sshd.service", "services.status", "livre", False),
    ("ligue wifi", "wifi.toggle", "alterar", True),
    ("ligue bluetooth", "bluetooth.toggle", "alterar", True),
    ("suba compose", "compose.up", "alterar", True),
    ("rode os testes", "tests.run", "alterar", True),
    ("atualize o sistema", "system.update", "alterar", True),
    ("reinicie o serviço sshd.service", "services.restart", "alterar", True),
]
project = os.environ["SMOKE_PROJECT"]
for query, tool, tier, confirm in cases:
    call = subprocess.run(
        ["gdbus", "call", "--session", "--dest", "org.forjaos.Hero",
         "--object-path", "/org/forjaos/Hero", "--method",
         "org.forjaos.Hero.AskText", query, project, "{}"],
        capture_output=True, text=True, timeout=70, check=True,
    )
    reply = json.loads(ast.literal_eval(call.stdout.strip())[0])
    result = (reply.get("tool"), reply.get("tier"), reply.get("requires_confirmation"))
    expected = (tool, tier, confirm)
    if result != expected:
        raise AssertionError(f"{query}: expected={expected}, actual={result}, status={reply.get('status')}")
    print(f"OK {query}: {result}, status={reply.get('status')}")
print("catalog-smoke: 10/10")
PY
