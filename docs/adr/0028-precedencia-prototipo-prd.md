# ADR-028 — Precedência entre protótipo e PRD na implementação de telas

**Status:** aceito · **Data:** 2026-11-08 · **Relacionados:** ADR-004, ADR-006, ADR-027

## Contexto

Os protótipos em `docs/telas/` foram gerados antes das decisões de nome e de arquitetura do PRD. Eles mostram `Jarvis local` (ADR-006 descartou "Jarvis" por marca Marvel/Disney), `devos doctor` e `devos-term` (o CLI é `forja`, ADR-020), `nftables` (o PRD fixa firewalld, ADR-022), `24.04 LTS` (o versionamento é `AAAA.MM.DD` + `vX.Y.Z`, NFR-044), `x86_64 / arm64` (ARM é backlog 2.0), `Kernel 6.12.x-bazzite` (o kernel é o que a base Universal Blue entregar), `RTX 4070` (a máquina de referência é RTX 5060 8 GB, §10.2) e `Escudo ativo` sem que o módulo Escudo esteja instalado (ADR-023: opt-in). Ao mesmo tempo, os protótipos são a única definição visual que existe — abandoná-los produz telas genéricas.

## Decisão

Ao implementar qualquer tela:

1. **Do protótipo (`code.html` + `screen.png`) vêm:** layout, hierarquia visual, posição e tamanho de regiões, tokens de cor (via `palette.json`, ADR-027), espaçamento, raio, elevação, tipografia, animações e estados. Isso é copiado com fidelidade e verificado por captura lado a lado.
2. **Do PRD vêm:** todos os textos, nomes de produto e de componentes, comandos, versões, hardware, serviços de sistema e qualquer informação factual. O protótipo nunca é fonte de conteúdo.
3. **Divergência entre protótipo e PRD vira issue** com label `area/brand` e referência ao FR; nunca improviso na implementação. Se a divergência for de layout (o protótipo mostra algo que o PRD proíbe, como um painel que exige porta aberta), a issue decide antes do código.
4. **Tabela de substituições obrigatórias** (aplicada em toda tela, registrada na spec `docs/design-system/telas/<slug>.md`):

| No protótipo | Na implementação | Fonte |
| --- | --- | --- |
| `Jarvis`, `Jarvis local` | `Guará` (persona padrão) / `HERO` (motor) / `HERO local` | ADR-005, ADR-006 |
| `devos`, `devos doctor`, `devos ai`, `devos up`, `devos install` | `forja`, `forja doctor`, `forja ai`, `forja up`, `forja install` | ADR-020, FR-060 |
| `devos-term` | `forja-term` | FR-035 |
| `rodrigo@devos` | `usuario@forjaos` (ou `$USER@forjaos`) | FR-003 |
| `nftables` | `firewalld` | ADR-022 |
| `24.04 LTS`, `24.04` | versão corrente `AAAA.MM.DD` (imagem) ou `vX.Y.Z` (release) | NFR-044 |
| `x86_64 / arm64` | `x86-64-v3` | §10.1 |
| `Kernel 6.12.x-bazzite` | `kernel Bazzite` sem número fixo (vem da base) | ADR-001 |
| `RTX 4070` | `RTX 5060 8 GB` (desktop de referência) | §10.2 |
| `GameMode on` | `hero-game.target` / `Modo Jogo` | FR-043 |
| `Escudo ativo` no painel | exibido só se `forja install escudo` foi executado; caso contrário o indicador não aparece | ADR-023, NFR-027 |
| `DeveloperOS` isolado | `ForjaOS` (sem descritor) | ADR-031 |
| Ícones Material Symbols | Breeze recolorido por token ou SVG próprio em `brand/icons/` | DESIGN-RULES §5 |

5. **O `code.html` não é lido antes da spec da tela.** O agente abre primeiro `docs/design-system/telas/<slug>.md`, que já lista regiões, medidas, tokens e substituições; o `code.html` serve para conferir medida ou classe específica.

## Alternativas descartadas

- **Fidelidade total ao protótipo:** reproduziria marca de terceiro e comandos inexistentes.
- **Corrigir os 16 `code.html` antes de implementar:** bloqueia a Fase 1 por semanas para reescrever HTML que não é o produto final.

## Consequências

- Toda spec de tela traz a seção "Conteúdo (PRD → substituir)" preenchida a partir de `grep` no `code.html`.
- O revisor cruzado (METHODOLOGY §4) reprova PR de tela com qualquer string da coluna "No protótipo".
- Quando um protótipo for regenerado com conteúdo correto, a spec da tela atualiza o hash SHA-256 e remove as substituições que deixaram de ser necessárias.
