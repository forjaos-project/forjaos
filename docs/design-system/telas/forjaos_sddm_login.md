# Tela: SDDM Login

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_sddm_login` |
| Protótipo | `docs/telas/forjaos_sddm_login/code.html` (sha256 `035648977fcf`) · `screen.png` |
| Requisitos | FR-057, FR-002 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | Tema SDDM em QML (Qt6) com wallpaper escuro, campo único, avatar, logo discreto |
| Pasta do monorepo | brand/sddm |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Fundo | wallpaper oficial escuro (FR-055) com overlay `canvas` 60 % + blur 24 px | FR-057 |
| Barra superior | 40 px: logo 24 px + 'FORJA OS' `label-md`; direita: 'KDE Plasma 6 · Wayland', relógio `code-md`, Wi-Fi, bateria `label-xs` | FR-057 |
| Relógio | centro-superior: hora `display-lg` 700 tabular + data por extenso `body-md` muted | FR-057 |
| Card de login | centralizado, largura 448 px (max-w-md), raio 24 px (rounded-3xl → usar 16 px `radius.xl` do palette), `layer-2` 0,85 + blur; avatar 96 px círculo com anel ciano 2 px; nome `headline-md`; `usuario@forjaos` `code-sm` muted; campo de senha único 48 px raio 8 fundo `layer-3` borda `border-ghost` → foco `border-active`; botão olho à direita | FR-057 |
| Alternativas | linha de chips 22 px: 'FIDO2', 'Biometria', 'Outro usuário' `label-sm` — exibir só os métodos realmente configurados no PAM | FR-057 |
| Rodapé do card | 'Layout: ABNT2 (pt-BR)' e 'Sessão: Wayland' `label-xs`; combobox de sessão | FR-057 |
| Ações de energia | 3 botões fantasma 40 px (Suspender, Reiniciar, Desligar) `label-sm` no rodapé da tela | FR-057 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `devos` | 1 | forja (CLI), forja-term (terminal) | ADR-020, FR-035, FR-060 |
| `rodrigo@` | 1 | usuario@forjaos ($USER@forjaos) | FR-003 |
| `Modo Desenvolvedor` | 1 | remover — não existe esse modo no PRD | FR-057 |
| `NVIDIA PRIME Offload Ativo` | 1 | remover do login (informação técnica demais) | FR-057 |
| `Full-Stack / Gamedev` | 1 | remover — subtítulo de perfil não existe no SDDM | FR-057 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

Sem ícones Material no protótipo. Ícones necessários na implementação vêm de Breeze ou `brand/icons/` e devem ser listados aqui antes do gate *plan*.

## Checklist de fidelidade

- [ ] Campo único de senha, foco inicial no campo (FR-057)
- [ ] Avatar do usuário vem do AccountsService
- [ ] Raio do card = `radius.xl` (16 px), não 24 px
- [ ] Sem Fira Code; relógio em Plus Jakarta Sans tabular
- [ ] Tema aplicado por padrão em `/etc/sddm.conf.d/`
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_sddm_login/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Chips FIDO2/Biometria aparecem no protótipo sem o PRD prever autenticação alternativa; exibir só se PAM configurado pelo usuário.
- Protótipo usa Fira Code (ADR-027 proíbe).
