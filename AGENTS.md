# AGENTS.md — ForjaOS

Sistema operacional open source baseado em Linux (Fedora Atomic via Universal Blue, bootc) para desenvolvimento e jogos, com assistente local HERO (mascote Guará), Memória do sistema e CLI `forja`. Monorepo, equipe solo, Claude Code e Codex trabalham em paralelo. Texto em pt-BR; código, nomes de arquivo e commits em inglês.

## Como trabalhar

- O que falta: `TODO.md`. Pegue um item, faça, marque `[x]`, commite na `main` e siga para o próximo.
- Antes de dar push: `git pull --rebase origin main` (o outro agente pode ter mexido).
- Sem plano em arquivo, review, claim ou ADR. Registre uma decisão só se ela for difícil de lembrar depois, em uma linha no commit.
- PR só quando o remoto exigir: abra apenas depois de finalizar a implementação e marcar o item `[x]` no `TODO.md`. PR em rascunho é proibida.
- Entrega só está concluída após a PR ser mesclada na `main` e a issue correspondente estar fechada. Se o item não tiver issue, crie uma antes da PR. Não apresente trabalho parcial como tarefa concluída.
- Depois de mesclar a PR e fechar a issue, remova a imagem/instância Docker e o cache de build criados exclusivamente para o item, após salvar qualquer artefato exigido para entrega. Remova por referência/ID específicos; não use limpeza global nem toque em imagens base, containers, volumes ou caches compartilhados. Em seguida, execute TRIM (`fstrim -v /mnt/docker-desktop-disk`), pare o Docker Desktop, confirme que o VHDX está desanexado (`Get-VHD`), compacte-o (`Optimize-VHD -Mode Full`), reinicie o Docker e valide o espaço livre, os volumes e a saúde dos serviços.
- Build, ISO e testes rodam **local**. O GitHub guarda o código e recebe só a ISO final. Testes e validação em hardware ficam para o build final.

## Proteções (as únicas regras)

1. Nenhum segredo em arquivo, commit ou log. Chaves só no KWallet.
2. Nada destrutivo (`rm -rf`, `dd`, firewall, SELinux, `/etc`) sem confirmação do Rodrigo.
3. SSD do host Windows: antes de build/ISO/VM local, `powershell -NoProfile -File scripts/host/check-disk.ps1 -Mode Check`; não comece com menos de 160 GiB livres no C: (ADR-0037).

## Onde achar as coisas

| Preciso de… | Arquivo |
| --- | --- |
| Requisitos e arquitetura | `docs/PRD.md` |
| O que falta | `TODO.md` |
| Cores, fontes e medidas | `brand/palette.json` |
| Como uma tela deve ficar | `docs/design-system/DESIGN-RULES.md`, `docs/design-system/telas/<slug>.md` |
| Decisões já tomadas | `docs/adr/` |
| Regras específicas de uma pasta | `<pasta>/AGENTS.md` |

Pastas: `image/` (imagem bootc), `cli/` (`forja`), `hero/`, `hero-mcp/`, `hero-memory/`, `brand/`, `site/`, `docs/`, `scripts/`.
