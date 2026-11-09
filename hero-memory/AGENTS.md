# hero-memory/ — `memd`, coletores, visualizador, MCP `hero-memory`

**Escopo:** FR-130–FR-137, NFR-009, NFR-034; ADR-018, ADR-019.
**Equivale a:** `hero-memory` (ADR-026). Rust (`memd`), QML (visualizador). rpm via COPR, release `hero-memory-vX.Y.Z`.

## Toolchain e testes
- Rust: `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test && cargo llvm-cov --fail-under-lines 70`.
- QML: `qmllint`; `scripts/check-tokens.sh`; perf: abre < 1 s, < 150 MB e 60 fps com 10k nós (FR-135).
- Rebuild de 10k notas < 5 min (FR-133); `systemd-cgtop` 1 h ≤ 2 % CPU (NFR-009).
- Vault de teste abre no Obsidian e no Logseq sem conversão (FR-131).

## DoD local
- Unit `memd.service` (user) com `MemoryMax=300M`, `CPUQuota=20%`, `IOSchedulingClass=idle`, `Nice=15` (FR-130).
- Coletor novo: plugin com toggle, teste unitário, retenção configurável, **desligado por padrão** (exceto shell, git, HERO — FR-132).
- `graph.json` valida contra o schema do graphify (FR-134).
- Índice derivável: `forja memory rebuild` reconstrói tudo do vault (FR-133).

## Nunca
- Coletar conteúdo de janela ou captura de tela — só título + app (NFR-034).
- Gravar segredos: `.env`, senhas e tokens filtrados antes de indexar (NFR-024).
- Usar WebGL/QtWebEngine antes de provar que QML puro não atinge 10k nós a 60 fps (ADR-019).
- Captura total estilo Recall (ADR-018).

## Telas desta pasta
`forjaos_visualizador_de_mem_ria_linha_do_tempo_di_ria`, `forjaos_visualizador_do_grafo_da_mem_ria_fr_135`.

## Antes de começar aqui
1. `python3 scripts/roadmap.py available` → o item escolhido tem escopo desta pasta? Se não, pare.
2. `AGENTS.md` da raiz → regras e fluxo valem integralmente.
3. Telas desta pasta → leia a spec em `docs/design-system/telas/` **antes** do `code.html`.
