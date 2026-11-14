# ADR-0039 — Build local e testes sem assinatura da ISO

**Status:** aceito · **Data:** 2026-11-13 · **Aprovação:** mantenedor · **Substitui:** ADR-0036 · **Relacionados:** F1-002, FR-010, FR-014, NFR-011, ADR-0035

## Decisão

- Construir e validar as ISOs de teste no PC do mantenedor, usando o payload `:testing` verificado pelo digest e pela assinatura já publicados.
- Manter as ISOs de teste sem assinatura de blob e no disco local `D:`. Teste de boot, instalação em VM e gravação física não pedem acesso à chave privada nem publicação de release candidata.
- Só depois da aceitação local, produzir a ISO final, assinar o arquivo com a chave cosign oficial e publicar a ISO, o checksum e o inventário de licenças como assets do GitHub Release. A ISO não entra no histórico Git.
- Os testes continuam verificando tamanho, checksum, conteúdo do initramfs e inicialização. A assinatura do payload do sistema permanece obrigatória; apenas a assinatura da ISO de teste foi removida.
- O build usa o SSD C: para armazenamento temporário do Podman, com a reserva do host em vigor; os ISOs e evidências ficam no D:.

## Motivo

Os testes de assinatura em ISO candidata e a publicação de releases `rc.N` acrescentavam espera sem ajudar a validar Wi-Fi, boot ou instalação. A assinatura protege o artefato distribuído ao público; não é necessária para validar localmente uma ISO de teste.

## Efeito

O workflow de ISO não assina builds de PR nem publica releases candidatas. A assinatura permanece obrigatória no caminho de release final. A distribuição continua respeitando o limite de 6 GB e o limite de asset inferior a 2 GiB.
