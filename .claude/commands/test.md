# /test — Gate 3: provar que funciona (e que é fiel, se for tela)

**Quando usar:** com a branch do `/code` completa, antes de abrir PR.

**Pré-condições**
- Todos os commits do plano feitos.
- Para tela: implementação rodando para capturar tela.

**Passos** (`docs/dev/METHODOLOGY.md §3`)
1. Rode a verificação da raiz (abaixo) **e** a da pasta tocada:
   - Rust (`cli/ hero/ hero-mcp/ hero-memory/`): `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test && cargo llvm-cov --fail-under-lines 70`
   - `image/`: `bash scripts/tests/*.sh` + `scripts/check-branding.sh` (+ `podman build` no CI)
   - `brand/`: `scripts/check-tokens.sh` + `qmllint` nos `.qml`
   - `site/`: build sem warnings + `scripts/check-tokens.sh`
   - `scripts/ docs/`: `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` + `bash scripts/tests/*.sh`
2. Prove que o teste testa: reverta a implementação de uma tarefa e confirme que o teste falha; desfaça.
3. Tela: capture lado a lado em `docs/design-system/telas/<slug>/compare-AAAA-MM-DD.png` (protótipo à esquerda, implementação à direita, mesma resolução) e confira as medidas-chave da spec.
4. Unit systemd nova: `systemd-analyze verify <unit>`.
5. Cole a saída dos comandos na descrição do PR (o revisor vai rodar de novo).

**Verificação**
```bash
python3 -m unittest discover -s scripts/tests -p 'test_*.py' && bash scripts/tests/*.sh && scripts/check-tokens.sh && scripts/check-agents-sync.sh && python3 scripts/roadmap.py validate --branch && python3 scripts/gen_tela_specs.py --check
```

**Saída esperada:** tudo verde; captura lado a lado commitada quando houver tela; pronto para `/review`.
