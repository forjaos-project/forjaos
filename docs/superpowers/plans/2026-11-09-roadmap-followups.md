# Itens novos no roadmap (follow-ups do F0-006 e da revisão do PR #9) Implementation Plan

**Goal:** Registrar como itens do roadmap as tarefas descobertas no F0-006 e na revisão do PR #9, em vez de deixá-las soltas (METHODOLOGY §5, passo 5).

**Architecture:** Só `docs/roadmap/roadmap.json` muda: dois itens `todo` novos, com `scope` e `depends_on`. Gerados ficam para o `roadmap-sync`.

**Tech Stack:** JSON, `scripts/roadmap.py`.

---

### Task 1: Adicionar GOV-011 e F1-011 (NFR-040, NFR-041, NFR-042, FR-002, FR-003, FR-053)

**Files:** Modify: `docs/roadmap/roadmap.json`

- GOV-011 (`.github/`, fase 0): CI de verificação em PR rodando as suítes e checagens que hoje só rodam localmente; nota sobre não tornar o job obrigatório enquanto PRs do `roadmap-sync` (GITHUB_TOKEN) não disparam workflows.
- F1-011 (`image/`, fase 1, depende de F0-002): ícone ForjaOS no hicolor, `LOGO=` no `os-release` e `image-info.json` da Universal Blue apontando para `ghcr.io/forjaos-project`.
- Prova: `python3 scripts/roadmap.py validate --branch` verde; `git diff origin/main -- docs/roadmap/roadmap.json` só com os dois itens novos.
- Commit: `chore(roadmap): add GOV-011 CI checks and F1-011 image rebranding items`
