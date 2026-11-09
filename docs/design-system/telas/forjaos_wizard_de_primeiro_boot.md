# Tela: Wizard de primeiro boot — passos 1–5 (foco: passo 2 Mascote & Voz)

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_wizard_de_primeiro_boot` |
| Protótipo | `docs/telas/forjaos_wizard_de_primeiro_boot/code.html` (sha256 `e85c11734b68`) · `screen.png` |
| Requisitos | FR-020, FR-021, FR-022, FR-023, FR-024 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | Wizard QML tela cheia (Kirigami), pulável, 6 passos; roda sem rede |
| Pasta do monorepo | image/firstboot |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Cabeçalho | 64 px: 'ForjaOS Setup' `headline-sm` + chip 'Primeiro boot' `label-xs`; direita: chips de status (Plasma 6 Wayland, Ollama online, KWallet ativo) | FR-020 |
| Trilho de passos | coluna esquerda 288 px (w-72): 6 itens 56 px, número em círculo 32 px, título `body-md` 600, subtítulo `code-sm` muted; ativo com borda esquerda 2 px ciano e fundo `layer-2`; concluído com ✓ verde | FR-020 |
| Painel do passo (Mascote) | título `headline-lg` + FR; grid de 8 cartões de nome 2×4 (Guará, Tupã, Jaci, Iara, Ipê, Boto, Curió, Arara) 140×96 px raio 12, selecionado com borda ciano + glow; cartão '+ Nome personalizado' tracejado | FR-021 |
| Voz | combobox de vozes Piper pt-BR (2–3) + botão 'Ouvir amostra' 36 px fantasma; slider 'Sensibilidade da wake word' com valor % | FR-021, FR-080 |
| Painel do passo (Perfil) | cards de perfil 2 colunas: web, backend, gamedev, devops, IA + link 'Modo mínimo'; cada card: ícone 24, título `headline-sm`, stack `code-sm`, descrição `body-sm`, chips de pacotes 22 px; toggle 'Ativo' | FR-022 |
| Painel do passo (Contas) | 2 linhas: 'GitHub CLI login (gh auth login)' com botão; 'Chaves de IA (Anthropic/OpenAI/OpenRouter/Nous)' com status 'KWallet'; nota de segurança `body-sm` em card `warning` 10 % | FR-023 |
| Rodapé | 72 px: 'Voltar' fantasma; centro: comando equivalente `code-sm` 'forja setup --profile gamedev --mascot guara' com copiar; 'Pular wizard' link; 'Avançar' primário 40 px | FR-024 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `TPM2` | 2 | KWallet (TPM2 não é requisito do PRD; só se ADR futuro aprovar) | FR-023, NFR-024 |
| `forja-train` | 1 | `forja mascot train` | FR-082 |
| `Qwen 8B` | 1 | Qwen3 8B Q4 (Ollama) | ADR-013 |
| `treinar via forja-train CLI` | 1 | `forja mascot train "<nome>"` | FR-082 |
| `KWallet TPM2 Active` | 1 | KWallet ativo | FR-023 |
| `Fabíola (Neural pt-BR)` | 1 | voz Piper pt-BR embarcada (nome real, licença verificada) | ADR-011 |
| `Godot 4.3` | 1 | Godot 4 (Flatpak Flathub, versão corrente) | FR-041 |
| `Go 1.23` | 1 | Go (versão corrente) | FR-022 |
| `Vite / Next` | 1 | remover — não listado no perfil web do PRD | FR-022 |
| `Tailwind CLI` | 1 | remover | FR-022 |
| `PyTorch ROCm/CUDA` | 1 | remover — perfil IA do PRD: Ollama, Hermes, Codex, Claude Code, Jupyter | FR-022 |
| `Aseprite` | 1 | só se licença (FR-022) | FR-022 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

| Material Symbol | Breeze / próprio |
| --- | --- |
| `add_circle` | `list-add` |
| `arrow_back` | `go-previous` |
| `arrow_forward` | `go-next` |
| `check` | `checkmark` |
| `code` | `text-x-script` |
| `database` | `server-database` |
| `key` | `dialog-password` |
| `layers` | `layer-visible-on` |
| `lock` | `object-locked` |
| `memory` | `cpu` |
| `play_arrow` | `media-playback-start` |
| `psychology` | `próprio: hero-thinking` |
| `shield` | `security-high` |
| `sports_esports` | `input-gaming` |
| `terminal` | `utilities-terminal` |

## Checklist de fidelidade

- [ ] Completa em < 5 min sem rede (FR-020)
- [ ] Seleção grava `~/.config/hero/persona.toml` (FR-021)
- [ ] Nome personalizado dispara treino em segundo plano, Guará ativo até ficar pronto (FR-082)
- [ ] Chaves só no KWallet via `secret-tool`; grep de dotfiles no CI (FR-023)
- [ ] Tudo reproduzível por `forja setup --profile X --mascot Y` (FR-024)
- [ ] Navegável por teclado, contraste AA (NFR-050)
- [ ] Perfis = exatamente os 6 do FR-022
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_wizard_de_primeiro_boot/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Lista de pacotes por perfil no protótipo difere do FR-022 (Vite/Next, Tailwind CLI, PyTorch, Vulkan SDK não constam); vale o FR-022.
- `TPM2` em KWallet não é requisito; remover menção.
- Vozes Piper nomeadas no protótipo (Fabíola) precisam de licença verificada voz a voz (ADR-011).
