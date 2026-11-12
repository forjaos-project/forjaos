# PRD — ForjaOS

**Documento da verdade do projeto.** Tudo o que está aqui está decidido. Mudanças entram por ADR (seção 14) que revoga a decisão anterior com a razão escrita — nunca por conversa.

| Campo | Valor |
| --- | --- |
| Produto | ForjaOS — sistema operacional open source baseado em Linux para desenvolvimento de software e jogos |
| Descritor | Nenhum: o nome é só "ForjaOS" (ADR-031) |
| Motor de assistente | HERO (daemon `herod`) |
| Mascote padrão | Guará (lobo-guará do cerrado); nome escolhido pelo usuário na instalação |
| CLI | `forja` |
| Versão do PRD | 1.0 — 2026-11-08 |
| Equipe | Solo, 100 % comunitário |
| Licença do código próprio | Apache-2.0 |
| Status | Fase 0 (Fundação) |
| Status operacional | ver `docs/STATUS.md` (gerado) e `docs/roadmap/index.html` |

**Regras deste documento**

1. Não há checkpoints de aprovação humana. Cada entregável tem um critério de pronto (DoD) objetivo, verificável por script ou por observação direta em hardware. Passou, está pronto.
2. Não há bloqueio entre frentes. Imagem, HERO, Memória, CLI e identidade visual evoluem em repositórios separados com releases independentes. A fase indica prioridade de tempo, não dependência.
3. Requisitos têm ID (`FR-xxx` funcional, `NFR-xxx` não funcional). Issues, commits e ADRs referenciam o ID.
4. Idioma do produto: pt-BR primeiro e en-US em seguida. Idioma do código, commits e docs técnicas: inglês.

---

## 1. Visão

ForjaOS é a distro que um desenvolvedor instala e, em menos de 15 minutos, está com Docker subindo, Git autenticado, Steam rodando e um assistente de voz local que conhece o sistema. Não é "mais um Arch bonito" nem "Ubuntu com tema". É um sistema **image-based** (atualização atômica, rollback em um comando) com **IA nativa e local** como camada do SO, não como app instalado.

**Posicionamento em uma frase:** *Forja — onde você constrói. Linux para quem projeta, planeja, desenvolve e joga, com um assistente inteligente que roda na sua máquina.*

**Diferenciais, em ordem de peso:**

1. HERO — assistente de voz e texto integrado ao desktop, 100 % local na fala, que executa ações no sistema via MCP sob um Policy Engine.
2. Memória do sistema — vault Markdown + grafo do que você fez (shell, git, conversas, projetos).
3. Dev + gamedev prontos — Docker/Podman, Godot, MCPs, CLIs, Unity Hub (instalador), Ollama, Hermes Agent, Codex CLI, Claude Code (instalador), chaves no keyring.
4. Image-based sobre Universal Blue — kernel, NVIDIA, Steam e codecs mantidos upstream; ForjaOS mantém só a camada própria.
5. Identidade: tema único aplicado a tudo, mascote com personalidade, CLI `forja` como porta de entrada.

**Público-alvo primário:** desenvolvedor full-stack brasileiro, 25–45 anos, máquina com GPU NVIDIA RTX ou AMD RDNA2+, que hoje usa Windows com WSL ou Ubuntu/Pop!_OS e joga no mesmo computador. **Secundário:** dev e gamedev indie (Node/React/Godot/Unity/Web/Mobile/Desktop), estudante de computação, entusiasta de IA local.

**Não é para:** servidores, hardware anterior a 2018, quem quer rolling release puro, quem precisa de `apt install` como fluxo primário.

---

## 2. Objetivos e não-objetivos

### 2.1 Objetivos do 1.0

| ID | Objetivo | Métrica de sucesso |
| --- | --- | --- |
| G1 | Instalável por qualquer dev sem suporte | 5 usuários externos instalam do pendrive ao `docker compose up` sem abrir issue de bloqueio |
| G2 | Rápido e leve | Metas da seção 9 passam no CI e na máquina de referência |
| G3 | Assistente útil, não demo | 10 tarefas do catálogo (seção 7.6) executadas por voz e texto com taxa de sucesso ≥ 90 % na máquina de referência |
| G4 | Distribuível legalmente | `THIRD_PARTY_LICENSES.md` gerado; zero marca Fedora/Bazzite visível; nada proprietário embarcado fora do permitido |
| G5 | Validado em hardware real | ISO gravada em pendrive instala em notebook com NVIDIA híbrida e em desktop com RTX, em dual boot com Windows |
| G6 | Sustentável por uma pessoa | Build diário automático; atualização de base do Universal Blue absorvida sem intervenção manual em ≥ 90 % dos dias |

### 2.2 Não-objetivos do 1.0 (backlog 2.0 — seção 12)

Instalador próprio, loja de apps própria, COSMIC como desktop, spin tiling completo, visão por câmera, OCR de tela, integrações Gmail/Agenda/Spotify, suporte ARM, versão paga, loja de skills do HERO, captura total de memória estilo Recall.

---

## 3. Princípios de produto

1. **Herdar antes de construir.** Se Universal Blue, KDE ou um pacote Fedora resolve, usa-se. Código próprio só onde há diferencial.
2. **Local primeiro.** Voz, wake word, STT, TTS e o LLM da rota de voz rodam na máquina. Cloud é opt-in por rota e nunca recebe áudio.
3. **Nada age sem o Policy Engine.** Toda ação com efeito no sistema passa por tier e gera `AuditEvent`.
4. **Opcional e removível.** HERO e Memória são serviços de usuário; `systemctl --user disable hero` deixa um Plasma limpo.
5. **Consumo é feature.** Todo serviço próprio tem `MemoryMax`, `CPUQuota` e `Nice` declarados. Modelos de IA descarregam quando ociosos.
6. **Uma porta de entrada.** O CLI `forja` encapsula bootc, ujust, podman, HERO e Memória. Tudo que a UI faz, o CLI faz.
7. **O usuário é dono do dado.** Vault em Markdown aberto; índice reconstruível; áudio nunca persiste.
8. **Decisão escrita vence.** ADR revoga ADR. Sem reabrir por opinião.

---

## 4. Decisões arquiteturais (registro consolidado)

