# AGENTS.md — regras para agentes (Claude Code, Codex e humanos) no ForjaOS

Este arquivo é a **fonte única** de regras de agente deste repositório. `CLAUDE.md` o importa (`@AGENTS.md`); Codex o lê nativamente. Cada pasta de componente tem um `AGENTS.md` curto com o que muda ali. Regras em pt-BR; código, nomes de arquivo e commits em inglês.

## Projeto

ForjaOS: sistema operacional open source baseado em Linux (Fedora Atomic via Universal Blue, bootc) para desenvolvimento e jogos, com assistente local HERO (mascote Guará), Memória do sistema e CLI `forja`. Monorepo (ADR-026). Equipe solo; qualidade vem do processo, não de revisão humana constante.

| Preciso de… | Leia |
| --- | --- |
| O que construir (requisitos `FR-`/`NFR-`, ADRs 001–024, roadmap) | `docs/PRD.md` |
| O que fazer **agora** (itens disponíveis, em andamento, bloqueios) | `python3 scripts/roadmap.py available` · `docs/STATUS.md` (gerado) · visual em `docs/roadmap/index.html` |
| Como trabalhar (5 gates, checklists, comandos) | `docs/dev/METHODOLOGY.md` |
| Como uma tela é construída (tokens, tradução, DoD visual) | `docs/design-system/DESIGN-RULES.md` + `docs/design-system/telas/<slug>.md` |
| Tokens (cores, fontes, raio, dimensões) | `brand/palette.json` |
| Decisões posteriores ao PRD | `docs/adr/0026-*.md`, `0027-*.md`, `0028-*.md` |
| Specs e planos aprovados | `docs/superpowers/specs/`, `docs/superpowers/plans/` |

## Regras invioláveis

1. **Comece por `git fetch origin && python3 scripts/roadmap.py available`.** Pegue um item da lista com `claim` e faça push na hora. Não pegue item fora da lista sem pedido explícito do humano.
2. **Cinco gates, nenhum pulável:** plan → code → test → review → ship. Hotfix de segurança pula só *plan*.
3. **Quem pega o item leva até o merge** (ADR-033). Claude Code e Codex trabalham em paralelo, cada um no seu item, sem esperar o outro. O gate *review* roda com contexto limpo (subagente/sessão nova da mesma ferramenta) e o merge exige `review: 8/8` + CI verde (sem CI de PR ainda: saída da verificação colada pelo revisor, ADR-033 §5).
4. **PRD manda no conteúdo; protótipo manda no layout** (ADR-028). Strings proibidas em código de tela: `Jarvis`, `devos`, `nftables`, `24.04`, `arm64`, `RTX 4070`. Divergência vira issue, não improviso.
5. **Toda cor vem de `brand/palette.json`** (ADR-027). Fontes: Plus Jakarta Sans (UI), JetBrains Mono (mono), Inter só em corpo denso. Fira Code proibida. `scripts/check-tokens.sh` é juiz.
6. **Nada de tela genérica:** Breeze/Fedora/Bazzite visível, componente sem estilo, medida "a olho" ou ícone Material Symbols no produto reprovam o PR.
7. **Nenhuma ação destrutiva fora de tier:** `rm -rf`, `dd`, firewall, SELinux, `/etc` só com confirmação explícita do humano e registro no PR (FR-093, FR-100).
8. **Toda unit systemd própria declara `MemoryMax`, `CPUQuota`, `Nice`.** Modelos de IA descarregam quando ociosos.
9. **Chaves só no KWallet.** Nenhum segredo em arquivo, commit, log ou descrição de PR (NFR-024).
10. **Cada PR altera só o próprio item no `roadmap.json`** (`claim` → `done`). `docs/STATUS.md` e `docs/roadmap/index.html` são gerados na `main` pelo workflow `roadmap-sync`: nunca editados à mão, nunca commitados em PR.
11. **Decisão escrita vence.** Mudar uma decisão = novo ADR que revoga o anterior. Não reabra por opinião.
12. **Não adicione dependência, repositório de terceiros ou licença** sem justificativa no commit e verificação (G4: Apache/MIT/BSD/OFL/CC-BY).

## Fluxo

