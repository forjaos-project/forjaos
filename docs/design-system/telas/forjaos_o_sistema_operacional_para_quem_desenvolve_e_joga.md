# Tela: Landing page — 'O sistema operacional para quem desenvolve e joga'

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_o_sistema_operacional_para_quem_desenvolve_e_joga` |
| Protótipo | `docs/telas/forjaos_o_sistema_operacional_para_quem_desenvolve_e_joga/code.html` (sha256 `726b691ecb30`) · `screen.png` |
| Requisitos | G1, NFR-043, NFR-033 |
| Tema | light (Alabaster Forge) |
| Tecnologia-alvo | Landing page (Astro) em `site/landing`; mesma base de tokens/CSS do site de docs |
| Pasta do monorepo | site/landing |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Header | igual ao das docs (64 px) com nav: Recursos, HERO AI & Guará, Stack Dev & Jogos, Arquitetura Atomic, Documentação, GitHub; CTA 'Baixar ISO' primário | G1 |
| Hero | 2 colunas: título `text-[64px]`→ usar `display-lg` escalado (56–64 px) 'O Linux onde você projeta · constrói · joga' com palavras em `primary`; parágrafo `body-lg`; 2 botões (Baixar ISO primário 48 px + tamanho; Ver no GitHub secundário); linha de comando copiável `code-md`; direita: mockup do desktop em card raio 16 sombra L3 (imagem estática, não iframe) | G1 |
| Faixa de métricas | 3 cards: Guará ouvindo / VRAM local / latência — **só números reais ou remover** | NFR-033 |
| Seções de recurso | alternadas texto/imagem; eyebrow `label-sm` + `display-sm` + `body-md`; chips de tecnologia 22 px | G1 |
| Tabela comparativa | 'Recurso' × ForjaOS / Ubuntu / Arch / Windows+WSL2; células com ✓/✗ coloridas; cabeçalho sticky; claims só com fonte verificável | G1 |
| CTA final + rodapé | banner `primary-container` com botão branco; rodapé 3 colunas links + licença Apache-2.0 + CC BY-SA 4.0 artes | ADR-007 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `24.04` | 12 | versão AAAA.MM.DD (imagem) / vX.Y.Z (release) | NFR-044 |
| `ghcr.io/forjaos/forjaos-nvidia:24.04` | 1 | ghcr.io/<org>/forjaos-nvidia-open:stable | FR-001 |
| `ghcr.io/forjaos/nvidia:stable` | 2 | ghcr.io/<org>/forjaos-nvidia-open:stable | FR-001 |
| `Kernel 6.9-cachyos-scx` | 1 | kernel Bazzite | ADR-001 |
| `RTX 4080` | 1 | RTX 5060 8 GB | §10.2 |
| `4.8k` | 1 | contagem real do GitHub ou omitir | NFR-033 |
| `3.4k` | 1 | contagem real do GitHub ou omitir | NFR-033 |
| `universal-blue 24.04` | 1 | tag da imagem corrente | NFR-044 |
| `NVIDIA Driver 555` | 1 | driver vem da base; sem número fixo | ADR-001 |
| `GPG` | 1 | assinatura de commit opcional; não prometida pelo PRD | FR-031 |
| `ISO 24.04 LTS` | 2 | ISO vX.Y.Z | NFR-044 |
| `5.8 GB` | 2 | tamanho real (≤ 6 GB, NFR-011) | NFR-011 |
| `NVIDIA Driver 555.58.02` | 1 | driver vem da base; sem número fixo | ADR-001 |
| `GPU RTX 4080` | 1 | RTX 5060 8 GB | §10.2 |
| `★ 3.4k` | 1 | contagem real do GitHub ou omitir | NFR-033 |
| `forja-user@workstation` | 1 | usuario@forjaos | FR-003 |
| `Dolphin Dev Edition` | 1 | só se ADR aprovar a tela do explorer | — |
| `Benchmark de Eficiência` | 1 | só com medições reais publicadas em docs/releases/ | G2 |
| `Menos de 15 minutos` | 1 | manter — é a meta G1 (dizer 'meta') | G1 |
| `Tour Rápido (3 min)` | 1 | só quando houver vídeo | — |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

| Material Symbol | Breeze / próprio |
| --- | --- |
| `bolt` | `próprio: hero-spark` |
| `check_circle` | `dialog-ok-apply` |
| `close` | `window-close` |
| `download` | `download` |
| `folder_special` | `folder-favorites` |
| `forum` | `view-conversation-balloon` |
| `graphic_eq` | `próprio: waveform` |
| `history` | `view-history` |
| `hub` | `próprio: graph` |
| `inventory_2` | `package-x-generic` |
| `layers` | `layer-visible-on` |
| `lock_reset` | `view-refresh` |
| `memory` | `cpu` |
| `person` | `user-identity` |
| `play_circle` | `media-playback-start` |
| `restart_alt` | `system-reboot` |
| `smart_toy` | `próprio: mascote (estado)` |
| `space_dashboard` | `view-grid` |
| `sports_esports` | `input-gaming` |
| `star` | `rating` |
| `terminal` | `utilities-terminal` |
| `timer` | `chronometer` |
| `usb` | `drive-removable-media` |
| `verified` | `checkmark` |

## Checklist de fidelidade

- [ ] Nenhuma métrica inventada; cada número tem fonte em docs/releases/ (NFR-033)
- [ ] Download aponta para GitHub Release com SHA-256 (FR-010)
- [ ] Tokens light do palette; dark alternável
- [ ] Lighthouse ≥ 90 em acessibilidade
- [ ] pt-BR + en-US
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_o_sistema_operacional_para_quem_desenvolve_e_joga/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Tabela comparativa e métricas (★ 3.4k, 0.4ms, 3.8 GB VRAM) são ilustrativas: só publicar com medições em `docs/releases/` (NFR-033, G2).
- `24.04 LTS` aparece 12×; `Kernel 6.9-cachyos-scx` e `NVIDIA Driver 555` não são da base (ADR-001).
- Seção `Dolphin Dev Edition` depende do ADR do explorer.