| ADR | Decisão | Escolha | Alternativas descartadas e por quê |
| --- | --- | --- | --- |
| ADR-001 | Base | Fedora Atomic via Universal Blue; bases desktop `bazzite-nvidia-open:stable` e `bazzite:stable` (ADR-0032) | Arch/Omarchy (rolling quebra driver; Omarchy já ocupa o nicho); NixOS (curva, binários proprietários); Debian/Ubuntu (kernel velho para gaming) |
| ADR-002 | Modelo de build | bootc/OCI: Containerfile + GitHub Actions + cosign + GHCR; ISO por rede via `image-builder generic-iso` (ADR-0035) | ISO artesanal (não reproduzível); live-build (Debian) |
| ADR-003 | Desktop | KDE Plasma 6 padrão; spin tiling (niri) só no 2.0 | GNOME (gaming fraco, extensões quebram); COSMIC (estável desde 12/2025, mas lacunas de applets — candidato 2.0); Hyprland como padrão (descoberta zero para quem vem do Windows) |
| ADR-004 | Nome do SO | ForjaOS, sem descritor (ADR-031) | "DeveloperOS" sozinho (genérico, colide com DevOS-Developer-OS no GitHub); Ipê (menos ligado a dev/jogos) |
| ADR-005 | Assistente | Projeto novo, nativo: daemon Rust (`herod`) + QML/KDE Frameworks. rrb-jarvisOS descontinuado como código; suas decisões migram como ADR-010 a ADR-016 | Portar o Electron do jarvisOS (150–300 MB ociosos, migração dupla) |
| ADR-006 | Nome do mascote | Escolhido na instalação; padrão **Guará**. HERO é o nome do motor | Nome fixo HERO (saturado, wake word curta); "Jarvis" (marca Marvel/Disney) |
| ADR-007 | Licenças | Código próprio Apache-2.0; artes CC BY-SA 4.0; nome e logo sob política de marca própria | AGPL (afasta contribuição de empresas; sem versão paga planejada, perde o motivo) |
| ADR-008 | Hardware mínimo | NVIDIA RTX 20xx+ (driver aberto) ou AMD RDNA2+, 8 GB VRAM, 16 GB RAM, NVMe, UEFI | Suportar Pascal (GTX 10xx) exigiria driver proprietário legado, fora do driver 590+ |
| ADR-009 | Equipe e sustentação | Solo, 100 % comunitário, sem versão paga | — |
| ADR-010 | STT | faster-whisper, modelo small, pt-BR fixo, processo filho sob demanda | whisper.cpp (herdado do jarvisOS: custo do runtime Python assumido pela qualidade) |
| ADR-011 | TTS | Piper; vozes pt-BR com licença verificada uma a uma | ElevenLabs/Gemini TTS (cloud, fere "local primeiro") |
| ADR-012 | Wake word | openWakeWord (Apache-2.0) em ONNX Runtime, CPU; **modelos treinados pelo projeto** com áudio sintético do Piper | Porcupine (free tier encerrado em 2026-06-30, exige AccessKey online); modelos prontos do openWakeWord (CC BY-NC-SA, não comercial) |
| ADR-013 | LLM da rota de voz | Qwen3 8B Q4 via Ollama, só local; Qwen3 4B Q4 em GPU de 8 GB com jogo aberto; sem fallback cloud | Fallback cloud na fala (fere privacidade e o invariante) |
| ADR-014 | Invariante de ação | Conversa por voz não executa ação sem passar pelo Policy Engine; tiers por tool; `AuditEvent` em journald | Allowlist simples sem tiers |
| ADR-015 | Microfone | Um único dono: HERO é um nó PipeWire; wake word e push-to-talk são consumidores | Captura por API direta (lição "capturar ≠ capturarPcm") |
| ADR-016 | Áudio | Nunca persiste em disco; transcrição por enunciado completo | Gravação para melhorar modelo |
| ADR-017 | Agente | Loop próprio no HERO; Hermes Agent avaliado em spike de 1 semana na Fase 3 antes de qualquer adoção | Adotar Hermes de cara (substitui loop sem medir) |
| ADR-018 | Memória | Vault Markdown (compatível Obsidian/Logseq) + SQLite (FTS5 + sqlite-vec) + `graph.json` no formato do graphify; coletores por fonte, opt-in | Captura total (modelo Recall) |
| ADR-019 | Visualizador de memória | App QML (Qt Quick) próprio, grafo em WebGL via QtWebEngine só se QML puro não atingir 10 k nós a 60 fps | Electron; Obsidian (proprietário, não embarcável) |
| ADR-020 | CLI | `forja`, Rust (clap), um binário, subcomandos espelham a UI | Shell scripts soltos; `ujust` direto (fica como backend) |
| ADR-021 | Instalador | Anaconda via `image-builder generic-iso`, com payload por rede e sem instalador próprio (ADR-0035) | Calamares (não suporta bootc nativamente); instalador próprio (anos de trabalho) |
| ADR-022 | Segurança padrão | SELinux enforcing (herdado), firewalld, auditd, Secure Boot com chave ublue + MOK; zero porta aberta | Desligar SELinux "para facilitar" |
| ADR-023 | Módulo Escudo | CrowdSec e Suricata como opt-in instalável via `forja install escudo`, nunca no padrão | IDS no padrão (CPU constante, modo promíscuo) |
| ADR-024 | Validação física | Todo release `stable` é instalado a partir de ISO em pendrive em dois hardwares de referência: notebook com NVIDIA híbrida e desktop RTX, ambos em dual boot com Windows | Só VM |

---

## 5. Arquitetura

### 5.1 Camadas

```
┌─────────────────────────────────────────────────────────────┐
│ Identidade: tema Plasma, SDDM, Plymouth, wallpapers, mascote │
├─────────────────────────────────────────────────────────────┤
│ Experiência: overlay Central de Comando (QML), plasmoids,    │
│ KRunner plugin, dock, CLI forja                              │
├──────────────────────┬──────────────────────────────────────┤
│ HERO (herod, Rust)   │ Memória (memd, Rust)                 │
│ wake word, STT, TTS, │ coletores, índice SQLite, graph.json │
│ roteador, Policy     │ hero-memory MCP                      │
│ Engine, MCP client   │                                      │
├──────────────────────┴──────────────────────────────────────┤
│ MCP servers locais (stdio): hero-system, hero-desktop,      │
│ hero-dev, hero-memory — usados por HERO, Claude Code,       │
│ Codex CLI e Hermes Agent                                    │
├─────────────────────────────────────────────────────────────┤
│ Stack dev/jogos: Docker CE + Podman, Godot, Steam/Proton,   │
│ Ollama, Hermes Agent, Codex CLI, VS Code, distrobox, brew   │
├─────────────────────────────────────────────────────────────┤
│ Base: Universal Blue bazzite-nvidia-open (Fedora Atomic,    │
│ kernel Bazzite, NVIDIA open modules, PipeWire, Plasma 6)    │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Repositórios

> **Revogado por ADR-026 (2026-11-08):** o projeto é um monorepo em `forjaos-project/forjaos` (antes `rrb-forjaOS`); a tabela abaixo permanece como registro histórico. Mapeamento: `forjaos-image` → `image/`, `forja-cli` → `cli/`, `hero` → `hero/`, `hero-mcp` → `hero-mcp/`, `hero-memory` → `hero-memory/`, `forjaos-brand` → `brand/`, `forjaos-site` → `site/`. Ver `docs/adr/0026-monorepo.md`.

| Repo | Conteúdo | Linguagem | Release |
| --- | --- | --- | --- |
| `forjaos-image` | Containerfile, `build_files/`, `system_files/`, recipes `ujust`, workflow, ISO, docs, ADRs do SO | Shell, Containerfile, YAML | Imagem OCI diária (`:testing`), `:stable` semanal, ISO por release |
| `forja-cli` | CLI `forja` | Rust | Binário embarcado na imagem; releases independentes |
| `hero` | `herod`, plasmoid, KRunner plugin, overlay QML, modelos de wake word, Policy Engine, roteador, ADRs do assistente | Rust, QML, C++ (cola KDE) | rpm próprio via COPR, embarcado na imagem |
| `hero-mcp` | `hero-system`, `hero-desktop`, `hero-dev` | Rust | rpm via COPR |
| `hero-memory` | `memd`, coletores, visualizador QML, `hero-memory` MCP | Rust, QML | rpm via COPR |
| `forjaos-brand` | Logo, mascote (fontes SVG), paleta, tipografia, wallpapers, tema Plasma/SDDM/Plymouth, ícones, tema VS Code/terminal | SVG, QML, JSON | Pacote `forjaos-branding` rpm |
| `forjaos-site` | Site, docs do usuário, download | Astro ou Hugo | GitHub Pages |

Cada repo tem `LICENSE` (Apache-2.0; `forjaos-brand` CC BY-SA 4.0 para artes + `TRADEMARK.md`), `docs/adr/`, CI com lint, testes e release automatizado por tag.

### 5.3 Variantes de imagem

| Tag | Base ublue | GPU | Desktop |
| --- | --- | --- | --- |
| `forjaos:stable` | `bazzite:stable` | AMD / Intel | Plasma 6 |
| `forjaos-nvidia-open:stable` | `bazzite-nvidia-open:stable` | NVIDIA Turing+ | Plasma 6 |
| `forjaos-tiling:stable` (2.0) | `forjaos-nvidia-open` + niri | ambas | niri + Plasma como fallback |

Canais: `:testing` (build diário, sem promessa), `:stable` (promovido semanalmente quando o CI de metas passa), `:vX.Y` (tag fixa por release).

### 5.4 Fluxo de build e release

```
push/cron ─► GitHub Actions
  ├─ podman build (Containerfile) ─► imagem OCI
  ├─ testes de imagem: pacotes presentes, serviços habilitados, zero marca Fedora/Bazzite, SELinux enforcing
  ├─ cosign sign ─► push ghcr.io/<org>/forjaos*:testing
  ├─ (semanal) VM boot: systemd-analyze, free, ss -tlnp, metas NFR ─► promove :stable
  └─ (release) image-builder generic-iso ─► ISO Anaconda por rede ─► checksum + assinatura ─► GitHub Release
