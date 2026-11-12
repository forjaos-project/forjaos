# ADR-0035 — Distribuição da ISO de instalação do ForjaOS

**Status:** proposto, decisão do mantenedor pendente · **Data:** 2026-11-12 · **Relacionados:** F1-002, FR-004, FR-010, FR-014, NFR-011, ADR-002, ADR-021, ADR-024, ADR-0034

## Contexto verificado

O PR #50 construiu ISOs Anaconda interativas com `bootc-image-builder --type bootc-installer`, usando um digest assinado para cada variante. O CI [43259935854](https://github.com/forjaos-project/forjaos/actions/runs/43259935854) mediu 9.938.606.080 bytes para `forjaos.iso` e 10.805.409.792 bytes para `forjaos-nvidia-open.iso`. Os dois builds falharam no verificador de 6.000.000.000 bytes. O `verify` do mesmo HEAD passou; isso não comprova o DoD da ISO. O teste de ciclo em VM ainda estava em andamento na última consulta.

O PRD limita cada ISO a 6 GB (NFR-011, também citado em FR-004) e exige ISO, SHA-256 e assinatura no GitHub Release (FR-010). O [GitHub limita cada asset de Release a menos de 2 GiB](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases). Assim, mesmo uma ISO offline entre 2 GiB e 6 GB não pode ser publicada como arquivo único no Release. O PRD também exige a gravação e o boot por três métodos (FR-014); o CI ainda não pode substituir essa prova física.

O tipo `bootc-installer` embute o payload OCI na ISO. Os manifests comprimidos dos payloads usados no CI somam aproximadamente 4,87 GB (genérica) e 5,25 GB (NVIDIA), antes do ambiente Anaconda e da estrutura da mídia. Esses tamanhos são diagnóstico, não limite inferior matemático da ISO final. A alternativa de instalador menor requer decidir se o payload pode ser baixado durante a instalação e verificar a assinatura também nessa etapa.

## Opções para decisão

### A — ISO de instalação por rede (recomendação técnica)

Gerar uma ISO Anaconda enxuta para cada variante, com referência imutável ao digest do payload; exigir conexão durante a instalação. Medir as duas ISOs reais, exigir ≤ 6 GB e, para publicação direta no GitHub Release, < 2 GiB cada. Verificar a assinatura do payload no ambiente instalador antes da gravação do sistema e testar o boot/instalação em VM e em mídia física. Se o tipo `generic-iso` ou o `image-builder` sucessor for necessário, atualizar explicitamente ADR-002/ADR-021 e a descrição do FR-010; não trocar o construtor por inferência. O guia deve declarar a necessidade de rede.

**Impacto:** preserva o limite e a publicação de arquivo único se as medidas confirmarem < 2 GiB; a instalação passa a depender de rede e de disponibilidade do registro. Nenhum resultado de tamanho ou funcionamento é presumido antes do CI real.

### B — Manter ISO offline

Reduzir payload e ambiente instalador até as duas ISOs ficarem ≤ 6 GB, mantendo Anaconda e payload embutido. Se cada arquivo ainda ficar ≥ 2 GiB, publicar partes menores que 2 GiB no GitHub Release com reconstrução documentada e SHA-256 do arquivo reconstruído, ou aprovar um destino de distribuição próprio. Medir e testar a reconstrução, assinatura, gravação e boot antes da entrega.

**Impacto:** mantém instalação sem rede, mas exige redução grande frente aos tamanhos observados e distribuição em partes ou infraestrutura adicional. O objetivo de pendrive de 8 GB do PRD só permanece válido se o arquivo final couber.

### C — Alterar o limite de tamanho

Aceitar ISOs offline próximas aos tamanhos medidos e mudar NFR-011, FR-004, documentação de mídia e distribuição por novo ADR. O limite de 2 GiB por asset continua exigindo partes ou destino próprio.

**Impacto:** menor mudança no construtor atual, mas altera uma meta explícita de produto e a mídia mínima; não resolve sozinho a publicação.

## Decisão pendente

O mantenedor deve escolher o comportamento de instalação e a distribuição antes de alterar o pipeline ou o PRD. Até lá, F1-002 permanece `doing`, o PR #50 não atende `review: 8/8` nem CI verde, e nenhuma ISO deve ser anunciada como release. Após a escolha, registrar a decisão aprovada neste ADR, atualizar o plano e executar os cinco gates do repositório. O inventário de licenças do ambiente instalador deve acompanhar a prova de distribuição (G4).
