# ADR-0035 — Distribuição da ISO de instalação do ForjaOS

**Status:** aceito · **Data:** 2026-11-12 · **Aprovação:** mantenedor, 2026-11-12 · **Revoga parcialmente:** ADR-002 e ADR-021 quanto ao construtor da ISO · **Relacionados:** F1-002, FR-004, FR-010, FR-014, NFR-011, ADR-024, ADR-0034

## Contexto verificado

O PR #50 construiu ISOs Anaconda interativas com `bootc-image-builder --type bootc-installer`, usando um digest assinado para cada variante. O CI [43259935854](https://github.com/forjaos-project/forjaos/actions/runs/43259935854) mediu 9.938.606.080 bytes para `forjaos.iso` e 10.805.409.792 bytes para `forjaos-nvidia-open.iso`. Os dois builds falharam no verificador de 6.000.000.000 bytes. O `verify` do mesmo HEAD passou; isso não comprova o DoD da ISO. O teste de ciclo em VM ainda estava em andamento na última consulta.

O PRD limita cada ISO a 6 GB (NFR-011, também citado em FR-004) e exige ISO, SHA-256 e assinatura no GitHub Release (FR-010). O [GitHub limita cada asset de Release a menos de 2 GiB](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases). Assim, mesmo uma ISO offline entre 2 GiB e 6 GB não pode ser publicada como arquivo único no Release. O PRD também exige a gravação e o boot por três métodos (FR-014); o CI ainda não pode substituir essa prova física.

O tipo `bootc-installer` embute o payload OCI na ISO. Os manifests comprimidos dos payloads usados no CI somam aproximadamente 4,87 GB (genérica) e 5,25 GB (NVIDIA), antes do ambiente Anaconda e da estrutura da mídia. Esses tamanhos são diagnóstico, não limite inferior matemático da ISO final. A alternativa de instalador menor requer decidir se o payload pode ser baixado durante a instalação e verificar a assinatura também nessa etapa.

A [documentação atual do Image Builder](https://osbuild.org/docs/developer-guide/projects/image-builder/advanced/bootc/isos/) descreve `generic-iso` com Anaconda e payload por registro remoto; o payload só é embutido quando `--bootc-installer-payload-ref` é fornecido. O [projeto upstream incorporou o `bootc-image-builder` ao `image-builder`](https://github.com/osbuild/image-builder/blob/main/bootc-image-builder/README.md). Essas fontes demonstram um caminho técnico para o protótipo, mas não provam o tamanho final nem a verificação de assinatura do ForjaOS.

## Decisão

O mantenedor aprovou a opção A em 2026-11-12: cada variante terá uma ISO Anaconda de instalação **por rede**, construída pelo `image-builder` com o tipo `generic-iso`. O payload ForjaOS fica no GHCR e é referenciado por digest imutável. O construtor verifica a assinatura desse digest antes do build; o instalador deve exigir a mesma chave pública e verificar a assinatura no download, falhando fechado se a verificação ou a rede falhar. Não há instalação desassistida nem seleção automática de disco.

O limite de 6 GB do NFR-011 permanece. Para publicação como arquivo único no GitHub Release, cada ISO também deve medir menos de 2 GiB. O CI mede ambas as variantes e prova checksum, assinatura da ISO, boot do instalador e instalação a partir do digest assinado. A validação de pendrive e hardware real do ADR-024/FR-014 continua obrigatória para o aceite de release. A necessidade de rede deve constar no guia e no download.

ADR-002 e ADR-021 continuam válidos quanto a bootc/OCI, cosign, GHCR e Anaconda sem instalador próprio. Apenas a referência ao antigo `bootc-image-builder` como construtor da ISO é substituída por `image-builder generic-iso`.

## Alternativas não escolhidas

### Manter ISO offline

Reduzir payload e ambiente instalador até as duas ISOs ficarem ≤ 6 GB, mantendo Anaconda e payload embutido. Se cada arquivo ainda ficar ≥ 2 GiB, publicar partes menores que 2 GiB no GitHub Release com reconstrução documentada e SHA-256 do arquivo reconstruído, ou aprovar um destino de distribuição próprio. Medir e testar a reconstrução, assinatura, gravação e boot antes da entrega.

**Impacto:** mantém instalação sem rede, mas exige redução grande frente aos tamanhos observados e distribuição em partes ou infraestrutura adicional. O objetivo de pendrive de 8 GB do PRD só permanece válido se o arquivo final couber.

### Alterar o limite de tamanho

Aceitar ISOs offline próximas aos tamanhos medidos e mudar NFR-011, FR-004, documentação de mídia e distribuição por novo ADR. O limite de 2 GiB por asset continua exigindo partes ou destino próprio.

**Impacto:** menor mudança no construtor atual, mas altera uma meta explícita de produto e a mídia mínima; não resolve sozinho a publicação.

## Consequências e verificação

F1-002 permanece `doing` até o build real, a publicação verificável, a revisão `8/8` e as provas físicas exigidas. Nenhuma ISO pode ser anunciada como release antes desses gates. O inventário de licenças do ambiente instalador acompanha a prova de distribuição (G4). O CI deve falhar se o digest no Kickstart divergir do digest verificado ou se a política de assinatura estiver ausente.
