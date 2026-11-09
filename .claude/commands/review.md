# /review — Gate 4: revisão cruzada (quem implementou não revisa)

**Quando usar:** em um PR aberto por **outra** ferramenta. Você está revisando código que outra ferramenta escreveu. Se você escreveu esta branch, pare e peça a outra (Claude Code ↔ Codex).

**Pré-condições**
- PR aberto com template preenchido, incluindo "Implementado por".
- `git log --format=%an origin/main..HEAD` e a descrição do PR confirmam que o autor não é você.

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
