# Tela: Plasmoid do Guará (barra + popup)

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_plasmoid_do_guar_kde_plasma_6` |
| Protótipo | `docs/telas/forjaos_plasmoid_do_guar_kde_plasma_6/code.html` (sha256 `62976ac0e58b`) · `screen.png` |
| Requisitos | FR-120, FR-123, FR-054, FR-071, FR-076 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | Plasmoid QML (`org.forjaos.hero`) para o painel do Plasma 6 + popup; menu de contexto nativo |
| Pasta do monorepo | hero/plasmoid |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Ícone na barra | mascote em miniatura 24 px + anel de estado 2 px na cor do estado (`mascot.state_colors`); label opcional 'ESCUTANDO' `label-xs` | FR-120, FR-071 |
| Popup | largura 384 px (w-96 ≈ 24 rem) → usar 384 px; raio 12; `layer-2` + blur; cabeçalho: mascote 56 px (h-14) + nome `headline-sm` + 'HERO ATIVO · herod (PID)' `label-xs` | FR-120 |
| Transcrição | card `layer-1` raio 8: 'Entrada de voz transcrita' `label-xs` + latência; frase `body-md` entre aspas; ação executada `code-sm` + chip de tier | FR-103 |
| Comando rápido | input 40 px `code-md` + botão 'Enviar' primário 36 px | FR-085 |
| Toggles | 4 linhas 36 px: Mic ativo (Super+M), Wake word ('Ei, Guará'), Modo Jogo, Ver memória do dia (N eventos); switch 36×20 raio full | FR-076, FR-043 |
| Menu de contexto | itens nativos: Abrir Central de Comando (Super+Espaço), Mutar microfone, Abrir visualizador de memória, Ativar Modo Jogo (Super+G), Desligar HERO (kill switch) | FR-120, FR-076 |
| Estados do mascote | 5 estados com cor de anel/glow: idle muted, listening ciano, thinking violeta (auréola orbital), speaking laranja (visemes + ondas laterais), error `danger` (glitch X) | FR-054, FR-123 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `RTX 4070` | 1 | RTX 5060 8 GB (desktop de referência) | §10.2 |
| `Polkit` | 1 | Policy Engine (tiers livre/alterar/bloqueado) | FR-100 |
| `Tier 1` | 2 | tier `livre` / `alterar` / `bloqueado` (nomes do PRD) | FR-100 |
| `Tier 1 · OK` | 1 | tier `livre` · ok | FR-100 |
| `Piper Fabíola` | 1 | voz Piper pt-BR com licença verificada (nome real da voz embarcada) | ADR-011 |
| `RTX 4070 · 46°C` | 1 | GPU detectada | FR-036 |
| `fur eyes spark mouth` | — | camadas `body ears eyes mouth glow badge` (palette › mascot.svg_layers) | FR-054 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

Sem ícones Material no protótipo. Ícones necessários na implementação vêm de Breeze ou `brand/icons/` e devem ser listados aqui antes do gate *plan*.

## Checklist de fidelidade

- [ ] 60 fps na animação sem rasterização por frame (FR-123)
- [ ] Indicador permanente de microfone + AuditEvent ao mutar (FR-076)
- [ ] Estados seguem sinal D-Bus `StateChanged` (FR-071)
- [ ] Popup ≤ 384 px; fecha ao perder foco
- [ ] Lip-sync por `VisemeEvent[]` (FR-084)
- [ ] Sem Fira Code
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_plasmoid_do_guar_kde_plasma_6/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Protótipo menciona Polkit e Tier 1; o PRD usa Policy Engine com tiers livre/alterar/bloqueado (FR-100).
- Nomes de camadas SVG do protótipo (fur/eyes/spark/mouth) diferem do palette (body/ears/eyes/mouth/glow/badge); vale o palette.
- Protótipo usa Fira Code (ADR-027 proíbe).
