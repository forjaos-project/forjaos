# Tela: Documentação técnica oficial (site de docs)

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_docs_documenta_o_t_cnica_oficial` |
| Protótipo | `docs/telas/forjaos_docs_documenta_o_t_cnica_oficial/code.html` (sha256 `3394666da984`) · `screen.png` |
| Requisitos | NFR-043, G1 |
| Tema | light (Alabaster Forge) |
| Tecnologia-alvo | Site de docs (Astro ou Hugo) em `site/docs`; o **mesmo layout** gera `docs/roadmap/index.html` (CSS estático) |
| Pasta do monorepo | site/docs |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Header fixo | 64 px (`dimensions.docs_header_height`); fundo `layer-1` 85 % + blur; sombra `0 1px 8px rgba(0,0,0,.04)`; logo 32 px + 'ForjaOS' `headline-sm` + badge de versão `label-sm` em `primary-fixed`; busca 'Pesquisar documentação…' 448 px com kbd `Cmd+K`→`Ctrl+K`; nav (Visão geral, CLI & Tools, Arquitetura, HERO AI, GitHub); toggle de tema; avatar 32 px | NFR-043 |
| Sidebar | 288 px (`dimensions.docs_sidebar_width`) fixa, `layer-1`, padding 16/24; grupos `label-sm` uppercase `outline`; itens `body-sm` 30 px raio 8, ativo `primary-container`/`on-primary-container` | NFR-043 |
| Container | max 1520 px, padding 24 px; breadcrumb `label-md` com chevrons | NFR-043 |
| Banner | raio 12 px `layer-1` padding 32, sombra sm; blobs `primary` 5 % e `secondary` 5 % blur 64; chips de status 22 px; título `display-lg` com palavra em `primary`; descrição `body-lg` max 48 rem; card de specs 320 px à direita `surface-container-low` | NFR-043 |
| Grid principal | 12 colunas: 9 conteúdo + 3 TOC sticky ('Nesta página' `label-sm` + lista `body-sm`; 'Recursos oficiais' links) | NFR-043 |
| Seções | marcador quadrado 10 px `primary` + `label-sm` uppercase + `display-sm`; cards 3 colunas raio 12 `layer-1` padding 24 com número em quadrado 40 px; blocos de código raio 8 `surface-container-low` com botão copiar + toast inferior direito `inverse-surface`; tabela de tiers com pills coloridas (livre ciano, alterar laranja, bloqueado vermelho) | NFR-043, FR-100 |
| Rodapé de navegação | '← Anterior' fantasma / 'Próximo →' primário 40 px | NFR-043 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `24.04` | 6 | versão AAAA.MM.DD (imagem) / vX.Y.Z (release) | NFR-044 |
| `arm64` | 1 | remover — só x86-64-v3 | §10.1 |
| `6.12` | 2 | kernel Bazzite (sem número fixo) | ADR-001 |
| `forja doctor --strict` | 1 | `forja doctor` (sem flag --strict no PRD) | FR-036 |
| `ghcr.io/forjaos/forjaos-nvidia:24.04` | 2 | ghcr.io/<org>/forjaos-nvidia-open:stable | FR-001 |
| `4.8k` | 1 | contagem real do GitHub ou omitir | NFR-033 |
| `Cmd+K` | 1 | Ctrl+K | — |
| `PRD 1.0 Alinhado` | 1 | badge com versão do PRD real | — |
| `x86_64 / arm64` | 1 | remover — só x86-64-v3 | §10.1 |
| `Escalonador eBPF scx_lavd` | 2 | só se a base entregar sched_ext; senão remover a página | ADR-001 |
| `sudo bootc switch ghcr.io/forjaos/forjaos-nvidia:24.04` | 2 | `sudo bootc switch ghcr.io/<org>/forjaos-nvidia-open:stable` | FR-001 |
| `Fedora Silverblue/Bazzite` | 1 | 'qualquer sistema bootc/Fedora Atomic' (sem marca na UI do produto; em docs pode citar como origem de rebase) | G4 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

| Material Symbol | Breeze / próprio |
| --- | --- |
| `arrow_back` | `go-previous` |
| `arrow_forward` | `go-next` |
| `check_circle` | `dialog-ok-apply` |
| `chevron_right` | `go-next` |
| `content_copy` | `edit-copy` |
| `description` | `text-x-generic` |
| `download` | `download` |
| `folder` | `folder` |
| `history` | `view-history` |
| `hub` | `próprio: graph` |
| `light_mode` | `weather-clear` |
| `menu_book` | `help-contents` |
| `open_in_new` | `window-new` |
| `person` | `user-identity` |
| `search` | `search` |
| `search_insights` | `edit-find` |
| `security` | `security-high` |
| `shield` | `security-high` |
| `sync` | `view-refresh` |
| `verified` | `checkmark` |

## Checklist de fidelidade

- [ ] Header 64 / sidebar 288 / container 1520 (palette › dimensions)
- [ ] Tema light = Alabaster Forge; dark alternável
- [ ] Navegação por teclado e contraste AA
- [ ] Sem Material Symbols **ou** conjunto único de ícones em todo o site (DESIGN-RULES §5)
- [ ] Blocos de código copiáveis com toast
- [ ] pt-BR e en-US (NFR-043, NFR-051)
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_docs_documenta_o_t_cnica_oficial/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Protótipo usa Tailwind CDN; o site compila CSS estático a partir do palette (sem CDN em runtime).
- Página `Escalonador eBPF scx_lavd` depende da base Universal Blue entregar sched_ext; confirmar antes de publicar.
- `24.04 LTS` aparece 6×: versionamento é AAAA.MM.DD / vX.Y.Z (NFR-044).
- `x86_64 / arm64` → só x86-64-v3 (§10.1).
