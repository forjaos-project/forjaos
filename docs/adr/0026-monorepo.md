# ADR-026 — Monorepo em `forjaos-project/forjaos`

**Status:** aceito · **Data:** 2026-11-08 · **Revoga:** PRD §5.2 (tabela de 7 repositórios) · **Relacionados:** ADR-009 (equipe solo)

## Contexto

O PRD 1.0 §5.2 prevê sete repositórios (`forjaos-image`, `forja-cli`, `hero`, `hero-mcp`, `hero-memory`, `forjaos-brand`, `forjaos-site`), cada um com CI, release e ADRs próprios. A equipe é uma pessoa a 15–20 h/semana (ADR-009). Sete repositórios significam sete pipelines, sete fluxos de release, versionamento cruzado entre `hero` ↔ `hero-mcp` ↔ `hero-memory` e `AGENTS.md`/`CLAUDE.md` duplicados em sete lugares — a deriva entre eles é certa. Hoje existe um único repositório, `RodReis/rrb-forjaOS`, contendo apenas `docs/`.

## Decisão

O ForjaOS é desenvolvido como **monorepo** em `forjaos-project/forjaos`, com uma pasta por componente:

| Pasta | Equivale a (PRD §5.2) | Conteúdo |
| --- | --- | --- |
| `image/` | `forjaos-image` | Containerfile, `build_files/`, `system_files/`, recipes `ujust`, ISO |
| `cli/` | `forja-cli` | CLI `forja` (Rust) |
| `hero/` | `hero` | `herod`, overlay, plasmoid, KRunner, wake word, Policy Engine |
| `hero-mcp/` | `hero-mcp` | `hero-system`, `hero-desktop`, `hero-dev` |
| `hero-memory/` | `hero-memory` | `memd`, coletores, visualizador, MCP `hero-memory` |
| `brand/` | `forjaos-brand` | `palette.json`, logo, mascote, wallpapers, temas Plasma/SDDM/Plymouth/GRUB/Konsole |
| `site/` | `forjaos-site` | Site, docs do usuário, download |

Regras:

1. Cada pasta tem um `AGENTS.md` curto com escopo, toolchain, testes e DoD locais. As regras globais vivem em `AGENTS.md` da raiz.
2. ADRs de produto ficam em `docs/adr/` (raiz); não há mais espelhamento entre repositórios.
3. Releases por tag prefixada: `cli-vX.Y.Z`, `hero-vX.Y.Z`, `hero-mcp-vX.Y.Z`, `hero-memory-vX.Y.Z`, `brand-vX.Y.Z`; a imagem segue `image-AAAA.MM.DD` e o release do SO `vX.Y.Z` (NFR-044).
4. CI por caminho (`paths:` nos workflows): mudança em `hero/` não reconstrói a imagem.
5. Se um componente precisar sair (contribuição externa forte, política de licença distinta), extrai-se com `git subtree split` preservando histórico — decisão por novo ADR.

## Alternativas descartadas

- **Sete repositórios (PRD §5.2):** fiel ao plano original, mas multiplica CI, release e documentação de agente por sete para uma pessoa.
- **Git submodules:** combina o pior dos dois (repos separados + acoplamento manual de SHA).

## Consequências

- A tabela da §5.2 do PRD permanece como histórico com nota de revogação apontando para este ADR.
- Labels `area/*` do PRD §14.2 continuam válidas e mapeiam 1:1 para as pastas.
- `check-branding.sh`, `check-tokens.sh` e `check-agents-sync.sh` rodam da raiz sobre todas as pastas.
