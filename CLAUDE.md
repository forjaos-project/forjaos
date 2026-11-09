@AGENTS.md

# Claude Code — notas específicas

- Os cinco gates do fluxo estão disponíveis como comandos: `/plan`, `/code`, `/test`, `/review`, `/ship` (`.claude/commands/`). O texto deles é o mesmo do bloco **Fluxo** do `AGENTS.md`.
- Antes de qualquer tarefa: `git fetch origin && python3 scripts/roadmap.py available`, depois `claim` do item escolhido com `--agent claude` e push imediato da branch. Não pegue item fora da lista sem pedido explícito.
- **Revisão (ADR-033):** você leva o item até o merge. Rode `/review` num subagente novo (ferramenta Agent) sem o histórico desta sessão; ele recebe só o número do PR.
- Telas: abra `docs/design-system/telas/<slug>.md` antes do `code.html`. Tokens só de `brand/palette.json`.
- Arquivos gerados (`docs/STATUS.md`, `docs/roadmap/index.html`, `docs/design-system/telas/*.md` exceto Status/Pendências) não são editados com Edit/Write; telas: regenere com `gen_tela_specs.py`; STATUS/index.html só o workflow `roadmap-sync` na `main` regenera (nunca rode `build` na branch).
- Superpowers (brainstorming → writing-plans → executing-plans) complementam os gates: *brainstorming* alimenta a spec, *writing-plans* é o gate *plan*, *executing-plans* é o gate *code*. As regras deste repositório prevalecem onde divergirem.
