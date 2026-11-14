# hero-mcp/ — servidores MCP `hero-system`, `hero-desktop`, `hero-dev`

**Escopo:** FR-110–FR-112 e a tabela de tools/tiers da §7.5 do PRD. Usados por HERO, Claude Code, Codex CLI e Hermes Agent.
**Equivale a:** `hero-mcp` (ADR-026). Rust com `rmcp`, transporte stdio, **sem porta de rede**. rpm via COPR, release `hero-mcp-vX.Y.Z`.

## Toolchain e testes
- `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test && cargo llvm-cov --fail-under-lines 70`.
- `mcp-inspector` valida cada server (FR-110); teste de schema JSON de todo manifesto.
- Teste de escopo: `hero-dev` só enxerga diretórios de `~/.config/hero/projects.toml` (FR-112).

## DoD local
- Tool nova: entrada na tabela §7.5 do PRD **ou** ADR; tier declarado no manifesto; schema de entrada/saída; teste.
- Nenhuma tool com tier `livre` tem efeito colateral no sistema.
- `forja mcp register` registra o server em Claude Code, Codex e Hermes (FR-111).

## Nunca
- Abrir socket TCP/UDP (stdio apenas — FR-110, NFR-012).
- Tool que execute `rm`, `dd`, firewall ou `/etc` fora de `bloqueado` por padrão (FR-093).
- `clipboard.read` e `screenshot.take` abaixo de tier `alterar` (§7.5).
