# Regras de design, layout e tokens — ForjaOS

**Versão:** 1.0 · **Data:** 2026-11-08 · **Decisões:** ADR-027 (tokens canônicos), ADR-028 (precedência protótipo × PRD) · **Fonte de tokens:** `brand/palette.json`

Este documento diz como uma tela do ForjaOS é construída para ser **fiel ao protótipo e nunca genérica**. Ele é lido antes de qualquer tarefa que toque QML, tema Plasma/SDDM/Plymouth/GRUB/Konsole, SVG ou site. As specs individuais estão em `docs/design-system/telas/<slug>.md`.

## 1. Fonte da verdade

| Para | Fonte | Observação |
| --- | --- | --- |
| Cores, tipografia, raio, espaçamento, elevação, dimensões, movimento | `brand/palette.json` | única; verificada por `scripts/check-tokens.sh` |
| Layout, hierarquia, posição, estados, animação de cada tela | `docs/telas/<slug>/screen.png` + `code.html` | lidos **depois** da spec da tela |
| Racional de cada tema | `docs/telas/design/cybernetic_forge/DESIGN.md` (escuro), `alabaster_forge/DESIGN.md` (claro) | `cybernetic_obsidian` é histórico |
| Conteúdo: textos, nomes, comandos, versões, hardware | `docs/PRD.md` | o protótipo nunca é fonte de conteúdo (ADR-028) |
| Inventário por tela | `docs/design-system/telas/<slug>.md` | regiões, medidas, substituições, ícones, checklist |

Tema padrão: **escuro** (Cybernetic Forge). O claro (Alabaster Forge) é alternável pelo atalho do sistema (FR-050) e obrigatório no site e nas docs.

## 2. Proibições — o que torna uma tela "genérica"

Qualquer item abaixo reprova o PR no gate *review*:

1. Breeze, Fedora, Bazzite ou qualquer tema padrão **visível** em superfície própria (painel, dock, overlay, wizard, SDDM, Plymouth, GRUB, Konsole, visualizador de memória).
2. Cor hex que não existe no `palette.json` (variante `#rrggbbaa` de cor do palette é permitida).
3. Fonte fora de **Plus Jakarta Sans** (UI), **JetBrains Mono** (mono) e **Inter** (só corpo denso). Fira Code, Roboto, Noto como UI principal: proibidas.
4. `#000000` puro em overlay ou sombra; usa-se opacidade sobre `canvas`/`void`.
5. Pílula totalmente arredondada (`radius: full`) fora de toggle e status dot.
6. Ícones Material Symbols no produto (ver §5). Só o protótipo os usa.
7. Strings da coluna "No protótipo" do ADR-028 (`Jarvis`, `devos`, `nftables`, `24.04`, `arm64`, `RTX 4070`, `Kernel 6.12`).
8. Texto placeholder (lorem, "Título aqui", dados fictícios não previstos pela spec).
9. Componente "default" de toolkit sem estilo (botão, input, lista) — tudo recebe os tokens.
10. Medida "a olho": toda largura/altura/raio/espaçamento vem do `palette.json` ou da medida registrada na spec da tela.

## 3. Grade e dimensões

- **Unidade:** 8 px; micro-ajustes em 4 px. Toda margem, padding e gap é múltiplo de 4, preferencialmente de 8.
- **Raio:** 8 px padrão (janelas, painéis, botões, inputs); 4 px em chips, badges e elementos aninhados; 12 px no dock; 16 px no overlay e shells flutuantes; `full` só em toggles e status dots.
- **Dimensões fixas** (de `palette.json › dimensions`):

