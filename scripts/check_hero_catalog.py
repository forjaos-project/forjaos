#!/usr/bin/env python3
"""Check that every MCP tool has a safe HERO policy declaration."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "hero-mcp" / "manifests"
MEMORY_MCP = ROOT / "hero-memory" / "src" / "mcp.rs"
POLICY = ROOT / "hero" / "tool-policy.toml"
TIERS = {"livre": 0, "alterar": 1, "bloqueado": 2}
EXPECTED_TOOLS = 49
MEMORY_TOOLS = {
    "memory_search": ("memory.search", "livre"),
    "memory_timeline": ("memory.timeline", "livre"),
    "memory_related": ("memory.related", "livre"),
    "memory_remember": ("memory.remember", "livre"),
    "memory_forget": ("memory.forget", "alterar"),
}


def main() -> int:
    policy = tomllib.loads(POLICY.read_text(encoding="utf-8"))
    declared = policy.get("tools")
    if not isinstance(declared, dict):
        raise ValueError("hero/tool-policy.toml precisa declarar [tools]")

    errors: list[str] = []
    seen: set[str] = set()
    count = 0
    for path in sorted(MANIFESTS.glob("*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("transport") != "stdio":
            errors.append(f"{path.name}: transporte MCP precisa ser stdio")
        tools = manifest.get("tools")
        if not isinstance(tools, list):
            errors.append(f"{path.name}: tools precisa ser uma lista")
            continue
        for tool in tools:
            name = tool.get("name")
            tier = tool.get("tier")
            if not isinstance(name, str) or not isinstance(tier, str):
                errors.append(f"{path.name}: ferramenta sem nome ou tier")
                continue
            count += 1
            if name in seen:
                errors.append(f"{path.name}: ferramenta duplicada {name}")
            seen.add(name)
            effective = declared.get(name)
            if tier not in TIERS:
                errors.append(f"{name}: tier MCP desconhecido {tier}")
            elif effective not in TIERS:
                errors.append(f"{name}: tier ausente ou inválido na política")
            elif TIERS[effective] < TIERS[tier]:
                errors.append(f"{name}: política reduz o tier MCP {tier} para {effective}")
            if not isinstance(tool.get("inputSchema"), dict):
                errors.append(f"{name}: schema de entrada ausente")

    if not count:
        errors.append("nenhum manifesto MCP foi encontrado")
    elif count != EXPECTED_TOOLS:
        errors.append(f"quantidade de ferramentas inesperada: esperado {EXPECTED_TOOLS}, encontrado {count}")

    memory_source = MEMORY_MCP.read_text(encoding="utf-8")
    for mcp_name, (policy_name, minimum) in MEMORY_TOOLS.items():
        if not re.search(rf'"name"\s*:\s*"{re.escape(mcp_name)}"', memory_source):
            errors.append(f"hero-memory/src/mcp.rs: ferramenta ausente {mcp_name}")
        effective = declared.get(policy_name)
        if effective not in TIERS:
            errors.append(f"{policy_name}: tier ausente ou inválido na política")
        elif TIERS[effective] < TIERS[minimum]:
            errors.append(f"{policy_name}: política reduz o tier mínimo {minimum} para {effective}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Catalogo HERO valido: {count} ferramentas MCP + {len(MEMORY_TOOLS)} de memoria; tiers nao rebaixados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
