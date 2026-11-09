# Tela: Central de Comando HERO — overlay (versão anterior)

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_central_de_comando_hero_overlay` |
| Protótipo | `docs/telas/forjaos_central_de_comando_hero_overlay/code.html` (sha256 `6ab07829474c`) · `screen.png` |
| Requisitos | FR-121, FR-103 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | Referência secundária. Usar **só** para animação do waveform, chip 'Audio In (PipeWire)' e rótulos já corretos (Guará/forja). Layout canônico = `forjaos_central_de_comando_hero_corrigida` |
| Pasta do monorepo | hero/overlay |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Waveform | 8 barras, largura 4 px, altura 6→26 px, período 1,2 s, atraso 0,15 s entre barras, cor `accent-cyan` | FR-121 |
| Chip de áudio | 'Audio In (PipeWire): <nó>' `label-xs` muted sob a frase ouvida | ADR-015 |
| Chip do modelo | 'Qwen3 8B · 100 % local' `label-sm` ciano no card do assistente | ADR-013 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `devos` | 1 | forja (CLI), forja-term (terminal) | ADR-020, FR-035, FR-060 |
| `rodrigo@` | 3 | usuario@forjaos ($USER@forjaos) | FR-003 |
| `nftables` | 1 | firewalld | ADR-022 |
| `RTX 4070` | 1 | RTX 5060 8 GB (desktop de referência) | §10.2 |
| `GameMode` | 1 | Modo Jogo (hero-game.target) | FR-043 |
| `Escudo ativo` | 1 | indicador só se `forja install escudo` executado | ADR-023, NFR-027 |
| `Zero Cloud Leaks` | 1 | '100 % local' | NFR-031 |
| `rodrigo@forja` | 3 | usuario@forjaos | FR-003 |
| `pty/3` | 1 | remover | — |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

Sem ícones Material no protótipo. Ícones necessários na implementação vêm de Breeze ou `brand/icons/` e devem ser listados aqui antes do gate *plan*.

## Checklist de fidelidade

- [ ] Não implementar esta tela isoladamente — entregar via spec `corrigida`
- [ ] Waveform com os parâmetros acima (`motion.wave_bar_ms`)
- [ ] Nenhuma string 'Escudo ativo' sem Escudo
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_central_de_comando_hero_overlay/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Versão anterior do overlay. Não implementar isoladamente; a spec canônica é `forjaos_central_de_comando_hero_corrigida`.
