# TODO — ForjaOS

Lista simples. Marque `[x]` ao terminar. Sem plano, review, claim ou ADR: faça, commite na `main`, siga.

Build, ISO e testes rodam **local**. O GitHub guarda o código e recebe só a ISO final.

## Em andamento

- (nada)

## Falta implementar


### Fase 1 — Imagem instalável

- [x] `F1-010` Ferramentas DX livres dos scripts ublue-os/bazzite-dx na base desktop, com conferência das licenças RPM no build. VS Code, Docker CE e repositórios externos aguardam a decisão prevista no ADR-0034; tamanho da ISO fica para o build final (FR-001, FR-005, ADR-0032)


### Fase 2 — Experiência dev/gamedev

- [x] `F2-002` Experiência dev: Podman rootless, Docker CE rootless opcional, Git via keyring, Distrobox, Dev Containers CLI e VS Code opcional, Homebrew, uv e zsh + Starship (FR-030–FR-035). VS Code e Docker ficam fora da imagem e exigem escolha explícita no primeiro boot.
- [x] `F2-003` Jogos e gamedev: Steam e steam-devices preservados; gamescope, MangoHud e Bluetooth na imagem; perfil gamedev instala Godot com templates, ProtonPlus, Lutris e Heroic; Godot Tools entra no VS Code quando escolhido; Modo Jogo ativa `hero-game.target` para Steam/gamescope, Não perturbe e perfil performance. Integração com HERO/Memória e medição de FPS ficam em F4-004; jogos e controles em hardware ficam para o build final (FR-040, FR-041, FR-043, FR-044).
- [x] `F2-004` CLI `forja` completo no escopo FR-060–063: subcomandos, `--json`, ajuda pt-BR/en, completions bash/zsh/fish e confirmação `[s/N]`. Contratos e fluxos seguros validados no Windows e em Linux com D-Bus privado e backends simulados; `cargo llvm-cov --all-targets --fail-under-lines 70` passou com 70,42% de linhas. Voz, wake word e treino continuam em F4-002/003; a instalação real do Escudo continua em F5-002.
- [ ] `F2-005` forja mcp register + Trivy no CI (FR-111, NFR-026)

### Fase 3 — HERO v0 nativo (texto + sistema)

- [ ] `F3-001` herod: daemon Rust, D-Bus org.forjaos.Hero, máquina de estados, limites de consumo (FR-070, FR-071, FR-078). Em andamento: API D-Bus de texto/estado, confirmação de ação de uso único, resumo de ações aprovadas em memd, unit com limites e timeout de 58 s com subprocessos canceláveis. O binário embarcado e a chamada D-Bus foram verificados em contêiner; faltam áudio e validação de consumo em hardware Linux de referência.
- [ ] `F3-002` Roteador de intenções, provedores por rota, Ollama gerenciado, persona (FR-090, FR-091, FR-092, FR-096). Em andamento: chat local via Ollama, seleção 8B/4B por VRAM/Modo Jogo e keep-alive de cinco minutos; faltam rotas, provedores e persona configuráveis.
- [ ] `F3-003` Policy Engine (tiers) e AuditEvent em journald (FR-100, FR-101, FR-102, FR-103). Em andamento: tiers livres/alterar/bloqueado, confirmação curta e log sem texto da pergunta; faltam avaliação de rotinas e cobertura por tool.
- [ ] `F3-004` MCP servers hero-system, hero-desktop, hero-dev (rmcp, stdio) (FR-110, FR-112)
- [ ] `F3-005` Overlay Central de Comando em modo texto — tela central_de_comando_hero_corrigida (FR-121, FR-085, FR-124, FR-125)
- [ ] `F3-006` Plasmoid do Guará (texto) e plugin KRunner — tela plasmoid_do_guar (FR-120, FR-122)
- [ ] `F3-007` Catálogo de ações (10 do G3), rota código, rota saúde-do-sistema (FR-093, FR-094, FR-095). Em andamento: Compose up/down/logs, modo jogo, Git status, abrir projeto atual, testes com confirmação, GPU/CPU/RAM/rede, Wi-Fi/Bluetooth/VPN com confirmação, URL, memória, update, rollback e reinício de serviço; faltam apps/serviços adicionais, política por manifesto e validação de catálogo.
- [ ] `F3-008` Spike Hermes Agent (1 semana) → ADR-025 (FR-097)

### Fase 4 — Voz + Memória

