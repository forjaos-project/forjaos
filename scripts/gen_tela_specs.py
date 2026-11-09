#!/usr/bin/env python3
"""gen_tela_specs.py — gera docs/design-system/telas/<slug>.md a partir dos protótipos em docs/telas.

Uso: python3 scripts/gen_tela_specs.py [--check]
  sem flag : (re)escreve as specs, preservando a seção "## Pendências e divergências conhecidas"
             e o campo "Status" já existentes em cada arquivo.
  --check  : só compara o hash SHA-256 do code.html com o registrado na spec; exit 1 se divergir.

A tabela TELAS abaixo é a fonte das specs. Edite aqui, não nos .md gerados (exceto Status e Pendências).
Só stdlib.
"""
import hashlib, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TELAS_DIR = ROOT / "docs" / "telas"
OUT = ROOT / "docs" / "design-system" / "telas"

# Substituições do ADR-028 (string no protótipo -> implementação, fonte)
SUBST = {
    "Jarvis": ("Guará (persona) / HERO (motor)", "ADR-005, ADR-006"),
    "devos": ("forja (CLI), forja-term (terminal)", "ADR-020, FR-035, FR-060"),
    "rodrigo@": ("usuario@forjaos ($USER@forjaos)", "FR-003"),
    "nftables": ("firewalld", "ADR-022"),
    "24.04": ("versão AAAA.MM.DD (imagem) / vX.Y.Z (release)", "NFR-044"),
    "arm64": ("remover — só x86-64-v3", "§10.1"),
    "6.12": ("kernel Bazzite (sem número fixo)", "ADR-001"),
    "RTX 4070": ("RTX 5060 8 GB (desktop de referência)", "§10.2"),
    "GameMode": ("Modo Jogo (hero-game.target)", "FR-043"),
    "Escudo ativo": ("indicador só se `forja install escudo` executado", "ADR-023, NFR-027"),
    "DeveloperOS": ("ForjaOS (sem descritor)", "ADR-031"),
    "Feral": ("remover — Modo Jogo é hero-game.target, não Feral GameMode", "FR-043"),
    "Fedora Atomic 41": ("base Universal Blue (sem versão Fedora exposta)", "FR-002, G4"),
    "NVIDIA Open 590": ("driver NVIDIA open (versão vem da base)", "ADR-001"),
    "TPM2": ("KWallet (TPM2 não é requisito do PRD; só se ADR futuro aprovar)", "FR-023, NFR-024"),
    "Polkit": ("Policy Engine (tiers livre/alterar/bloqueado)", "FR-100"),
    "Tier 1": ("tier `livre` / `alterar` / `bloqueado` (nomes do PRD)", "FR-100"),
    "WebGL": ("QML puro; QtWebEngine só se QML não atingir 10k nós a 60 fps", "ADR-019"),
    "Alacritty": ("Konsole (terminal padrão)", "FR-035"),
    "Fish Shell": ("zsh padrão (fish disponível)", "FR-035"),
    "KWin-scx": ("KWin (Wayland)", "ADR-003"),
    "Forja Package Store": ("`forja install` (não há loja própria no 1.0)", "§2.2"),
    "forja-train": ("`forja mascot train`", "FR-082"),
    "forja fix": ("remover — subcomando não existe", "FR-060"),
    "forja doctor --strict": ("`forja doctor` (sem flag --strict no PRD)", "FR-036"),
    "ghcr.io/forjaos/forjaos-nvidia:24.04": ("ghcr.io/<org>/forjaos-nvidia-open:stable", "FR-001"),
    "ghcr.io/forjaos/nvidia:stable": ("ghcr.io/<org>/forjaos-nvidia-open:stable", "FR-001"),
    "Kernel 6.9-cachyos-scx": ("kernel Bazzite", "ADR-001"),
    "RTX 4080": ("RTX 5060 8 GB", "§10.2"),
    "Qwen 8B": ("Qwen3 8B Q4 (Ollama)", "ADR-013"),
    "claude-sonnet": ("Claude Code (API)", "FR-005"),
    "Hermes Engine": ("Hermes Agent", "FR-005"),
    "local-copilot": ("remover — não existe no PRD", "FR-005"),
    "4.8k": ("contagem real do GitHub ou omitir", "NFR-033"),
    "3.4k": ("contagem real do GitHub ou omitir", "NFR-033"),
    "universal-blue 24.04": ("tag da imagem corrente", "NFR-044"),
    "NVIDIA Driver 555": ("driver vem da base; sem número fixo", "ADR-001"),
    "GPG": ("assinatura de commit opcional; não prometida pelo PRD", "FR-031"),
    "Atuin Cloud Sync": ("atuin local (sync é opt-in do usuário)", "FR-132, NFR-033"),
}

# Ícones Material Symbols -> Breeze (nome do ícone) ou "próprio" (SVG em brand/icons/)
ICONS = {
    "search": "search", "settings": "configure", "folder": "folder", "folder_open": "folder-open",
    "terminal": "utilities-terminal", "code": "text-x-script", "code_blocks": "code-context",
    "memory": "cpu", "speed": "speedometer", "wifi": "network-wireless", "bluetooth": "network-bluetooth",
    "vpn_key": "network-vpn", "key": "dialog-password", "lock": "object-locked", "shield": "security-high",
    "security": "security-high", "verified_user": "security-high", "verified": "checkmark",
    "check": "checkmark", "check_circle": "dialog-ok-apply", "warning": "dialog-warning",
    "mic": "audio-input-microphone", "volume_up": "audio-volume-high", "graphic_eq": "próprio: waveform",
    "smart_toy": "próprio: mascote (estado)", "psychology": "próprio: hero-thinking", "neurology": "próprio: hero-ai",
    "sports_esports": "input-gaming", "play_arrow": "media-playback-start", "play_circle": "media-playback-start",
    "pause": "media-playback-pause", "sync": "view-refresh", "sync_alt": "view-refresh", "download": "download",
    "content_copy": "edit-copy", "open_in_new": "window-new", "close": "window-close", "minimize": "window-minimize",
    "crop_square": "window-maximize", "fullscreen": "view-fullscreen", "splitscreen": "view-split-left-right",
    "split_scene": "view-split-left-right", "view_column": "view-list-details", "grid_view": "view-list-icons",
    "format_list_bulleted": "view-list-text", "view_quilt": "view-grid", "view_stream": "view-list-tree",
    "description": "text-x-generic", "article": "text-x-generic", "sticky_note_2": "note", "note_add": "document-new",
    "edit_note": "document-edit", "today": "view-calendar-day", "calendar_month": "view-calendar", "calendar_today": "view-calendar",
    "event": "view-calendar", "schedule": "chronometer", "hourglass_top": "chronometer", "timer": "chronometer",
    "history": "view-history", "commit": "vcs-commit", "fork_right": "vcs-branch", "hub": "próprio: graph",
    "scatter_plot": "próprio: graph-nodes", "category": "view-categories", "layers": "layer-visible-on",
    "database": "server-database", "dns": "network-server", "hard_drive": "drive-harddisk", "usb": "drive-removable-media",
    "cloud_done": "cloud-upload", "desktop_windows": "computer", "deployed_code": "package-x-generic",
    "build_circle": "run-build", "tune": "configure", "more_vert": "overflow-menu", "notifications": "notifications",
    "public": "internet-web-browser", "person": "user-identity", "home": "go-home", "arrow_back": "go-previous",
    "arrow_forward": "go-next", "arrow_upward": "go-up", "arrow_downward": "go-down", "chevron_left": "go-previous",
    "chevron_right": "go-next", "expand_more": "go-down", "add": "list-add", "add_circle": "list-add",
    "delete": "edit-delete", "do_not_disturb_on": "notifications-disabled", "power_settings_new": "system-shutdown",
    "battery_charging_full": "battery-full-charging", "auto_awesome": "próprio: hero-spark", "bolt": "próprio: hero-spark",
    "insights": "office-chart-line", "manage_search": "edit-find", "find_in_page": "edit-find", "search_insights": "edit-find",
    "filter_alt": "view-filter", "filter_center_focus": "zoom-fit-best", "fit_screen": "zoom-fit-best", "zoom_in": "zoom-in",
    "zoom_out": "zoom-out", "explore": "find-location", "travel_explore": "find-location", "map": "map-globe",
    "share": "document-share", "push_pin": "pin", "forum": "view-conversation-balloon", "record_voice_over": "audio-input-microphone",
    "text_fields": "format-text-bold", "drag_handle": "transform-move", "reorder": "view-sort", "view_in_ar": "próprio: 3d",
    "bubble_chart": "próprio: graph-nodes", "inventory_2": "package-x-generic", "folder_special": "folder-favorites",
    "space_dashboard": "view-grid", "star": "rating", "lock_reset": "view-refresh", "restart_alt": "system-reboot",
    "rocket_launch": "próprio: launch", "receipt_long": "view-list-text", "pets": "próprio: mascote", "menu_book": "help-contents",
    "light_mode": "weather-clear", "person_outline": "user-identity", "sync_problem": "dialog-warning",
}

