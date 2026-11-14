# ForjaOS

Sistema operacional open source baseado em Linux (Fedora Atomic via Universal Blue, `bootc`) para quem desenvolve e joga: Docker e Git prontos em menos de 15 minutos, Steam herdado, e um assistente de voz **100 % local** (HERO, mascote Guará) que age no sistema sob um Policy Engine. Monorepo; equipe solo; Apache-2.0 (código) e CC BY-SA 4.0 (artes).

## Comece por aqui

| Quero… | Arquivo |
| --- | --- |
| Entender o produto e os requisitos | [`docs/PRD.md`](docs/PRD.md) |
| Ver o que falta | [`TODO.md`](TODO.md) |
| Cores, fontes e medidas | [`brand/palette.json`](brand/palette.json) |
| Construir uma tela fiel ao protótipo | [`docs/design-system/`](docs/design-system/) · protótipos em [`docs/telas/`](docs/telas/) |
| Decisões já tomadas | [`docs/adr/`](docs/adr/) |

## Para agentes (Claude Code, Codex)

Leia [`AGENTS.md`](AGENTS.md): meia página, três proteções e o fluxo (pegar item do `TODO.md`, fazer, commitar na `main`).

## Estrutura

```
image/  cli/  hero/  hero-mcp/  hero-memory/  brand/  site/   ← componentes
docs/   PRD, ADRs, design system, protótipos
scripts/ gen_tela_specs.py · check-tokens.sh · check-branding.sh · build-iso · tests/
```

Build, ISO e testes rodam local; o GitHub recebe a ISO final.
