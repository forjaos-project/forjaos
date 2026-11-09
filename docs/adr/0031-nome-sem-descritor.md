# ADR-031 — O nome do SO é só "ForjaOS" (sem descritor)

**Status:** aceito · **Data:** 2026-11-09 · **Revoga:** parte do ADR-004 (o descritor "DeveloperOS") · **Relacionados:** ADR-004, ADR-028, FR-003

## Contexto

O ADR-004 fixou o nome "ForjaOS" com o descritor "DeveloperOS". O descritor chegou ao `PRETTY_NAME` do `/etc/os-release` (FR-003) e passaria a aparecer em tudo o que lê esse campo. O nome já estava definido e o descritor não é desejado.

## Decisão

1. O nome do produto é **ForjaOS**, sem descritor, em qualquer superfície (código, imagem, site, marketing).
2. FR-003: `PRETTY_NAME="ForjaOS X.Y"`.
3. "DeveloperOS" deixa de ser nome ou descritor e permanece apenas como string a substituir quando aparecer em protótipos (ADR-028). O restante do ADR-004 (ForjaOS em vez de "DeveloperOS" sozinho ou Ipê) continua valendo.
4. `docs/analise/` é registro histórico da análise de 2026-11-08 e não é reescrito.

## Consequências

- PRD (ADR-004, FR-003), ADR-028 e `scripts/gen_tela_specs.py` atualizados; specs de tela regeneradas se o texto delas mudar.
- Itens de imagem (F0-002 em diante) usam o `PRETTY_NAME` novo.
