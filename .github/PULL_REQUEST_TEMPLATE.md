<!-- Fluxo: docs/dev/METHODOLOGY.md — nenhum campo fica vazio. PR incompleto não entra em review. -->

## Requisitos

- IDs do PRD cobertos (`FR-` / `NFR-` / `ADR-`): 
- Itens do roadmap (`docs/roadmap/roadmap.json`) entregues por este PR: 

## Plano

- Plano seguido: `docs/superpowers/plans/AAAA-MM-DD-<slug>.md`
- Spec de origem (se houver): `docs/superpowers/specs/…`

## Tela (apagar a seção se não houver tela)

- Spec da tela: `docs/design-system/telas/<slug>.md` (hash conferido com `python3 scripts/gen_tela_specs.py --check`)
- Captura lado a lado: `docs/design-system/telas/<slug>/compare-AAAA-MM-DD.png`
- Medidas-chave conferidas (largura/altura/raio/gap): 
- Substituições do ADR-028 aplicadas: ☐

## Gates

- [ ] **plan** — plano commitado; toda tarefa cita um ID do PRD
- [ ] **code** — branch pela convenção; um commit por tarefa; TDD; commits convencionais
- [ ] **test** — verificação da raiz + da pasta passou (saída abaixo); `check-tokens.sh` OK; `roadmap.py validate --branch` OK
- [ ] **review** — revisão cruzada concluída com `review: 8/8` (e `visual: fiel` se tela)
- [ ] **ship** — `scripts/roadmap.py done <ID> --pr N` executado; só o item deste PR mudou no `roadmap.json`; `STATUS.md`/`index.html` fora do diff

## Quem fez o quê

- Implementado por: ☐ Claude Code ☐ Codex ☐ humano
- Revisado por (obrigatoriamente **outra** ferramenta/pessoa): ☐ Claude Code ☐ Codex ☐ humano

## Saída da verificação

```text
(cole aqui a saída de: python3 -m unittest discover -s scripts/tests -p 'test_*.py' && scripts/run-shell-tests.sh && scripts/check-tokens.sh && scripts/check-agents-sync.sh && python3 scripts/roadmap.py validate --branch  + comando da pasta)
```

## Segurança e consumo

- [ ] Nenhum segredo em arquivo, log ou nesta descrição (NFR-024)
- [ ] Units systemd novas declaram `MemoryMax`, `CPUQuota`, `Nice`
- [ ] SELinux, firewalld, `/etc` e tiers do Policy Engine intocados fora do escopo declarado
- [ ] Dependência nova: licença verificada e justificada no commit

## Notas para o revisor

(decisões tomadas, divergências encontradas entre protótipo e PRD, o que ficou fora e por quê)
