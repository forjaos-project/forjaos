<!-- GERADO por scripts/roadmap.py a partir de docs/roadmap/roadmap.json — NÃO EDITAR À MÃO -->

# Status — ForjaOS

**Atualizado em:** 2026-11-14 · **Itens:** 26/57 feitos (46 %) · 0 em andamento · 31 a fazer · 0 bloqueados

Gerado na `main` pelo workflow `roadmap-sync` — não edite nem commite em PR. Visual: `docs/roadmap/index.html`. Fonte: `docs/roadmap/roadmap.json`. Antes de pegar tarefa: `git fetch origin && python3 scripts/roadmap.py available`.

## Fase atual

**Fase 1 — Imagem instalável** (semanas 3–8) · DoD: Pendrive → instalação em dual boot no desktop de referência → docker compose up + Steam em < 15 min; NFR-001, 002, 011, 012 passando

## Próxima tarefa

**`F1-003` — Dual boot com Windows, Secure Boot + MOK, pós-instalação automática**

- Requisitos: FR-011, FR-012, FR-013
- Fase: 1 — Imagem instalável
- Estado: a fazer

Comece pelo gate *plan* (`docs/dev/METHODOLOGY.md §1`).

## Disponíveis agora (trabalho em paralelo)

- `F1-003` Dual boot com Windows, Secure Boot + MOK, pós-instalação automática · escopo: (definir no claim) · depende de: —
- `F1-004` Notebook híbrido (PRIME offload) e checklist de hardware · escopo: (definir no claim) · depende de: —
- `F1-006` Tema Plasma Forja (escuro/claro), layout padrão, wallpapers, atalhos — telas desktop_principal_dock / modo_claro · escopo: (definir no claim) · depende de: —
- `F1-007` Plymouth, SDDM e GRUB temáticos — telas splash_plymouth / sddm_login / bootloader_grub · escopo: (definir no claim) · depende de: —
- `F1-008` Konsole tema + forja doctor — tela terminal_konsole_dev_forja_doctor · escopo: (definir no claim) · depende de: —
- `F1-009` CLI forja: esqueleto Rust, doctor, install unity/claude-code · escopo: (definir no claim) · depende de: —
- `F1-010` Reproduzir componentes DX na base Bazzite desktop a partir dos scripts ublue-os/bazzite-dx, com verificação de licença · escopo: image/ · depende de: F0-002

Pegar: `python3 scripts/roadmap.py claim <ID> --agent claude|codex` (METHODOLOGY §6).

## Em andamento

- (nada em andamento)

## Bloqueios

- (nenhum)

## Feito

