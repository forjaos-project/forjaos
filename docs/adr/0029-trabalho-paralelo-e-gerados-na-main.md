# ADR-029 — Trabalho paralelo entre agentes e arquivos gerados só na `main`

**Status:** aceito · **Data:** 2026-11-09 · **Relacionados:** ADR-026, NFR-042 · **Revoga parcialmente:** `docs/superpowers/specs/2026-11-08-metodologia-implementacao-design.md` §4.3 (gate *ship*) e §4.5 (`add-delivery`, STATUS como fonte da próxima tarefa)

## Contexto

A spec de 2026-11-08 mandava, no gate *ship*, registrar a entrega com `roadmap.py add-delivery` e regenerar `STATUS.md` e `roadmap/index.html` **no mesmo PR**, e tratava o `STATUS.md` como fonte da próxima tarefa. Isso funciona para um agente por vez. Com Claude Code e Codex implementando em paralelo, cada PR reescreve os mesmos arquivos gerados e o `roadmap.json` inteiro: todo par de PRs conflita, e o `STATUS.md` fica defasado em relação às branches abertas.

## Decisão

1. **Reserva (`claim`)**: antes de planejar, o agente roda `roadmap.py claim <ID> --agent claude|codex` na própria branch e faz push imediato. O claim grava `status: doing`, `agent`, `scope` e `claimed_at` no item. `available` e `claim` leem o `roadmap.json` de `origin/main` mais os claims das branches remotas, nunca a cópia de trabalho. O claim é recusado fora de branch própria, com base desatualizada, para item que não está `todo` em `origin/main`, com dependência não feita (`depends_on`) ou com escopo sobreposto a item em andamento.
2. **Entrega (`done`)**: o gate *ship* roda `roadmap.py done <ID> --pr N --summary "…"`. Cada PR altera só o próprio item do `roadmap.json`. `add-delivery` deixa de ser o fluxo; `deliveries[]` fica como histórico somente leitura.
3. **Gerados só na `main`**: `docs/STATUS.md` e `docs/roadmap/index.html` não entram em PR. O workflow `roadmap-sync` os regenera na `main` após cada merge que toque o roadmap. `roadmap.py validate --branch` falha se a branch os alterou.
4. **Fonte da próxima tarefa**: passa a ser `python3 scripts/roadmap.py available`, não o `STATUS.md`.
5. **Escopo de commit `roadmap`** passa a ser válido (`chore(roadmap): claim <ID>`, `docs(roadmap): deliver <ID> (PR #N)`).

## Consequências

- Itens com escopos disjuntos não conflitam no merge (coberto por `test_two_parallel_branches_merge_without_conflict`).
- O claim só vale depois do push da branch; entre o `fetch` e o push ainda existe uma janela de corrida, que aparece como conflito no merge do `roadmap.json`. Uma trava atômica por ref fica como melhoria futura, registrada como item novo se o problema ocorrer.
- Branch de PR fechado sem merge segura o claim até ser apagada; a regra é apagar a branch remota abandonada.
- O `STATUS.md` na `main` lista "Disponíveis" sem os claims das branches abertas; o comando `available` é a visão correta.