DARK_TOPBAR = [
    ("Barra superior", "altura 40 px (`dimensions.topbar_height`); fundo `glass-topbar` blur 14 px; borda inferior `rgba(0,229,255,0.12)`; esquerda: logo 20 px + dots de workspace + `Projeto: <repo> · branch <nome>`; centro: data/hora `code-md`; direita: chip HERO (estado), GPU + temperatura, Wi-Fi, BT, [Escudo], bateria", "FR-052"),
]
DARK_DOCK = [
    ("Dock", "centralizado, 12 px da borda inferior, altura 64 px, raio 12 px, `glass-dock` blur 24 px, borda `border-ghost-strong`; ícones 48 px raio 8, gap 8 px; ordem: Terminal, Code, Git, Docker, Unity*, Godot, HERO, Monitor, Navegador, Apps; ponto ativo 3 px ciano sob o ícone (`*Unity` só após instalação)", "FR-052"),
]
OVERLAY = [
    ("Overlay Central de Comando", "coluna direita **520 px** (`dimensions.overlay_width`), 16 px da borda direita, altura = tela − 32 px; fundo `layer-2` 0,70 + blur 24 px; borda `border-active`; raio 16 px; cabeçalho `headline-sm` 'Central de Comando' + chip `Super + Espaço`", "FR-121"),
    ("Card do assistente", "topo do overlay; mascote 40 px à esquerda; linha 1 `label-sm` ciano '<Mascote> · ouvindo palavra de ativação (100 % local)'; linha 2 `body-md` com a frase ouvida entre aspas; linha 3 ações executadas `code-sm` com ✓ e tier + duração ('2,1 s'); waveform 8 barras 4–26 px abaixo", "FR-103, FR-121"),
    ("Tiles 2×3", "grid 2 colunas, gap 8 px, cada tile `layer-1` raio 8, padding 12 px, altura 56 px: título `body-md` 600 + subtítulo `code-sm` muted + status dot 6 px à direita (ciano ligado, violeta BT, verde firewall, cinza desligado). Ordem: Wi-Fi, Bluetooth, VPN, Modo Jogo, Firewall, Não perturbe", "FR-121"),
    ("Desempenho", "card com 4 medidores (CPU, RAM, GPU, VRAM) em grid 4 col; valor `headline-sm` tabular; barra 4 px abaixo, cor por métrica (ciano/azul/violeta/laranja); label 'ao vivo' com dot pulsante; amostra 2 s; pausa ao fechar", "FR-121"),
    ("Containers + IA", "2 cards lado a lado: lista nome `code-md` + chip estado 22 px (verde 'rodando', âmbar 'reiniciando'); IA lista Ollama/Hermes/Claude Code/Codex com chip `local` (ciano) ou `API` (cinza)", "FR-121, FR-092"),
    ("Segurança e logs", "card: 3 linhas `code-sm` (CrowdSec, Suricata, journald) com tempo à direita; **CrowdSec/Suricata só aparecem com Escudo instalado**; sem Escudo o card mostra firewalld + auditd + journald", "FR-095, ADR-023"),
    ("Rede", "card: interface/banda, download/upload, latência, dispositivos na LAN; valores `code-md` ciano à direita", "FR-121"),
]
TERMINAL_WINDOW = [
    ("Janela Konsole", "raio 12 px, borda `border-ghost`, fundo `konsole-bg` (#080b11) sem blur; barra de título 40 px com 3 dots (vermelho/amarelo/verde 12 px) + abas (`forja-term · zsh` ativa com borda ciano 1 px, `claude`, `codex`, `ollama`) `code-md`", "FR-035"),
    ("Saída `forja doctor`", "prompt `usuario@forjaos ~/proj/<repo> (main) $`; linhas de check em 2 colunas (≥ 1100 px) com ✓ verde (`success`) / ! âmbar (`warning`); link sublinhado ciano para ação sugerida", "FR-036"),
    ("Saída `forja ai`", "linha '↳ roteando: local (ollama) · contexto: …' `code-sm` muted; caixa de resposta `layer-1` raio 8 padding 12 px; termos de código em chip `code-sm` com fundo `layer-3`; pergunta final com `[s/N]` em âmbar", "FR-061"),
]

