# hero/ — HERO: `herod`, overlay, plasmoid, KRunner, wake word, Policy Engine

**Escopo:** FR-070–FR-078 (motor), FR-080–FR-085 (voz), FR-090–FR-097 (rotas), FR-100–FR-103 (Policy Engine/auditoria), FR-120–FR-125 (interface), NFR-003–NFR-010, NFR-030–NFR-032.
**Equivale a:** `hero` (ADR-026). Rust (`herod`), QML/Kirigami (overlay, plasmoid), C++ só como cola KDE. rpm via COPR, release `hero-vX.Y.Z`.

## Toolchain e testes
- Rust: `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test && cargo llvm-cov --fail-under-lines 70`.
- QML: `qmllint`; `scripts/check-tokens.sh`; perf test 60 fps do mascote (FR-123); overlay abre ≤ 150 ms (NFR-010).
- Áudio sintético (Piper) para testar wake word, barge-in e supressão do próprio TTS (FR-073, FR-081).
- `strace` por escrita em disco durante captura (FR-077).

## DoD local
- Unit `herod.service` (user) com `MemoryMax=400M`, `CPUQuota=50%`, `Nice=5` (FR-070); ocioso ≤ 120 MB com `memd` (NFR-003); VRAM 0 após 5 min (NFR-004).
- Toda tool tem tier declarado; `AuditEvent` em journald (`SYSLOG_IDENTIFIER=hero-audit`) sem áudio nem texto completo (FR-102).
- Estados publicados por D-Bus `org.forjaos.Hero` a cada transição (FR-071).
- Rotas `conversa-de-voz` e `sistema` recusam provedor cloud (FR-091).

## Nunca
- Persistir áudio em disco (FR-077, NFR-030).
- Executar ação sem Policy Engine (ADR-014). Nunca descer um tier abaixo do declarado no manifesto (FR-100).
- Fallback cloud na rota de voz (ADR-013).
- Capturar microfone fora do nó PipeWire do HERO (ADR-015).
- Usar "Jarvis" em qualquer string, inclusive testes.

## Telas desta pasta
`forjaos_central_de_comando_hero_corrigida` (canônica), `forjaos_central_de_comando_hero_overlay` (só referência), `forjaos_plasmoid_do_guar_kde_plasma_6`.
