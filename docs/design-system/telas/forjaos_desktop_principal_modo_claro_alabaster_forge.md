# Tela: Desktop principal (claro — Alabaster Forge)

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_desktop_principal_modo_claro_alabaster_forge` |
| Protótipo | `docs/telas/forjaos_desktop_principal_modo_claro_alabaster_forge/code.html` (sha256 `0122c347b27f`) · `screen.png` |
| Requisitos | FR-050, FR-052 |
| Tema | light (Alabaster Forge) |
| Tecnologia-alvo | Variante clara do look-and-feel Plasma 'Forja' + Konsole claro + overlay/plasmoid em tema claro |
| Pasta do monorepo | brand/plasma |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Barra superior | 44 px (h-11) → **padronizar em 40 px**; fundo `frosted` blur 12 px, hairline inferior `hairline`; esquerda: logo + 'Forja OS' `headline-sm` + badge de versão `label-sm` em `primary-fixed`; workspaces '1 · Dev / 2 · Web / 3 · GameEngine' chips 22 px; centro: busca 'Buscar apps, arquivos…' 320 px raio 8 `layer-2`; direita: chip 'Guará AI · Super+Espaço', layout PT-BR, relógio `code-md` | FR-052 |
| Janela Konsole clara | fundo `layer-1` (#ffffff), hairline `hairline`, sombra L3 quando focada; abas `code-md`; cabeçalho 'Forja Doctor' `headline-sm` + subtítulo `body-sm` muted; checks em cards 1 coluna com ícone 20 px à esquerda, título `body-md` 600, descrição `body-sm`, valor `code-sm` à direita | FR-036 |
| Painel lateral direito | 320 px (w-80) `layer-1` hairline raio 12: card HERO (estado, modelo carregado, contexto dev), telemetria (CPU/RAM/GPU/NVMe) com barras 6 px `accent-cyan`/`accent-indigo`/`accent-orange`, card do projeto | FR-121 |
| Dock inferior | mesma geometria do escuro: 64 px, 12 px da borda, raio 12, `frosted` + sombra L2; tooltip `body-sm` acima | FR-052 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `devos` | 2 | forja (CLI), forja-term (terminal) | ADR-020, FR-035, FR-060 |
| `rodrigo@` | 2 | usuario@forjaos ($USER@forjaos) | FR-003 |
| `24.04` | 2 | versão AAAA.MM.DD (imagem) / vX.Y.Z (release) | NFR-044 |
| `6.12` | 1 | kernel Bazzite (sem número fixo) | ADR-001 |
| `RTX 4070` | 2 | RTX 5060 8 GB (desktop de referência) | §10.2 |
| `KWin-scx` | 1 | KWin (Wayland) | ADR-003 |
| `Forja Package Store` | 1 | `forja install` (não há loja própria no 1.0) | §2.2 |
| `forja fix` | 1 | remover — subcomando não existe | FR-060 |
| `GPG` | 2 | assinatura de commit opcional; não prometida pelo PRD | FR-031 |
| `Forja Doctor v2.4` | 1 | `forja doctor` (versão do CLI real) | FR-036 |
| `CUDA 12.6` | 2 | versão detectada em runtime | FR-036 |
| `32 GB DDR5` | 1 | valor detectado | FR-036 |
| `Ter, 23 Abr` | 1 | data real | — |
| `game-api (Rust+Bevy)` | 1 | projeto real detectado | FR-112 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

| Material Symbol | Breeze / próprio |
| --- | --- |
| `add` | `list-add` |
| `auto_awesome` | `próprio: hero-spark` |
| `battery_charging_full` | `battery-full-charging` |
| `build_circle` | `run-build` |
| `check_circle` | `dialog-ok-apply` |
| `code` | `text-x-script` |
| `code_blocks` | `code-context` |
| `delete` | `edit-delete` |
| `deployed_code` | `package-x-generic` |
| `folder` | `folder` |
| `memory` | `cpu` |
| `mic` | `audio-input-microphone` |
| `more_vert` | `overflow-menu` |
| `notifications` | `notifications` |
| `public` | `internet-web-browser` |
| `search` | `search` |
| `settings` | `configure` |
| `smart_toy` | `próprio: mascote (estado)` |
| `speed` | `speedometer` |
| `split_scene` | `view-split-left-right` |
| `sports_esports` | `input-gaming` |
| `terminal` | `utilities-terminal` |
| `tune` | `configure` |
| `volume_up` | `audio-volume-high` |
| `warning` | `dialog-warning` |
| `wifi` | `network-wireless` |

## Checklist de fidelidade

- [ ] Alternância claro/escuro pelo atalho do sistema sem reinício (FR-050)
- [ ] Barra 40 px (não 44)
- [ ] Contraste AA de `text-muted` sobre `layer-1`
- [ ] Nenhuma cor fora do tema light do palette
- [ ] Sombra L3 só na janela focada
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_desktop_principal_modo_claro_alabaster_forge/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- (nenhuma registrada ainda — adicione aqui o que o protótipo mostra e o PRD não prevê; cada item vira issue antes de implementar)