TELAS = [
    dict(slug="forjaos_splash_plymouth", pendencias=["Protótipo mostra 3 linhas de status (kernel, SELinux, PipeWire); FR-056 pede splash sem texto. Decisão: sem texto; linhas só com Esc (modo verboso)."], nome="Splash Plymouth", fr="FR-056, FR-002", tema="dark",
         alvo="Tema Plymouth (script + PNG/SVG do logo); sem texto além do opcional de erro", pasta="brand/plymouth",
         regioes=[
             ("Fundo", "`canvas` (#070a11) sólido; glow radial ciano/violeta 20 % no centro (gradiente, sem imagem pesada)", "FR-056"),
             ("Logo", "logo ForjaOS centralizado, 144–176 px (w-36/w-44); wordmark 'FORJA' + 'OS' em `display-sm`; descritor 'The DevOS' `label-sm` só em marketing — **não** no Plymouth do produto (ADR-004)", "FR-053, FR-056"),
             ("Barra de progresso", "largura 256 px (w-64), altura 4–6 px (h-1/h-1.5), raio full, trilho `layer-3`, preenchimento gradiente ciano→violeta", "FR-056"),
             ("Rodapé", "texto 'Pressione Esc para logs' `label-xs` muted a 32 px da base — opcional; o PRD pede 'sem texto', então fica **desligado por padrão**", "FR-056"),
         ],
         icones=[], extra_subst={"Iniciando módulos do kernel & daemon herod": ("remover — Plymouth sem texto (FR-056)", "FR-056"), "SELinux: enforcing": ("remover do splash", "FR-056"), "PipeWire Core OK": ("remover do splash", "FR-056")},
         checklist=["Exibição extra ≤ 3 s medida com `systemd-analyze` (FR-056)", "Nenhum texto de status visível por padrão", "Logo renderiza a 1080p e 4K sem serrilhado (SVG → PNG em 2 tamanhos)", "Cores: só `canvas`, `accent-cyan`, `accent-violet`, `layer-3`", "Fonte do wordmark (se rasterizada) = Plus Jakarta Sans"]),
    dict(slug="forjaos_bootloader_grub", pendencias=["Efeito scanlines/CRT do protótipo não será implementado (sem valor funcional, custo de legibilidade).", "GRUB não renderiza blur/translucidez: fundo sólido `void` com wallpaper opcional a 20 %."], nome="Bootloader GRUB", fr="FR-002, FR-008, FR-011", tema="dark",
         alvo="GRUB theme (`theme.txt`, fontes PF2 geradas de Plus Jakarta Sans/JetBrains Mono, PNGs de borda)", pasta="brand/grub",
         regioes=[
             ("Fundo", "o quase-preto do protótipo vira `void` (#0a0d14), com wallpaper desfocado a 20 % opcional; scanlines **não** (efeito de protótipo, custo zero de valor)", "FR-002"),
             ("Cabeçalho", "faixa 72 px: logo 32 px + 'FORJA OS' `headline-sm`; direita: 'UEFI x86-64 · Secure Boot' `label-xs` muted", "FR-012"),
             ("Lista de entradas", "cards 100 % largura, padding 20 px, raio 12 px, gap 12 px; entrada ativa com borda esquerda 3 px ciano e gradiente ciano→violeta 12 %; título `headline-sm`, subtítulo `code-sm` muted (commit bootc, kernel); tecla de atalho em chip `label-xs` à direita", "FR-008"),
             ("Entradas", "1) ForjaOS <versão> (stable · padrão) 2) ForjaOS rollback anterior (commit) 3) Windows Boot Manager (dual boot) 4) Modo de resgate", "FR-008, FR-011"),
             ("Contador", "'Boot automático em: Ns' `code-md` ciano, canto superior direito do painel", "FR-008"),
             ("Rodapé", "legenda de teclas ↑/↓ Enter e Esc `label-xs`; sem URL de site no GRUB", "FR-002"),
         ],
         icones=[], extra_subst={"Fedora Atomic 41": SUBST["Fedora Atomic 41"], "Linux 6.12.8-bazzite": ("kernel Bazzite (número vem do boot)", "ADR-001"), "NVIDIA Open 590": SUBST["NVIDIA Open 590"], "forja.dev": ("remover até domínio registrado (risco §15)", "§15"), "MemTest86+": ("só se o pacote estiver na imagem", "FR-005")},
         checklist=["Nenhuma string 'Fedora'/'Bazzite' visível (check-branding.sh)", "Windows listado quando detectado (FR-011)", "Entrada de rollback aponta para deployment anterior do bootc", "Fontes PF2 geradas do palette (ui + mono)", "Cores só do palette (GRUB aceita só opaco → tokens `*-flat`)"]),
    dict(slug="forjaos_sddm_login", pendencias=["Chips FIDO2/Biometria aparecem no protótipo sem o PRD prever autenticação alternativa; exibir só se PAM configurado pelo usuário.", "Protótipo usa Fira Code (ADR-027 proíbe)."], nome="SDDM Login", fr="FR-057, FR-002", tema="dark",
         alvo="Tema SDDM em QML (Qt6) com wallpaper escuro, campo único, avatar, logo discreto", pasta="brand/sddm",
         regioes=[
             ("Fundo", "wallpaper oficial escuro (FR-055) com overlay `canvas` 60 % + blur 24 px", "FR-057"),
             ("Barra superior", "40 px: logo 24 px + 'FORJA OS' `label-md`; direita: 'KDE Plasma 6 · Wayland', relógio `code-md`, Wi-Fi, bateria `label-xs`", "FR-057"),
             ("Relógio", "centro-superior: hora `display-lg` 700 tabular + data por extenso `body-md` muted", "FR-057"),
             ("Card de login", "centralizado, largura 448 px (max-w-md), raio 24 px (rounded-3xl → usar 16 px `radius.xl` do palette), `layer-2` 0,85 + blur; avatar 96 px círculo com anel ciano 2 px; nome `headline-md`; `usuario@forjaos` `code-sm` muted; campo de senha único 48 px raio 8 fundo `layer-3` borda `border-ghost` → foco `border-active`; botão olho à direita", "FR-057"),
             ("Alternativas", "linha de chips 22 px: 'FIDO2', 'Biometria', 'Outro usuário' `label-sm` — exibir só os métodos realmente configurados no PAM", "FR-057"),
             ("Rodapé do card", "'Layout: ABNT2 (pt-BR)' e 'Sessão: Wayland' `label-xs`; combobox de sessão", "FR-057"),
             ("Ações de energia", "3 botões fantasma 40 px (Suspender, Reiniciar, Desligar) `label-sm` no rodapé da tela", "FR-057"),
         ],
         icones=[], extra_subst={"Modo Desenvolvedor": ("remover — não existe esse modo no PRD", "FR-057"), "NVIDIA PRIME Offload Ativo": ("remover do login (informação técnica demais)", "FR-057"), "Full-Stack / Gamedev": ("remover — subtítulo de perfil não existe no SDDM", "FR-057")},
         checklist=["Campo único de senha, foco inicial no campo (FR-057)", "Avatar do usuário vem do AccountsService", "Raio do card = `radius.xl` (16 px), não 24 px", "Sem Fira Code; relógio em Plus Jakarta Sans tabular", "Tema aplicado por padrão em `/etc/sddm.conf.d/`"]),
    dict(slug="forjaos_desktop_principal_dock", pendencias=["O protótipo mostra o overlay sempre aberto ocupando a coluna direita; no produto ele é um overlay sob demanda (FR-121). A composição da tela é referência de convivência janela + overlay, não um layout fixo.", "Terminal padrão `forja-term` como perfil de Konsole (nome do perfil, não binário novo)."], nome="Desktop principal (escuro) com dock e overlay", fr="FR-050, FR-052, FR-055, FR-058", tema="dark",
         alvo="Plasma 6: look-and-feel 'Forja', layout de painel (`layout.js`), dock (Plasma panel flutuante ou Latte-like próprio em QML), wallpaper, Konsole; overlay vem da tela `central_de_comando_hero_corrigida`", pasta="brand/plasma + image/system_files",
         regioes=DARK_TOPBAR + [("Área de trabalho", "wallpaper oficial escuro (ondas ciano/violeta sobre grafite); janelas com raio 12 px, sombra L2", "FR-055")] + TERMINAL_WINDOW[:1] + [("Overlay à direita", "ver spec `forjaos_central_de_comando_hero_corrigida` (canônica). Esta tela mostra o overlay sempre visível só para composição; no produto ele abre por Super+Espaço", "FR-121")] + DARK_DOCK,
         icones=[], extra_subst={"Kernel 6.x · sched_ext ativo (scx_lavd)": ("texto real do `forja doctor` (kernel/scheduler detectados)", "FR-036")},
         checklist=["Barra superior 40 px com os itens do FR-052 na ordem", "Dock 64 px / 12 px da borda / ícones 48 px / ponto ativo 3 px", "Atalhos Super+Espaço, Super+T, Super+E, Super+G, Super+M aplicados (FR-058)", "Wallpaper em /usr/share/wallpapers/ForjaOS/", "Zero ícone/wallpaper Fedora/Bazzite (check-branding.sh)"]),
    dict(slug="forjaos_desktop_principal_modo_claro_alabaster_forge", nome="Desktop principal (claro — Alabaster Forge)", fr="FR-050, FR-052", tema="light",
         alvo="Variante clara do look-and-feel Plasma 'Forja' + Konsole claro + overlay/plasmoid em tema claro", pasta="brand/plasma",
         regioes=[
             ("Barra superior", "44 px (h-11) → **padronizar em 40 px**; fundo `frosted` blur 12 px, hairline inferior `hairline`; esquerda: logo + 'Forja OS' `headline-sm` + badge de versão `label-sm` em `primary-fixed`; workspaces '1 · Dev / 2 · Web / 3 · GameEngine' chips 22 px; centro: busca 'Buscar apps, arquivos…' 320 px raio 8 `layer-2`; direita: chip 'Guará AI · Super+Espaço', layout PT-BR, relógio `code-md`", "FR-052"),
             ("Janela Konsole clara", "fundo `layer-1` (#ffffff), hairline `hairline`, sombra L3 quando focada; abas `code-md`; cabeçalho 'Forja Doctor' `headline-sm` + subtítulo `body-sm` muted; checks em cards 1 coluna com ícone 20 px à esquerda, título `body-md` 600, descrição `body-sm`, valor `code-sm` à direita", "FR-036"),
             ("Painel lateral direito", "320 px (w-80) `layer-1` hairline raio 12: card HERO (estado, modelo carregado, contexto dev), telemetria (CPU/RAM/GPU/NVMe) com barras 6 px `accent-cyan`/`accent-indigo`/`accent-orange`, card do projeto", "FR-121"),
             ("Dock inferior", "mesma geometria do escuro: 64 px, 12 px da borda, raio 12, `frosted` + sombra L2; tooltip `body-sm` acima", "FR-052"),
         ],
         icones=["add", "auto_awesome", "battery_charging_full", "build_circle", "check_circle", "code", "code_blocks", "delete", "deployed_code", "folder", "memory", "mic", "more_vert", "notifications", "public", "search", "settings", "smart_toy", "speed", "split_scene", "sports_esports", "terminal", "tune", "volume_up", "warning", "wifi"],
         extra_subst={"Forja Doctor v2.4": ("`forja doctor` (versão do CLI real)", "FR-036"), "CUDA 12.6": ("versão detectada em runtime", "FR-036"), "32 GB DDR5": ("valor detectado", "FR-036"), "Ter, 23 Abr": ("data real", "—"), "game-api (Rust+Bevy)": ("projeto real detectado", "FR-112")},
         checklist=["Alternância claro/escuro pelo atalho do sistema sem reinício (FR-050)", "Barra 40 px (não 44)", "Contraste AA de `text-muted` sobre `layer-1`", "Nenhuma cor fora do tema light do palette", "Sombra L3 só na janela focada"]),
    dict(slug="forjaos_central_de_comando_hero_overlay", pendencias=["Versão anterior do overlay. Não implementar isoladamente; a spec canônica é `forjaos_central_de_comando_hero_corrigida`."], nome="Central de Comando HERO — overlay (versão anterior)", fr="FR-121, FR-103", tema="dark",
         alvo="Referência secundária. Usar **só** para animação do waveform, chip 'Audio In (PipeWire)' e rótulos já corretos (Guará/forja). Layout canônico = `forjaos_central_de_comando_hero_corrigida`", pasta="hero/overlay",
         regioes=[("Waveform", "8 barras, largura 4 px, altura 6→26 px, período 1,2 s, atraso 0,15 s entre barras, cor `accent-cyan`", "FR-121"),
                  ("Chip de áudio", "'Audio In (PipeWire): <nó>' `label-xs` muted sob a frase ouvida", "ADR-015"),
                  ("Chip do modelo", "'Qwen3 8B · 100 % local' `label-sm` ciano no card do assistente", "ADR-013")],
         icones=[], extra_subst={"Zero Cloud Leaks": ("'100 % local'", "NFR-031"), "rodrigo@forja": ("usuario@forjaos", "FR-003"), "pty/3": ("remover", "—")},
         checklist=["Não implementar esta tela isoladamente — entregar via spec `corrigida`", "Waveform com os parâmetros acima (`motion.wave_bar_ms`)", "Nenhuma string 'Escudo ativo' sem Escudo"]),
    dict(slug="forjaos_central_de_comando_hero_corrigida", pendencias=["Card Segurança e logs mostra CrowdSec/Suricata como se fossem padrão; são opt-in (ADR-023). Sem Escudo: firewalld + auditd + journald.", "Tile `Firewall · nftables` → `Firewall · firewalld` (ADR-022).", "Card Rede lista dispositivos na LAN: exige varredura ativa — avaliar tier e consumo antes de implementar (princípio 5)."], nome="Central de Comando HERO — overlay 520 px (canônica)", fr="FR-121, FR-103, FR-093, FR-100", tema="dark",
         alvo="Overlay QML (Qt Quick + Kirigami) aberto por Super+Espaço, wake word ou clique no plasmoid; processo encerra ao fechar (só o plasmoid fica)", pasta="hero/overlay",
         regioes=DARK_TOPBAR + TERMINAL_WINDOW + OVERLAY + DARK_DOCK,
         icones=["crop_square", "mic", "terminal", "verified_user"],
         extra_subst={"KWin Plasma 6": ("remover rótulo decorativo", "—"), "GameMode on": ("Modo Jogo · hero-game.target", "FR-043"), "ATIVO": ("chip 'ativo' `label-xs` em `accent-cyan`", "FR-043")},
         checklist=["Largura exata 520 px; abre em ≤ 150 ms (NFR-010)", "Fecha com Esc/clique fora; lembra última aba", "Tier e resultado por ação ('✓ docker compose up · ✓ Godot aberto · 2,1 s') (FR-103)", "Desempenho amostra a cada 2 s e pausa ao fechar", "Consumo do overlay fechado = 0 processos além do plasmoid", "Card Segurança sem CrowdSec/Suricata quando Escudo ausente", "Tiles refletem estado real via D-Bus (NetworkManager, BlueZ, firewalld, hero-game.target, DnD)"]),
    dict(slug="forjaos_plasmoid_do_guar_kde_plasma_6", pendencias=["Protótipo menciona Polkit e Tier 1; o PRD usa Policy Engine com tiers livre/alterar/bloqueado (FR-100).", "Nomes de camadas SVG do protótipo (fur/eyes/spark/mouth) diferem do palette (body/ears/eyes/mouth/glow/badge); vale o palette.", "Protótipo usa Fira Code (ADR-027 proíbe)."], nome="Plasmoid do Guará (barra + popup)", fr="FR-120, FR-123, FR-054, FR-071, FR-076", tema="dark",
         alvo="Plasmoid QML (`org.forjaos.hero`) para o painel do Plasma 6 + popup; menu de contexto nativo", pasta="hero/plasmoid",
         regioes=[
             ("Ícone na barra", "mascote em miniatura 24 px + anel de estado 2 px na cor do estado (`mascot.state_colors`); label opcional 'ESCUTANDO' `label-xs`", "FR-120, FR-071"),
             ("Popup", "largura 384 px (w-96 ≈ 24 rem) → usar 384 px; raio 12; `layer-2` + blur; cabeçalho: mascote 56 px (h-14) + nome `headline-sm` + 'HERO ATIVO · herod (PID)' `label-xs`", "FR-120"),
             ("Transcrição", "card `layer-1` raio 8: 'Entrada de voz transcrita' `label-xs` + latência; frase `body-md` entre aspas; ação executada `code-sm` + chip de tier", "FR-103"),
             ("Comando rápido", "input 40 px `code-md` + botão 'Enviar' primário 36 px", "FR-085"),
             ("Toggles", "4 linhas 36 px: Mic ativo (Super+M), Wake word ('Ei, Guará'), Modo Jogo, Ver memória do dia (N eventos); switch 36×20 raio full", "FR-076, FR-043"),
             ("Menu de contexto", "itens nativos: Abrir Central de Comando (Super+Espaço), Mutar microfone, Abrir visualizador de memória, Ativar Modo Jogo (Super+G), Desligar HERO (kill switch)", "FR-120, FR-076"),
             ("Estados do mascote", "5 estados com cor de anel/glow: idle muted, listening ciano, thinking violeta (auréola orbital), speaking laranja (visemes + ondas laterais), error `danger` (glitch X)", "FR-054, FR-123"),
         ],
         icones=[], extra_subst={"Polkit": SUBST["Polkit"], "Tier 1 · OK": ("tier `livre` · ok", "FR-100"), "Piper Fabíola": ("voz Piper pt-BR com licença verificada (nome real da voz embarcada)", "ADR-011"), "RTX 4070 · 46°C": ("GPU detectada", "FR-036"), "fur eyes spark mouth": ("camadas `body ears eyes mouth glow badge` (palette › mascot.svg_layers)", "FR-054")},
         checklist=["60 fps na animação sem rasterização por frame (FR-123)", "Indicador permanente de microfone + AuditEvent ao mutar (FR-076)", "Estados seguem sinal D-Bus `StateChanged` (FR-071)", "Popup ≤ 384 px; fecha ao perder foco", "Lip-sync por `VisemeEvent[]` (FR-084)", "Sem Fira Code"]),
    dict(slug="forjaos_terminal_konsole_dev_forja_doctor", pendencias=["Sidebar de perfis/workspaces à esquerda não é funcionalidade do Konsole; fica fora do 1.0 ou vira plugin próprio por ADR.", "`Atuin Cloud Sync` e `TPM2` não estão no PRD; atuin é local (FR-132) e chaves ficam no KWallet (FR-023).", "`nftables strict/drop` → firewalld zona public (ADR-022)."], nome="Terminal Konsole dev + saída forja doctor / forja ai", fr="FR-035, FR-036, FR-061, FR-062", tema="dark",
         alvo="Konsole: `.colorscheme` + profile (fonte JetBrains Mono 13, zsh + starship); saída colorida do CLI `forja` (crate `cli/`)", pasta="brand/konsole + cli",
         regioes=[
             ("Sidebar de perfis (opcional)", "256 px (w-64) `layer-1`: perfis de sessão e workspaces — **não é padrão do Konsole**; fica como pendência (ver abaixo)", "FR-035"),
             ("Barra de abas", "48 px: abas `code-md` com ícone 16 px; ativa com fundo `layer-3` + borda inferior ciano 2 px", "FR-035"),
             ("Área do terminal", "fundo `konsole-bg`; fonte `code-md` 13/18 JetBrains Mono; prompt starship: `usuario@forjaos in ~/proj/<repo> on main` com cores ciano (user), violeta (path), laranja (branch)", "FR-035"),
             ("Saída `forja doctor`", "cada item: ✓ `success` / ! `warning` / ✗ `danger` + descrição; seção 'Daemons: herod (PID) · memd (PID)'; 'Portas abertas: 0' ; sugestão final com comando em chip", "FR-036, NFR-012"),
             ("Saída `forja ai`", "'↳ roteando: local (ollama/qwen3:8b) · contexto: …' + resposta em caixa + '[s/N]' com botões textuais 'Sim [s] / Não [n]'", "FR-061"),
             ("Painel auxiliar (split)", "split inferior 256 px com `podman logs -f` em `code-sm`; cabeçalho 'Painel auxiliar' `label-xs`", "FR-035"),
             ("Barra de status", "28 px: UTF-8, Ln/Col, RAM do Konsole, atalhos F4 split / Ctrl+Shift+F buscar / Super+Espaço HERO `label-xs`", "FR-035"),
             ("Overlay à direita", "igual à spec canônica do overlay (não duplicar aqui)", "FR-121"),
         ],
         icones=["add", "bluetooth", "check", "check_circle", "code", "commit", "do_not_disturb_on", "drag_handle", "expand_more", "folder", "fork_right", "fullscreen", "graphic_eq", "hub", "insights", "memory", "mic", "neurology", "person", "play_arrow", "psychology", "public", "schedule", "security", "shield", "smart_toy", "speed", "splitscreen", "sports_esports", "sync_alt", "terminal", "text_fields", "tune", "verified_user", "view_in_ar", "view_quilt", "view_stream", "vpn_key", "warning", "wifi"],
         extra_subst={"DevOS": ("ForjaOS", "ADR-004"), "claude-daemon": ("claude (aba)", "—"), "codex-engine": ("codex (aba)", "—"), "ollama-core": ("ollama (aba)", "—"), "forja-engine": ("remover", "—"), "feat/cyber-term": ("branch real", "—"), "Feral Activo": SUBST["Feral"], "nftables drop": ("firewalld · zona public", "ADR-022"), "Blindagem Ativa": ("só com Escudo", "ADR-023"), "TPM2 KWallet": ("KWallet", "FR-023"), "Atuin Cloud Sync": SUBST["Atuin Cloud Sync"], "Fish Shell / Alacritty": ("zsh / Konsole", "FR-035"), "Konsole v6.2.4": ("versão da base", "—")},
         checklist=["`.colorscheme` gerado do palette: Background=`konsole-bg`, Foreground=`on-surface`, Color0–7 mapeados (DESIGN-RULES §4)", "Profile: JetBrains Mono 13, zsh, starship, atuin, zoxide, fzf (FR-035)", "`forja doctor` sai com código ≠ 0 se item crítico falha (FR-036)", "`--json` em todos os subcomandos (FR-062)", "Confirmação `[s/N]` antes de tier alterar (FR-061)", "Sem Inter em texto de terminal"]),
    dict(slug="forjaos_file_explorer_especializado_dev_edition", pendencias=["**Sem FR no PRD.** Antes de qualquer implementação: ADR definindo escopo (places + service menus + colunas Git via Dolphin plugins, sem fork) e FR novo (sugestão: FR-037 em §6.4).", "Prévia do `docker-compose.yml` expõe `DATABASE_URL=postgres://root:secret@…` — toda prévia de env/segredo é mascarada (NFR-024).", "`Escudo Ativo` na barra só com Escudo instalado (ADR-023)."], nome="Dolphin Dev Edition (explorador de arquivos)", fr="SEM FR — abrir ADR/issue antes de implementar", tema="dark",
         alvo="Dolphin (KDE) com: places customizados (Repositórios dev, Vault, Containers), service menus (Abrir no Code, Subir Compose, Perguntar ao HERO), colunas de status Git, painel de informações estendido. **Não** é fork do Dolphin", pasta="— (a definir por ADR; provável `image/system_files` + `hero-mcp`)",
         regioes=[
             ("Barra superior", "igual DARK_TOPBAR; 'Guará · ESCUTANDO' no chip HERO", "FR-052"),
             ("Toolbar do Dolphin", "48 px: voltar/avançar/acima, breadcrumb `proj › game-api › src` em chips, busca ⌘F → Ctrl+F", "—"),
             ("Painel Places", "260 px (w-[260px]) `layer-1`: grupos `label-xs` uppercase: FAVORITOS, REPOSITÓRIOS DEV ATIVOS (ícone + nome + branch `code-sm` + chip de status), MEMÓRIA DO SISTEMA (vault), CONTÊINERES & VOLUMES, DISCOS & REDE", "FR-112, FR-131"),
             ("Lista", "linhas 28 px (`dimensions.tree_row`); colunas Nome / Status Git · Tipo / Tamanho / Modificado; filtro 'Todos · Modificados (2) · Não rastreados (1)' em chips; ícone de tipo 20 px", "—"),
             ("Inspetor", "320 px (w-80) à direita: nome + chip tipo; prévia de código `code-sm` com destaque; metadados (MIME, permissões); último commit (hash em chip, mensagem, autor); 3 ações: Executar com Podman, Editar no VS Code, Perguntar ao HERO", "FR-094"),
             ("Barra de status", "28 px: '8 arquivos, 3 diretórios · 1 selecionado · UTF-8 · YAML'", "—"),
         ],
         icones=["add", "arrow_back", "arrow_downward", "arrow_forward", "arrow_upward", "bubble_chart", "cloud_done", "code", "database", "deployed_code", "description", "desktop_windows", "dns", "download", "expand_more", "find_in_page", "folder", "folder_open", "format_list_bulleted", "grid_view", "hard_drive", "home", "hub", "key", "lock", "memory", "play_arrow", "play_circle", "search", "smart_toy", "sticky_note_2", "terminal", "today", "usb", "verified_user", "view_column"],
         extra_subst={"⌘F": ("Ctrl+F", "—"), "Escudo Ativo": SUBST["Escudo ativo"], "DevLab NAS NFS": ("montagens reais do usuário", "—"), "DATABASE_URL=postgres://root:secret@": ("nunca exibir segredo em prévia; mascarar valores de env", "NFR-024")},
         checklist=["**Bloqueado até ADR**: definir escopo (service menus + places + colunas) e FR novo", "Prévia de arquivos `.env*` sempre mascarada", "Linhas 28 px, places 260 px, inspetor 320 px", "Ações do inspetor passam pelo Policy Engine (tier alterar para 'Subir Compose')"]),
    dict(slug="forjaos_wizard_de_primeiro_boot", pendencias=["Lista de pacotes por perfil no protótipo difere do FR-022 (Vite/Next, Tailwind CLI, PyTorch, Vulkan SDK não constam); vale o FR-022.", "`TPM2` em KWallet não é requisito; remover menção.", "Vozes Piper nomeadas no protótipo (Fabíola) precisam de licença verificada voz a voz (ADR-011)."], nome="Wizard de primeiro boot — passos 1–5 (foco: passo 2 Mascote & Voz)", fr="FR-020, FR-021, FR-022, FR-023, FR-024", tema="dark",
         alvo="Wizard QML tela cheia (Kirigami), pulável, 6 passos; roda sem rede", pasta="image/firstboot",
         regioes=[
             ("Cabeçalho", "64 px: 'ForjaOS Setup' `headline-sm` + chip 'Primeiro boot' `label-xs`; direita: chips de status (Plasma 6 Wayland, Ollama online, KWallet ativo)", "FR-020"),
             ("Trilho de passos", "coluna esquerda 288 px (w-72): 6 itens 56 px, número em círculo 32 px, título `body-md` 600, subtítulo `code-sm` muted; ativo com borda esquerda 2 px ciano e fundo `layer-2`; concluído com ✓ verde", "FR-020"),
             ("Painel do passo (Mascote)", "título `headline-lg` + FR; grid de 8 cartões de nome 2×4 (Guará, Tupã, Jaci, Iara, Ipê, Boto, Curió, Arara) 140×96 px raio 12, selecionado com borda ciano + glow; cartão '+ Nome personalizado' tracejado", "FR-021"),
             ("Voz", "combobox de vozes Piper pt-BR (2–3) + botão 'Ouvir amostra' 36 px fantasma; slider 'Sensibilidade da wake word' com valor %", "FR-021, FR-080"),
             ("Painel do passo (Perfil)", "cards de perfil 2 colunas: web, backend, gamedev, devops, IA + link 'Modo mínimo'; cada card: ícone 24, título `headline-sm`, stack `code-sm`, descrição `body-sm`, chips de pacotes 22 px; toggle 'Ativo'", "FR-022"),
             ("Painel do passo (Contas)", "2 linhas: 'GitHub CLI login (gh auth login)' com botão; 'Chaves de IA (Anthropic/OpenAI/OpenRouter/Nous)' com status 'KWallet'; nota de segurança `body-sm` em card `warning` 10 %", "FR-023"),
             ("Rodapé", "72 px: 'Voltar' fantasma; centro: comando equivalente `code-sm` 'forja setup --profile gamedev --mascot guara' com copiar; 'Pular wizard' link; 'Avançar' primário 40 px", "FR-024"),
         ],
         icones=["add_circle", "arrow_back", "arrow_forward", "check", "code", "database", "key", "layers", "lock", "memory", "play_arrow", "psychology", "shield", "sports_esports", "terminal"],
         extra_subst={"treinar via forja-train CLI": ("`forja mascot train \"<nome>\"`", "FR-082"), "KWallet TPM2 Active": ("KWallet ativo", "FR-023"), "Fabíola (Neural pt-BR)": ("voz Piper pt-BR embarcada (nome real, licença verificada)", "ADR-011"), "Godot 4.3": ("Godot 4 (Flatpak Flathub, versão corrente)", "FR-041"), "Go 1.23": ("Go (versão corrente)", "FR-022"), "Vite / Next": ("remover — não listado no perfil web do PRD", "FR-022"), "Tailwind CLI": ("remover", "FR-022"), "PyTorch ROCm/CUDA": ("remover — perfil IA do PRD: Ollama, Hermes, Codex, Claude Code, Jupyter", "FR-022"), "Aseprite": ("só se licença (FR-022)", "FR-022")},
         checklist=["Completa em < 5 min sem rede (FR-020)", "Seleção grava `~/.config/hero/persona.toml` (FR-021)", "Nome personalizado dispara treino em segundo plano, Guará ativo até ficar pronto (FR-082)", "Chaves só no KWallet via `secret-tool`; grep de dotfiles no CI (FR-023)", "Tudo reproduzível por `forja setup --profile X --mascot Y` (FR-024)", "Navegável por teclado, contraste AA (NFR-050)", "Perfis = exatamente os 6 do FR-022"]),
    dict(slug="forjaos_wizard_de_primeiro_boot_passo_6_resumo_conclus_o", pendencias=["Flags `--voice --autostart --seal` não existem no `forja setup` do PRD (FR-024/FR-060); gerar só flags reais.", "Log cita `systemd-sysupdate`, `TensorRT`, `PCR-7`, `Fedora Atomic 41`: nada disso é da arquitetura (ADR-002, ADR-012, FR-002)."], nome="Wizard de primeiro boot — passo 6 (resumo e conclusão)", fr="FR-020, FR-024", tema="dark",
         alvo="Último passo do wizard QML: resumo das escolhas + progresso da instalação em segundo plano", pasta="image/firstboot",
         regioes=[
             ("Cabeçalho e trilho", "iguais ao passo 1–5; passo 6 ativo 'Concluir'", "FR-020"),
             ("Grid de resumo", "cards 2 colunas gap 12: Mascote (nome, wake word, TTS, LLM), Perfil (nome + chips de pacotes), Agentes & inferência, Cofre de credenciais (GitHub @user, KWallet), Base imutável (imagem + SELinux); cada card `layer-1` raio 8 padding 16, título `label-sm` uppercase, valor `body-md`", "FR-020"),
             ("Reproduzir via CLI", "card com comando `code-md` em caixa `layer-3` + botão 'Copiar'", "FR-024"),
             ("Progresso", "card: título 'Provisionando camada de usuário', barra 8 px ciano→violeta com %, 'Fase N/5', 'N de M etapas', taxa e tempo restante em 3 colunas `code-md` tabular", "FR-020"),
             ("Log ao vivo", "caixa 256 px (max-h-64) `konsole-bg` `code-sm`: linhas [✓]/[RUNNING]/[PENDING] coloridas; link 'Ver logs (journalctl -f)'", "FR-020"),
             ("Rodapé", "aviso 'Não desligue o computador' `body-sm` `warning`; botão 'Finalizar e entrar no desktop' primário 40 px (habilita ao concluir ou permite continuar em segundo plano)", "FR-020"),
         ],
         icones=["check", "content_copy", "key", "lock", "memory", "neurology", "pets", "receipt_long", "rocket_launch", "sports_esports", "terminal", "tune", "verified_user"],
         extra_subst={"TPM2": SUBST["TPM2"], "PCR-7": ("remover", "FR-023"), "--voice fabiola --autostart --seal": ("flags reais do `forja setup` (ver FR-060); `--seal` não existe", "FR-024, FR-060"), "Fedora Atomic 41 • NVIDIA Open Kernel 590.28": ("'base Universal Blue · NVIDIA open · SELinux enforcing · zram'", "FR-002"), "ZRAM 8GB lz4": ("zram (tamanho detectado) · zstd", "FR-036"), "ghcr.io/forjaos-nvidia-open:stable": ("ghcr.io/<org>/forjaos-nvidia-open:stable", "FR-001"), "TensorRT": ("ONNX Runtime CPU (openWakeWord)", "ADR-012"), "systemd-sysupdate": ("remover — bootc gerencia deploy", "ADR-002"), "sys-finalize --atomic-commit": ("remover — comando inexistente", "—"), "Blender 4.2 LTS": ("Blender (Flatpak, versão corrente)", "FR-005"), "@rodrigo-forja": ("@<usuário gh>", "FR-031")},
         checklist=["Com rede: instala em segundo plano e permite entrar no desktop (FR-020)", "Resumo bate 1:1 com as escolhas dos passos 2–5", "Comando CLI gerado é executável e reproduz o estado (FR-024)", "Log vem do journald do serviço de pós-instalação", "Nenhuma menção a Fedora/versão da base (FR-002)"]),
    dict(slug="forjaos_visualizador_de_mem_ria_linha_do_tempo_di_ria", pendencias=["Protótipo cita `Polkit: Tier 1 Auto-Aprovado` → Policy Engine tier livre (FR-100).", "`Fish Shell / Alacritty` → zsh / Konsole (FR-035).", "Número de nós/arestas e tamanho de memd são ilustrativos; vêm do `memory.db`."], nome="Visualizador de Memória — linha do tempo diária", fr="FR-135, FR-131, FR-132, FR-136", tema="dark",
         alvo="App QML (Qt Quick + Kirigami) `forja-memory`; tela 2 de 3 (Ctrl+2)", pasta="hero-memory/viewer",
         regioes=[
             ("Barra de título", "64 px: 'Forja Memory · memd' `headline-sm` + caminho do vault `code-sm`; direita: '14.280 nós · 38.410 arestas', 'memd: 84 MB · 0,2 % CPU', 'sqlite-vec pronto' `label-xs`", "FR-130, FR-133"),
             ("Sidebar", "256 px (w-64) `layer-1`: 3 telas (Grafo Ctrl+1, Linha do tempo Ctrl+2, Busca Ctrl+3) itens 40 px; botão 'Sincronizar vault'; seção 'Navegador' com atalhos; rodapé com VRAM/GPU e tamanho do graph.json", "FR-135"),
             ("Seletor de dia", "linha 48 px: chips de datas (06, 07, **08 Nov (Hoje)**, 09) 22 px + botão 'Ir para hoje'", "FR-135"),
             ("Cards de resumo", "4 cards: 'Atividade contínua · N eventos', 'Foco · 4h 12m', coletores (shell/git/HERO/janelas/notas com contagem), estado do memd", "FR-132"),
             ("Fluxo cronológico", "coluna central 75 %: linha vertical 1 px `border-ghost` à esquerda; eventos com dot 10 px colorido por coletor (shell ciano, git violeta, HERO laranja, janelas cinza, notas verde), hora `code-sm`, título `body-md` 600, corpo `body-sm`; cards expansíveis com diff/commands em `code-sm`", "FR-134, FR-135"),
             ("Painel direito", "25 %: prévia do `daily/AAAA-MM-DD.md` (frontmatter + markdown renderizado) `body-sm`/`code-sm`; distribuição por projeto (barras); comando equivalente `forja memory timeline --date …`; link 'Regras de captura'", "FR-131, FR-136"),
         ],
         icones=["calendar_month", "category", "check_circle", "chevron_left", "chevron_right", "close", "commit", "content_copy", "crop_square", "description", "desktop_windows", "edit_note", "event", "filter_alt", "hourglass_top", "hub", "manage_search", "memory", "minimize", "neurology", "note_add", "open_in_new", "power_settings_new", "record_voice_over", "reorder", "scatter_plot", "smart_toy", "sync", "terminal", "today", "tune", "verified", "verified_user", "view_in_ar"],
         extra_subst={"Polkit: Tier 1 Auto-Aprovado": ("Policy Engine · tier livre", "FR-100"), "Fish Shell / Alacritty": ("zsh / Konsole", "FR-035"), "TPM2 Desbloqueado": ("remover", "—"), "Godot 4.3 LTS": ("Godot 4", "FR-041"), "Blender 4.2 LTS": ("Blender", "FR-005"), "Obsidian": ("'Abrir no editor' (Obsidian/Logseq se instalados pelo usuário)", "FR-131")},
         checklist=["Abre em < 1 s; < 150 MB com 10k nós (FR-135)", "Eventos vêm do `memory.db` (FTS5) — nunca lê o vault direto para a timeline", "Cores por coletor fixas (ver Regiões)", "Prévia do daily abre o arquivo real do vault (FR-131)", "Retenção por coletor respeitada (FR-137)", "Fontes: Plus Jakarta Sans + JetBrains Mono; Inter só na lista densa de eventos se > 20 linhas"]),
    dict(slug="forjaos_visualizador_do_grafo_da_mem_ria_fr_135", pendencias=["Protótipo assume WebGL2; ADR-019 manda QML puro primeiro e QtWebEngine só se 10k nós a 60 fps falhar.", "Botão 3D fica desabilitado no 1.0."], nome="Visualizador de Memória — grafo", fr="FR-135, FR-134, FR-133", tema="dark",
         alvo="App QML `forja-memory`, tela 1 de 3 (Ctrl+1): grafo força-dirigida em QML/Canvas; QtWebEngine só se QML puro não atingir 10k nós a 60 fps (ADR-019)", pasta="hero-memory/viewer",
         regioes=[
             ("Barra de título e sidebar", "iguais à tela de linha do tempo", "FR-135"),
             ("Toolbar do grafo", "48 px: busca 'FTS5 + nomic-embed' Ctrl+F 320 px; modo 'Força (Barnes-Hut)' + slider repulsão; FPS `label-xs`; botões Fit / 2D / 3D (3D fica **desligado** no 1.0)", "FR-135"),
             ("Filtros por tipo", "chips 22 px com contagem: Todos, Git repos, Notas & wikilinks, Shell, Diálogos HERO, Janelas & apps, Commits & diffs — cores = coletor", "FR-134"),
             ("Canvas", "área central `void`; nós círculo 8–24 px por grau, cor por tipo, label `code-sm` ao hover/zoom; clusters com título `label-xs`; arestas 1 px `border-ghost`, destacadas em ciano ao selecionar; HUD canto inferior esquerdo: 'POS / θ / FPS' `label-xs`", "FR-134, FR-135"),
             ("Inspetor de entidade", "380 px (w-[380px]) à direita: caminho do arquivo `code-sm`, tipo, grau, modificado; prévia markdown; 'Conexões diretas' lista com peso 0–1 e tipo da aresta; 'Similaridade semântica (KNN k=3)' com distância cosseno; 3 botões: Abrir no editor, Explorar vizinhança, Perguntar ao HERO", "FR-133, FR-136"),
             ("Barra de status", "28 px: SQLite MB, RAM/300 MB max, CPU, I/O idle, nós/arestas visíveis, 'Vault sincronizado', próxima varredura; comando `forja memory graph <repo>`", "FR-130, FR-132"),
         ],
         icones=["article", "calendar_month", "calendar_today", "category", "chevron_right", "close", "cloud_done", "commit", "crop_square", "description", "explore", "filter_center_focus", "fit_screen", "folder_open", "forum", "hub", "layers", "manage_search", "map", "memory", "minimize", "neurology", "open_in_new", "pause", "push_pin", "record_voice_over", "scatter_plot", "share", "smart_toy", "sync", "terminal", "travel_explore", "verified", "zoom_in", "zoom_out"],
         extra_subst={"RESOLVER: WebGL2": ("QML/Canvas (ADR-019)", "ADR-019"), "60 FPS WebGL": ("60 fps QML", "ADR-019"), "3D": ("desabilitado no 1.0", "§2.2"), "Abrir no Obsidian / Editor": ("Abrir no editor", "FR-131")},
         checklist=["10k nós a 60 fps no desktop de referência ou ADR para QtWebEngine (ADR-019)", "`graph.json` no formato do graphify (FR-134)", "Filtros por tipo e por data (FR-135)", "Inspetor lê do SQLite + arquivo do vault", "Cores de nó = cores de coletor da tela de timeline"]),
    dict(slug="forjaos_docs_documenta_o_t_cnica_oficial", pendencias=["Protótipo usa Tailwind CDN; o site compila CSS estático a partir do palette (sem CDN em runtime).", "Página `Escalonador eBPF scx_lavd` depende da base Universal Blue entregar sched_ext; confirmar antes de publicar.", "`24.04 LTS` aparece 6×: versionamento é AAAA.MM.DD / vX.Y.Z (NFR-044).", "`x86_64 / arm64` → só x86-64-v3 (§10.1)."], nome="Documentação técnica oficial (site de docs)", fr="NFR-043, G1", tema="light",
         alvo="Site de docs (Astro ou Hugo) em `site/docs`; o **mesmo layout** gera `docs/roadmap/index.html` (CSS estático)", pasta="site/docs",
         regioes=[
             ("Header fixo", "64 px (`dimensions.docs_header_height`); fundo `layer-1` 85 % + blur; sombra `0 1px 8px rgba(0,0,0,.04)`; logo 32 px + 'ForjaOS' `headline-sm` + badge de versão `label-sm` em `primary-fixed`; busca 'Pesquisar documentação…' 448 px com kbd `Cmd+K`→`Ctrl+K`; nav (Visão geral, CLI & Tools, Arquitetura, HERO AI, GitHub); toggle de tema; avatar 32 px", "NFR-043"),
             ("Sidebar", "288 px (`dimensions.docs_sidebar_width`) fixa, `layer-1`, padding 16/24; grupos `label-sm` uppercase `outline`; itens `body-sm` 30 px raio 8, ativo `primary-container`/`on-primary-container`", "NFR-043"),
             ("Container", "max 1520 px, padding 24 px; breadcrumb `label-md` com chevrons", "NFR-043"),
             ("Banner", "raio 12 px `layer-1` padding 32, sombra sm; blobs `primary` 5 % e `secondary` 5 % blur 64; chips de status 22 px; título `display-lg` com palavra em `primary`; descrição `body-lg` max 48 rem; card de specs 320 px à direita `surface-container-low`", "NFR-043"),
             ("Grid principal", "12 colunas: 9 conteúdo + 3 TOC sticky ('Nesta página' `label-sm` + lista `body-sm`; 'Recursos oficiais' links)", "NFR-043"),
             ("Seções", "marcador quadrado 10 px `primary` + `label-sm` uppercase + `display-sm`; cards 3 colunas raio 12 `layer-1` padding 24 com número em quadrado 40 px; blocos de código raio 8 `surface-container-low` com botão copiar + toast inferior direito `inverse-surface`; tabela de tiers com pills coloridas (livre ciano, alterar laranja, bloqueado vermelho)", "NFR-043, FR-100"),
             ("Rodapé de navegação", "'← Anterior' fantasma / 'Próximo →' primário 40 px", "NFR-043"),
         ],
         icones=["arrow_back", "arrow_forward", "check_circle", "chevron_right", "content_copy", "description", "download", "folder", "history", "hub", "light_mode", "menu_book", "open_in_new", "person", "search", "search_insights", "security", "shield", "sync", "verified"],
         extra_subst={"Cmd+K": ("Ctrl+K", "—"), "PRD 1.0 Alinhado": ("badge com versão do PRD real", "—"), "x86_64 / arm64": SUBST["arm64"], "Escalonador eBPF scx_lavd": ("só se a base entregar sched_ext; senão remover a página", "ADR-001"), "sudo bootc switch ghcr.io/forjaos/forjaos-nvidia:24.04": ("`sudo bootc switch ghcr.io/<org>/forjaos-nvidia-open:stable`", "FR-001"), "forja doctor --strict": SUBST["forja doctor --strict"], "4.8k": SUBST["4.8k"], "Fedora Silverblue/Bazzite": ("'qualquer sistema bootc/Fedora Atomic' (sem marca na UI do produto; em docs pode citar como origem de rebase)", "G4")},
         checklist=["Header 64 / sidebar 288 / container 1520 (palette › dimensions)", "Tema light = Alabaster Forge; dark alternável", "Navegação por teclado e contraste AA", "Sem Material Symbols **ou** conjunto único de ícones em todo o site (DESIGN-RULES §5)", "Blocos de código copiáveis com toast", "pt-BR e en-US (NFR-043, NFR-051)"]),
    dict(slug="forjaos_o_sistema_operacional_para_quem_desenvolve_e_joga", pendencias=["Tabela comparativa e métricas (★ 3.4k, 0.4ms, 3.8 GB VRAM) são ilustrativas: só publicar com medições em `docs/releases/` (NFR-033, G2).", "`24.04 LTS` aparece 12×; `Kernel 6.9-cachyos-scx` e `NVIDIA Driver 555` não são da base (ADR-001).", "Seção `Dolphin Dev Edition` depende do ADR do explorer."], nome="Landing page — 'O sistema operacional para quem desenvolve e joga'", fr="G1, NFR-043, NFR-033", tema="light",
         alvo="Landing page (Astro) em `site/landing`; mesma base de tokens/CSS do site de docs", pasta="site/landing",
         regioes=[
             ("Header", "igual ao das docs (64 px) com nav: Recursos, HERO AI & Guará, Stack Dev & Jogos, Arquitetura Atomic, Documentação, GitHub; CTA 'Baixar ISO' primário", "G1"),
             ("Hero", "2 colunas: título `text-[64px]`→ usar `display-lg` escalado (56–64 px) 'O Linux onde você projeta · constrói · joga' com palavras em `primary`; parágrafo `body-lg`; 2 botões (Baixar ISO primário 48 px + tamanho; Ver no GitHub secundário); linha de comando copiável `code-md`; direita: mockup do desktop em card raio 16 sombra L3 (imagem estática, não iframe)", "G1"),
             ("Faixa de métricas", "3 cards: Guará ouvindo / VRAM local / latência — **só números reais ou remover**", "NFR-033"),
             ("Seções de recurso", "alternadas texto/imagem; eyebrow `label-sm` + `display-sm` + `body-md`; chips de tecnologia 22 px", "G1"),
             ("Tabela comparativa", "'Recurso' × ForjaOS / Ubuntu / Arch / Windows+WSL2; células com ✓/✗ coloridas; cabeçalho sticky; claims só com fonte verificável", "G1"),
             ("CTA final + rodapé", "banner `primary-container` com botão branco; rodapé 3 colunas links + licença Apache-2.0 + CC BY-SA 4.0 artes", "ADR-007"),
         ],
         icones=["bolt", "check_circle", "close", "download", "folder_special", "forum", "graphic_eq", "history", "hub", "inventory_2", "layers", "lock_reset", "memory", "person", "play_circle", "restart_alt", "smart_toy", "space_dashboard", "sports_esports", "star", "terminal", "timer", "usb", "verified"],
         extra_subst={"ISO 24.04 LTS": ("ISO vX.Y.Z", "NFR-044"), "5.8 GB": ("tamanho real (≤ 6 GB, NFR-011)", "NFR-011"), "Kernel 6.9-cachyos-scx": SUBST["Kernel 6.9-cachyos-scx"], "NVIDIA Driver 555.58.02": SUBST["NVIDIA Driver 555"], "GPU RTX 4080": SUBST["RTX 4080"], "★ 3.4k": SUBST["3.4k"], "4.8k": SUBST["4.8k"], "universal-blue 24.04": SUBST["universal-blue 24.04"], "forja-user@workstation": ("usuario@forjaos", "FR-003"), "Dolphin Dev Edition": ("só se ADR aprovar a tela do explorer", "—"), "Benchmark de Eficiência": ("só com medições reais publicadas em docs/releases/", "G2"), "Menos de 15 minutos": ("manter — é a meta G1 (dizer 'meta')", "G1"), "Tour Rápido (3 min)": ("só quando houver vídeo", "—")},
         checklist=["Nenhuma métrica inventada; cada número tem fonte em docs/releases/ (NFR-033)", "Download aponta para GitHub Release com SHA-256 (FR-010)", "Tokens light do palette; dark alternável", "Lighthouse ≥ 90 em acessibilidade", "pt-BR + en-US"]),
]

