# Trabalho paralelo Claude Code + Codex — plano (retroativo)

> **Nota de processo:** este plano foi escrito após a implementação, a pedido da revisão independente do PR #2 (achado B3). A decisão que ele registra está em ADR-029. O gate *plan* foi pulado no PR #2 e a exceção está registrada no PR.

**Goal:** permitir que dois agentes implementem itens do roadmap ao mesmo tempo sem conflito de merge (NFR-042, ADR-029).

**Architecture:** `roadmap.json` guarda `scope` e `depends_on` por item; `roadmap.py` expõe `available`, `claim`, `done`, `validate --branch` e `build`; o workflow `roadmap-sync` regenera os arquivos gerados só na `main`.

**Tech Stack:** Python 3 stdlib, `unittest`, Bash, GitHub Actions.

## Mapa de arquivos

- `scripts/roadmap.py`, `scripts/tests/test_roadmap.py` — CLI e testes.
- `docs/roadmap/roadmap.json` — `scope` e `depends_on` nos itens da Fase 0.
- `.github/workflows/roadmap-sync.yml` — regeneração na `main`.
- `AGENTS.md`, `CLAUDE.md`, `.claude/commands/*.md`, `docs/dev/METHODOLOGY.md`, `README.md`, `.github/PULL_REQUEST_TEMPLATE.md` — fluxo `claim`/`done`.
- `docs/adr/0029-trabalho-paralelo-e-gerados-na-main.md` — decisão.

## Tarefas

### Tarefa 1 — CLI `claim` / `done` / `available` (NFR-042, ADR-029)
- Arquivos: `scripts/roadmap.py`, `scripts/tests/test_roadmap.py`.
- Prova: testes de claim, done, dependência, escopo e merge real de duas branches.
- DoD: `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` verde.
- Commit: `chore(scripts): roadmap claim/done with scope and dependencies`.

### Tarefa 2 — Base em `origin/main` e guardas do claim (NFR-042, ADR-029)
- Arquivos: `scripts/roadmap.py` (`load_base`, `claim_guards`), `scripts/tests/test_roadmap.py`.
- Prova: `test_claim_guards_refuse_stale_base_and_main`, `test_load_base_reads_origin_main_not_working_copy`.
- DoD: com `origin/main` à frente, `available` não lista item entregue e `claim` recusa.
- Commit: `fix(scripts): read roadmap base from origin/main and guard claims`.

### Tarefa 3 — Workflow `roadmap-sync` (ADR-029)
- Arquivos: `.github/workflows/roadmap-sync.yml`.
- Prova: simulação local de `build` seguido de `build --check`.
- DoD: workflow regenera `STATUS.md` e `index.html` na `main` com `[skip ci]`.
- Commit: `chore(scripts): roadmap-sync workflow regenerates generated files on main`.

### Tarefa 4 — Documentação do fluxo e escopo `roadmap` (ADR-029)
- Arquivos: `AGENTS.md`, `CLAUDE.md`, `.claude/commands/*.md`, `docs/dev/METHODOLOGY.md`, `README.md`, `.github/PULL_REQUEST_TEMPLATE.md`.
- Prova: `scripts/check-agents-sync.sh` e a verificação de commits do `/code` sem saída.
- DoD: bloco Fluxo idêntico aos comandos; `roadmap` aceito como escopo de commit.
- Commit: `docs(agents): parallel work between Claude Code and Codex`.

### Tarefa 5 — Runner dos testes shell (ADR-029)
- Arquivos: `scripts/run-shell-tests.sh` e menções em `AGENTS.md`, `README.md`, `METHODOLOGY.md`, `test.md`, template de PR.
- Prova: `scripts/run-shell-tests.sh` roda os dois testes `.sh`, um `bash` por arquivo.
- DoD: bits de execução gravados no git para `scripts/*.sh` e `scripts/tests/*.sh`.
- Commit: `fix(scripts): run each shell test in its own bash and set exec bits`.