- [ ] `F4-001` Gatilhos de voz, barge-in, mic kill switch, áudio nunca persiste (FR-072, FR-073, FR-074, FR-075, FR-076, FR-077)
- [ ] `F4-002` Wake word openWakeWord: 8 modelos embarcados + treino de nome personalizado (FR-080, FR-081, FR-082). Interface CLI presente; arquivos fonte baixados em `D:\ForjaOS` e índice privado de 8.571 candidatos negativos pt-BR gerado sem extrair áudio. Modelos e treinador não estão instalados. Fontes livres e pendências de licença dos ONNX compartilhados constam em `hero/wakeword/DATASETS.md`. **Pendência aceita em 15/11/2026:** as gravações autorizadas das oito frases por 20 locutores reais não estarão disponíveis agora; a validação FR-081 e a conclusão do item aguardam essa coleta.
- [ ] `F4-003` STT faster-whisper, TTS Piper com visemes, mascote animado 60 fps (FR-083, FR-084, FR-123). CLI lista e baixa duas vozes pt-BR CC0 com revisão/hash fixados. Worker local STT/TTS em pipes, com dependências e modelo small fixados por SHA-256, TTS em blocos e visemas derivados de alinhamentos; build e testes sintéticos na imagem Linux passaram. O caminho para `pw-cat` e o cancelamento do `SpeechHandle` passaram com consumidor sintético; faltam teste com servidor PipeWire real, ligação ao `herod`, captura pelo nó PipeWire HERO, API D-Bus de interrupção, wizard de voz, animação e metas de latência em hardware Linux de referência.
- [ ] `F4-004` Modo Jogo completo e medição de impacto em FPS (FR-043, NFR-008)
- [ ] `F4-005` memd: vault, coletores, índice SQLite FTS5 + sqlite-vec, graph.json, retenção (FR-130, FR-131, FR-132, FR-133, FR-134, FR-137). Em andamento: eventos shell/HERO, Git por hook e varredura diária, janelas KWin opt-in, notas em `vault/notes/`, tipos de nó e arestas de coocorrência em janelas de 15 min, Graphify local sob demanda e embarcado com dependências travadas, merge de nós/arestas Graphify no grafo geral e toggles dos coletores. Reconstrução sintética de 10 mil notas em contêiner: 58,5 s, SQLite íntegro; faltam medição de CPU ociosa por 1 h e validação em hardware Linux de referência.
- [ ] `F4-006` Visualizador de memória (timeline + grafo) e MCP hero-memory — telas visualizador_* (FR-135, FR-136). Em andamento: visualizador QML com timeline, grafo de força calculado em WorkerScript, busca, zoom/pan, filtros por tipo/data (incluindo código) e toggle dos coletores; MCP stdio oferece search/timeline/related/remember/forget. Em contêiner Linux offscreen, 10 mil nós/30 mil relações receberam layout em 5,4 s; ainda faltam medição de abertura, 60 fps/consumo no Linux de referência e registro nos clientes.

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
- [ ] `F5-001` Validação física completa (§11) nos 2 hardwares com registro em docs/releases/ (ADR-024, G5). No Dell Inspiron de teste, o Anaconda iniciou e conectou à rede; o particionador parou com `no free partition slots` apesar de 97,66 GiB livres. Repetir após a correção da partição e validar Windows, GRUB e Secure Boot/MOK.
- [ ] Gerar a ISO final e subir no GitHub Release

## Feito (32)

- [x] `F2-001` Wizard de primeiro boot QML com seis passos, preflight, perfis instalados em segundo plano, chaves no KWallet e reprodução por `forja setup`. Prévia de voz e modelos wake word ficam para F4, conforme decisão do mantenedor em 2026-11-14. Build, testes e validação em hardware ficam para o build final.

- [x] `F1-006` Layout (dock com Code/Godot), atalho Meta+E, temas e wallpapers instalados no rpm forjaos-plasma. Faltam: Super+Espaço, Super+G e Super+M (dependem do HERO e do Modo Jogo)
- [x] `F1-007` Plymouth forjaos-dark como padrão (embutido no initramfs), temas GRUB instalados em /usr/share/grub/themes e fontes PF2 geradas. O serviço de primeiro boot do F1-003 ativa o tema GRUB. O SDDM não se aplica: a base usa o Plasma Login Manager, que não aceita tema QML de terceiros; o login já usa o wallpaper ForjaOS
- [x] `F1-008` Perfil Konsole ForjaOS (JetBrains Mono 13, esquema Forja Dark) como padrão e `forja doctor` com --json e código de saída. zsh + Starship instalados no primeiro boot (F2-002).
- [x] `F1-003` Dual boot: preflight de segurança Dual Boot/MOK, NTFS somente leitura, ajuste do relógio local ao detectar Windows e ativação do tema/fontes GRUB no primeiro boot. O host do wizard integra a tela QML em F2-001; aceitação física de instalação e boot fica em F5-001.
- [x] `F1-009` CLI Rust `forja` embutida na imagem, com `doctor`, `install unity` (AppImage oficial em `~/.local`, lançador e fallback sem FUSE) e `install claude-code` (instalador oficial); confirmação `[s/N]`, `--yes`, `--json` e ajuda PT-BR/EN. Documentação da ajuda gerada em `site/docs/`.
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
