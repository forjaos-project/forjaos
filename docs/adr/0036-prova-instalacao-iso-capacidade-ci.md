# ADR-0036 — Prova de instalação da ISO e capacidade do CI

**Status:** aceito · **Data:** 2026-11-12 · **Aprovação:** mantenedor, 2026-11-12 (opção B) · **Revoga parcialmente:** ADR-0035, somente quanto ao local de execução da instalação completa em VM · **Relacionados:** F1-002, FR-010, FR-014, NFR-011, NFR-020, ADR-024, ADR-0033

## Contexto verificado

O ADR-0035 exige que o CI prove a instalação a partir do digest assinado. O workflow atual constrói as duas ISOs, verifica tamanho, SHA-256 e assinatura, e inicializa cada ISO em VM até a tela do Anaconda. O teste de boot encerra a VM nessa tela; ele não instala o sistema.

O [runner Linux padrão para repositórios públicos do GitHub Actions](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) oferece 14 GB de SSD. O ensaio local do F1-002 usou um disco virtual de 32 GiB e o arquivo QCOW2 chegou a cerca de 25 GB durante a instalação do payload genérico. O Anaconda registrou 271 camadas, 4,9 GB compactados, `Installation complete!` e `Complete!`; após um reinício de configuração inicial, o disco alcançou `forjaos login:`. Essa primeira prova usou uma ISO diagnóstica reconstruída localmente, identificada em `docs/evidence/f1-002/local-network-install-2026-11-12.md`. Depois, os dois assets exatos da candidata `v0.1.0-rc.1` foram instalados e iniciaram do disco virtual, conforme `docs/evidence/f1-002/candidate-v0.1.0-rc.1-vm.md`. Não há runner maior configurado para o projeto.

Uma instalação completa no runner padrão não cabe no armazenamento observado. Declarar o boot da tela como instalação completa esconderia a diferença entre os gates.

## Decisão

Para F1-002, o CI de PR continua obrigatório para as duas variantes: build real, tamanho, checksum, assinatura, política de assinatura do payload, digest fixo e boot até o Anaconda. A instalação completa do **asset exato** de cada variante da candidata publicada é executada em VM local com armazenamento suficiente, usando procedimento reproduzível e disco descartável. O registro versionado deve incluir versão, SHA-256 da ISO, digest do payload, comando de boot, saída de conclusão do Anaconda e boot do disco instalado. O revisor em contexto limpo verifica os registros e repete ao menos uma instalação quando o ambiente permitir.

As provas físicas de Fedora Media Writer, Ventoy e `dd`, o hardware, o estado do Secure Boot e a revisão `8/8` continuam obrigatórios antes de declarar FR-014 aceito. Uma ISO diagnóstica não substitui o asset da candidata. Nenhuma falha de assinatura, ausência de rede ou instalação incompleta pode ser registrada como sucesso.

Essa decisão substitui apenas a exigência de **instalação completa dentro do runner padrão** do ADR-0035. Os demais requisitos do ADR-0035 permanecem: ISO por rede, digest imutável, assinatura verificada no build e na instalação, limite de 6 GB e asset menor que 2 GiB no GitHub Release.

## Alternativa

Configurar runner próprio ou runner maior com pelo menos 64 GB de armazenamento disponível e manter a instalação completa das duas variantes dentro do GitHub Actions. Isso recupera um gate automático de PR, mas exige infraestrutura, credenciais, manutenção e capacidade ainda não configuradas. Nesse caminho, o teste local serve apenas como diagnóstico até o runner estar operacional.

## Condição de aceite

O F1-002 só avança após registrar instalação completa e boot do disco para os dois assets exatos da candidata, além das provas físicas e da revisão independente.
