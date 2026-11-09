# Tela: Wizard de primeiro boot — passo 6 (resumo e conclusão)

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_wizard_de_primeiro_boot_passo_6_resumo_conclus_o` |
| Protótipo | `docs/telas/forjaos_wizard_de_primeiro_boot_passo_6_resumo_conclus_o/code.html` (sha256 `c7f78715ceb8`) · `screen.png` |
| Requisitos | FR-020, FR-024 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | Último passo do wizard QML: resumo das escolhas + progresso da instalação em segundo plano |
| Pasta do monorepo | image/firstboot |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Cabeçalho e trilho | iguais ao passo 1–5; passo 6 ativo 'Concluir' | FR-020 |
| Grid de resumo | cards 2 colunas gap 12: Mascote (nome, wake word, TTS, LLM), Perfil (nome + chips de pacotes), Agentes & inferência, Cofre de credenciais (GitHub @user, KWallet), Base imutável (imagem + SELinux); cada card `layer-1` raio 8 padding 16, título `label-sm` uppercase, valor `body-md` | FR-020 |
| Reproduzir via CLI | card com comando `code-md` em caixa `layer-3` + botão 'Copiar' | FR-024 |
| Progresso | card: título 'Provisionando camada de usuário', barra 8 px ciano→violeta com %, 'Fase N/5', 'N de M etapas', taxa e tempo restante em 3 colunas `code-md` tabular | FR-020 |
| Log ao vivo | caixa 256 px (max-h-64) `konsole-bg` `code-sm`: linhas [✓]/[RUNNING]/[PENDING] coloridas; link 'Ver logs (journalctl -f)' | FR-020 |
| Rodapé | aviso 'Não desligue o computador' `body-sm` `warning`; botão 'Finalizar e entrar no desktop' primário 40 px (habilita ao concluir ou permite continuar em segundo plano) | FR-020 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `Fedora Atomic 41` | 1 | base Universal Blue (sem versão Fedora exposta) | FR-002, G4 |
| `TPM2` | 5 | KWallet (TPM2 não é requisito do PRD; só se ADR futuro aprovar) | FR-023, NFR-024 |
| `Hermes Engine` | 1 | Hermes Agent | FR-005 |
| `local-copilot` | 1 | remover — não existe no PRD | FR-005 |
| `PCR-7` | 1 | remover | FR-023 |
| `--voice fabiola --autostart --seal` | 1 | flags reais do `forja setup` (ver FR-060); `--seal` não existe | FR-024, FR-060 |
| `Fedora Atomic 41 • NVIDIA Open Kernel 590.28` | 1 | 'base Universal Blue · NVIDIA open · SELinux enforcing · zram' | FR-002 |
| `ZRAM 8GB lz4` | 1 | zram (tamanho detectado) · zstd | FR-036 |
| `ghcr.io/forjaos-nvidia-open:stable` | 1 | ghcr.io/<org>/forjaos-nvidia-open:stable | FR-001 |
| `TensorRT` | 1 | ONNX Runtime CPU (openWakeWord) | ADR-012 |
| `systemd-sysupdate` | 1 | remover — bootc gerencia deploy | ADR-002 |
| `sys-finalize --atomic-commit` | 1 | remover — comando inexistente | — |
| `Blender 4.2 LTS` | 2 | Blender (Flatpak, versão corrente) | FR-005 |
| `@rodrigo-forja` | 1 | @<usuário gh> | FR-031 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

| Material Symbol | Breeze / próprio |
| --- | --- |
| `check` | `checkmark` |
| `content_copy` | `edit-copy` |
| `key` | `dialog-password` |
| `lock` | `object-locked` |
| `memory` | `cpu` |
| `neurology` | `próprio: hero-ai` |
| `pets` | `próprio: mascote` |
| `receipt_long` | `view-list-text` |
| `rocket_launch` | `próprio: launch` |
| `sports_esports` | `input-gaming` |
| `terminal` | `utilities-terminal` |
| `tune` | `configure` |
| `verified_user` | `security-high` |

## Checklist de fidelidade

- [ ] Com rede: instala em segundo plano e permite entrar no desktop (FR-020)
- [ ] Resumo bate 1:1 com as escolhas dos passos 2–5
- [ ] Comando CLI gerado é executável e reproduz o estado (FR-024)
- [ ] Log vem do journald do serviço de pós-instalação
- [ ] Nenhuma menção a Fedora/versão da base (FR-002)
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_wizard_de_primeiro_boot_passo_6_resumo_conclus_o/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Flags `--voice --autostart --seal` não existem no `forja setup` do PRD (FR-024/FR-060); gerar só flags reais.
- Log cita `systemd-sysupdate`, `TensorRT`, `PCR-7`, `Fedora Atomic 41`: nada disso é da arquitetura (ADR-002, ADR-012, FR-002).
