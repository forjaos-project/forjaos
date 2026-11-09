# ADR-033 — Cada agente leva o item até o merge; revisão com contexto limpo + CI

**Status:** aceito · **Data:** 2026-11-09 · **Revoga:** a revisão cruzada entre ferramentas (regra 3 do `AGENTS.md`, regra 2 e §4 de `docs/dev/METHODOLOGY.md`) · **Relacionados:** ADR-029, NFR-040, NFR-041, NFR-042, GOV-011

## Contexto

Com a revisão cruzada, um PR do Claude Code espera o Codex terminar o que está fazendo para ser revisado, e vice-versa. O mantenedor precisa ficar trocando de ferramenta e esperando; o paralelismo do ADR-029 vira fila. Decisão do mantenedor em 2026-11-09: quem pega o item resolve até o PR verde.

A revisão cruzada achou problemas reais (PR #9: assinatura cosign nunca encontrada e troca de variante sem verificação; PR #8: ajustes visuais). Tirar o revisor sem substituto deixaria esse tipo de erro passar; por isso a revisão fica, feita pela mesma ferramenta sem o contexto de quem implementou, e o CI passa a bloquear o merge.

## Decisão

1. O agente que faz o `claim` leva o item pelos cinco gates até o merge. Não há espera pelo outro agente.
2. O gate *review* é executado pela **mesma ferramenta com contexto limpo**: uma instância que não participou da implementação e recebe apenas o número do PR e as regras do repositório.
   - Claude Code: subagente novo (ferramenta Agent), sem o histórico da sessão que implementou.
   - Codex: sessão nova (thread nova ou `codex exec`), aberta só para a revisão.
3. O revisor roda a verificação do gate *test* do zero e percorre os mesmos 8 itens. Cada achado vira commit `fix(review): …` na branch; o ciclo se repete até `review: 8/8`.
4. O comentário de fechamento é `review: N/8` seguido da linha `revisor: <ferramenta> (contexto limpo)`.
5. O gate *ship* exige `review: 8/8` **e CI verde**. Enquanto o CI de verificação em PR (GOV-011) não existir, o revisor cola no comentário a saída da verificação que rodou do zero.
6. O mantenedor continua podendo pedir revisão de outra ferramenta ou humana em qualquer PR; isso é opcional.

## Consequências

- Os dois agentes trabalham em paralelo sem fila de revisão.
- A independência diminui: os pontos cegos do mesmo modelo podem se repetir. Mitigação: contexto limpo, verificação refeita do zero e CI obrigatório. O GOV-011 passa a ser pré-requisito real do *ship*.
- PRs abertos antes deste ADR (#9, #11, #12) seguem a regra nova: cada autor conclui o próprio PR.
