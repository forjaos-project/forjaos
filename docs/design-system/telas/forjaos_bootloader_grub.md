# Tela: Bootloader GRUB

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_bootloader_grub` |
| Protótipo | `docs/telas/forjaos_bootloader_grub/code.html` (sha256 `ba9f787360f5`) · `screen.png` |
| Requisitos | FR-002, FR-008, FR-011 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | GRUB theme (`theme.txt`, fontes PF2 geradas de Plus Jakarta Sans/JetBrains Mono, PNGs de borda) |
| Pasta do monorepo | brand/grub |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Fundo | o quase-preto do protótipo vira `void` (#0a0d14), com wallpaper desfocado a 20 % opcional; scanlines **não** (efeito de protótipo, custo zero de valor) | FR-002 |
| Cabeçalho | faixa 72 px: logo 32 px + 'FORJA OS' `headline-sm`; direita: 'UEFI x86-64 · Secure Boot' `label-xs` muted | FR-012 |
| Lista de entradas | cards 100 % largura, padding 20 px, raio 12 px, gap 12 px; entrada ativa com borda esquerda 3 px ciano e gradiente ciano→violeta 12 %; título `headline-sm`, subtítulo `code-sm` muted (commit bootc, kernel); tecla de atalho em chip `label-xs` à direita | FR-008 |
| Entradas | 1) ForjaOS <versão> (stable · padrão) 2) ForjaOS rollback anterior (commit) 3) Windows Boot Manager (dual boot) 4) Modo de resgate | FR-008, FR-011 |
| Contador | 'Boot automático em: Ns' `code-md` ciano, canto superior direito do painel | FR-008 |
| Rodapé | legenda de teclas ↑/↓ Enter e Esc `label-xs`; sem URL de site no GRUB | FR-002 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `6.12` | 1 | kernel Bazzite (sem número fixo) | ADR-001 |
| `Fedora Atomic 41` | 1 | base Universal Blue (sem versão Fedora exposta) | FR-002, G4 |
| `NVIDIA Open 590` | 1 | driver NVIDIA open (versão vem da base) | ADR-001 |
| `Linux 6.12.8-bazzite` | 1 | kernel Bazzite (número vem do boot) | ADR-001 |
| `forja.dev` | 1 | remover até domínio registrado (risco §15) | §15 |
| `MemTest86+` | 1 | só se o pacote estiver na imagem | FR-005 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

Sem ícones Material no protótipo. Ícones necessários na implementação vêm de Breeze ou `brand/icons/` e devem ser listados aqui antes do gate *plan*.

## Checklist de fidelidade

- [ ] Nenhuma string 'Fedora'/'Bazzite' visível (check-branding.sh)
- [ ] Windows listado quando detectado (FR-011)
- [ ] Entrada de rollback aponta para deployment anterior do bootc
- [ ] Fontes PF2 geradas do palette (ui + mono)
- [ ] Cores só do palette (GRUB aceita só opaco → tokens `*-flat`)
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_bootloader_grub/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Efeito scanlines/CRT do protótipo não será implementado (sem valor funcional, custo de legibilidade).
- GRUB não renderiza blur/translucidez: fundo sólido `void` com wallpaper opcional a 20 %.
