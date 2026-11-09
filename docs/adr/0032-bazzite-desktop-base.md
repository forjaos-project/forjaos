# ADR-0032 — Bases Bazzite desktop publicadas para as imagens ForjaOS

**Status:** aceito · **Data:** 2026-11-09 · **Revoga:** somente a escolha das imagens base no ADR-001 · **Relacionados:** ADR-001, ADR-003, FR-001, F0-002

## Contexto

O ADR-001 indicava `ghcr.io/ublue-os/bazzite-dx-nvidia-open:stable`, mas essa referência não é publicada. As variantes publicadas de Bazzite DX são geradas a partir de `bazzite-deck*`, conforme a [pipeline oficial de `ublue-os/bazzite-dx`](https://raw.githubusercontent.com/ublue-os/bazzite-dx/main/.github/workflows/build.yml): a matriz `base_image` lista `bazzite-deck`, `bazzite-deck-gnome`, `bazzite-deck-nvidia-gnome` e `bazzite-deck-nvidia`; o nome DX é derivado dessas bases. A [documentação do Bazzite](https://docs.bazzite.gg/General/FAQ/) informa que as variantes Deck iniciam no Steam Gaming Mode, enquanto `bazzite` e `bazzite-nvidia-open` são variantes desktop Plasma sem esse modo. A linha Deck conflita com o Plasma como sessão padrão do ADR-003.

## Evidência verificada em 2026-11-09

`skopeo version 1.22.3` foi executado pelo contêiner `quay.io/skopeo/stable:latest`, sem instalar ferramentas no host:

```sh
skopeo inspect docker://ghcr.io/ublue-os/bazzite-nvidia-open:stable
# Name: ghcr.io/ublue-os/bazzite-nvidia-open
# Digest: sha256:9c3c4df94a7731238021549ed3fc951c3ae5e1fee37667d16754f37ae0f73134
# Architecture: amd64
# Labels.containers.bootc: 1

skopeo inspect docker://ghcr.io/ublue-os/bazzite:stable
# Name: ghcr.io/ublue-os/bazzite
# Digest: sha256:3c67436e214fe34be11565cd3f0065789b1f107984ab247ca6cea4bcd2c94597
# Architecture: amd64
# Labels.containers.bootc: 1
```

A imagem NVIDIA foi baixada e o módulo nela foi inspecionado diretamente:

```sh
docker run --rm --entrypoint /bin/sh ghcr.io/ublue-os/bazzite-nvidia-open:stable -c \
  "find /usr/lib/modules -path '*/extra/nvidia/nvidia.ko*' -print"
# /usr/lib/modules/7.2.15-ogc1.1.fc45.x86_64/extra/nvidia/nvidia.ko.xz

docker run --rm --entrypoint /bin/sh ghcr.io/ublue-os/bazzite-nvidia-open:stable -c \
  "modinfo /usr/lib/modules/*/extra/nvidia/nvidia.ko* | grep -i '^license'"
# license:        Dual MIT/GPL
```

Os digests são evidência pontual das tags `stable` consultadas nessa data; novas publicações podem movê-las. A licença `Dual MIT/GPL` foi observada no módulo `nvidia.ko.xz` dessa imagem, sem inferir a licença de todos os demais componentes.

## Decisão

1. `forjaos-nvidia-open` deriva de `ghcr.io/ublue-os/bazzite-nvidia-open:stable`.
2. `forjaos` deriva de `ghcr.io/ublue-os/bazzite:stable`.
3. Os nomes das imagens ForjaOS, o modelo Fedora Atomic/Universal Blue do ADR-001 e o Plasma padrão do ADR-003 permanecem. Este ADR revoga somente as duas referências de imagem base do ADR-001.
4. A camada de ferramentas DX será um item separado após F0-002, a partir dos scripts de `ublue-os/bazzite-dx` com verificação de licenças antes da inclusão de componentes. F0-002 não instala essa camada.

## Consequências

- FR-001 e o PRD passam a apontar para bases desktop que existem no registro.
- O `Containerfile` mínimo pode ser construído sobre a base NVIDIA sem herdar a linhagem Deck.
- A equivalência funcional da camada DX depende do item específico do roadmap, sem alterar o escopo de F0-002.
