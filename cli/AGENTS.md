# cli/ — CLI `forja`

**Escopo:** FR-060–FR-063 (subcomandos, confirmação `[s/N]`, `--json`, completions), FR-036 (`forja doctor`), FR-024 (`forja setup`), FR-042 (`forja install unity`), FR-023 (`forja keys`), FR-082 (`forja mascot train`), FR-111 (`forja mcp register`), FR-133/137 (`forja memory`).
**Equivale a:** `forja-cli` (ADR-026). Binário único Rust (clap) embarcado na imagem; release `cli-vX.Y.Z`.

## Toolchain e testes
- `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test && cargo llvm-cov --fail-under-lines 70` (NFR-041).
- Testes de integração em `cli/tests/` com fixtures; cada subcomando tem teste de `--help` (pt-BR e en) e de schema `--json`.
- `ujust`, `bootc`, `podman`, D-Bus do HERO são **backends**: o CLI encapsula, nunca reimplementa.

## DoD local
- Subcomando novo: `--help` nos dois idiomas, `--json`, completions zsh/bash/fish regeneradas, documentado em `site/docs`.
- `forja doctor` sai ≠ 0 quando item crítico falha; saída colorida igual à spec `forjaos_terminal_konsole_dev_forja_doctor`.
- Ação de tier ≥ alterar pede confirmação `[s/N]` e mostra rota + contexto (FR-061).

## Nunca
- Gravar chave de API em arquivo; só KWallet via `secret-tool` (FR-023, NFR-024).
- Executar `rm`, `dd`, firewall ou escrita em `/etc` sem passar pelo Policy Engine do HERO quando acionado por ele (FR-093).
- Usar `devos` em qualquer string; o binário é `forja`.

## Telas desta pasta
`forjaos_terminal_konsole_dev_forja_doctor` (saída do `forja doctor`/`forja ai`; o tema do Konsole fica em `brand/`).