| Elemento | Valor | Origem |
| --- | --- | --- |
| Barra superior | 40 px | desktop (FR-052) |
| Overlay Central de Comando | 520 px de largura, 16 px da borda direita, 32 px de margem vertical total | FR-121 |
| Dock | 64 px de altura, 12 px acima da borda inferior, ícone 48 px raio 8, ponto ativo 3 px | FR-052 |
| Toolbar de app | 40 px compacta / 48 px padrão | Alabaster §Layout |
| Cabeçalho de card | 36 px | Forge §Cards |
| Linha de árvore/lista | 28 px | Alabaster §Lists |
| Chip/pílula de status | 22 px, raio 4–6 | Alabaster §Chips |
| Status dot | 6 px | Forge §Telemetry |
| Botão | 36 px (toolbar) / 40 px (diálogo) | Alabaster §Buttons |
| Checkbox | 16 px, raio 4 | Alabaster §Checkbox |
| Docs/site: cabeçalho 64 px, sidebar 288 px, conteúdo máx. 1520 px | tela `forjaos_docs_*` | NFR-043 |

- **Responsivo (site/docs):** ≥ 1280 px multi-pane; < 1280 px painéis colapsam em drawers e gutter cai para `sm`.

## 4. Tabela de tradução de tokens

Um token, uma linha, todas as tecnologias. Nomes CSS seguem `--fj-<token>`; nomes QML vivem em `brand/qml/ForjaTheme.qml` (singleton, a criar na Fase 1) como `Forja.<token>`.

| `palette.json` | CSS (site, roadmap) | QML (`ForjaTheme`) | KColorScheme (`.colors`) | Konsole `.colorscheme` | Plymouth script | GRUB `theme.txt` |
| --- | --- | --- | --- | --- | --- | --- |
| `canvas` | `--fj-canvas` | `Forja.canvas` | `[Colors:Window] BackgroundNormal` | `[Background] Color` | `Window.SetBackgroundTopColor/BottomColor` | `desktop-color` |
| `layer-1` | `--fj-layer-1` | `Forja.layer1` | `[Colors:View] BackgroundNormal` | — | — | `+ boot_menu { item_color }` fundo |
| `layer-2` | `--fj-layer-2` | `Forja.layer2` | `[Colors:View] BackgroundAlternate` | `[BackgroundIntense] Color` | — | — |
| `layer-3` | `--fj-layer-3` | `Forja.layer3` | `[Colors:Button] BackgroundNormal` | — | — | — |
| `on-surface` | `--fj-on-surface` | `Forja.text` | `[Colors:Window] ForegroundNormal` | `[Foreground] Color` | cor do texto (se houver) | `title-color`, `item_color` |
| `text-muted` | `--fj-text-muted` | `Forja.textMuted` | `[Colors:Window] ForegroundInactive` | `[ForegroundFaint] Color` | — | `message-color` |
| `accent-cyan` / `primary-container` | `--fj-accent-cyan` | `Forja.accent` | `[Colors:Selection] BackgroundNormal`, `[Colors:View] DecorationFocus` | `[Color4] Color` (azul) + cursor | barra de progresso | `selected_item_color`, `border` da entrada ativa |
| `accent-violet` | `--fj-accent-violet` | `Forja.ai` | `[Colors:View] ForegroundLink` | `[Color5] Color` (magenta) | — | — |
| `accent-orange` / `mascot` | `--fj-accent-orange` | `Forja.mascot` | `[Colors:View] ForegroundNeutral` | `[Color3] Color` (amarelo/laranja) | logo spark | — |
| `success` | `--fj-success` | `Forja.success` | `[Colors:View] ForegroundPositive` | `[Color2] Color` | — | — |
| `warning` | `--fj-warning` | `Forja.warning` | `[Colors:View] ForegroundNeutral` | `[Color3Intense] Color` | — | — |
| `danger` / `error` | `--fj-danger` | `Forja.danger` | `[Colors:View] ForegroundNegative` | `[Color1] Color` | — | — |
| `border-ghost` (alpha) | `--fj-border-ghost` | `Forja.borderGhost` | `[Colors:Window] BackgroundAlternate` (aprox.) | — | — | — |
| `radius.md` | `--fj-radius` | `Forja.radius` | — (decoração Aurorae/Breeze fork) | — | — | — |
| `typography.families.ui` | `--fj-font-ui` | `Forja.fontUi` | `kdeglobals [General] font` | — | — | `font` (PF2 gerado) |
| `typography.families.mono` | `--fj-font-mono` | `Forja.fontMono` | `kdeglobals [General] fixed` | `[General] Font` (profile) | — | PF2 gerado |
| `dimensions.*` | `--fj-dim-*` | `Forja.dim.*` | — | — | — | medidas em px no `theme.txt` |