Os cinco blocos abaixo são idênticos aos comandos `.claude/commands/{plan,code,test,review,ship}.md`. `scripts/check-agents-sync.sh` falha se divergirem. Para alterar o fluxo: edite o comando e rode `scripts/check-agents-sync.sh --fix`, que regenera este bloco.

<!-- flow:start -->
# /plan — Gate 1: planejar antes de tocar em código

**Quando usar:** sempre que uma tarefa nova vai começar. Sem plano aprovado não existe branch.

**Pré-condições**
- Rodou `git fetch origin && python3 scripts/roadmap.py available` e o item aparece como **disponível** (ou foi pedido explicitamente pelo humano).
- Existe spec aprovada em `docs/superpowers/specs/` **ou** issue com `FR-`/`NFR-`/`ADR-` e DoD objetivo.
- Se a tarefa envolve tela: a spec `docs/design-system/telas/<slug>.md` existe e o hash bate (`python3 scripts/gen_tela_specs.py --check`).

**Passos** (`docs/dev/METHODOLOGY.md §1`)
0. **Reserve a tarefa antes de planejar** (`docs/dev/METHODOLOGY.md §6`):
   ```bash
   git fetch origin && git switch -c <tipo>/<ID>-<slug> origin/main
   python3 scripts/roadmap.py claim <ID> --agent claude|codex [--scope pasta/]
   git commit -am "chore(roadmap): claim <ID>" && git push -u origin HEAD
   ```
   O push imediato é o que avisa o outro agente. Claim recusado (dependência não feita, escopo ocupado, item já pego) → volte ao `available` e escolha outro.
1. Leia o PRD nos IDs citados e, se houver tela, a spec da tela **antes** do `code.html`.
2. Escreva `docs/superpowers/plans/AAAA-MM-DD-<slug>.md` com: Goal, Architecture, Tech Stack, mapa de arquivos, tarefas de ≤ 2 h — cada uma com arquivos exatos, o teste que a prova, DoD e mensagem de commit.
3. Toda tarefa cita um ID do PRD. Nenhuma diz "TBD", "depois", "tratar erros" sem dizer como.
4. Se alguma tarefa depende de decisão não tomada, pare: a decisão vira ADR primeiro.
5. Se o plano não cabe em uma branch/PR, divida em dois planos.

**Verificação**
```bash
f=docs/superpowers/plans/<arquivo>.md
grep -L 'FR-\|NFR-\|ADR-' "$f"               # vazio
grep -niE 'TBD|TODO|depois|a definir' "$f"   # vazio
```

**Saída esperada:** item em `doing` na branch remota (claim) e plano commitado nela em `docs/superpowers/plans/` com mensagem `docs(plans): <slug>`.

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

# /test — Gate 3: provar que funciona (e que é fiel, se for tela)

**Quando usar:** com a branch do `/code` completa, antes de abrir PR.

**Pré-condições**
- Todos os commits do plano feitos.
- Para tela: implementação rodando para capturar tela.

**Passos** (`docs/dev/METHODOLOGY.md §3`)
1. Rode a verificação da raiz (abaixo) **e** a da pasta tocada:
   - Rust (`cli/ hero/ hero-mcp/ hero-memory/`): `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test && cargo llvm-cov --fail-under-lines 70`
   - `image/`: `scripts/run-shell-tests.sh` + `scripts/check-branding.sh` (+ `podman build` no CI)
   - `brand/`: `scripts/check-tokens.sh` + `qmllint` nos `.qml`
   - `site/`: build sem warnings + `scripts/check-tokens.sh`
   - `scripts/ docs/`: `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` + `scripts/run-shell-tests.sh`
2. Prove que o teste testa: reverta a implementação de uma tarefa e confirme que o teste falha; desfaça.
3. Tela: capture lado a lado em `docs/design-system/telas/<slug>/compare-AAAA-MM-DD.png` (protótipo à esquerda, implementação à direita, mesma resolução) e confira as medidas-chave da spec.
4. Unit systemd nova: `systemd-analyze verify <unit>`.
5. Cole a saída dos comandos na descrição do PR (o revisor vai rodar de novo).

**Verificação**
```bash
python3 -m unittest discover -s scripts/tests -p 'test_*.py' && scripts/run-shell-tests.sh && scripts/check-tokens.sh && scripts/check-agents-sync.sh && python3 scripts/roadmap.py validate --branch && python3 scripts/gen_tela_specs.py --check
```

