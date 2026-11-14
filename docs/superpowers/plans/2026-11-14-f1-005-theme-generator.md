# F1-005 — Gerador de temas a partir da paleta

## Goal

Implementar a geração determinística dos formatos de tema previstos em FR-051 a partir de `brand/palette.json`, preservando o gerador Plasma existente e adicionando alvos SDDM, Plymouth, Konsole, VS Code e GTK. O Firefox fica como saída opcional de userChrome, conforme PRD. Não alterar valores existentes da paleta; isso exigiria novo ADR-027.

## Architecture

- `brand/palette.json` continua sendo a única fonte de valores de cor, tipografia e dimensões.
- `brand/plasma/build_plasma.py` permanece responsável pelos artefatos Plasma já existentes.
- Um orquestrador em `brand/themes/build_themes.py` converte tokens para os formatos de cada alvo, chama o gerador Plasma e oferece `--check` determinístico para CI.
- Cada formato recebe arquivos escuro/claro gerados em sua pasta dentro de `brand/`; artefatos gerados não são editados manualmente.
- Conversões de transparência ou cor opaca usam tokens presentes na paleta; o gerador falha com mensagem objetiva quando um token necessário estiver ausente.
- Apenas biblioteca padrão Python; nenhuma dependência nova, repositório externo ou licença.

## Tech Stack

Python 3 (biblioteca padrão), JSON, CSS/QSS, INI, SVG e arquivos de tema próprios dos formatos alvo. Testes `unittest` existentes de `brand/tests/` são executados no CI.

## File map

- `brand/themes/build_themes.py` — conversão dos tokens, renderizadores por formato e gravação/check de saídas.
- `brand/plasma/build_plasma.py` — integração do Plasma ao fluxo unificado, mantendo a API existente.
- `brand/sddm/`, `brand/plymouth/`, `brand/konsole/`, `brand/vscode/`, `brand/gtk/`, `brand/firefox/` — ativos gerados para cada consumidor.
- `brand/tests/test_theme_generator.py` — cobertura do contrato, conteúdo, paleta e idempotência de cada destino.
- `brand/LICENSES.md` — registrar os geradores e os formatos como código/arte próprios, sem novas licenças.
- `docs/superpowers/plans/2026-11-14-f1-005-theme-generator.md` — este plano.

## Tasks

### 1. Definir e testar contrato do gerador unificado — FR-051

- Arquivos: `brand/tests/test_theme_generator.py`.
- Teste: executar os testes novos antes da implementação e observar falha por ausência do gerador/artefatos; validar targets escuro/claro, paleta, saída opcional Firefox e modo `--check`.
- DoD: testes especificam caminhos estáveis para Plasma, SDDM, Plymouth, Konsole, VS Code, GTK e Firefox opcional sem exigir ferramenta externa.
- Commit: `test(brand): define generated theme contracts`.

### 2. Implementar renderizadores de formatos e orquestração — FR-051

- Arquivos: `brand/themes/build_themes.py`, saídas em `brand/{sddm,plymouth,konsole,vscode,gtk,firefox}/`.
- Teste: os contratos da tarefa 1 passam; duas execuções idênticas produzem bytes idênticos; `--check` detecta saída ausente ou alterada.
- DoD: cada saída dark/light deriva dos tokens e contém apenas tokens admitidos; transparência é achatada sobre `canvas` quando o formato exigir opacidade; Firefox só é escrito quando solicitado.
- Commit: `feat(brand): generate themes from canonical palette`.

### 3. Integrar Plasma, documentar licença e validar o fluxo — FR-051

- Arquivos: `brand/plasma/build_plasma.py`, `brand/tests/test_theme_generator.py`, `brand/LICENSES.md`.
- Teste: gerador unificado atualiza os artefatos Plasma existentes sem divergência funcional; rodar `python3 -m unittest discover -s brand/tests -p 'test_*.py'`, `scripts/check-tokens.sh`, `scripts/gen_tela_specs.py --check` e `python3 brand/themes/build_themes.py --check`.
- DoD: CI existente roda os novos testes de `brand/tests/`; nenhum novo job/dependência é necessário; os ativos de tema estão descritos como gerados e os limites de captura visual do release continuam explícitos.
- Commit: `docs(brand): document generated theme assets`.

## Gates

- /test executa também suíte de raiz e `brand/tests/` conforme `AGENTS.md`; cada saída é revisada para formato e conteúdo.
- FR-051 pede captura de cada superfície no release. Este item comprova geração e determinismo dos formatos; captura em runtime fica limitada a consumidores instalados/disponíveis neste ambiente e será registrada separadamente, sem alegar uma captura inexistente.
- /review deve verificar o diff e o histórico em contexto limpo; /ship só após `review: 8/8` e CI verde.