- `GOV-001` ADRs 026–028 (monorepo, tokens canônicos, precedência protótipo × PRD) e nota no PRD (ADR-026, ADR-027, ADR-028) · fase 0 — 2026-11-08
- `GOV-002` brand/palette.json (fonte única de tokens) + scripts/check-tokens.sh (FR-051, ADR-027) · fase 0 — 2026-11-08
- `GOV-003` docs/dev/METHODOLOGY.md — 5 gates (plan, code, test, review, ship) (NFR-040, NFR-041, NFR-042) · fase 0 — 2026-11-08
- `GOV-004` docs/design-system/DESIGN-RULES.md — regras, tradução de tokens, DoD visual (FR-050, FR-051, ADR-028) · fase 0 — 2026-11-08
- `GOV-005` Specs de fidelidade das 16 telas (scripts/gen_tela_specs.py) (FR-052, FR-121, FR-120, FR-020, FR-135, NFR-043) · fase 0 — 2026-11-08
- `GOV-006` Roadmap como fonte única: roadmap.json → STATUS.md + index.html (scripts/roadmap.py) (NFR-042, NFR-044) · fase 0 — 2026-11-08
- `GOV-007` AGENTS.md (fonte única), CLAUDE.md (@AGENTS.md), comandos /plan /code /test /review /ship, AGENTS.md por pasta (NFR-042) · fase 0 — 2026-11-08
- `GOV-008` PR template, check-agents-sync.sh, stub check-branding.sh, README (NFR-042) · fase 0 — 2026-11-08
- `GOV-009` Higiene do repositório: .gitignore, .gitattributes (LF), remoção de .pyc e .lnk, nome forjaos-project/forjaos (NFR-042) · fase 0 — 2026-11-09
- `GOV-010` Trabalho em paralelo Claude Code + Codex: claim/done por item, escopo e dependências, gerados só na main (NFR-042) · fase 0 — PR #2 · 2026-11-09
- `GOV-011` CI de verificação em PR: unittest (scripts/tests, brand/tests), run-shell-tests, check-tokens, check-agents-sync, roadmap validate --branch, gen_tela_specs --check, build_logo --check (NFR-040, NFR-041, NFR-042) · fase 0 — PR #16 · 2026-11-09 · Hoje nenhum workflow roda esses testes (só roadmap-sync e signing-preflight). PRs do roadmap-sync abertos com GITHUB_TOKEN não disparam workflows: não marcar o job como status check obrigatório da main sem resolver isso, senão o bot trava.
- `GOV-012` Proteção do espaço livre do SSD em builds locais e Docker Desktop (ADR-0037, NFR-042) · fase 0 — PR #52 · 2026-11-12
- `F0-001` Org GitHub + GHCR + cosign: segredos e permissões do repositório (ADR-002, G6) · fase 0 — PR #4 · 2026-11-09
- `F0-002` Containerfile mínimo FROM bazzite-nvidia-open:stable + os-release ForjaOS (FR-001, FR-003) · fase 0 — PR #9 · 2026-11-09
- `F0-003` Workflow GitHub Actions: podman build → testes de imagem → cosign → push :testing diário (ADR-002, NFR-040) · fase 0 — PR #23 · 2026-11-09
- `F0-004` check-branding.sh real: grep da imagem por marca Fedora/Bazzite/Bluefin; falha o CI (FR-002, G4) · fase 0 — PR #20 · 2026-11-09
- `F0-005` THIRD_PARTY_LICENSES.md gerado no CI (G4, ADR-007) · fase 0 — PR #27 · 2026-11-09
- `F0-006` Logo ForjaOS v1 em SVG (mono, cor, dark/light, ícone 16–512) (FR-053) · fase 0 — PR #8 · 2026-11-09
- `F0-007` Mascote Guará estático v1 (SVG com camadas nomeadas, 5 estados) (FR-054) · fase 0 — PR #36 · 2026-11-10
- `F0-008` bootc switch para a imagem em VM + upgrade/rollback testados (FR-001, FR-008) · fase 0 — PR #45 · 2026-11-12
- `F0-009` Substituir pacotes de identidade e entradas herdadas por forjaos-branding sem quebrar dependências (FR-002, G4) · fase 0 — PR #34 · 2026-11-09 · Remedia parte não visual da falha do workflow na issue #25; temas e wallpapers seguem F1-006/F1-007.
- `F0-010` Eliminar branding visível no Plasma, launchers e metadados de aplicativos e publicar imagens testing assinadas (FR-002, FR-055) · fase 0 — PR #39 · 2026-11-10 · Correção objetiva da issue #25. Entrega ativos visuais mínimos e amplia o checker; F1-006 mantém layout, alternância de tema e atalhos completos. A divergência Discover/Bazaar está na issue #40.
- `F1-001` Pacotes removidos/adicionados e serviços padrão da imagem (FR-004, FR-005, FR-006, FR-007) · fase 1 — PR #48 · 2026-11-12 · ADR-0034: F1-001 entrega a parcela verificável dos FR-004 a FR-007. O limite da ISO depende de F1-002; o inventário do forja doctor depende de F1-009; os componentes DX dependem de F1-010; herod e memd dependem dos cards próprios. Os requisitos completos permanecem abertos para a release.
- `F1-002` ISO Anaconda por rede via image-builder, checksum, assinatura, guia de gravação (FR-010, FR-014) · fase 1 — PR #50 · 2026-11-13
- `F1-005` Gerador de temas a partir do palette.json (Plasma, SDDM, Plymouth, Konsole, VS Code, GTK) (FR-051) · fase 1 — PR #57 · 2026-11-14
- `F1-011` Rebranding mínimo da imagem: ícone ForjaOS (brand/logo/png) no hicolor, LOGO= no os-release e /usr/share/ublue-os/image-info.json apontando para ghcr.io/forjaos-project (FR-002, FR-003, FR-053) · fase 1 — PR #31 · 2026-11-09 · Achados da revisão do PR #9: image-info.json ainda aponta para a imagem Bazzite (lido por ujust e pelas atualizações) e o LOGO foi removido sem substituto. Conferir scripts do Bazzite que testam ID=bazzite.

