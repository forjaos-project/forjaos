# Guará estático v1 — F0-007

## Objetivo e fonte

Entregar cinco SVGs vetoriais do lobo-guará para os estados `idle`, `listening`, `thinking`, `speaking` e `error` (FR-054). O mantenedor escolheu a direção **A, geométrica e legível em 24 px**, entre as três opções da [prévia](../../../brand/mascot/preview/guara-concepts-2026-11-10.png). A imagem é referência de forma, não um recurso embarcado. A spec do plasmoid `docs/design-system/telas/forjaos_plasmoid_do_guar_kde_plasma_6.md` define estados e camadas; `brand/palette.json` define as cores.

## Desenho

- Cabeça frontal simétrica em `viewBox="0 0 512 512"`: orelhas altas com pontas escuras, face laranja, juba angular nas bochechas, focinho claro e nariz escuro. A juba e as orelhas diferenciam o Guará de uma raposa genérica. Sem texto, bitmap ou referência externa.
- Os seis grupos `body`, `ears`, `eyes`, `mouth`, `glow` e `badge` mantêm geometria e IDs estáveis entre os estados para futura animação QML. O traço principal, os olhos e o nariz continuam legíveis ao reduzir a 24 px.
- `idle`: olhos tranquilos, boca neutra e anel discreto em `text-muted`; `listening`: olhos atentos, anel ciano e duas ondas curtas; `thinking`: olhar focado, anel violeta e pequeno arco orbital; `speaking`: boca aberta, anel laranja e ondas laterais; `error`: olhos em X, boca curta e anel `danger`.
- Usar apenas valores de `brand/palette.json`: pele `accent-orange` → `accent-orange-soft`, focinho `tertiary` e contorno `void`; estados seguem `mascot.state_colors`. O fundo permanece transparente para funcionar em claro e escuro.

## Arquivos e validação

- `brand/mascot/build_guara.py` gera os cinco SVGs de forma determinística a partir da paleta, sem dependência nova. `--check` falha quando um artefato diverge.
- `brand/mascot/guara-<state>.svg` são os recursos versionados. `brand/mascot/preview/guara-concepts-2026-11-10.png` guarda somente a referência aprovada; uma comparação de estados em 512 px e 24 px acompanha o PR.
- `brand/tests/test_guara.py` verifica estados, seis IDs, cores da paleta, ausência de texto/bitmap/links externos, e consistência da silhueta. `scripts/check-tokens.sh` deve passar.
- `brand/LICENSES.md` registra os SVGs como arte própria CC BY-SA 4.0; o gerador é Apache-2.0.

## Limite do item

F0-007 cobre os cinco estados estáticos e a interface de camadas. Os 15 visemes e a animação a 60 fps pertencem à implementação do plasmoid (FR-054/FR-123), e não são declarados como entregues neste item. Nenhuma tela, unit ou arquivo em `/etc` muda.