```

---

## 6. Requisitos funcionais — Sistema

### 6.1 Imagem e base

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-001 | Imagem OCI derivada de `bazzite-nvidia-open` e `bazzite`, construída por Containerfile (ADR-0032) | `podman build` passa no CI; `bootc switch ghcr.io/<org>/forjaos-nvidia-open:stable` funciona a partir de Bazzite |
| FR-002 | Rebranding total: nenhum texto, ícone ou wallpaper Fedora/Bazzite/Bluefin visível em boot, login, desktop, Configurações, `os-release`, Discover | Script `check-branding.sh` no CI grepa a imagem e falha ao encontrar; inspeção visual nos 2 hardwares de referência |
| FR-003 | `/etc/os-release`: `NAME="ForjaOS"`, `PRETTY_NAME="ForjaOS X.Y"`, `ID=forjaos`, `ID_LIKE="fedora"`, `HOME_URL`, `BUG_REPORT_URL` | Teste no CI |
| FR-004 | Pacotes removidos da base que não servem ao público: emuladores pré-instalados, Waydroid, apps de mídia duplicados (lista em `build_files/remove.txt`) | Lista aplicada; tamanho da ISO ≤ 6 GB |
| FR-005 | Pacotes adicionados: Docker CE, Podman, distrobox, Homebrew, VS Code (rpm oficial), Godot 4 (Flatpak Flathub), Ollama, Hermes Agent (uv tool), Codex CLI, `gh`, git-credential-libsecret, kubectl, k9s, terraform, Node LTS (via `fnm`), Python 3 + uv, Rust (`rustup` via recipe), Java 21 (OpenJDK) + `sdkman` via recipe, Blender (Flatpak), btop, nvtop, Cockpit (desligado), firewalld, auditd, `forja`, `hero*`, `forjaos-branding` | `forja doctor` lista cada um como presente |
| FR-006 | Serviços habilitados por padrão: `docker.socket` (rootless por usuário via recipe), `firewalld`, `auditd`, `herod` (user), `memd` (user). Desligados: `sshd`, `cockpit.socket` | `systemctl is-enabled` testado no CI |
| FR-007 | Codecs, Steam, Proton, gamescope, MangoHud, controles (udev) herdados do Bazzite e mantidos | Teste de boot semanal confirma `steam` presente |
| FR-008 | Atualização atômica com `bootc upgrade` automática diária (uupd herdado) e rollback com `bootc rollback` ou pelo menu de boot | Teste no CI: upgrade e rollback em VM |

### 6.2 Instalação e dual boot

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-010 | ISO Anaconda por rede gerada por `image-builder generic-iso` para cada variante, assinada, com checksum SHA-256 publicado; payload fixado por digest e assinatura verificada também na instalação (ADR-0035) | Cada ISO < 2 GiB no GitHub Release; checksum e assinaturas conferem; instalador exige rede e rejeita payload sem assinatura válida |
| FR-011 | Instalação ao lado do Windows: o instalador detecta Windows, permite redimensionar NTFS e instalar na partição livre; GRUB lista Windows | Instalação real nos 2 hardwares de referência com Windows preservado e bootável |
| FR-012 | Secure Boot funcional: módulos NVIDIA assinados com a chave ublue; o 1º boot pede enroll da chave MOK com instrução na tela em pt-BR | Boot com Secure Boot ativo nos 2 hardwares |
| FR-013 | Pós-instalação automática: `timedatectl set-local-rtc 1` quando Windows detectado; montagem NTFS somente leitura por padrão; aviso sobre Fast Startup e BitLocker na primeira tela do wizard | Script roda no 1º boot; teste manual |
| FR-014 | Gravação em pendrive documentada e testada com Fedora Media Writer, Ventoy e `dd` | Guia em `docs/install.md`; os 3 métodos testados no release |
| FR-015 | Notebook com gráficos híbridos (iGPU + NVIDIA): sistema boota no modo híbrido padrão (PRIME offload), `prime-run` disponível, tela externa via NVIDIA funciona | Teste no notebook de referência: Plasma na iGPU, jogo via `prime-run`, HDMI externo |
| FR-016 | Hardware do notebook funcional sem intervenção: Wi-Fi, Bluetooth, touchpad (gestos), teclas de brilho/volume, suspensão e retorno, bateria com perfis de energia | Checklist `docs/hardware-checklist.md` preenchido no release |

### 6.3 Primeiro boot e wizard

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-020 | Wizard de 1º boot (QML, tela cheia, pulável) em 6 passos: idioma/teclado → nome e voz do mascote → perfil (web, backend, gamedev, devops, IA, mínimo) → contas (GitHub via `gh auth`, chaves de API opcionais) → instaladores proprietários (Unity Hub, Claude Code) → resumo | Wizard completa em < 5 min sem rede; com rede instala o escolhido em segundo plano |
| FR-021 | Passo "mascote": lista curada com 8 nomes cujas wake words já estão embarcadas (Guará, Tupã, Jaci, Iara, Ipê, Boto, Curió, Arara), preview de voz (2–3 vozes Piper pt-BR) e campo "nome personalizado" | Seleção grava `~/.config/hero/persona.toml`; nome personalizado dispara treinamento em segundo plano (FR-064) |
| FR-022 | Perfis instalam conjuntos: **web** (Node, pnpm, Chrome, Postman), **backend** (Java, Go, Python, Postgres container, DBeaver), **gamedev** (Godot, Blender, Unity Hub, Aseprite se licença, Krita), **devops** (kubectl, k9s, helm, terraform, ansible, AWS/GCP/Azure CLIs), **IA** (Ollama + modelos sugeridos, Hermes, Codex, Claude Code, Jupyter), **mínimo** (nada além da base) | Cada perfil tem `recipes/profile-<nome>.just`; teste de instalação no CI em VM |
| FR-023 | Chaves de API (Anthropic, OpenAI, OpenRouter, Nous Portal) gravadas no KWallet via `secret-tool`; nunca em dotfiles | `forja keys set anthropic` grava; `forja keys env` imprime `export` só para a sessão; grep de `.bashrc`/`.zshrc` por chaves no CI do wizard |
| FR-024 | Tudo que o wizard faz é reproduzível por `forja setup --profile gamedev --mascot guara` | Teste no CI |

### 6.4 Experiência de desenvolvimento

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-030 | Docker CE e Podman coexistem; `docker` rootless configurado para o usuário no 1º boot; `podman` rootless padrão | `docker run hello-world` e `podman run hello-world` sem sudo |
| FR-031 | Git autenticado pelo sistema: `gh auth login` no wizard configura `git-credential-libsecret`; SSH agent via KWallet | `git push` em repo privado sem pedir senha após o wizard |
| FR-032 | distrobox e toolbox prontos com imagens Ubuntu, Arch e Fedora pré-definidas (`forja box create ubuntu`) | Comando cria e entra no container em < 60 s com rede |
| FR-033 | devcontainers: VS Code com extensão Dev Containers e `devcontainer` CLI | Abrir repo com `.devcontainer` funciona |
| FR-034 | Homebrew instalado para CLIs que não estão em rpm | `brew install` funciona |
| FR-035 | Terminal padrão: Konsole com tema ForjaOS, zsh + starship + atuin + zoxide + fzf configurados; bash e fish disponíveis | Terminal abre com prompt ForjaOS |
| FR-036 | `forja doctor` verifica e reporta: kernel, scheduler, zram, driver GPU, CUDA, Docker, Podman, Git auth, Ollama e modelo carregado, chaves presentes, Unity Hub, Claude Code, Codex, Hermes, serviços HERO/Memória, portas abertas | Saída igual à do mockup; código de saída ≠ 0 se algo crítico falha |

### 6.5 Experiência de jogos e gamedev

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-040 | Steam, Proton (GE via ProtonPlus), gamescope, MangoHud, Lutris e Heroic herdados do Bazzite e funcionais | 3 jogos de referência (um nativo, dois Proton) rodam no desktop de referência |
| FR-041 | Godot 4 (Flatpak) com export templates baixados no perfil gamedev; integração com VS Code (extensão godot-tools) | Projeto exemplo exporta Linux e Web |
| FR-042 | Unity Hub via `forja install unity`: baixa o AppImage/tar oficial, instala em `~/.local`, cria `.desktop`, aplica dependências conhecidas (libssl1.1 compat quando necessário) | Unity Hub abre, faz login e instala um editor LTS |
| FR-043 | Modo Jogo: target `hero-game.target` ativado automaticamente quando Steam/gamescope sobe (ou por tile/CLI); para `memd`, descarrega Ollama, mantém só wake word; perfil de energia performance; Não perturbe ligado | FPS com modo jogo ≤ 1 % abaixo de HERO desligado, medido com MangoHud nos 3 jogos |
| FR-044 | Controles (Xbox, DualSense, 8BitDo) funcionam via Bluetooth e USB sem configuração | Checklist no release |

### 6.6 Interface e identidade visual

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-050 | Tema Plasma "Forja" (escuro padrão, claro disponível): paleta roxo/azul-ciano sobre grafite (conforme mockup), acento laranja-guará para o mascote; cantos 8 px; blur moderado | Tema instalado e selecionado por padrão; variantes clara/escura alternam pelo atalho do sistema |
| FR-051 | Tema aplicado em cadeia: Plasma, SDDM, Plymouth, Konsole, VS Code, GTK (via `gtk-theme` Breeze-like), Firefox (userChrome opcional) — uma paleta, um arquivo fonte em `forjaos-brand/palette.json` que gera os demais | Script de geração no CI; captura de tela de cada superfície no release |
| FR-052 | Layout padrão: painel superior (projeto/branch atual, relógio, GPU e temperatura, rede, BT, Escudo, bateria, indicador HERO); dock inferior central com lançadores (Terminal, Code, Git, Docker, Unity*, Godot, HERO, Monitor, Navegador, Apps); overlay Central de Comando à direita por Super+Espaço | Layout aplicado no 1º login; `*Unity` só após instalação |
| FR-053 | Logo ForjaOS (bigorna estilizada + spark em forma de chave `<>`), em SVG, versões mono, cor, dark/light, ícone 16–512 px | Arquivos em `forjaos-brand/logo/`; usados em Plymouth, SDDM, `os-release` logo, site |
| FR-054 | Mascote Guará: lobo-guará 2D vetorial, estilo flat com gradiente sutil, 5 estados (ocioso, escutando, pensando, falando, erro) + 12–15 visemes; arquivos SVG com camadas nomeadas para animação em QML | Animação roda a 60 fps no plasmoid; outro personagem pode ser trocado mantendo os nomes de camada |
| FR-055 | Wallpapers: 4 oficiais em 4K (claro/escuro × abstrato/mascote), formato do mockup (ondas roxo/ciano sobre grafite), mais 1 por release | Em `forjaos-brand/wallpapers/`, instalados em `/usr/share/wallpapers/ForjaOS/` |
| FR-056 | Plymouth: logo + barra fina, sem texto, ≤ 3 s de exibição extra | Boot medido |
| FR-057 | SDDM: tema com wallpaper escuro, campo único, avatar, logo discreto | Captura no release |
| FR-058 | Atalhos padrão documentados: Super+Espaço (Central de Comando/HERO), Super+T (terminal), Super+E (arquivos), Super+G (modo jogo), Super+M (mute do microfone do HERO) | `docs/shortcuts.md`; aplicados via `kglobalshortcutsrc` na imagem |

### 6.7 CLI `forja`

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-060 | Binário único Rust; subcomandos: `doctor`, `setup`, `install <pacote>` (unity, claude-code, escudo, …), `up`/`down`/`logs` (atalho para compose do projeto atual), `box` (distrobox), `keys`, `ai "<pergunta>"` (envia ao HERO por D-Bus), `mascot` (nome, voz, treinar), `memory` (search, timeline, rebuild), `game-mode on|off`, `update`, `rollback`, `report` (gera diagnóstico para issue) | Cada subcomando tem `--help` em pt-BR e en; testes de integração em VM |
| FR-061 | `forja ai` imprime rota escolhida, contexto usado e pede confirmação `[s/N]` antes de qualquer ação de tier ≥ alterar (conforme mockup) | Teste com tool de tier alterar |
| FR-062 | Saída colorida, `--json` em todos os comandos para scripts | Teste de schema JSON |
| FR-063 | Completions para zsh, bash e fish instaladas | Tab completa |

---

## 7. Requisitos funcionais — HERO (assistente)

### 7.1 Motor

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-070 | `herod`: daemon Rust, unit systemd de usuário com `MemoryMax=400M` (sem modelos), `CPUQuota=50%`, `Nice=5`; expõe API D-Bus `org.forjaos.Hero` e socket Unix | `systemctl --user status herod` ativo após login; limites aplicados |
| FR-071 | Estados do motor (máquina única, publicada por D-Bus): `desligado`, `ocioso`, `escutando`, `gravando`, `transcrevendo`, `pensando`, `falando`, `erro` | Sinal D-Bus a cada transição; mascote reflete |
| FR-072 | Dois gatilhos: wake word (sempre que `herod` roda, inclusive tela bloqueada) e push-to-talk (hotkey global toggle + botão segurar no overlay). Push-to-talk sempre vence e suspende detecção | Teste: PTT durante wake word suspende detecção |
| FR-073 | Barge-in por voz com supressão do próprio áudio (o TTS não dispara a wake word) | Teste automatizado com áudio sintético do Piper contendo o nome |
| FR-074 | Disparo com turno em andamento (`gravando`, `transcrevendo`, `pensando`) é ignorado com sinal visual; em `falando` interrompe e aceita | Teste de estado |
| FR-075 | Tela bloqueada: responde só por voz; overlay não sobe; ações de tier ≥ alterar são recusadas até desbloquear | Teste com `loginctl lock-session` |
| FR-076 | Controles do microfone: kill switch no tray e no overlay, hotkey de mute (Super+M), indicador permanente (ícone do plasmoid + indicador de mic do PipeWire), `AuditEvent` ao ligar/desligar | Teste manual e log em journald |
| FR-077 | Áudio nunca persiste; buffers em memória liberados após transcrição | Revisão de código + teste de `strace` por escrita em disco durante captura |
| FR-078 | Timeout de turno 60 s; falha de STT/LLM retorna frase fixa local e volta a `ocioso` | Teste com Ollama parado |

### 7.2 Voz

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-080 | Wake word via openWakeWord (ONNX Runtime, CPU); frame de 80 ms; sensibilidade ajustável com teste ao vivo no overlay | Latência wake → `escutando` ≤ 300 ms; falso positivo ≤ 1 por 8 h de áudio ambiente de referência |
| FR-081 | 8 modelos de wake word embarcados (lista FR-021), treinados pelo projeto com áudio sintético Piper (várias vozes, ruído, reverb) e validados com 20 locutores reais gravados pela comunidade | Dataset e script de treino em `hero/wakeword/`; métricas por modelo publicadas |
| FR-082 | Nome personalizado: `forja mascot train "<nome>"` gera dataset sintético e treina em GPU local (20–60 min) ou CPU (2–4 h) em segundo plano; Guará ativo até o modelo pronto; nomes de 1 sílaba ou da lista de palavras comuns pt-BR recebem aviso de falso positivo | Treino completa na máquina de referência; modelo ativa sem reiniciar `herod` |
| FR-083 | STT: faster-whisper small pt-BR, processo filho (Python via `uv`, runtime baixado no 1º uso com SHA-256 pinado), carregado após wake word, descarregado após 5 min ocioso | Fim da fala → texto ≤ 1 s para enunciado de 5 s na máquina de referência |
| FR-084 | TTS: Piper, processo filho sob demanda; voz escolhida no wizard; síntese em bloco com `SpeechHandle` para interrupção; emite `VisemeEvent[]` (timeline de fonemas → visemes) para o mascote | Fim do texto → início do áudio ≤ 600 ms; lip-sync visualmente alinhado |
| FR-085 | Modo texto completo: tudo que a voz faz, o campo de texto do overlay e `forja ai` fazem | Paridade testada no catálogo FR-093 |

### 7.3 Cérebro e rotas

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-090 | Roteador classifica a intenção em rotas: `conversa-de-voz`, `sistema` (ações), `pesquisa`, `criação`, `código`, `saúde-do-sistema`, `memória`. Classificação por modelo local pequeno + regras; usuário vê a rota escolhida | Acurácia ≥ 90 % no conjunto de 200 frases de teste |
| FR-091 | Provedor por rota configurável no overlay e em `~/.config/hero/routes.toml`: `conversa-de-voz` e `sistema` só aceitam local; demais aceitam Ollama, Claude API, OpenAI API, OpenRouter, Nous Portal; chave do KWallet | Tentativa de configurar cloud na rota de voz é recusada com mensagem |
| FR-092 | Ollama gerenciado pelo HERO: modelo padrão Qwen3 8B Q4; se VRAM livre < 6 GB ou modo jogo ativo, usa Qwen3 4B Q4; descarrega após 5 min ocioso; `keep_alive` controlado | `nvidia-smi` mostra 0 MB do Ollama após 5 min; troca de modelo testada |
| FR-093 | Catálogo inicial de ações (tier entre parênteses): abrir projeto X no editor (livre); subir/derrubar compose do projeto (alterar); mostrar logs de serviço/container (livre); status de GPU/CPU/RAM/rede (livre); ligar/desligar Wi-Fi, BT, VPN, modo jogo, não perturbe (alterar); abrir URL/app (livre); criar nota na memória (livre); buscar na memória (livre); rodar testes do projeto (alterar); `git status`/`git log` (livre); criar branch (alterar); atualizar sistema (alterar); reiniciar serviço (alterar); instalar pacote (alterar); qualquer `rm`, `dd`, mudança de firewall, alteração em `/etc` (bloqueado por padrão) | 10 tarefas do G3 passam por voz e texto |
| FR-094 | Rota `código`: delega para terminal gerenciado rodando Claude Code, Codex CLI ou Hermes Agent no diretório do projeto, com os MCP servers do HERO já registrados; HERO acompanha e resume | "HERO, pede pro Claude rodar os testes do game-api" abre terminal, executa, resume |
| FR-095 | Rota `saúde-do-sistema`: lê journald (prioridade ≤ err nas últimas 24 h), `nvidia-smi`, firewalld, auditd, `ss -tlnp`, espaço em disco, temperatura; resume em linguagem natural e aponta ação | Resumo correto em cenário com erro injetado |
| FR-096 | Persona: texto livre editável + bloco fixo não editável que garante formato de voz (frases curtas, confirma ação antes de executar, diz a rota quando perguntado); histórico em memória de 10 trocas; contexto do app (`SnapshotDoApp`) no prompt | Teste de prompt |
| FR-097 | Spike Hermes Agent (Fase 3, 1 semana): medir Hermes como motor das rotas `código` e `pesquisa` contra o loop próprio em 20 tarefas; resultado vira ADR-025 | ADR escrito com números |

### 7.4 Policy Engine e auditoria

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-100 | Tiers: `livre` (executa), `alterar` (confirma por voz/clique antes de executar), `bloqueado` (recusa, explica, oferece comando para o usuário rodar). Tier por tool declarado no manifesto do MCP server; usuário pode subir tier, nunca descer abaixo do declarado | Teste por tool |
| FR-101 | Avaliação na configuração para sequências/rotinas (conforme jarvisOS F04): atividade acima do tier permitido não pode ser salva na rotina | Teste de salvamento |
| FR-102 | `AuditEvent` estruturado em journald (`SYSLOG_IDENTIFIER=hero-audit`): timestamp, gatilho, rota, tool, tier, decisão, duração; nunca o áudio nem o texto completo da fala | `journalctl -t hero-audit -o json` legível; teste de campos |
| FR-103 | Overlay mostra, por ação executada, o tier e o resultado (conforme mockup: "✓ docker compose up · ✓ Godot aberto · 2,1 s") | Visual no release |

### 7.5 MCP servers (`hero-mcp`)

| Server | Tools (tier) |
| --- | --- |
| `hero-system` | `services.list/status` (livre), `services.restart` (alterar), `journal.query` (livre), `firewall.status` (livre), `firewall.toggle_zone` (bloqueado), `gpu.status`, `cpu.status`, `mem.status`, `disk.status`, `thermal.status` (livre), `network.status` (livre), `wifi.toggle`, `bluetooth.toggle`, `vpn.toggle` (alterar), `system.update` (alterar), `system.rollback` (alterar), `ollama.models`, `ollama.load/unload` (alterar), `packages.install` (alterar), `power.profile` (alterar), `game_mode.toggle` (alterar) |
| `hero-desktop` | `windows.list`, `windows.focus` (livre), `notify.send` (livre), `dnd.toggle` (alterar), `media.play/pause/next` (livre), `clipboard.read` (alterar), `clipboard.write` (livre), `screenshot.take` (alterar, com indicador), `apps.launch` (livre), `url.open` (livre) |
| `hero-dev` | `projects.list` (livre, pastas conhecidas), `project.open` (livre), `compose.up/down/logs` (alterar/alterar/livre), `containers.list/logs` (livre), `git.status/log/diff` (livre), `git.branch.create` (alterar), `git.commit` (alterar), `tests.run` (alterar), `terminal.spawn_agent` (alterar: claude-code, codex, hermes) |
| `hero-memory` | `memory.search`, `memory.timeline`, `memory.related` (livre), `memory.remember` (livre), `memory.forget` (alterar) |

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-110 | Todos os servers em Rust (`rmcp`), transporte stdio, sem porta de rede; manifesto JSON com tools, schemas e tier declarado | `mcp-inspector` valida cada server |
| FR-111 | Registro automático dos servers em Claude Code (`~/.claude.json`), Codex CLI e Hermes Agent via `forja mcp register` (chamado pelo wizard) | `claude mcp list` mostra os 4 |
| FR-112 | `hero-dev` só vê diretórios em `~/.config/hero/projects.toml` (preenchido por `forja project add` ou detecção de `.git` em `~/proj`, `~/dev`, `~/code`) | Teste de escopo |

### 7.6 Interface do HERO

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-120 | Plasmoid na barra: mascote em miniatura com estado; clique abre o overlay; menu de contexto com mute, modo texto, desligar | Plasmoid instalado por padrão |
| FR-121 | Overlay Central de Comando (QML, conforme mockup): coluna à direita, 520 px, abre por Super+Espaço, wake word ou clique; fecha com Esc ou clique fora; lembra a última aba. Seções: card do assistente (mascote, transcrição, ações com tier, waveform), tiles (Wi-Fi, BT, VPN, Modo Jogo, Firewall, Não perturbe), Desempenho (CPU, RAM, GPU, VRAM, amostra a cada 2 s, pausa ao fechar), Containers, IA · modelos, Segurança e logs, Rede | Overlay funcional no release; consumo do overlay fechado = 0 (processo encerra, só o plasmoid fica) |
| FR-122 | Plugin KRunner: digitar na busca do Plasma com prefixo `h ` ou frase em linguagem natural envia ao HERO | Teste |
| FR-123 | Mascote animado com os 5 estados e lip-sync por `VisemeEvent[]`; QML, 60 fps, GPU-friendly (sem rasterização por frame) | Perf test |
| FR-124 | Notificações do HERO via `org.freedesktop.Notifications` com ações inline (confirmar/cancelar tier alterar) | Teste |
| FR-125 | Tudo em pt-BR e en-US via Qt Linguist; idioma segue o do sistema | Strings 100 % traduzidas no release |

---

## 8. Requisitos funcionais — Memória do sistema

| ID | Requisito | DoD |
| --- | --- | --- |
| FR-130 | `memd`: daemon Rust, unit de usuário com `MemoryMax=300M`, `CPUQuota=20%`, `IOSchedulingClass=idle`, `Nice=15` | Limites aplicados; indexação não aparece acima de 2 % de CPU médio |
| FR-131 | Vault em `~/ForjaOS/vault/` com `daily/AAAA-MM-DD.md`, `projects/<repo>.md`, `hero/AAAA-MM-DD.md`, `graph/graph.json`; Markdown + `[[wikilinks]]` + frontmatter YAML; abre no Obsidian/Logseq sem conversão | Teste de abertura nos dois |
| FR-132 | Coletores, cada um um plugin ligável no overlay e em `memory.toml`, todos **desligados exceto shell, git e HERO** no 1º boot: **shell** (via atuin: comando, cwd, exit, duração), **git** (hooks post-commit + varredura diária dos projetos), **HERO** (conversas resumidas e ações aprovadas), **janelas** (título + app + tempo a cada 30 s via KWin D-Bus; nunca conteúdo), **código** (graphify por repositório, sob demanda via `forja memory graph <repo>`), **notas** (pasta do vault) | Cada coletor com teste unitário e toggle funcional |
| FR-133 | Índice `~/.local/share/hero/memory.db`: SQLite com FTS5 e sqlite-vec; embeddings locais via Ollama (`nomic-embed-text` ou equivalente ≤ 300 MB); índice derivável — `forja memory rebuild` reconstrói do vault | Rebuild de 10 k notas < 5 min na máquina de referência |
| FR-134 | Grafo: nós = notas, repos, commits, comandos, conversas, janelas; arestas = wikilinks, co-ocorrência temporal (mesma janela de 15 min), relações do graphify; exportado em `graph.json` no formato do graphify | Validação de schema |
| FR-135 | Visualizador QML: três telas — linha do tempo do dia, grafo (força dirigida, zoom, filtro por tipo/data), busca; abre em < 1 s; < 150 MB com 10 k nós; 60 fps no desktop de referência | Perf test |
| FR-136 | `hero-memory` MCP com `search`, `timeline`, `related(entity)`, `remember(note)`, `forget(id)`; usado pelo HERO para contexto e por Claude Code/Codex para contexto de projeto | "O que eu fiz ontem no game-api?" responde com fontes clicáveis |
| FR-137 | Retenção configurável por coletor (padrão: janelas 90 dias, shell 1 ano, demais ilimitado); `forja memory purge` | Teste |

---

## 9. Requisitos não funcionais

### 9.1 Performance (medidos no CI em VM e na máquina de referência: Ryzen 7 9800X3D + RTX 5060 8 GB; falha bloqueia promoção a `stable`)

| ID | Métrica | Meta | Como medir |
| --- | --- | --- | --- |
| NFR-001 | Boot (firmware → SDDM) | ≤ 12 s em NVMe | `systemd-analyze` |
| NFR-002 | RAM ociosa após login, HERO e Memória desligados | ≤ 1,6 GB | `free -m` 60 s após login, média de 3 |
| NFR-003 | RAM adicional com HERO ocioso (só wake word) + `memd` | ≤ 120 MB | `smem -P herod\|memd` |
| NFR-004 | VRAM com HERO ocioso | 0 MB | `nvidia-smi` após 5 min sem uso |
| NFR-005 | Wake word → `escutando` | ≤ 300 ms | `hero-audit` timestamps |
| NFR-006 | Fim da fala → início da resposta falada (LLM já carregado) | ≤ 2,5 s | idem |
| NFR-007 | Carga a frio Qwen3 8B Q4 | ≤ 6 s | idem |
| NFR-008 | Impacto em jogo com modo jogo | ≤ 1 % FPS | MangoHud, 3 jogos, com/sem HERO |
| NFR-009 | Indexação de memória | ≤ 2 % CPU médio; I/O só idle | `systemd-cgtop` 1 h |
| NFR-010 | Overlay abrir | ≤ 150 ms | timestamp QML |
| NFR-011 | Tamanho da ISO | ≤ 6 GB | CI |
| NFR-012 | Portas abertas por padrão | 0 (exceto loopback) | `ss -tlnp` |
| NFR-013 | Upgrade + rollback | atômicos, rollback ≤ 1 reboot | CI em VM |

### 9.2 Segurança

| ID | Requisito |
| --- | --- |
| NFR-020 | SELinux enforcing; política própria para `herod`, `memd` e MCP servers (confinados ao `$HOME` do usuário e aos sockets declarados) |
| NFR-021 | firewalld zona `public` padrão, nenhum serviço exposto; Cockpit e sshd desligados até o usuário ligar |
| NFR-022 | Secure Boot suportado (chave ublue + MOK); kernel e módulos NVIDIA assinados |
| NFR-023 | Imagem assinada com cosign; `bootc` verifica assinatura (`--enforce-container-sigpolicy`) |
| NFR-024 | Chaves de API só no KWallet; nenhuma em arquivo de texto; wrapper expõe por processo |
| NFR-025 | Downloads do HERO (runtime Python, modelos Whisper/Piper/wake word) com SHA-256 pinado e `AuditEvent` |
| NFR-026 | CVE scan da imagem (Trivy) no CI; CVE crítica em pacote próprio bloqueia promoção; em pacote herdado gera issue automática |
| NFR-027 | Módulo Escudo (opt-in, `forja install escudo`): CrowdSec (bloqueio de IPs em SSH/HTTP), Suricata (modo IDS na interface escolhida), painel no overlay. Declarado como consumidor de CPU na instalação |
| NFR-028 | Sandbox de dev como padrão sugerido: perfis instalam ferramentas de linguagem dentro de distrobox quando possível; `npm install` global no host gera aviso do HERO |

### 9.3 Privacidade técnica (propriedades do sistema, verificáveis)

| ID | Propriedade |
| --- | --- |
| NFR-030 | Áudio nunca é escrito em disco (FR-077) |
| NFR-031 | Nenhum byte de áudio ou transcrição sai da máquina nas rotas `conversa-de-voz` e `sistema` (FR-091) |
| NFR-032 | Rotas cloud enviam só o texto da pergunta e o contexto selecionado; o overlay mostra o que foi enviado |
| NFR-033 | Telemetria do projeto: nenhuma. Contagem de downloads vem do GitHub Releases |
| NFR-034 | Coletor de janelas grava título e app, nunca conteúdo ou captura de tela |

### 9.4 Qualidade e manutenção

| ID | Requisito |
| --- | --- |
| NFR-040 | Build diário automático; falha abre issue; `:stable` só promove com todos os testes verdes |
| NFR-041 | Cobertura de testes em Rust ≥ 70 % nos crates `herod`, `forja`, `memd`, MCP servers |
| NFR-042 | Toda feature tem issue com ID do PRD; todo ADR tem número sequencial e status (`aceito`, `revogado por ADR-nnn`) |
| NFR-043 | Docs do usuário em pt-BR e en-US no site; cada subcomando `forja` documentado |
| NFR-044 | Versionamento: imagem `AAAA.MM.DD` (data do build) + tag semântica por release (`v1.0.0`); crates seguem semver |

### 9.5 Acessibilidade e idioma

| ID | Requisito |
| --- | --- |
| NFR-050 | Overlay e wizard navegáveis por teclado; contraste AA no tema escuro e claro; tamanho de fonte segue o sistema |
| NFR-051 | pt-BR padrão; en-US completo; estrutura pronta para es-419 |
| NFR-052 | HERO funciona 100 % em modo texto para quem não usa voz |

---

## 10. Hardware

### 10.1 Suportado (1.0)

| Componente | Mínimo | Recomendado |
| --- | --- | --- |
| CPU | x86-64-v3 (Zen 2 / Intel 10ª gen) | Zen 4 / Intel 13ª gen |
| GPU | NVIDIA RTX 20xx (Turing) ou AMD RDNA2, 8 GB VRAM | RTX 40xx/50xx ou RDNA3+, 12 GB+ |
| RAM | 16 GB | 32 GB |
| Disco | NVMe 128 GB livres | NVMe 512 GB |
| Firmware | UEFI, Secure Boot opcional | — |
| Notebook | iGPU + NVIDIA híbrida (PRIME offload) | — |

Fora: GTX 10xx e anteriores (sem driver aberto), BIOS legado, 32 bits, ARM (2.0).

### 10.2 Hardwares de referência (ADR-024)

| Papel | Máquina | O que valida |
| --- | --- | --- |
| Desktop | Ryzen 7 9800X3D, RTX 5060 8 GB, NVMe, Windows 11 em dual boot | Metas NFR, jogos, Ollama 8B, Secure Boot, dual boot |
| Notebook | Notebook com iGPU + NVIDIA RTX (modelo a registrar em `docs/hardware.md` quando adquirido/definido), Windows em dual boot | Gráficos híbridos, Wi-Fi/BT, suspensão, bateria, touchpad, tela externa, instalação por pendrive |

---

## 11. Caminho de validação física (ISO → pendrive → notebook)

Este fluxo roda em todo release `stable` e é o DoD final do G5.

| Passo | Ação | Verificação |
| --- | --- | --- |
| 1 | `forja-image` release gera `forjaos-nvidia-open-vX.Y.iso` + `SHA256SUMS` + assinatura | Checksum confere após download |
| 2 | Gravar no pendrive (≥ 8 GB) com Fedora Media Writer **e** com Ventoy (dois pendrives) | Ambos bootam no notebook e no desktop |
| 3 | Boot do pendrive no notebook com Secure Boot ligado | Tela do Anaconda com tema ForjaOS |
| 4 | Instalar ao lado do Windows (redimensionar NTFS, criar partições, GRUB com Windows) | Reboot: GRUB lista ForjaOS e Windows; Windows boota |
| 5 | 1º boot: enroll MOK, Plymouth, SDDM, wizard (perfil gamedev + mascote Guará + GitHub) | Wizard completa; `forja doctor` sem erro crítico |
| 6 | Checklist de hardware (FR-016): Wi-Fi, BT, touchpad, teclas de função, brilho, suspensão/retorno, bateria, webcam, áudio, microfone, HDMI | `docs/hardware-checklist.md` preenchido |
| 7 | Gráficos híbridos: Plasma na iGPU; `prime-run glxinfo` mostra NVIDIA; jogo via Steam com `prime-run`; monitor externo | FR-015 |
| 8 | HERO: wake word "Ei, Guará" → "qual a temperatura da GPU?" → resposta por voz; "sobe o compose do projeto X" → confirmação → execução | 10 tarefas do G3 |
| 9 | Memória: após 1 h de uso, "o que eu fiz na última hora?" responde com shell, git e HERO | FR-136 |
| 10 | Modo jogo: abrir Steam, rodar jogo de referência, MangoHud | NFR-008 |
| 11 | `forja update` para o `:testing` seguinte e `forja rollback` | NFR-013 |
| 12 | Repetir 3–11 no desktop de referência | — |
| 13 | Registrar resultados em `docs/releases/vX.Y-validation.md` com fotos/capturas | Arquivo no repo |

Falhas encontradas aqui viram issues com prioridade máxima para o próximo `:testing`; não bloqueiam outras frentes.

---

## 12. Roadmap

Fases indicam prioridade de tempo. Não há dependência que impeça iniciar uma fase enquanto outra está aberta; o que há é ordem de valor.

| Fase | Semanas | Entregáveis | DoD objetivo |
| --- | --- | --- | --- |
| **0 — Fundação** | 1–2 | Org GitHub, 7 repos com LICENSE/ADR/CI; ADR-001 a 024 commitados; paleta, logo v1, mascote estático v1; Containerfile mínimo sobre `bazzite-nvidia-open` (ADR-0032); `check-branding.sh`; `THIRD_PARTY_LICENSES` no CI | Imagem builda no Actions, assinada, no GHCR; `bootc switch` para ela funciona em VM |
| **1 — Imagem instalável** | 3–8 | FR-001 a FR-016 (exceto notebook, se não disponível), FR-050 a FR-058, ISO, guia de instalação, recipes `ujust` básicas, `forja doctor` e `forja install unity/claude-code` | Pendrive → instalação em dual boot no desktop de referência → `docker compose up` + Steam em < 15 min; NFR-001, 002, 011, 012 passando |
| **2 — Experiência dev/gamedev** | 9–12 | FR-020 a FR-044, FR-060 a FR-063; perfis; chaves no KWallet; registro MCP; Trivy no CI | 5 usuários externos instalam e completam o wizard sem issue bloqueante; CVE scan limpo em pacotes próprios |
| **3 — HERO v0 nativo (texto + sistema)** | 13–22 | FR-070, 071, 085, 090–096, 100–103, 110–112, 120–122, 124–125 em modo texto; spike Hermes (FR-097 → ADR-025); os 4 MCP servers | 10 tarefas do G3 por texto; `herod` ocioso ≤ 120 MB; HERO desligado deixa zero processo |
| **4 — Voz + Memória** | 23–32 | FR-072 a FR-084 (wake word embarcada, treino de nome personalizado, STT, TTS, visemes), FR-123, FR-043 modo jogo, FR-130 a FR-137 | NFR-003 a 009 passando; 10 tarefas do G3 por voz; "o que eu fiz ontem?" com fontes |
| **5 — Release 1.0** | 33–36 | Validação física completa (seção 11) nos 2 hardwares; Escudo opt-in; site + docs pt-BR/en; canais `stable`/`testing`; `TRADEMARK.md`; release v1.0.0 | 50 instalações externas em 30 dias sem bug bloqueante aberto |

Estimativa com uma pessoa a 15–20 h/semana. Fases 3 e 4 são o caminho crítico; identidade visual (FR-05x) e Memória podem avançar em paralelo em qualquer semana.

---

## 13. Backlog 2.0 (fora do 1.0, registrado para não perder)

- Spin `forjaos-tiling` com niri e Plasma como fallback
- COSMIC como desktop alternativo (reavaliar quando applets de rede/BT/energia estiverem completos)
- Visão: câmera/Frigate, detecção de presença para saudação
- OCR de tela como coletor de memória (opt-in)
- Integrações Gmail, Agenda, Spotify no HERO
- Loja de skills/rotinas do HERO (compartilhar `routes.toml` e rotinas)
- Suporte ARM (Snapdragon X, Apple Silicon via Asahi quando viável)
- Sincronização de vault entre máquinas (Syncthing integrado)
- `forja cloud`: provisionar VM na nuvem com a mesma imagem para dev remoto
- Perfis de energia por app, undervolt assistido para notebooks
- Multiusuário com personas separadas do HERO

---

## 14. Governança técnica

### 14.1 ADRs

- Local: `docs/adr/NNNN-titulo.md` em cada repo; os de produto (001–024) vivem em `forjaos-image` e são espelhados em `hero` e `hero-memory` quando aplicáveis.
- Formato: Contexto · Decisão · Alternativas · Consequências · Status (`aceito` | `revogado por ADR-NNNN`).
- Mudar uma decisão = novo ADR que cita e revoga o anterior. O anterior não é editado.

### 14.2 Issues e PRs

- Toda issue referencia `FR-xxx`/`NFR-xxx`/`ADR-xxx`.
- Labels: `area/image`, `area/hero`, `area/memory`, `area/cli`, `area/brand`, `area/site`, `fase/0..5`, `hardware/notebook`, `hardware/desktop`.
- PR mergeia com CI verde. Sem revisor obrigatório enquanto o time for uma pessoa; quando houver colaboradores, CODEOWNERS por área.

### 14.3 Releases

- `:testing` diário automático; `:stable` semanal automático se NFR passam; `vX.Y.Z` manual com ISO e validação física (seção 11).
- Changelog gerado de commits convencionais (`feat:`, `fix:`, `adr:`).

---

## 15. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
| --- | --- | --- | --- |
| Universal Blue muda base (ex.: troca de Bazzite para outra imagem) | Média | Alto | `FROM` fixado por tag; teste diário detecta; camada própria é fina |
| NVIDIA híbrida no notebook não funciona out-of-the-box | Alta | Alto | Herdar configuração do Bazzite para laptops; testar cedo (Fase 1) assim que o notebook estiver disponível; documentar modelos validados |
| Wake word com falso positivo em pt-BR | Média | Médio | Dataset com ruído/TV/conversa; sensibilidade ajustável; 20 locutores reais na validação |
| Qwen3 8B não cabe com jogo em 8 GB | Certa | Médio | Troca automática para 4B; modo jogo descarrega |
| Tempo: solo em meio período | Alta | Alto | Fases serializadas; identidade e Memória como "trabalho de folga"; cortar Escudo e KRunner se Fase 4 atrasar |
| Licença de voz Piper pt-BR | Baixa | Médio | Verificar voz a voz antes de embarcar; manter só MIT/Apache/CC-BY |
| Colisão de nome ForjaOS | Baixa | Médio | Consulta INPI e domínios na Fase 0; `TRADEMARK.md` |
| Anaconda com dual boot confunde usuário | Média | Médio | Guia ilustrado; vídeo; FR-013 automatiza pós-instalação |
| Secure Boot + MOK falha em firmware específico | Média | Médio | Documentar desligar Secure Boot como fallback; lista de firmwares testados |
| Hermes Agent evolui mais rápido que o loop próprio | Média | Baixo | Spike na Fase 3 decide; interface de rota permite trocar motor sem tocar no resto |

---

## 16. Glossário

| Termo | Significado |
| --- | --- |
| bootc / image-based | SO distribuído como imagem OCI; `/usr` imutável; atualização atômica com rollback |
| Universal Blue (ublue) | Projeto que publica imagens bootc sobre Fedora Atomic (Bazzite, Bluefin, Aurora) |
| Bazzite-DX | Variante do Bazzite com ferramentas de desenvolvimento |
| HERO | Motor do assistente ForjaOS (`herod`) |
| Guará | Mascote padrão; nome da persona escolhido pelo usuário |
| Wake word | Palavra de ativação ("Ei, Guará") detectada localmente |
| Rota | Categoria de intenção que define provedor e tier |
| Tier | Nível de permissão de uma tool: livre, alterar, bloqueado |
| Policy Engine | Componente que aplica tiers e gera `AuditEvent` |
| MCP | Model Context Protocol; interface padrão de tools para LLMs |
| Vault | Pasta Markdown da Memória do sistema |
| ujust | Receitas `just` do Universal Blue para tarefas de sistema |
| PRIME offload | Modo em que o desktop roda na iGPU e apps escolhidos na NVIDIA |
| MOK | Machine Owner Key; chave que o usuário registra para Secure Boot aceitar módulos assinados |

---

## 17. Referências

- Universal Blue image-template — https://github.com/ublue-os/image-template
- Bazzite — https://bazzite.gg · Bluefin — https://projectbluefin.io
- bootc — https://bootc-dev.github.io/bootc/ · bootc-image-builder — https://github.com/osbuild/bootc-image-builder
- NVIDIA open GPU kernel modules — https://github.com/NVIDIA/open-gpu-kernel-modules
- KDE Plasma 6 / Kirigami / Plasma widgets — https://develop.kde.org
- PipeWire — https://pipewire.org · pipewire-rs — https://gitlab.freedesktop.org/pipewire/pipewire-rs
- openWakeWord — https://github.com/dscripka/openWakeWord
- faster-whisper — https://github.com/SYSTRAN/faster-whisper · Piper — https://github.com/rhasspy/piper
- Ollama — https://ollama.com · Qwen3 — https://github.com/QwenLM/Qwen3
- Hermes Agent — https://github.com/nousresearch/hermes-agent
- Codex CLI — https://github.com/openai/codex · Claude Code — https://docs.claude.com/en/docs/claude-code
- MCP — https://modelcontextprotocol.io · rmcp — https://github.com/modelcontextprotocol/rust-sdk
- graphify — https://github.com/Graphify-Labs/graphify
- atuin — https://atuin.sh · sqlite-vec — https://github.com/asg017/sqlite-vec
- Fedora trademark guidelines — https://fedoraproject.org/wiki/Legal:Trademark_guidelines
- Documento de análise e plano (artefato Claude Docs) — "ForjaOS (DeveloperOS) — Análise crítica e plano de construção", 2026-11-08
