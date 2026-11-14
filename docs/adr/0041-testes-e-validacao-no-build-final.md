# ADR-0041 — Testes, build e ISO 100 % locais; GitHub guarda o código e a ISO final

**Status:** proposto · **Data:** 2026-11-14 · **Decisão de:** mantenedor (conversa de 2026-11-14) · **Revoga parcialmente:** ADR-033 §3 e §5 (revisão refazendo o gate *test*; CI verde como condição de merge), ADR-0036, ADR-0040 (que só tirou a ISO do PR), `docs/dev/METHODOLOGY.md` §3 e §5, `.claude/commands/test.md`, e o DoD de fase do PRD §12 onde exigir teste ou medição · **Relacionados:** NFR-040, NFR-041, ADR-002, ADR-024, G1, G5, F0-003, F1-004, F5-001

## Contexto

O mantenedor quer concentrar toda a implementação primeiro e executar todos os testes uma única vez, no build final. Além disso, build, ISO e testes passam a rodar só na máquina local; o GitHub recebe apenas a ISO final. O ADR-0040 já havia tirado o build e o boot da ISO do PR; esta decisão estende o critério a todo teste e a todo build.

F1-004 (notebook híbrido) e G5 (validação física em 2 hardwares) dependem de um notebook de referência que ainda não existe (PRD §10.2); só podem ocorrer ao final.

## Decisão

1. **Sem gate *test* por item.** O ciclo por item é plan → code → review → ship. Os testes continuam sendo escritos no *code*; sua execução completa, as medições NFR-001 a NFR-013 e as provas em VM e hardware acontecem no build final.
2. **Tudo local.** Build da imagem, build da ISO, testes, medições e validação física rodam na máquina do mantenedor. Nenhum build, teste ou verificação depende de GitHub Actions.
3. **O código continua versionado no remoto** (branches, `claim` por push, PR e merge squash), sem nenhum build, teste ou workflow de verificação rodando lá. **O GitHub recebe como artefato só a ISO final** (release com checksum e assinatura, PRD §11).
4. **Build final de teste:** novo item de roadmap, fase 5, antes de F5-004. Roda a suíte completa, as metas NFR, o boot e a instalação das ISOs e a validação física. F1-004, F5-001 (G5), G1 e a meta de 50 instalações do 1.0 dependem dele.
5. O DoD de fase do PRD §12 que exige teste ou medição passa a ser verificado no build final.
6. Os checks estáticos (`check-tokens.sh`, `check-branding.sh`, `check-agents-sync.sh`, `roadmap validate`, `gen_tela_specs --check`) continuam como **scripts locais**, executados pelo autor antes do PR; sua saída é colada no PR. Deixam de rodar no GitHub Actions.
7. **Condição de merge:** `review: 8/8` mais a saída local dos checks do item 6 colada no PR (mesmo mecanismo que o ADR-033 §5 já previa antes do CI de PR). Não há CI verde a esperar.

## A definir (afeta o fluxo, não decidido aqui)

- O destino de F0-003 (build diário `:testing` assinado no GHCR) e do workflow `roadmap-sync`, que gera STATUS.md e `index.html` na `main` (não é build nem teste, então pode ficar; o build diário não).
- Como validar `bootc switch`, upgrade e rollback (F0-008, NFR-013) sem registry no GHCR: registry local ou arquivo OCI.

## Consequências

- Mais velocidade por item e nenhum custo de runner.
- Falhas de itens diferentes aparecem juntas no build final, e o `review` deixa de refazer a verificação do zero, que era o substituto da revisão cruzada no ADR-033.
- Sem CI no GitHub, o único filtro por item é o `review` em contexto limpo mais os checks locais colados no PR; nada impede que um item quebre a imagem até o build final.
- Sem `:stable` até o build final passar (NFR-040).
- Fica sem efeito a assinatura e a publicação automática diária de imagem `:testing`.

## Mudanças a aplicar (item GOV próprio, um PR ou commit)

- `.claude/commands/test.md`, `.claude/commands/review.md`, bloco *Fluxo* do `AGENTS.md` (via `scripts/check-agents-sync.sh --fix`), METHODOLOGY §3/§4/§5/§6, template do PR.
- `docs/roadmap/roadmap.json`: item do build final; F1-004 e F5-001 passam a depender dele.
- Notas de revogação parcial nos ADR-033 (§3 e §5), ADR-0036 e ADR-0040.
