# ADR-0040 — Build de ISO manual, fora do pull request

**Status:** aceito · **Data:** 2026-11-13 · **Aprovação:** mantenedor · **Relacionados:** F1-002, FR-010, NFR-011, ADR-0036, ADR-0039

## Contexto

Cada atualização do PR F1-002 disparava novos builds das duas ISOs e testes de boot no GitHub Actions, mesmo quando o commit novo só registrava evidência. O mantenedor escolheu construir e validar as ISOs de teste no PC local, com saída no D:, e publicar a ISO somente no fluxo final.

## Decisão

- O workflow `iso` não roda automaticamente em `pull_request`.
- O build continua disponível por `workflow_dispatch`. Uma execução sem `release_tag` produz apenas ativos de teste, sem assinatura de blob ou publicação.
- O fluxo de release final continua manual, restrito à `main`, com assinatura e publicação verificadas.
- O CI de PR mantém verificações estáticas e unitárias; os builds locais das duas variantes, seus hashes e as evidências de boot/instalação física são registrados no PR.
- Esta decisão revoga a exigência de build e boot automáticos de cada PR descrita no ADR-0036. Não altera a verificação assinada do payload, os limites de tamanho nem a assinatura da ISO final.

## Consequências

Commits de código ou documentação no PR deixam de consumir runners em builds de ISO. A revisão depende dos resultados locais versionados e dos gates estáticos do CI. O build remoto pode ser executado manualmente quando necessário.
