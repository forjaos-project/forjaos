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
- [x] `F2-005` `forja mcp register` nos clientes instalados + Trivy no CI: CVEs críticas novas bloqueiam `:testing`; CVEs herdadas geram issue (FR-111, NFR-026). Servidores ausentes são registrados quando F3-004/F4-006 os entregar.

### Fase 3 — HERO v0 nativo (texto + sistema)

- [x] `F3-004` MCP servers `hero-system`, `hero-desktop`, `hero-dev` (rmcp, stdio): 49 entradas, 48 ferramentas operacionais, schemas/tier conferidos com `mcp-inspector`; build da imagem e presença dos executáveis/manifests confirmados. `hero-dev` usa projetos cadastrados ou detectados nas raízes previstas. `terminal.spawn_agent` está no catálogo como bloqueada e não inicia agente autônomo (FR-110, FR-112).
- [x] `F3-005` Overlay Central de Comando em modo texto — tela central_de_comando_hero_corrigida (FR-121, FR-085, FR-124, FR-125). UI QML, métricas, chat D-Bus com seleção de idioma, confirmação inline/notificação, catálogo en-US e atalho Super+Espaço; tiles exibem estado de VPN e Não perturbe, e a VPN ativa pode ser desconectada pelo Policy Engine. Serviços de segurança e AuditEvent vêm de systemd/journald; mascote anima na transição de estado. Build final da imagem, smoke test D-Bus e comparação QML offscreen passaram; aparência aprovada pelo PI. Validação final em Plasma/hardware permanece para a integração de release.
- [x] `F3-006` Plasmoid textual do Guará (popup de 384 px, estado, resposta HERO e menu de contexto) + plugin KRunner com sintaxe `h <pergunta>` para `AskText` (FR-120, FR-122). RPM integrado à imagem; build final, contrato de imagem, checker de branding, smoke QML em Xvfb e comparação visual aprovados. KRunner compilado e empacotado; teste em sessão Plasma/hardware permanece para integração de release. Ações de mute, memória e desligamento não são expostas pelo serviço atual e não foram simuladas.
- [x] `F3-007` Catálogo de ações, rota código e rota saúde-do-sistema (FR-093–095, FR-100): tiers sincronizados aos 49 tools MCP e às 5 ferramentas MCP de memória, verificador de catálogo, delegação confirmada no Konsole em projeto Git permitido com saída em FIFO volátil e código de saída, e diagnóstico com journald/GPU/CPU/RAM/rede/firewall/auditd/portas/disco/temperatura. Build local da imagem e smoke D-Bus do `herod` passaram, com 10/10 classificações e confirmações verificadas; 46 testes Rust, Clippy e cobertura de linhas de 71,97% passaram. A prova por voz e em hardware de referência pertence ao build final, conforme a issue #92; o smoke em contêiner não representa execução das 10 tarefas em uma sessão Plasma.
- [x] `F3-008` Spike Hermes Agent (FR-097): 20 tarefas pareadas (10 código, 10 pesquisa) com `qwen3.5:4b`; loop HERO 14/20 tarefas com todos os marcadores e mediana de 0,49 s, Hermes text-only 11/20 e 11,43 s. O teste de ferramenta do Hermes terminou sem resposta final; decisão de manter o loop próprio e não adotar Hermes nesta versão em [ADR-025](docs/adr/0025-spike-hermes-agent.md). Os prompts forneceram o contexto e não mediram recuperação independente.

