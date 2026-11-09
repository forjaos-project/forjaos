# Tela: Visualizador de Memória — grafo

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_visualizador_do_grafo_da_mem_ria_fr_135` |
| Protótipo | `docs/telas/forjaos_visualizador_do_grafo_da_mem_ria_fr_135/code.html` (sha256 `e3eb4bbc5af8`) · `screen.png` |
| Requisitos | FR-135, FR-134, FR-133 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | App QML `forja-memory`, tela 1 de 3 (Ctrl+1): grafo força-dirigida em QML/Canvas; QtWebEngine só se QML puro não atingir 10k nós a 60 fps (ADR-019) |
| Pasta do monorepo | hero-memory/viewer |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Barra de título e sidebar | iguais à tela de linha do tempo | FR-135 |
| Toolbar do grafo | 48 px: busca 'FTS5 + nomic-embed' Ctrl+F 320 px; modo 'Força (Barnes-Hut)' + slider repulsão; FPS `label-xs`; botões Fit / 2D / 3D (3D fica **desligado** no 1.0) | FR-135 |
| Filtros por tipo | chips 22 px com contagem: Todos, Git repos, Notas & wikilinks, Shell, Diálogos HERO, Janelas & apps, Commits & diffs — cores = coletor | FR-134 |
| Canvas | área central `void`; nós círculo 8–24 px por grau, cor por tipo, label `code-sm` ao hover/zoom; clusters com título `label-xs`; arestas 1 px `border-ghost`, destacadas em ciano ao selecionar; HUD canto inferior esquerdo: 'POS / θ / FPS' `label-xs` | FR-134, FR-135 |
| Inspetor de entidade | 380 px (w-[380px]) à direita: caminho do arquivo `code-sm`, tipo, grau, modificado; prévia markdown; 'Conexões diretas' lista com peso 0–1 e tipo da aresta; 'Similaridade semântica (KNN k=3)' com distância cosseno; 3 botões: Abrir no editor, Explorar vizinhança, Perguntar ao HERO | FR-133, FR-136 |
| Barra de status | 28 px: SQLite MB, RAM/300 MB max, CPU, I/O idle, nós/arestas visíveis, 'Vault sincronizado', próxima varredura; comando `forja memory graph <repo>` | FR-130, FR-132 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `WebGL` | 3 | QML puro; QtWebEngine só se QML não atingir 10k nós a 60 fps | ADR-019 |
| `RESOLVER: WebGL2` | 1 | QML/Canvas (ADR-019) | ADR-019 |
| `60 FPS WebGL` | 1 | 60 fps QML | ADR-019 |
| `3D` | 2 | desabilitado no 1.0 | §2.2 |
| `Abrir no Obsidian / Editor` | 1 | Abrir no editor | FR-131 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

| Material Symbol | Breeze / próprio |
| --- | --- |
| `article` | `text-x-generic` |
| `calendar_month` | `view-calendar` |
| `calendar_today` | `view-calendar` |
| `category` | `view-categories` |
| `chevron_right` | `go-next` |
| `close` | `window-close` |
| `cloud_done` | `cloud-upload` |
| `commit` | `vcs-commit` |
| `crop_square` | `window-maximize` |
| `description` | `text-x-generic` |
| `explore` | `find-location` |
| `filter_center_focus` | `zoom-fit-best` |
| `fit_screen` | `zoom-fit-best` |
| `folder_open` | `folder-open` |
| `forum` | `view-conversation-balloon` |
| `hub` | `próprio: graph` |
| `layers` | `layer-visible-on` |
| `manage_search` | `edit-find` |
| `map` | `map-globe` |
| `memory` | `cpu` |
| `minimize` | `window-minimize` |
| `neurology` | `próprio: hero-ai` |
| `open_in_new` | `window-new` |
| `pause` | `media-playback-pause` |
| `push_pin` | `pin` |
| `record_voice_over` | `audio-input-microphone` |
| `scatter_plot` | `próprio: graph-nodes` |
| `share` | `document-share` |
| `smart_toy` | `próprio: mascote (estado)` |
| `sync` | `view-refresh` |
| `terminal` | `utilities-terminal` |
| `travel_explore` | `find-location` |
| `verified` | `checkmark` |
| `zoom_in` | `zoom-in` |
| `zoom_out` | `zoom-out` |

## Checklist de fidelidade

- [ ] 10k nós a 60 fps no desktop de referência ou ADR para QtWebEngine (ADR-019)
- [ ] `graph.json` no formato do graphify (FR-134)
- [ ] Filtros por tipo e por data (FR-135)
- [ ] Inspetor lê do SQLite + arquivo do vault
- [ ] Cores de nó = cores de coletor da tela de timeline
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_visualizador_do_grafo_da_mem_ria_fr_135/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Protótipo assume WebGL2; ADR-019 manda QML puro primeiro e QtWebEngine só se 10k nós a 60 fps falhar.
- Botão 3D fica desabilitado no 1.0.
