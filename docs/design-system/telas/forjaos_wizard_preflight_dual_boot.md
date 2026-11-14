# Tela: Wizard de primeiro boot — aviso de dual boot e Secure Boot

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_wizard_preflight_dual_boot` |
| Protótipo | `docs/telas/forjaos_wizard_preflight_dual_boot/code.html` (sha256 `d475f8df78a1`) · `screen.png` |
| Requisitos | FR-011, FR-012, FR-013 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | Primeira tela QML de orientação antes do passo 1 do wizard; não particiona nem altera disco |
| Pasta do monorepo | image/firstboot |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Cabeçalho | 64 px: marca ForjaOS, `headline-sm` e contexto 'Configuração inicial · etapa de segurança'; selo de prévia só existe no protótipo | FR-020 |
| Trilho do wizard | 6 passos horizontais, cada item com altura 42 px; passo 1 ativo com fundo `layer-3` e borda esquerda 2 px `accent-cyan` | FR-020 |
| Painel Windows | coluna esquerda; título `headline-lg`; status detectado em `body-md`; três cards `layer-1` com aviso sobre Inicialização Rápida/NTFS somente leitura, recuperação BitLocker e confirmação manual do disco no Anaconda | FR-011, FR-013 |
| Painel Secure Boot | coluna direita; card `layer-1`; estado real de Secure Boot; três passos `code-sm` para `Enroll MOK`, confirmar chave Universal Blue e reiniciar | FR-012, NFR-022 |
| Rodapé | 64 px: texto de revisão de disco e botão primário 42 px 'Continuar para idioma e teclado'; nenhuma ação de particionamento | FR-011, FR-020 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `—` | 0 | nenhuma substituição global encontrada; conferir textos manualmente | ADR-028 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

Sem ícones Material no protótipo. Ícones necessários na implementação vêm de Breeze ou `brand/icons/` e devem ser listados aqui antes do gate *plan*.

## Checklist de fidelidade

- [ ] Estados de Windows e Secure Boot vêm do sistema; a prévia marca dados ilustrativos
- [ ] Avisos em pt-BR citam BitLocker, Inicialização Rápida, NTFS somente leitura e MOK
- [ ] Botão apenas avança o wizard; nenhuma alteração de disco
- [ ] Tamanho mínimo 960×720 sem corte
- [ ] Cores e fontes usam tokens de `brand/palette.json`
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_wizard_preflight_dual_boot/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Estados de Windows e Secure Boot no protótipo são exemplos ilustrativos; a implementação só pode mostrar estados detectados.