### Fase 4 — Voz + Memória

  - [x] `F4-001` Gatilhos de voz, barge-in, mic kill switch e áudio só em memória (FR-072–077). PTT e wake word WeKws opt-in compartilham o nó PipeWire e os quadros PCM de 80 ms; o PTT tem prioridade, interrompe o Piper quando a fonte está pronta, e solicitações ocupadas são ignoradas com sinal. O microfone pode ser desligado por tray, overlay e Super+M, persiste o estado e gera AuditEvent. Tela bloqueada mantém wake/PTT e recusa texto/ações de tier `alterar`; teste Linux cobriu a fonte compartilhada sob bloqueio. A imagem local inclui runtime ONNX fixado e AEC dedicado; o worker rejeita silêncio/ruído curto. Ensaio com Piper e fonte virtual: áudio bruto ativou, Piper isolado após AEC não ativou em duas execuções, segunda fala sintética simultânea ativou; `strace` não observou escrita de áudio nas janelas medidas. Build local, lint bootc, contrato da imagem, branding, 82 testes Rust, Clippy, 9 testes Python do worker, suíte shell e 77,90% de cobertura de linhas passaram. Evidência em `docs/evidence/f4-001/`. Os modelos pt-BR aprovados e as métricas são F4-002; microfone físico, sala, sessão Plasma e metas de latência permanecem na validação final de hardware.
  - [x] `F4-002` Runtime WeKws e pipeline local de treinamento de wake word personalizada (FR-080–082): worker, extração log-mel, runtime ONNX fixado, treinador e exportação/medição implementados; reload do modelo por D-Bus sem reiniciar `herod`; manifesto privado com separação por locutor. Fonte WeKws Apache-2.0 fixada no commit `6a45aeb`. Smoke sintético de treino/exportação passou e não é evidência de reconhecimento real (`docs/evidence/f4-002/linux-training-smoke-2026-11-19.md`). A coleta e a aceitação de modelos ficam como débito do build final, detalhado abaixo. A amostra autorizada da voz de Rodrigo será usada em teste funcional local e não substituirá o conjunto comunitário FR-081.
  - [x] `F4-003` STT faster-whisper, TTS Piper com visemas e animação do mascote (FR-083, FR-084, FR-123; issue #103). Wizard permite baixar e selecionar uma das duas vozes pt-BR CC0 com revisão/hash fixados; `forja setup` preserva a escolha. `herod` expõe interrupção D-Bus independente do PTT; visemas alinhados são enviados ao overlay e animados por transformações QML, com 15 categorias fonéticas. Rust: 79 testes, Clippy e fmt passaram; worker: 2 testes passaram; imagem Linux: qmllint, lint bootc e contrato passaram. Sessão PipeWire real, metas FR-083/084, 60 fps e hardware de referência ficam na validação final #104.
- [x] `F4-004` Modo Jogo: pausa/restaura `memd`, descarrega modelos Ollama na entrada, usa Qwen3 4B local sob demanda e o descarrega após cada resposta, ativa/restaura perfil performance e Não perturbe (FR-043). 7 testes Python e 80 testes Rust passaram no Windows; fmt e Clippy passaram. O teste Linux via WSL ficou bloqueado por I/O no mount do D:. A medição NFR-008 com MangoHud, com/sem HERO nos 3 jogos, fica para a validação final no desktop Linux de referência.
- [x] `F4-005` memd (issue #109): vault, coletores, SQLite FTS5 + sqlite-vec, grafo Graphify e retenção (FR-130, FR-131, FR-132, FR-133, FR-134, FR-137). Shell/HERO, Git por hook e varredura diária, janelas KWin opt-in, notas Markdown opt-in, tipos de nó, coocorrência em janelas de 15 min, Graphify local e travado na imagem, merge do grafo e toggles implementados. `hero-memory`: fmt/Clippy, 20 testes e cobertura 72,26%; `forja` CLI: fmt/Clippy, 15 testes e cobertura 70,15%. Reconstrução sintética de 10 mil notas em WSL: 55,94 s, SQLite íntegro. CPU ociosa por 1 h, compatibilidade visual do vault em Obsidian/Logseq e hardware Linux de referência ficam na validação final ([issue #108](https://github.com/forjaos-project/forjaos/issues/108)).
- [x] `F4-006` Visualizador QML de memória e MCP hero-memory (FR-135, FR-136; issue #111): timeline diária e busca leem SQLite/FTS5; grafo de força em WorkerScript com zoom/pan, filtros por tipo/data, seleção e conexões; inspetor com prévia e abertura da fonte no editor; carga inicial e toggles fora da thread da UI. MCP search/timeline/related/remember/forget testado por stdio, com fontes em resource_link; registro da CLI validado para Claude Code/Codex/Hermes com clientes simulados. Linux offscreen com 10 mil nós/30 mil relações: primeiro quadro 288 ms, layout 7,6 s, pico do processo de teste 360,4 MiB (acima da meta; não comprova FR-135). memd: 20 testes, cobertura 72,29%; CLI: 16 testes, cobertura 71,39%; Clippy/fmt, 4 testes Python, qmllint e tokens passaram. Consumo, 60 fps, fidelidade visual e clientes reais em Plasma/hardware ficam para o build final na [issue #112](https://github.com/forjaos-project/forjaos/issues/112). Evidência em `docs/evidence/f4-006/`.

### Fase 5 — Release 1.0

- [ ] `F5-002` Módulo Escudo opt-in (forja install escudo) (NFR-027, ADR-023)
- [ ] `F5-003` Site + docs pt-BR/en — telas docs_documenta_o_t_cnica_oficial e landing (NFR-043, NFR-051)
- [ ] `F5-004` TRADEMARK.md, canais stable/testing, release v1.0.0 (ADR-007, G4)

### Fase 2 — Experiência dev/gamedev

- [ ] `ADR-EXPLORER` Decidir (ADR + FR novo) o escopo do Dolphin Dev Edition antes de implementar — tela file_explorer (ADR-028)

## No final (build final)

Testes, medições de NFR, boot/instalação das ISOs e validação em hardware real ficam todos aqui.

  - [ ] `F4-002` Validar os oito modelos WeKws (FR-080–082) ([issue #101](https://github.com/forjaos-project/forjaos/issues/101)): usar uma gravação autorizada da voz de Rodrigo para smoke funcional; coletar as oito frases de 20 locutores reais com consentimento para treino, avaliação e distribuição; completar ao menos 8 h de áudio ambiente negativo; montar os splits sem sobreposição de locutores, medir FAR e latência, embarcar modelos aprovados e testar o overlay ao vivo. A amostra individual de Rodrigo não conta como validação FR-081.
  - [ ] `F4-003` Validar voz local no Linux de referência ([issue #104](https://github.com/forjaos-project/forjaos/issues/104)): captura e interrupção em PipeWire real; latência FR-083 de até 1 s para fala de 5 s; primeiro áudio TTS em até 600 ms (FR-084); animação do mascote em 60 fps e ausência de persistência de áudio (FR-077/123).
- [ ] `F4-005` ([issue #108](https://github.com/forjaos-project/forjaos/issues/108)) Validar NFR-009 por 1 h, abrir vault de teste no Obsidian e Logseq e concluir prova no hardware Linux de referência.
- [ ] Rodar toda a suíte de testes e corrigir o que quebrar
- [ ] `F1-004` Notebook híbrido (PRIME offload) e checklist de hardware (FR-015, FR-016) — depende do notebook de referência estar disponível (§10.2)
- [ ] `F5-001` Validação física completa (§11) nos 2 hardwares com registro em docs/releases/ (ADR-024, G5). No Dell Inspiron, a instalação criou as partições Linux e abortou ao transicionar o `bootc` para `install_t` ([issue #114](https://github.com/forjaos-project/forjaos/issues/114)). Repetir com a ISO corrigida e validar instalação, Windows, GRUB e Secure Boot/MOK.
- [ ] Gerar a ISO final e subir no GitHub Release

## Feito (36)

- [x] `F2-001` Wizard de primeiro boot QML com seis passos, preflight, perfis instalados em segundo plano, chaves no KWallet e reprodução por `forja setup`. Prévia de voz e modelos wake word ficam para F4, conforme decisão do mantenedor em 2026-11-14. Build, testes e validação em hardware ficam para o build final.
- [x] `F3-001` Daemon `herod` em Rust com `org.forjaos.Hero`, propriedade `State`, `PropertiesChanged`, sinal `StateChanged(s)` e socket Unix local com diretório `0700` e socket `0600`. Unit limita 400 MiB/50% CPU/Nice 5; turno local tem timeout de 58 s, Ollama indisponível retorna resposta local sem fallback cloud e subprocessos são cancelados no timeout. Build release Linux passou; medição de consumo e validação em hardware Linux ficam para o build final (FR-070, FR-071, FR-078).
- [x] `F3-002` Roteador por regras + Qwen3 4B local para sete intenções; provedores Ollama, Anthropic, OpenAI, OpenRouter e Nous configuráveis por rota em TOML/D-Bus, com rotas de voz e sistema restritas ao local e chaves lidas do KWallet. Ollama escolhe Qwen3 8B/4B pela VRAM livre; no Modo Jogo usa Qwen3 4B sob demanda e descarrega após cada resposta (`keep_alive=0`). Fora do Modo Jogo, os modelos ficam carregados por cinco minutos. Persona editável fica subordinada ao bloco fixo, `SnapshotDoApp` entra no prompt e as dez trocas mais recentes ficam somente em memória. Build release Linux passou; acurácia no conjunto de 200 frases e validação de prompt ficam para a validação funcional final (FR-090, FR-091, FR-092, FR-096).
- [x] `F3-003` Policy Engine aplica o tier mínimo declarado em `hero/tool-policy.toml`, permite apenas elevação em `~/.config/hero/policy.toml`, recusa ferramentas bloqueadas e valida tier/IDs antes de persistir rotinas. D-Bus expõe tiers e `SaveRoutine`; decisões, confirmações, recusas e resultados geram AuditEvent JSON em journald sem texto da solicitação nem áudio. Respostas incluem ferramenta, tier e resultado; a apresentação visual do FR-103 pertence ao overlay F3-005. Build release Linux passou; validação funcional de tools/rotinas/journald fica para a integração final (FR-100, FR-101, FR-102, FR-103).

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