TEMPLATE = """# Tela: {nome}

| Campo | Valor |
| --- | --- |
| Slug | `{slug}` |
| Protótipo | `docs/telas/{slug}/code.html` (sha256 `{sha}`) · `screen.png` |
| Requisitos | {fr} |
| Tema | {tema_label} |
| Tecnologia-alvo | {alvo} |
| Pasta do monorepo | {pasta} |
| Status | {status} |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
{regioes}

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
{subst}

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

{icones}

## Checklist de fidelidade

{checklist}
- [ ] Captura lado a lado em `docs/design-system/telas/{slug}/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor cruzado registrou `visual: fiel`

## Pendências e divergências conhecidas

{pendencias}
"""

DEFAULT_PENDENCIAS = "- (nenhuma registrada ainda — adicione aqui o que o protótipo mostra e o PRD não prevê; cada item vira issue antes de implementar)"

def sha12(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]

def count_occ(html: str, needle: str) -> int:
    return len(re.findall(re.escape(needle), html))

def render(t: dict, html: str, status: str, pendencias: str) -> str:
    sha = sha12(TELAS_DIR / t["slug"] / "code.html")
    tema_label = "dark (Cybernetic Forge)" if t["tema"] == "dark" else "light (Alabaster Forge)"
    regioes = "\n".join(f"| {r} | {m} | {fr} |" for r, m, fr in t["regioes"])
    # substituições: as globais encontradas + extras da tela
    rows = []
    for k, (v, src) in SUBST.items():
        n = count_occ(html, k)
        if n:
            rows.append((k, n, v, src))
    for k, (v, src) in t.get("extra_subst", {}).items():
        if k in {r[0] for r in rows}:
            continue
        n = count_occ(html, k)
        rows.append((k, n if n else "—", v, src))
    if not rows:
        rows.append(("—", "0", "nenhuma substituição global encontrada; conferir textos manualmente", "ADR-028"))
    subst = "\n".join(f"| `{k}` | {n} | {v} | {src} |" for k, n, v, src in rows)
    if t["icones"]:
        icones = "| Material Symbol | Breeze / próprio |\n| --- | --- |\n" + "\n".join(
            f"| `{i}` | `{ICONS.get(i, 'DEFINIR')}` |" for i in t["icones"])
    else:
        icones = "Sem ícones Material no protótipo. Ícones necessários na implementação vêm de Breeze ou `brand/icons/` e devem ser listados aqui antes do gate *plan*."
    checklist = "\n".join(f"- [ ] {c}" for c in t["checklist"])
    return TEMPLATE.format(nome=t["nome"], slug=t["slug"], sha=sha, fr=t["fr"], tema_label=tema_label, alvo=t["alvo"],
                           pasta=t["pasta"], status=status, regioes=regioes, subst=subst, icones=icones,
                           checklist=checklist, pendencias=pendencias)

