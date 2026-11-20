# F4-006 — Integração local de software

Data: 20/11/2026. Windows + WSL Ubuntu, PySide6 Essentials 6.10.3,
`QT_QPA_PLATFORM=offscreen`, `QT_QUICK_BACKEND=software`. Dados sintéticos;
nenhuma coleta de atividade real nem alteração dos clientes pessoais.

## Resultados

- `hero-memory`: 20 testes Linux, fmt e Clippy com `-D warnings`; cobertura
  de linhas 72,29% (`cargo llvm-cov --fail-under-lines 70 --summary-only`).
- CLI: 16 testes Linux, fmt e Clippy; cobertura de linhas 71,39%.
- `python3 -m unittest scripts.tests.test_memory_viewer`: 4 testes; SQLite
  somente leitura, FTS5 sem acentos e conteúdo completo, data e caminhos seguros.
- `scripts/tests/smoke_memory_mcp.py <memd>`: binário Linux real, stdio,
  initialize, catálogo de cinco ferramentas, remember/search/timeline/related/
  forget e links `resource_link` das fontes. HOME/XDG temporários.
- Teste de registro da CLI: argumentos stdio de hero-memory e detecção de
  registro existente para Claude Code, Codex e Hermes usando clientes simulados.
  Não equivale a instalar o servidor nos clientes reais do usuário.
- `qmllint --unqualified disable hero-memory/visualizer/viewer.qml`: sem
  diagnósticos. Nomes do contexto Python são dinâmicos.
- `bash scripts/check-tokens.sh hero-memory/visualizer`: 3 arquivos aprovados.
- `git diff --check`: aprovado.

## Ensaio do visualizador

`scripts/tests/smoke_memory_viewer.py` gera índice, nota Markdown e grafo
temporários com 10.000 nós e 30.000 relações. Verifica janela QML, layout de
todos os nós, consulta FTS5 real e rejeição de traversal na prévia.

Última execução, após retirar a fixture Python da memória antes da abertura:

```json
{"first_frame_ms":288,"layout_ms":7606,"nodes":10000,"max_rss_mib":360.4}
```

O primeiro quadro é a janela responsiva com estado de carga; não é o grafo já
organizado. Execuções anteriores: 195–474 ms no primeiro quadro e 5,7–6,3 s
no layout. O pico RSS é do processo de teste completo e **excede 150 MB**;
não foi medido consumo isolado em sessão Plasma nem taxa de 60 fps. O runtime
emitiu um aviso Qt `QObject::connect(QJSEngine, QtObject): invalid nullptr
parameter`, sem impedir janela, layout ou consultas; investigar no build final.

[Captura offscreen do grafo sintético](graph-offscreen.png). É evidência de
renderização, não aprovação de fidelidade visual ao protótipo.

## Limites e artefatos

A [issue #112](https://github.com/forjaos-project/forjaos/issues/112) acompanha
consumo, 60 fps, fidelidade visual e uso dos clientes reais no Linux de referência.
FR-135 não tem aceitação integral. A ADR-019 continua exigindo prova antes de
considerar QtWebEngine. A integração de software é a issue #111.

Não foram criados containers, imagens nem caches Docker para esta tarefa.
Serviços e volumes compartilhados foram preservados. O runtime Python auxiliar
está em `D:\ForjaOS\validation\f4-006-python`; a captura original está em
`D:\ForjaOS\validation\f4-006-graph.png`. Compilação usou o target Rust
compartilhado já existente em `/home/rodri/forjaos-hero-target`; não removê-lo
como cache exclusivo deste item. Gate inicial do host: 185,15 GiB livres no C:.
