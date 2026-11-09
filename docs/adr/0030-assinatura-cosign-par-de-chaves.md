# ADR-030 — Assinatura da imagem com par de chaves cosign (não keyless)

**Status:** aceito · **Data:** 2026-11-08 · **Relacionados:** ADR-002, NFR-023, NFR-024, G6

## Contexto

O ADR-002 fixa cosign + GHCR para a imagem, e a NFR-023 exige que o `bootc` verifique a assinatura com `--enforce-container-sigpolicy`. Essa verificação é feita pelo `containers/image` a partir do `/etc/containers/policy.json` (requisito `sigstoreSigned`).

O cosign oferece dois modos:

- **Keyless** (OIDC do Actions + Fulcio + Rekor): sem segredo para guardar. Porém, até maio de 2026 o `containers/image` só casa a identidade do certificado Fulcio por e-mail (`subjectEmail`); certificados emitidos para workflows de CI trazem a identidade como URI, então a verificação no cliente falha. Há proposta de suporte (`subjectURI`/regex, plugins de política), sem implementação liberada.
- **Par de chaves**: a chave privada assina no CI; a chave pública vai na imagem e no `policy.json` (`keyPath`). É o padrão de todo o ecossistema Universal Blue (`ublue-os/image-template`, Bazzite, Bluefin) e é verificado pelo `bootc` hoje.

## Decisão

1. A imagem é assinada com **par de chaves cosign**. Keyless não é usado enquanto o `containers/image` não verificar identidades de CI.
2. A chave pública fica em `cosign.pub`, na raiz do repositório (convenção Universal Blue). F0-002 a copia para `/etc/pki/containers/` e referencia no `policy.json` da imagem.
3. A chave privada existe só no secret `SIGNING_SECRET` do repositório e num backup em gerenciador de senhas do mantenedor. Nunca em arquivo versionado, log ou descrição de PR (NFR-024); `.gitignore` bloqueia `cosign.key` e `cosign.private`.
4. Agentes não geram nem manipulam a chave privada: o par é gerado e o secret é cadastrado pelo humano (`docs/dev/SIGNING.md`).
5. O workflow `signing-preflight` confirma que a chave do secret corresponde à `cosign.pub` versionada.

## Consequências

- Existe um segredo a proteger e rotacionar. Rotação: novo par, troca do secret e da `cosign.pub` no mesmo PR; imagens anteriores deixam de verificar com a chave nova, então a rotação coincide com uma nova imagem `:testing`/`:stable`.
- Perda da chave privada sem backup obriga rotação; vazamento obriga rotação imediata.
- Quando o `containers/image` verificar identidades de CI, um novo ADR pode migrar para keyless e eliminar o segredo.