**Saída esperada:** tudo verde; captura lado a lado commitada quando houver tela; pronto para `/review`.

# /review — Gate 4: revisão com contexto limpo (ADR-033)

**Quando usar:** no PR do item que você pegou, antes do merge. Quem implementou leva o item até o fim; a revisão roda numa instância **sem o contexto da implementação** (Claude Code: subagente novo; Codex: sessão nova), que recebe só o número do PR e estas regras.

**Pré-condições**
- PR aberto com template preenchido.
- Revisor em contexto limpo: não reaproveite a sessão que implementou.

**Passos** (`docs/dev/METHODOLOGY.md §4`)
1. Rode do zero a verificação do `/test` (raiz + pasta). Não confie na saída colada.
2. Percorra os 8 itens:
   1. FR/NFR/ADR citado realmente coberto; DoD do PRD atendido.
   2. ADR-028: nenhuma string proibida (`Jarvis devos nftables 24.04 arm64 RTX 4070`); conteúdo bate com o PRD.
   3. ADR-027: `check-tokens.sh` OK; fontes só Plus Jakarta Sans / JetBrains Mono / Inter(dense).
   4. Testes existem, vieram antes da implementação (histórico) e provam comportamento, não só cobertura.
   5. Consumo declarado em toda unit systemd; modelos de IA descarregam ociosos.
   6. Nenhum segredo em arquivo (NFR-024).
   7. SELinux, firewalld, `/etc` e tiers do Policy Engine intocados fora do escopo.
   8. Roadmap: no `roadmap.json` só mudou o item deste PR (`claim` → `done`); `STATUS.md`/`index.html` **fora** do diff (`roadmap.py validate --branch`).
3. Tela: compare a captura lado a lado com a spec; registre `visual: fiel` ou liste as medidas divergentes.
4. Cada achado vira **commit na branch** com prefixo `fix(review): …` — não comentário solto.
5. Feche com um comentário `review: N/8`. Só `8/8` libera `/ship`.

**Verificação**
```bash
gh pr view <N> --json comments -q '.comments[].body' | grep -E '^review: 8/8$'
```

**Saída esperada:** comentário `review: 8/8` (+ `visual: fiel` quando houver tela) e zero achados abertos.

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
4. **Squash merge**; título = primeiro commit `feat/fix` da branch. Apague a branch remota.
5. Se surgiu tarefa nova durante o trabalho, adicione-a em `roadmap.json` (`items[]`) — nunca em TODO solto no código.

**Verificação**
```bash
python3 scripts/roadmap.py validate --branch && git log -1 --format=%s | grep -q 'docs(roadmap): deliver '
```

**Saída esperada:** PR mergeado com o item `done`; o workflow `roadmap-sync` regenera `docs/STATUS.md` e `docs/roadmap/index.html` na `main`.
<!-- flow:end -->

## Convenções

- **Branch:** `feat/FR-xxx-slug` · `fix/FR-xxx-slug` · `adr/NNNN-slug` · `docs/slug` · `chore/slug`. Nunca trabalhe em `main`.
- **Commit:** `tipo(escopo): resumo em inglês no imperativo`. Tipos `feat fix adr docs test chore refactor`. Escopos `image cli hero hero-mcp hero-memory brand site docs scripts agents roadmap plans`. Um commit por tarefa do plano.
- **PR:** template em `.github/PULL_REQUEST_TEMPLATE.md`; squash merge; branch apagada.
- **Idioma:** regras, PRD, ADRs e specs em pt-BR; código, commits, nomes de arquivo e docs técnicas em inglês; strings do produto em pt-BR + en-US via Qt Linguist.
- **Testes:** Rust `cargo test` + cobertura ≥ 70 % (NFR-041); shell `scripts/tests/*.sh`; Python `unittest`; tela = captura lado a lado.
- **Versionamento:** imagem `AAAA.MM.DD`; release `vX.Y.Z`; crates semver com tag prefixada (`cli-v0.1.0`).

## Estrutura do repositório

