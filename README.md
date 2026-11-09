# ForjaOS

Sistema operacional open source baseado em Linux (Fedora Atomic via Universal Blue, `bootc`) para quem desenvolve e joga: Docker e Git prontos em menos de 15 minutos, Steam herdado, e um assistente de voz **100 % local** (HERO, mascote Guará) que age no sistema sob um Policy Engine. Monorepo; equipe solo; Apache-2.0 (código) e CC BY-SA 4.0 (artes).

## Comece por aqui

| Quero… | Arquivo |
| --- | --- |
| Entender o produto, requisitos (`FR-`/`NFR-`) e decisões (ADR-001–024) | [`docs/PRD.md`](docs/PRD.md) |
| Saber o que está feito, onde estamos e a **próxima tarefa** | [`docs/STATUS.md`](docs/STATUS.md) (gerado) · [`docs/roadmap/index.html`](docs/roadmap/index.html) |
| Trabalhar no repositório (5 gates: plan → code → test → review → ship) | [`docs/dev/METHODOLOGY.md`](docs/dev/METHODOLOGY.md) |
| Construir uma tela fiel ao protótipo, sem nada genérico | [`docs/design-system/DESIGN-RULES.md`](docs/design-system/DESIGN-RULES.md) · [`docs/design-system/telas/`](docs/design-system/telas/) |
| Usar os tokens oficiais (cores, fontes, raio, dimensões) | [`brand/palette.json`](brand/palette.json) |
| Ver as decisões posteriores ao PRD | [`docs/adr/`](docs/adr/) (026 monorepo · 027 tokens canônicos · 028 precedência protótipo × PRD) |
| Ver os protótipos de tela | [`docs/telas/`](docs/telas/) (`code.html` + `screen.png` por tela) |

## Para agentes (Claude Code, Codex)

1. Leia [`AGENTS.md`](AGENTS.md) — fonte única de regras. `CLAUDE.md` apenas o importa.
2. Rode `git fetch origin && python3 scripts/roadmap.py available` e pegue um item com `claim` (Claude Code e Codex trabalham em paralelo, cada um no seu item — [METHODOLOGY §6](docs/dev/METHODOLOGY.md)).
3. Siga os gates: `/plan` → `/code` → `/test` → `/review` → `/ship` (Claude Code) ou as seções equivalentes do `AGENTS.md` (Codex). **Quem implementa não revisa.**
4. Toda entrega termina com `python3 scripts/roadmap.py done <ID> --pr N --summary "…"`. `docs/STATUS.md` e `docs/roadmap/index.html` são regenerados na `main` pelo workflow `roadmap-sync`.

## Estrutura

```
image/  cli/  hero/  hero-mcp/  hero-memory/  brand/  site/   ← componentes (cada um com AGENTS.md)
docs/   PRD, ADRs, metodologia, design system, specs/planos, roadmap (JSON → STATUS.md + HTML)
scripts/ roadmap.py · gen_tela_specs.py · check-tokens.sh · check-agents-sync.sh · check-branding.sh · tests/
```

## Verificação local

```bash
python3 -m unittest discover -s scripts/tests -p 'test_*.py' && bash scripts/tests/*.sh \
&& scripts/check-tokens.sh && scripts/check-agents-sync.sh \
&& python3 scripts/roadmap.py validate --branch && python3 scripts/gen_tela_specs.py --check
```

Status do projeto: **Fase 0 — Fundação** (ver `docs/STATUS.md`).
