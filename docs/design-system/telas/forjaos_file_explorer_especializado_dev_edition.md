# Tela: Dolphin Dev Edition (explorador de arquivos)

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_file_explorer_especializado_dev_edition` |
| Protótipo | `docs/telas/forjaos_file_explorer_especializado_dev_edition/code.html` (sha256 `62efb70a8f82`) · `screen.png` |
| Requisitos | SEM FR — abrir ADR/issue antes de implementar |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | Dolphin (KDE) com: places customizados (Repositórios dev, Vault, Containers), service menus (Abrir no Code, Subir Compose, Perguntar ao HERO), colunas de status Git, painel de informações estendido. **Não** é fork do Dolphin |
| Pasta do monorepo | — (a definir por ADR; provável `image/system_files` + `hero-mcp`) |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Barra superior | igual DARK_TOPBAR; 'Guará · ESCUTANDO' no chip HERO | FR-052 |
| Toolbar do Dolphin | 48 px: voltar/avançar/acima, breadcrumb `proj › game-api › src` em chips, busca ⌘F → Ctrl+F | — |
| Painel Places | 260 px (w-[260px]) `layer-1`: grupos `label-xs` uppercase: FAVORITOS, REPOSITÓRIOS DEV ATIVOS (ícone + nome + branch `code-sm` + chip de status), MEMÓRIA DO SISTEMA (vault), CONTÊINERES & VOLUMES, DISCOS & REDE | FR-112, FR-131 |
| Lista | linhas 28 px (`dimensions.tree_row`); colunas Nome / Status Git · Tipo / Tamanho / Modificado; filtro 'Todos · Modificados (2) · Não rastreados (1)' em chips; ícone de tipo 20 px | — |
| Inspetor | 320 px (w-80) à direita: nome + chip tipo; prévia de código `code-sm` com destaque; metadados (MIME, permissões); último commit (hash em chip, mensagem, autor); 3 ações: Executar com Podman, Editar no VS Code, Perguntar ao HERO | FR-094 |
| Barra de status | 28 px: '8 arquivos, 3 diretórios · 1 selecionado · UTF-8 · YAML' | — |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `RTX 4070` | 1 | RTX 5060 8 GB (desktop de referência) | §10.2 |
| `Alacritty` | 2 | Konsole (terminal padrão) | FR-035 |
| `⌘F` | 1 | Ctrl+F | — |
| `Escudo Ativo` | 2 | indicador só se `forja install escudo` executado | ADR-023, NFR-027 |
| `DevLab NAS NFS` | 1 | montagens reais do usuário | — |
| `DATABASE_URL=postgres://root:secret@` | 1 | nunca exibir segredo em prévia; mascarar valores de env | NFR-024 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

| Material Symbol | Breeze / próprio |
| --- | --- |
| `add` | `list-add` |
| `arrow_back` | `go-previous` |
| `arrow_downward` | `go-down` |
| `arrow_forward` | `go-next` |
| `arrow_upward` | `go-up` |
| `bubble_chart` | `próprio: graph-nodes` |
| `cloud_done` | `cloud-upload` |
| `code` | `text-x-script` |
| `database` | `server-database` |
| `deployed_code` | `package-x-generic` |
| `description` | `text-x-generic` |
| `desktop_windows` | `computer` |
| `dns` | `network-server` |
| `download` | `download` |
| `expand_more` | `go-down` |
| `find_in_page` | `edit-find` |
| `folder` | `folder` |
| `folder_open` | `folder-open` |
| `format_list_bulleted` | `view-list-text` |
| `grid_view` | `view-list-icons` |
| `hard_drive` | `drive-harddisk` |
| `home` | `go-home` |
| `hub` | `próprio: graph` |
| `key` | `dialog-password` |
| `lock` | `object-locked` |
| `memory` | `cpu` |
| `play_arrow` | `media-playback-start` |
| `play_circle` | `media-playback-start` |
| `search` | `search` |
| `smart_toy` | `próprio: mascote (estado)` |
| `sticky_note_2` | `note` |
| `terminal` | `utilities-terminal` |
| `today` | `view-calendar-day` |
| `usb` | `drive-removable-media` |
| `verified_user` | `security-high` |
| `view_column` | `view-list-details` |

## Checklist de fidelidade

- [ ] **Bloqueado até ADR**: definir escopo (service menus + places + colunas) e FR novo
- [ ] Prévia de arquivos `.env*` sempre mascarada
- [ ] Linhas 28 px, places 260 px, inspetor 320 px
- [ ] Ações do inspetor passam pelo Policy Engine (tier alterar para 'Subir Compose')
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_file_explorer_especializado_dev_edition/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- **Sem FR no PRD.** Antes de qualquer implementação: ADR definindo escopo (places + service menus + colunas Git via Dolphin plugins, sem fork) e FR novo (sugestão: FR-037 em §6.4).
- Prévia do `docker-compose.yml` expõe `DATABASE_URL=postgres://root:secret@…` — toda prévia de env/segredo é mascarada (NFR-024).
- `Escudo Ativo` na barra só com Escudo instalado (ADR-023).