| Pasta | Conteúdo | Linguagem | AGENTS.md local |
| --- | --- | --- | --- |
| `image/` | Containerfile, `build_files/`, `system_files/`, recipes `ujust`, ISO, wizard de 1º boot | Shell, Containerfile, QML | `image/AGENTS.md` |
| `cli/` | CLI `forja` | Rust | `cli/AGENTS.md` |
| `hero/` | `herod`, overlay, plasmoid, KRunner, wake word, Policy Engine | Rust, QML, C++ | `hero/AGENTS.md` |
| `hero-mcp/` | `hero-system`, `hero-desktop`, `hero-dev` | Rust | `hero-mcp/AGENTS.md` |
| `hero-memory/` | `memd`, coletores, visualizador, MCP `hero-memory` | Rust, QML | `hero-memory/AGENTS.md` |
| `brand/` | `palette.json`, logo, mascote, wallpapers, temas Plasma/SDDM/Plymouth/GRUB/Konsole | JSON, SVG, QML | `brand/AGENTS.md` |
| `site/` | Site, docs do usuário, download | Astro | `site/AGENTS.md` |
| `docs/` | PRD, ADRs, metodologia, design system, specs/planos, roadmap, STATUS | Markdown, JSON, HTML gerado | — |
| `scripts/` | `roadmap.py`, `gen_tela_specs.py`, `check-*.sh`, testes | Python, Bash | — |
| `.claude/commands/` | `/plan /code /test /review /ship` | Markdown | — |

## Design

- Leia `docs/design-system/DESIGN-RULES.md` antes de tocar em QML, tema, SVG ou site.
- **Nunca abra `docs/telas/<slug>/code.html` antes da spec `docs/design-system/telas/<slug>.md`.** A spec já traz regiões, medidas, tokens, ícones e substituições; o HTML serve para conferir detalhe.
- Hash da spec ≠ hash do `code.html` → spec desatualizada: `python3 scripts/gen_tela_specs.py` e revise antes de implementar.
- DoD visual: captura lado a lado + `check-tokens.sh` + medidas conferidas + substituições aplicadas + `visual: fiel` do revisor.
- Tela sem FR no PRD (ex.: explorer Dolphin) não se implementa: primeiro ADR + FR.

## Roadmap e status

- Fonte única: `docs/roadmap/roadmap.json`. Gerados: `docs/STATUS.md` e `docs/roadmap/index.html`.
- Pegar tarefa: `git fetch origin && python3 scripts/roadmap.py available` → `claim <ID> --agent claude|codex [--scope pasta/]` → commit e push imediato da branch.
- Gate *ship*: `python3 scripts/roadmap.py done <ID> --pr N --summary "…"` → commit `docs(roadmap): deliver <ID> (PR #N)`. Sem `build` na branch.
- Paralelo só entre escopos diferentes; `claim` recusa dependência não feita e escopo sobreposto (`image/` × `image/build/`; `.` bloqueia tudo). Item pego em outra branch some do `available`. Abandonou? Apague a branch remota.
- Tarefa nova descoberta durante o trabalho → novo item em `roadmap.json` (com `scope` e `depends_on`), nunca `TODO` solto no código.
- `python3 scripts/roadmap.py validate --branch` roda em todo gate *test*; `build --check` roda só na `main`, no workflow `roadmap-sync`.

## Verificações (scripts)

| Script | O que faz | Quando roda |
| --- | --- | --- |
| `scripts/check-tokens.sh` | Falha se houver hex fora do `palette.json` em QML/CSS/SVG/HTML/Rust/Python próprios | `/code`, `/test`, `/review`, CI |
| `scripts/check-agents-sync.sh` | Falha se o bloco Fluxo deste arquivo ≠ `.claude/commands/*.md` | `/test`, CI |
| `scripts/check-branding.sh` | Falha se a imagem expõe marca Fedora/Bazzite/Bluefin (FR-002) — **stub até F0-004** | `/test` em `image/`, CI |
| `scripts/gen_tela_specs.py --check` | Falha se o hash de um `code.html` mudou sem atualizar a spec | `/plan` de tela, `/test` |
| `scripts/roadmap.py validate --branch` | Falha se o `roadmap.json` é inválido ou se a branch alterou `STATUS.md`/`index.html` | `/test`, `/ship` |
| `scripts/roadmap.py build` (workflow `roadmap-sync`) | Regenera `STATUS.md`/`index.html` na `main` após cada merge | `main` |
| `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` + `scripts/run-shell-tests.sh` | Testes dos próprios scripts | `/test`, CI |
