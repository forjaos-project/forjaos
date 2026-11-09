# /ship — Gate 5: registrar a entrega no roadmap e mergear

**Quando usar:** após `review: 8/8` e CI verde (ADR-033: sem CI de PR ainda, vale a saída da verificação colada pelo revisor).

**Pré-condições**
- `review: 8/8` no PR; CI verde; branch rebased em `main`.
- O item deste PR está `doing` na branch (feito no `claim` do `/plan`).

**Passos** (`docs/dev/METHODOLOGY.md §5`)
1. Na branch:
   ```bash
   python3 scripts/roadmap.py done <ID> --pr <N> --summary "<uma frase do que foi entregue>"
   git commit -am "docs(roadmap): deliver <ID> (PR #<N>)"
   git push
   ```
   Não rode `build` nem commite `STATUS.md`/`index.html`: o workflow `roadmap-sync` regenera os dois na `main` depois do merge.
2. Se a entrega fecha o DoD de uma fase do PRD §12, mude o `status` da fase em `roadmap.json` no mesmo commit (`doing` → `done`, próxima `todo` → `doing`).
3. Confira o template do PR: nenhum campo vazio, checklist dos 5 gates marcado.
4. **Squash merge**; título = primeiro commit `feat/fix` da branch. Apague a branch remota e o worktree local (`git worktree remove <caminho> && git worktree prune`), para não acumular clones em disco.
5. Se surgiu tarefa nova durante o trabalho, adicione-a em `roadmap.json` (`items[]`) — nunca em TODO solto no código.

**Verificação**
```bash
python3 scripts/roadmap.py validate --branch && git log -1 --format=%s | grep -q 'docs(roadmap): deliver '
```

**Saída esperada:** PR mergeado com o item `done`; o workflow `roadmap-sync` regenera `docs/STATUS.md` e `docs/roadmap/index.html` na `main`.
