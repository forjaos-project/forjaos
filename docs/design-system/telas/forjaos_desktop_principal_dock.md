# Tela: Desktop principal (escuro) com dock e overlay

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_desktop_principal_dock` |
| Protótipo | `docs/telas/forjaos_desktop_principal_dock/code.html` (sha256 `bb4d4486970a`) · `screen.png` |
| Requisitos | FR-050, FR-052, FR-055, FR-058 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | Plasma 6: look-and-feel 'Forja', layout de painel (`layout.js`), dock (Plasma panel flutuante ou Latte-like próprio em QML), wallpaper, Konsole; overlay vem da tela `central_de_comando_hero_corrigida` |
| Pasta do monorepo | brand/plasma + image/system_files |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Barra superior | altura 40 px (`dimensions.topbar_height`); fundo `glass-topbar` blur 14 px; borda inferior `rgba(0,229,255,0.12)`; esquerda: logo 20 px + dots de workspace + `Projeto: <repo> · branch <nome>`; centro: data/hora `code-md`; direita: chip HERO (estado), GPU + temperatura, Wi-Fi, BT, [Escudo], bateria | FR-052 |
| Área de trabalho | wallpaper oficial escuro (ondas ciano/violeta sobre grafite); janelas com raio 12 px, sombra L2 | FR-055 |
| Janela Konsole | raio 12 px, borda `border-ghost`, fundo `konsole-bg` (#080b11) sem blur; barra de título 40 px com 3 dots (vermelho/amarelo/verde 12 px) + abas (`forja-term · zsh` ativa com borda ciano 1 px, `claude`, `codex`, `ollama`) `code-md` | FR-035 |
| Overlay à direita | ver spec `forjaos_central_de_comando_hero_corrigida` (canônica). Esta tela mostra o overlay sempre visível só para composição; no produto ele abre por Super+Espaço | FR-121 |
| Dock | centralizado, 12 px da borda inferior, altura 64 px, raio 12 px, `glass-dock` blur 24 px, borda `border-ghost-strong`; ícones 48 px raio 8, gap 8 px; ordem: Terminal, Code, Git, Docker, Unity*, Godot, HERO, Monitor, Navegador, Apps; ponto ativo 3 px ciano sob o ícone (`*Unity` só após instalação) | FR-052 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `Jarvis` | 4 | Guará (persona) / HERO (motor) | ADR-005, ADR-006 |
| `devos` | 10 | forja (CLI), forja-term (terminal) | ADR-020, FR-035, FR-060 |
| `rodrigo@` | 3 | usuario@forjaos ($USER@forjaos) | FR-003 |
| `nftables` | 1 | firewalld | ADR-022 |
| `RTX 4070` | 1 | RTX 5060 8 GB (desktop de referência) | §10.2 |
| `GameMode` | 1 | Modo Jogo (hero-game.target) | FR-043 |
| `Escudo ativo` | 1 | indicador só se `forja install escudo` executado | ADR-023, NFR-027 |
| `Alacritty` | 2 | Konsole (terminal padrão) | FR-035 |
| `Kernel 6.x · sched_ext ativo (scx_lavd)` | — | texto real do `forja doctor` (kernel/scheduler detectados) | FR-036 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

Sem ícones Material no protótipo. Ícones necessários na implementação vêm de Breeze ou `brand/icons/` e devem ser listados aqui antes do gate *plan*.

## Checklist de fidelidade

- [ ] Barra superior 40 px com os itens do FR-052 na ordem
- [ ] Dock 64 px / 12 px da borda / ícones 48 px / ponto ativo 3 px
- [ ] Atalhos Super+Espaço, Super+T, Super+E, Super+G, Super+M aplicados (FR-058)
- [ ] Wallpaper em /usr/share/wallpapers/ForjaOS/
- [ ] Zero ícone/wallpaper Fedora/Bazzite (check-branding.sh)
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_desktop_principal_dock/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- O protótipo mostra o overlay sempre aberto ocupando a coluna direita; no produto ele é um overlay sob demanda (FR-121). A composição da tela é referência de convivência janela + overlay, não um layout fixo.
- Terminal padrão `forja-term` como perfil de Konsole (nome do perfil, não binário novo).
