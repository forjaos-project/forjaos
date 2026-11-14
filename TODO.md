# TODO — ForjaOS

Lista simples. Marque `[x]` ao terminar. Sem plano, review, claim ou ADR: faça, commite na `main`, siga.

Build, ISO e testes rodam **local**. O GitHub guarda o código e recebe só a ISO final.

## Em andamento

- (nada)

## Falta implementar


### Fase 1 — Imagem instalável

- [ ] `F1-003` Dual boot com Windows, Secure Boot + MOK, pós-instalação automática (FR-011, FR-012, FR-013) — Codex pegou
- [ ] `F1-009` CLI forja: esqueleto Rust, doctor, install unity/claude-code (FR-042, FR-060)
- [ ] `F1-010` Reproduzir componentes DX na base Bazzite desktop a partir dos scripts ublue-os/bazzite-dx, com verificação de licença (FR-001, FR-005, ADR-0032)

### Fase 2 — Experiência dev/gamedev

- [ ] `F2-001` Wizard de primeiro boot (6 passos) — telas wizard_de_primeiro_boot e passo_6 (FR-020, FR-021, FR-022, FR-023, FR-024)
- [ ] `F2-002` Experiência dev: Docker/Podman rootless, Git via keyring, distrobox, devcontainers, brew (FR-030, FR-031, FR-032, FR-033, FR-034)
- [ ] `F2-003` Jogos e gamedev: Steam/Proton herdados, Godot, Modo Jogo (hero-game.target), controles (FR-040, FR-041, FR-043, FR-044)
- [ ] `F2-004` CLI forja completo: subcomandos, --json, completions, confirmação [s/N] (FR-060, FR-061, FR-062, FR-063)
- [ ] `F2-005` forja mcp register + Trivy no CI (FR-111, NFR-026)

### Fase 3 — HERO v0 nativo (texto + sistema)

- [ ] `F3-001` herod: daemon Rust, D-Bus org.forjaos.Hero, máquina de estados, limites de consumo (FR-070, FR-071, FR-078)
- [ ] `F3-002` Roteador de intenções, provedores por rota, Ollama gerenciado, persona (FR-090, FR-091, FR-092, FR-096)
- [ ] `F3-003` Policy Engine (tiers) e AuditEvent em journald (FR-100, FR-101, FR-102, FR-103)
- [ ] `F3-004` MCP servers hero-system, hero-desktop, hero-dev (rmcp, stdio) (FR-110, FR-112)
- [ ] `F3-005` Overlay Central de Comando em modo texto — tela central_de_comando_hero_corrigida (FR-121, FR-085, FR-124, FR-125)
- [ ] `F3-006` Plasmoid do Guará (texto) e plugin KRunner — tela plasmoid_do_guar (FR-120, FR-122)
- [ ] `F3-007` Catálogo de ações (10 do G3), rota código, rota saúde-do-sistema (FR-093, FR-094, FR-095)
- [ ] `F3-008` Spike Hermes Agent (1 semana) → ADR-025 (FR-097)

### Fase 4 — Voz + Memória

- [ ] `F4-001` Gatilhos de voz, barge-in, mic kill switch, áudio nunca persiste (FR-072, FR-073, FR-074, FR-075, FR-076, FR-077)
- [ ] `F4-002` Wake word openWakeWord: 8 modelos embarcados + treino de nome personalizado (FR-080, FR-081, FR-082)
- [ ] `F4-003` STT faster-whisper, TTS Piper com visemes, mascote animado 60 fps (FR-083, FR-084, FR-123)
- [ ] `F4-004` Modo Jogo completo e medição de impacto em FPS (FR-043, NFR-008)
- [ ] `F4-005` memd: vault, coletores, índice SQLite FTS5 + sqlite-vec, graph.json, retenção (FR-130, FR-131, FR-132, FR-133, FR-134, FR-137)
- [ ] `F4-006` Visualizador de memória (timeline + grafo) e MCP hero-memory — telas visualizador_* (FR-135, FR-136)

### Fase 5 — Release 1.0

- [ ] `F5-002` Módulo Escudo opt-in (forja install escudo) (NFR-027, ADR-023)
- [ ] `F5-003` Site + docs pt-BR/en — telas docs_documenta_o_t_cnica_oficial e landing (NFR-043, NFR-051)
- [ ] `F5-004` TRADEMARK.md, canais stable/testing, release v1.0.0 (ADR-007, G4)

### Fase 2 — Experiência dev/gamedev

- [ ] `ADR-EXPLORER` Decidir (ADR + FR novo) o escopo do Dolphin Dev Edition antes de implementar — tela file_explorer (ADR-028)

## No final (build final)

