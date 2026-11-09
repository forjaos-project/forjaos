# Tela: {nome}

| Campo | Valor |
| --- | --- |
| Slug | `{slug}` |
| Protótipo | `docs/telas/{slug}/code.html` (sha256 `{sha}`) · `screen.png` |
| Requisitos | {fr} |
| Tema | {tema_label} |
| Tecnologia-alvo | {alvo} |
| Pasta do monorepo | {pasta} |
| Status | {status} |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
{regioes}

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
{subst}

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

{icones}

## Checklist de fidelidade

{checklist}
- [ ] Captura lado a lado em `docs/design-system/telas/{slug}/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

{pendencias}