Regras da tradução:
- O gerador de temas (FR-051, Fase 1) lê `palette.json` e escreve `.colors`, `.colorscheme`, `theme.txt`, `plymouth script`, `ForjaTheme.qml` e `tokens.css`. Nenhum desses arquivos é editado à mão depois de gerado.
- Onde o alvo só aceita cor opaca (KColorScheme, GRUB), um valor com alfa é pré-composto sobre `canvas` do tema e o resultado é **adicionado ao `palette.json`** como token derivado (`*-flat`), para que `check-tokens.sh` continue válido.
- Konsole: o mapeamento ANSI completo (Color0–7 e Intense) é definido na spec `forjaos_terminal_konsole_dev_forja_doctor.md`.

## 5. Ícones

- O protótipo usa **Material Symbols Outlined**; o produto **não**.
- Produto KDE: ícones **Breeze** recoloridos pelos tokens (`currentColor`/esquema) **ou** SVG próprio em `brand/icons/` quando não há equivalente (mascote, logo, estados do HERO, Modo Jogo, Escudo).
- Cada spec de tela traz a tabela `Material Symbol → Breeze / próprio`. Sem a tabela preenchida, a tela não passa no gate *plan*.
- Tamanhos: 16 px (inline/texto), 20 px (toolbar), 24 px (dock pequeno/plasmoid), 48 px (dock).
- Site/docs: pode usar Material Symbols (Apache-2.0) **ou** os SVG de `brand/icons/`; o mesmo conjunto em todo o site.

## 6. Tipografia

Escala de `palette.json › typography.scale`. Uso obrigatório:

| Token | Família | Tamanho/linha | Onde |
| --- | --- | --- | --- |
| `display-lg` | UI 700 | 40/48 | título do wizard, hero da landing |
| `display-sm` | UI 600 | 30/38 | título de seção do site/docs |
| `headline-lg` | UI 600 | 24/32 | título de tela de app (visualizador de memória) |
| `headline-md` | UI 600 | 20/28 | título de diálogo/modal |
| `headline-sm` | UI 600 | 16/24 | título de janela, de card do overlay |
| `body-lg` / `body-md` / `body-sm` | UI 400 | 16/24 · 14/20 · 12/16 | texto corrido; **12 px é o mínimo** |
| `body-dense-*` | Inter 400 | 14/20 · 12/16 | tabelas densas, inspetores (> 20 linhas) |
| `code-lg` / `code-md` / `code-sm` | Mono | 14/22 · 13/18 · 11/16 | terminal, snippets, telemetria, atalhos |
| `label-md` / `label-sm` / `label-xs` | Mono 600 uppercase | 12/16 · 11/16 · 10/14; tracking 0.04–0.06em | status, chips, cabeçalhos de seção pequenos |

- **Números tabulares** (`font-variant-numeric: tabular-nums` / `font.features`) em toda métrica, relógio e contador.
- Títulos com tracking negativo conforme a escala; corpo sem tracking.
- Sem itálico decorativo; itálico só em termos técnicos estrangeiros no corpo de docs.

## 7. Elevação e profundidade

Tema escuro (Forge): hierarquia por **luminosidade + blur + borda ghost**, não por sombra.

| Nível | Superfície | Opacidade | Blur | Borda | Sombra |
| --- | --- | --- | --- | --- | --- |
| L0 canvas | `canvas` | 1 | 0 | — | — |
| L1 painéis, árvore, docks internos | `layer-1` | 0,85 | 16 px | `border-ghost` | — |
| L2 cards, overlay, dock flutuante | `layer-2` | 0,70 | 24 px | `border-active` (0,18–0,35) | `0 8px 32px -4px rgba(6,9,15,.8), 0 2px 8px -2px rgba(139,92,246,.1)` |
| L3 modais, menus | `layer-3` | 0,90 | 28 px | `border-ghost-strong` | idem L2 |

