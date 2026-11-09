# Tela: Terminal Konsole dev + saída forja doctor / forja ai

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_terminal_konsole_dev_forja_doctor` |
| Protótipo | `docs/telas/forjaos_terminal_konsole_dev_forja_doctor/code.html` (sha256 `f9fc45ae8be1`) · `screen.png` |
| Requisitos | FR-035, FR-036, FR-061, FR-062 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | Konsole: `.colorscheme` + profile (fonte JetBrains Mono 13, zsh + starship); saída colorida do CLI `forja` (crate `cli/`) |
| Pasta do monorepo | brand/konsole + cli |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Sidebar de perfis (opcional) | 256 px (w-64) `layer-1`: perfis de sessão e workspaces — **não é padrão do Konsole**; fica como pendência (ver abaixo) | FR-035 |
| Barra de abas | 48 px: abas `code-md` com ícone 16 px; ativa com fundo `layer-3` + borda inferior ciano 2 px | FR-035 |
| Área do terminal | fundo `konsole-bg`; fonte `code-md` 13/18 JetBrains Mono; prompt starship: `usuario@forjaos in ~/proj/<repo> on main` com cores ciano (user), violeta (path), laranja (branch) | FR-035 |
| Saída `forja doctor` | cada item: ✓ `success` / ! `warning` / ✗ `danger` + descrição; seção 'Daemons: herod (PID) · memd (PID)'; 'Portas abertas: 0' ; sugestão final com comando em chip | FR-036, NFR-012 |
| Saída `forja ai` | '↳ roteando: local (ollama/qwen3:8b) · contexto: …' + resposta em caixa + '[s/N]' com botões textuais 'Sim [s] / Não [n]' | FR-061 |
| Painel auxiliar (split) | split inferior 256 px com `podman logs -f` em `code-sm`; cabeçalho 'Painel auxiliar' `label-xs` | FR-035 |
| Barra de status | 28 px: UTF-8, Ln/Col, RAM do Konsole, atalhos F4 split / Ctrl+Shift+F buscar / Super+Espaço HERO `label-xs` | FR-035 |
| Overlay à direita | igual à spec canônica do overlay (não duplicar aqui) | FR-121 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `Jarvis` | 1 | Guará (persona) / HERO (motor) | ADR-005, ADR-006 |
| `devos` | 9 | forja (CLI), forja-term (terminal) | ADR-020, FR-035, FR-060 |
| `rodrigo@` | 3 | usuario@forjaos ($USER@forjaos) | FR-003 |
| `nftables` | 2 | firewalld | ADR-022 |
| `6.12` | 1 | kernel Bazzite (sem número fixo) | ADR-001 |
| `RTX 4070` | 2 | RTX 5060 8 GB (desktop de referência) | §10.2 |
| `GameMode` | 1 | Modo Jogo (hero-game.target) | FR-043 |
| `Feral` | 1 | remover — Modo Jogo é hero-game.target, não Feral GameMode | FR-043 |
| `TPM2` | 2 | KWallet (TPM2 não é requisito do PRD; só se ADR futuro aprovar) | FR-023, NFR-024 |
| `claude-sonnet` | 1 | Claude Code (API) | FR-005 |
| `Atuin Cloud Sync` | 1 | atuin local (sync é opt-in do usuário) | FR-132, NFR-033 |
| `DevOS` | 3 | ForjaOS | ADR-031 |
| `claude-daemon` | 1 | claude (aba) | — |
| `codex-engine` | 1 | codex (aba) | — |
| `ollama-core` | 1 | ollama (aba) | — |
| `forja-engine` | 1 | remover | — |
| `feat/cyber-term` | 1 | branch real | — |
| `Feral Activo` | 1 | remover — Modo Jogo é hero-game.target, não Feral GameMode | FR-043 |
| `nftables drop` | 1 | firewalld · zona public | ADR-022 |
| `Blindagem Ativa` | 1 | só com Escudo | ADR-023 |
| `TPM2 KWallet` | 2 | KWallet | FR-023 |
| `Fish Shell / Alacritty` | — | zsh / Konsole | FR-035 |
| `Konsole v6.2.4` | — | versão da base | — |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

| Material Symbol | Breeze / próprio |
| --- | --- |
| `add` | `list-add` |
| `bluetooth` | `network-bluetooth` |
| `check` | `checkmark` |
| `check_circle` | `dialog-ok-apply` |
| `code` | `text-x-script` |
| `commit` | `vcs-commit` |
| `do_not_disturb_on` | `notifications-disabled` |
| `drag_handle` | `transform-move` |
| `expand_more` | `go-down` |
| `folder` | `folder` |
| `fork_right` | `vcs-branch` |
| `fullscreen` | `view-fullscreen` |
| `graphic_eq` | `próprio: waveform` |
| `hub` | `próprio: graph` |
| `insights` | `office-chart-line` |
| `memory` | `cpu` |
| `mic` | `audio-input-microphone` |
| `neurology` | `próprio: hero-ai` |
| `person` | `user-identity` |
| `play_arrow` | `media-playback-start` |
| `psychology` | `próprio: hero-thinking` |
| `public` | `internet-web-browser` |
| `schedule` | `chronometer` |
| `security` | `security-high` |
| `shield` | `security-high` |
| `smart_toy` | `próprio: mascote (estado)` |
| `speed` | `speedometer` |
| `splitscreen` | `view-split-left-right` |
| `sports_esports` | `input-gaming` |
| `sync_alt` | `view-refresh` |
| `terminal` | `utilities-terminal` |
| `text_fields` | `format-text-bold` |
| `tune` | `configure` |
| `verified_user` | `security-high` |
| `view_in_ar` | `próprio: 3d` |
| `view_quilt` | `view-grid` |
| `view_stream` | `view-list-tree` |
| `vpn_key` | `network-vpn` |
| `warning` | `dialog-warning` |
| `wifi` | `network-wireless` |

## Checklist de fidelidade

- [ ] `.colorscheme` gerado do palette: Background=`konsole-bg`, Foreground=`on-surface`, Color0–7 mapeados (DESIGN-RULES §4)
- [ ] Profile: JetBrains Mono 13, zsh, starship, atuin, zoxide, fzf (FR-035)
- [ ] `forja doctor` sai com código ≠ 0 se item crítico falha (FR-036)
- [ ] `--json` em todos os subcomandos (FR-062)
- [ ] Confirmação `[s/N]` antes de tier alterar (FR-061)
- [ ] Sem Inter em texto de terminal
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_terminal_konsole_dev_forja_doctor/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Sidebar de perfis/workspaces à esquerda não é funcionalidade do Konsole; fica fora do 1.0 ou vira plugin próprio por ADR.
- `Atuin Cloud Sync` e `TPM2` não estão no PRD; atuin é local (FR-132) e chaves ficam no KWallet (FR-023).
- `nftables strict/drop` → firewalld zona public (ADR-022).
