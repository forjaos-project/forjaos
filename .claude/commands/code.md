# /code — Gate 2: implementar com TDD, um commit por tarefa

**Quando usar:** após `/plan` aprovado. Nunca em `main`.

**Pré-condições**
- Plano em `docs/superpowers/plans/` com as tarefas a executar.
- Na branch criada no `/plan` (`<tipo>/<ID>-<slug>`, tipos `feat fix adr docs chore`), com o claim já no remoto e rebaseada em `origin/main`.

**Passos** (`docs/dev/METHODOLOGY.md §2`)
1. Para cada tarefa do plano, nesta ordem: escreva o teste → rode e veja **falhar** → implemente o mínimo → rode e veja **passar** → refatore → commit.
2. Commit convencional: `tipo(escopo): resumo em inglês no imperativo`. Tipos `feat fix adr docs test chore refactor`; escopos `image cli hero hero-mcp hero-memory brand site docs scripts agents roadmap plans`. Um commit por tarefa.
3. Telas: abra a spec `docs/design-system/telas/<slug>.md`, aplique a tabela "Conteúdo (PRD → substituir)" (ADR-028), copie **medidas e tokens** (`brand/palette.json`), nunca hex solto, nunca fonte fora de Plus Jakarta Sans / JetBrains Mono / Inter(dense).
4. Toda unit systemd própria declara `MemoryMax`, `CPUQuota`, `Nice`.
5. Nenhum segredo em arquivo; chaves só via KWallet/`secret-tool`.
6. Dependência nova só com justificativa no commit e licença compatível (Apache/MIT/BSD/OFL/CC-BY).
7. Arquivos pequenos e com uma responsabilidade; acima de ~400 linhas, divida.

**Verificação**
```bash
git log --format=%s origin/main..HEAD | grep -vE '^(feat|fix|adr|docs|test|chore|refactor)\((image|cli|hero|hero-mcp|hero-memory|brand|site|docs|scripts|agents|roadmap|plans)\): '   # vazio
scripts/check-tokens.sh
git diff origin/main..HEAD | grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'   # vazio
```

**Saída esperada:** branch com N commits = N tarefas do plano, todos com teste correspondente; pronta para `/test`.