## A fazer (por fase)

### Fase 1 — Imagem instalável (em andamento)

- `F1-003` Dual boot com Windows, Secure Boot + MOK, pós-instalação automática (FR-011, FR-012, FR-013) · fase 1
- `F1-004` Notebook híbrido (PRIME offload) e checklist de hardware (FR-015, FR-016) · fase 1 — depende do notebook de referência estar disponível (§10.2)
- `F1-006` Tema Plasma Forja (escuro/claro), layout padrão, wallpapers, atalhos — telas desktop_principal_dock / modo_claro (FR-050, FR-052, FR-055, FR-058) · fase 1
- `F1-007` Plymouth, SDDM e GRUB temáticos — telas splash_plymouth / sddm_login / bootloader_grub (FR-056, FR-057, FR-002) · fase 1
- `F1-008` Konsole tema + forja doctor — tela terminal_konsole_dev_forja_doctor (FR-035, FR-036) · fase 1
- `F1-009` CLI forja: esqueleto Rust, doctor, install unity/claude-code (FR-042, FR-060) · fase 1
- `F1-010` Reproduzir componentes DX na base Bazzite desktop a partir dos scripts ublue-os/bazzite-dx, com verificação de licença (FR-001, FR-005, ADR-0032) · fase 1

### Fase 2 — Experiência dev/gamedev (a fazer)

- `F2-001` Wizard de primeiro boot (6 passos) — telas wizard_de_primeiro_boot e passo_6 (FR-020, FR-021, FR-022, FR-023, FR-024) · fase 2
- `F2-002` Experiência dev: Docker/Podman rootless, Git via keyring, distrobox, devcontainers, brew (FR-030, FR-031, FR-032, FR-033, FR-034) · fase 2
- `F2-003` Jogos e gamedev: Steam/Proton herdados, Godot, Modo Jogo (hero-game.target), controles (FR-040, FR-041, FR-043, FR-044) · fase 2
- `F2-004` CLI forja completo: subcomandos, --json, completions, confirmação [s/N] (FR-060, FR-061, FR-062, FR-063) · fase 2
- `F2-005` forja mcp register + Trivy no CI (FR-111, NFR-026) · fase 2
- `ADR-EXPLORER` Decidir (ADR + FR novo) o escopo do Dolphin Dev Edition antes de implementar — tela file_explorer (ADR-028) · fase 2 — protótipo sem FR no PRD

### Fase 3 — HERO v0 nativo (texto + sistema) (a fazer)

- `F3-001` herod: daemon Rust, D-Bus org.forjaos.Hero, máquina de estados, limites de consumo (FR-070, FR-071, FR-078) · fase 3
- `F3-002` Roteador de intenções, provedores por rota, Ollama gerenciado, persona (FR-090, FR-091, FR-092, FR-096) · fase 3
- `F3-003` Policy Engine (tiers) e AuditEvent em journald (FR-100, FR-101, FR-102, FR-103) · fase 3
- `F3-004` MCP servers hero-system, hero-desktop, hero-dev (rmcp, stdio) (FR-110, FR-112) · fase 3
- `F3-005` Overlay Central de Comando em modo texto — tela central_de_comando_hero_corrigida (FR-121, FR-085, FR-124, FR-125) · fase 3
- `F3-006` Plasmoid do Guará (texto) e plugin KRunner — tela plasmoid_do_guar (FR-120, FR-122) · fase 3
- `F3-007` Catálogo de ações (10 do G3), rota código, rota saúde-do-sistema (FR-093, FR-094, FR-095) · fase 3
- `F3-008` Spike Hermes Agent (1 semana) → ADR-025 (FR-097) · fase 3

