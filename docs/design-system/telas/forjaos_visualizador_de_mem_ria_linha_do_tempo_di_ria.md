# Tela: Visualizador de Memória — linha do tempo diária

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_visualizador_de_mem_ria_linha_do_tempo_di_ria` |
| Protótipo | `docs/telas/forjaos_visualizador_de_mem_ria_linha_do_tempo_di_ria/code.html` (sha256 `e1f29424a11d`) · `screen.png` |
| Requisitos | FR-135, FR-131, FR-132, FR-136 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | App QML (Qt Quick + Kirigami) `forja-memory`; tela 2 de 3 (Ctrl+2) |
| Pasta do monorepo | hero-memory/viewer |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Barra de título | 64 px: 'Forja Memory · memd' `headline-sm` + caminho do vault `code-sm`; direita: '14.280 nós · 38.410 arestas', 'memd: 84 MB · 0,2 % CPU', 'sqlite-vec pronto' `label-xs` | FR-130, FR-133 |
| Sidebar | 256 px (w-64) `layer-1`: 3 telas (Grafo Ctrl+1, Linha do tempo Ctrl+2, Busca Ctrl+3) itens 40 px; botão 'Sincronizar vault'; seção 'Navegador' com atalhos; rodapé com VRAM/GPU e tamanho do graph.json | FR-135 |
| Seletor de dia | linha 48 px: chips de datas (06, 07, **08 Nov (Hoje)**, 09) 22 px + botão 'Ir para hoje' | FR-135 |
| Cards de resumo | 4 cards: 'Atividade contínua · N eventos', 'Foco · 4h 12m', coletores (shell/git/HERO/janelas/notas com contagem), estado do memd | FR-132 |
| Fluxo cronológico | coluna central 75 %: linha vertical 1 px `border-ghost` à esquerda; eventos com dot 10 px colorido por coletor (shell ciano, git violeta, HERO laranja, janelas cinza, notas verde), hora `code-sm`, título `body-md` 600, corpo `body-sm`; cards expansíveis com diff/commands em `code-sm` | FR-134, FR-135 |
| Painel direito | 25 %: prévia do `daily/AAAA-MM-DD.md` (frontmatter + markdown renderizado) `body-sm`/`code-sm`; distribuição por projeto (barras); comando equivalente `forja memory timeline --date …`; link 'Regras de captura' | FR-131, FR-136 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `TPM2` | 1 | KWallet (TPM2 não é requisito do PRD; só se ADR futuro aprovar) | FR-023, NFR-024 |
| `Polkit` | 1 | Policy Engine (tiers livre/alterar/bloqueado) | FR-100 |
| `Tier 1` | 1 | tier `livre` / `alterar` / `bloqueado` (nomes do PRD) | FR-100 |
| `Alacritty` | 1 | Konsole (terminal padrão) | FR-035 |
| `Fish Shell` | 1 | zsh padrão (fish disponível) | FR-035 |
| `Polkit: Tier 1 Auto-Aprovado` | 1 | Policy Engine · tier livre | FR-100 |
| `Fish Shell / Alacritty` | 1 | zsh / Konsole | FR-035 |
| `TPM2 Desbloqueado` | 1 | remover | — |
| `Godot 4.3 LTS` | 1 | Godot 4 | FR-041 |
| `Blender 4.2 LTS` | 1 | Blender | FR-005 |
| `Obsidian` | 2 | 'Abrir no editor' (Obsidian/Logseq se instalados pelo usuário) | FR-131 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

| Material Symbol | Breeze / próprio |
| --- | --- |
| `calendar_month` | `view-calendar` |
| `category` | `view-categories` |
| `check_circle` | `dialog-ok-apply` |
| `chevron_left` | `go-previous` |
| `chevron_right` | `go-next` |
| `close` | `window-close` |
| `commit` | `vcs-commit` |
| `content_copy` | `edit-copy` |
| `crop_square` | `window-maximize` |
| `description` | `text-x-generic` |
| `desktop_windows` | `computer` |
| `edit_note` | `document-edit` |
| `event` | `view-calendar` |
| `filter_alt` | `view-filter` |
| `hourglass_top` | `chronometer` |
| `hub` | `próprio: graph` |
| `manage_search` | `edit-find` |
| `memory` | `cpu` |
| `minimize` | `window-minimize` |
| `neurology` | `próprio: hero-ai` |
| `note_add` | `document-new` |
| `open_in_new` | `window-new` |
| `power_settings_new` | `system-shutdown` |
| `record_voice_over` | `audio-input-microphone` |
| `reorder` | `view-sort` |
| `scatter_plot` | `próprio: graph-nodes` |
| `smart_toy` | `próprio: mascote (estado)` |
| `sync` | `view-refresh` |
| `terminal` | `utilities-terminal` |
| `today` | `view-calendar-day` |
| `tune` | `configure` |
| `verified` | `checkmark` |
| `verified_user` | `security-high` |
| `view_in_ar` | `próprio: 3d` |

## Checklist de fidelidade

- [ ] Abre em < 1 s; < 150 MB com 10k nós (FR-135)
- [ ] Eventos vêm do `memory.db` (FTS5) — nunca lê o vault direto para a timeline
- [ ] Cores por coletor fixas (ver Regiões)
- [ ] Prévia do daily abre o arquivo real do vault (FR-131)
- [ ] Retenção por coletor respeitada (FR-137)
- [ ] Fontes: Plus Jakarta Sans + JetBrains Mono; Inter só na lista densa de eventos se > 20 linhas
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_visualizador_de_mem_ria_linha_do_tempo_di_ria/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Protótipo cita `Polkit: Tier 1 Auto-Aprovado` → Policy Engine tier livre (FR-100).
- `Fish Shell / Alacritty` → zsh / Konsole (FR-035).
- Número de nós/arestas e tamanho de memd são ilustrativos; vêm do `memory.db`.
