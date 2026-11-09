# Tela: Splash Plymouth

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_splash_plymouth` |
| Protótipo | `docs/telas/forjaos_splash_plymouth/code.html` (sha256 `dc28e188dcb0`) · `screen.png` |
| Requisitos | FR-056, FR-002 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | Tema Plymouth (script + PNG/SVG do logo); sem texto além do opcional de erro |
| Pasta do monorepo | brand/plymouth |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Fundo | `canvas` (#070a11) sólido; glow radial ciano/violeta 20 % no centro (gradiente, sem imagem pesada) | FR-056 |
| Logo | logo ForjaOS centralizado, 144–176 px (w-36/w-44); wordmark 'FORJA' + 'OS' em `display-sm`; descritor 'The DevOS' `label-sm` só em marketing — **não** no Plymouth do produto (ADR-004) | FR-053, FR-056 |
| Barra de progresso | largura 256 px (w-64), altura 4–6 px (h-1/h-1.5), raio full, trilho `layer-3`, preenchimento gradiente ciano→violeta | FR-056 |
| Rodapé | texto 'Pressione Esc para logs' `label-xs` muted a 32 px da base — opcional; o PRD pede 'sem texto', então fica **desligado por padrão** | FR-056 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `Iniciando módulos do kernel & daemon herod` | — | remover — Plymouth sem texto (FR-056) | FR-056 |
| `SELinux: enforcing` | 1 | remover do splash | FR-056 |
| `PipeWire Core OK` | 1 | remover do splash | FR-056 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

Sem ícones Material no protótipo. Ícones necessários na implementação vêm de Breeze ou `brand/icons/` e devem ser listados aqui antes do gate *plan*.

## Checklist de fidelidade

- [ ] Exibição extra ≤ 3 s medida com `systemd-analyze` (FR-056)
- [ ] Nenhum texto de status visível por padrão
- [ ] Logo renderiza a 1080p e 4K sem serrilhado (SVG → PNG em 2 tamanhos)
- [ ] Cores: só `canvas`, `accent-cyan`, `accent-violet`, `layer-3`
- [ ] Fonte do wordmark (se rasterizada) = Plus Jakarta Sans
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_splash_plymouth/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Protótipo mostra 3 linhas de status (kernel, SELinux, PipeWire); FR-056 pede splash sem texto. Decisão: sem texto; linhas só com Esc (modo verboso).