Testes, medições de NFR, boot/instalação das ISOs e validação em hardware real ficam todos aqui.

- [ ] Rodar toda a suíte de testes e corrigir o que quebrar
- [ ] `F1-004` Notebook híbrido (PRIME offload) e checklist de hardware (FR-015, FR-016) — depende do notebook de referência estar disponível (§10.2)
- [ ] `F5-001` Validação física completa (§11) nos 2 hardwares com registro em docs/releases/ (ADR-024, G5)
- [ ] Gerar a ISO final e subir no GitHub Release

## Feito (29)

- [x] `F1-006` Layout (dock com Code/Godot), atalho Meta+E, temas e wallpapers instalados no rpm forjaos-plasma. Faltam: Super+Espaço, Super+G e Super+M (dependem do HERO e do Modo Jogo)
- [x] `F1-007` Plymouth forjaos-dark como padrão (embutido no initramfs) e temas GRUB instalados em /usr/share/grub/themes. Faltam: ativar o tema GRUB na instalação (junto do F1-003) e fontes PF2. O SDDM não se aplica: a base usa o Plasma Login Manager, que não aceita tema QML de terceiros; o login já usa o wallpaper ForjaOS
- [x] `F1-008` Perfil Konsole ForjaOS (JetBrains Mono 13, esquema Forja Dark) como padrão e `forja doctor` com --json e código de saída. Faltam: zsh+starship (F2-002) e o `forja` embutido na imagem (F1-009)
- [x] `GOV-001` ADRs 026–028 (monorepo, tokens canônicos, precedência protótipo × PRD) e nota no PRD
- [x] `GOV-002` brand/palette.json (fonte única de tokens) + scripts/check-tokens.sh
- [x] `GOV-003` docs/dev/METHODOLOGY.md — 5 gates (plan, code, test, review, ship)
- [x] `GOV-004` docs/design-system/DESIGN-RULES.md — regras, tradução de tokens, DoD visual
- [x] `GOV-005` Specs de fidelidade das 16 telas (scripts/gen_tela_specs.py)
- [x] `GOV-006` Roadmap como fonte única: roadmap.json → STATUS.md + index.html (scripts/roadmap.py)
- [x] `GOV-007` AGENTS.md (fonte única), CLAUDE.md (@AGENTS.md), comandos /plan /code /test /review /ship, AGENTS.md por pasta
- [x] `GOV-008` PR template, check-agents-sync.sh, stub check-branding.sh, README
- [x] `GOV-009` Higiene do repositório: .gitignore, .gitattributes (LF), remoção de .pyc e .lnk, nome forjaos-project/forjaos
- [x] `GOV-010` Trabalho em paralelo Claude Code + Codex: claim/done por item, escopo e dependências, gerados só na main
- [x] `GOV-011` CI de verificação em PR: unittest (scripts/tests, brand/tests), run-shell-tests, check-tokens, check-agents-sync, roadmap validate --branch, gen_tela_specs --check, build_logo --check
- [x] `GOV-012` Proteção do espaço livre do SSD em builds locais e Docker Desktop
- [x] `F0-001` Org GitHub + GHCR + cosign: segredos e permissões do repositório
- [x] `F0-002` Containerfile mínimo FROM bazzite-nvidia-open:stable + os-release ForjaOS
- [x] `F0-003` Workflow GitHub Actions: podman build → testes de imagem → cosign → push :testing diário
- [x] `F0-004` check-branding.sh real: grep da imagem por marca Fedora/Bazzite/Bluefin; falha o CI
- [x] `F0-005` THIRD_PARTY_LICENSES.md gerado no CI
- [x] `F0-006` Logo ForjaOS v1 em SVG (mono, cor, dark/light, ícone 16–512)
- [x] `F0-007` Mascote Guará estático v1 (SVG com camadas nomeadas, 5 estados)
- [x] `F0-008` bootc switch para a imagem em VM + upgrade/rollback testados
- [x] `F0-009` Substituir pacotes de identidade e entradas herdadas por forjaos-branding sem quebrar dependências
- [x] `F0-010` Eliminar branding visível no Plasma, launchers e metadados de aplicativos e publicar imagens testing assinadas
- [x] `F1-001` Pacotes removidos/adicionados e serviços padrão da imagem
- [x] `F1-002` ISO Anaconda por rede via image-builder, checksum, assinatura, guia de gravação
- [x] `F1-005` Gerador de temas a partir do palette.json (Plasma, SDDM, Plymouth, Konsole, VS Code, GTK)
- [x] `F1-011` Rebranding mínimo da imagem: ícone ForjaOS (brand/logo/png) no hicolor, LOGO= no os-release e /usr/share/ublue-os/image-info.json apontando para ghcr.io/forjaos-project