def existing_parts(path: Path):
    status, pend = "spec", DEFAULT_PENDENCIAS
    if path.exists():
        s = path.read_text(encoding="utf-8")
        m = re.search(r"^\| Status \| (.+?) \|$", s, re.M)
        if m: status = m.group(1)
        m = re.search(r"## Pendências e divergências conhecidas\n\n(.*)\Z", s, re.S)
        if m and m.group(1).strip(): pend = m.group(1).strip()
    return status, pend

def check() -> int:
    bad = 0
    for t in TELAS:
        spec = OUT / f"{t['slug']}.md"
        if not spec.exists():
            print(f"gen_tela_specs: FALTA {spec.relative_to(ROOT)}"); bad += 1; continue
        m = re.search(r"sha256 `([0-9a-f]{12})`", spec.read_text(encoding="utf-8"))
        real = sha12(TELAS_DIR / t["slug"] / "code.html")
        if not m or m.group(1) != real:
            print(f"gen_tela_specs: hash divergente em {t['slug']} (spec {m.group(1) if m else '?'} ≠ code.html {real})"); bad += 1
    print("gen_tela_specs: OK" if not bad else f"gen_tela_specs: {bad} problema(s)")
    return 1 if bad else 0

def main(argv) -> int:
    if "--check" in argv:
        return check()
    OUT.mkdir(parents=True, exist_ok=True)
    for t in TELAS:
        html = (TELAS_DIR / t["slug"] / "code.html").read_text(encoding="utf-8", errors="replace")
        spec = OUT / f"{t['slug']}.md"
        status, pend = existing_parts(spec)
        if pend == DEFAULT_PENDENCIAS and t.get("pendencias"):
            pend = "\n".join(f"- {p}" for p in t["pendencias"])
        spec.write_text(render(t, html, status, pend), encoding="utf-8")
        print(f"escrito {spec.relative_to(ROOT)}")
    # template de referência para telas futuras
    (OUT / "_TEMPLATE.md").write_text(TEMPLATE, encoding="utf-8")
    print(f"escrito {(OUT / '_TEMPLATE.md').relative_to(ROOT)}  (placeholders {{...}} preenchidos por este script)")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