Estado ativo/foco: borda → `border-active` + `glow-cyan`. Nunca `#000000` em overlay.

Tema claro (Alabaster): hierarquia por **hairline + sombra nítida**; vidro só no chrome (header, dock, menus) com `frosted` + blur 12 px + inset `frosted-inset`. Sombras L1/L2/L3 em `palette.json › elevation.light`.

## 8. Mascote (Guará) e estados do HERO

- 5 estados (FR-054, FR-071): `idle` (`text-muted`), `listening` (`accent-cyan`), `thinking` (`accent-violet`), `speaking` (`accent-orange`), `error` (`danger`). A cor do estado colore o anel/glow do mascote e o indicador do plasmoid; o corpo do mascote mantém o laranja-guará.
- SVG com camadas nomeadas `body`, `ears`, `eyes`, `mouth`, `glow`, `badge`; 15 visemes na camada `mouth` (FR-084). Trocar o personagem = manter os nomes das camadas.
- Animação em QML a 60 fps, sem rasterização por frame (FR-123): transforma propriedades (`opacity`, `scale`, `rotation`), não redesenha o SVG.
- Waveform do overlay: 8 barras, 4–26 px, período 1,2 s, atraso 0,15 s entre barras (`motion.wave_bar_ms`).

## 9. Acessibilidade e idioma

- Contraste **AA** em todo par texto/fundo dos dois temas. Pares verificados: `on-surface`/`surface`, `on-surface-variant`/`surface-container`, `on-primary`/`primary-container`, `text-muted`/`layer-1` (escuro: 4,6:1), `text-muted`/`layer-1` (claro: 4,8:1). Novo par → medir antes de usar.
- Foco visível: anel `0 0 0 3px` no tom primário (claro: `focus-ring`; escuro: `glow-cyan-strong`). Nunca `outline: none` sem substituto.
- Navegação por teclado completa em overlay e wizard (NFR-050); ordem de tab segue a leitura visual.
- Tamanho de fonte segue o do sistema; a escala é relativa ao `body-md`.
- pt-BR padrão e en-US completo (NFR-051); strings nunca concatenadas em código; plural via Qt Linguist.

## 10. DoD visual — quando uma tela está "fiel"

Uma tarefa de tela só passa no gate *test*/*review* com **todos**:

1. Captura lado a lado (`docs/design-system/telas/<slug>/compare-AAAA-MM-DD.png`), protótipo à esquerda, implementação à direita, mesma resolução.
2. `scripts/check-tokens.sh` OK.
3. Medidas-chave da spec conferidas e listadas no PR (largura/altura/raio/gap das regiões marcadas como "copiar").
4. Tabela de substituições do ADR-028 aplicada; `grep` das strings proibidas vazio.
5. Tabela de ícones da spec aplicada (nenhum Material Symbol no produto).
6. Estados previstos na spec implementados (hover/foco/ativo/erro; estados do mascote quando aplicável).
7. O revisor (contexto limpo, ADR-033) registra `visual: fiel` no comentário de review.

## 11. Como ler uma spec de tela

Cada `docs/design-system/telas/<slug>.md` tem:

- **Cabeçalho:** slug, caminho do protótipo com hash SHA-256 (12 hex) do `code.html`, FRs, tema, tecnologia-alvo, pasta do monorepo, status.
- **Regiões (layout → copiar):** cada bloco visual com medidas e tokens. Isso é reproduzido.
- **Conteúdo (PRD → substituir):** cada string do protótipo que o PRD corrige, com a fonte.
- **Ícones:** tabela Material Symbol → Breeze/próprio.
- **Checklist de fidelidade:** itens verificáveis específicos da tela.
- **Pendências e divergências:** o que o protótipo mostra e o PRD não prevê (vira issue antes de implementar).

Se o hash do `code.html` mudou, a spec está desatualizada: atualize a spec **antes** de implementar.