### Fase 4 — Voz + Memória (a fazer)

- `F4-001` Gatilhos de voz, barge-in, mic kill switch, áudio nunca persiste (FR-072, FR-073, FR-074, FR-075, FR-076, FR-077) · fase 4
- `F4-002` Wake word openWakeWord: 8 modelos embarcados + treino de nome personalizado (FR-080, FR-081, FR-082) · fase 4
- `F4-003` STT faster-whisper, TTS Piper com visemes, mascote animado 60 fps (FR-083, FR-084, FR-123) · fase 4
- `F4-004` Modo Jogo completo e medição de impacto em FPS (FR-043, NFR-008) · fase 4
- `F4-005` memd: vault, coletores, índice SQLite FTS5 + sqlite-vec, graph.json, retenção (FR-130, FR-131, FR-132, FR-133, FR-134, FR-137) · fase 4
- `F4-006` Visualizador de memória (timeline + grafo) e MCP hero-memory — telas visualizador_* (FR-135, FR-136) · fase 4

### Fase 5 — Release 1.0 (a fazer)

- `F5-001` Validação física completa (§11) nos 2 hardwares com registro em docs/releases/ (ADR-024, G5) · fase 5
- `F5-002` Módulo Escudo opt-in (forja install escudo) (NFR-027, ADR-023) · fase 5
- `F5-003` Site + docs pt-BR/en — telas docs_documenta_o_t_cnica_oficial e landing (NFR-043, NFR-051) · fase 5
- `F5-004` TRADEMARK.md, canais stable/testing, release v1.0.0 (ADR-007, G4) · fase 5

## Entregas (mais recentes primeiro)

- **2026-11-14** · PR #57 · Gera temas de desktop a partir da paleta canônica com validação de drift · itens: F1-005
- **2026-11-13** · PR #50 · Entrega ISO Anaconda rc4 com verificação de payload, Wi-Fi e teste físico dos três métodos; resultado Ventoy documentado · itens: F1-002
- **2026-11-12** · PR #48 · Remoção condicional do Waydroid e contrato verificável de pacotes e serviços nas duas imagens, conforme ADR-0034 · itens: F1-001
- **2026-11-12** · PR #45 · Validated signed Bazzite-to-ForjaOS switch, upgrade, and rollback in CI VM with seven deployment states · itens: F0-008
- **2026-11-12** · PR #52 · Reserva de 160 GiB antes de testes locais, monitor de 1 minuto e parada normal do Docker abaixo de 120 GiB no SSD C: · itens: GOV-012
- **2026-11-10** · PR #39 · Branding visível ForjaOS validado no primeiro login; imagens testing assinadas e checker sem achados. · itens: F0-010
- **2026-11-10** · PR #36 · Five layered Guara SVG states generated from palette.json with 24 px preview and verified tests · itens: F0-007
- **2026-11-09** · PR #31 · Identidade ForjaOS nas duas imagens com ícones hicolor, LOGO no os-release e image-info.json próprio por variante · itens: F1-011
- **2026-11-09** · PR #34 · RPM forjaos-branding substitui identidade herdada e entradas de startup nas duas variantes, preservando dependências e serviços. · itens: F0-009
- **2026-11-09** · PR #8 · Logo ForjaOS v1: marca, logotipo horizontal e ícone de app em SVG (cor sobre escuro, cor sobre claro e mono) e PNG 16–512, gerados de palette.json com wordmark Plus Jakarta Sans em contornos · itens: F0-006
