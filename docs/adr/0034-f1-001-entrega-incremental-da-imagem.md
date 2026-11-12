# ADR-0034 — Entrega incremental dos pacotes e serviços da imagem

**Status:** proposto · **Data:** 2026-11-12 · **Relacionados:** FR-004, FR-005, FR-006, FR-007, F1-001, F1-002, F1-009, F1-010, ADR-0032

## Contexto

O item F1-001 agrupa quatro requisitos cujo DoD depende de entregas posteriores. FR-004 exige uma ISO de até 6 GB, mas a geração da ISO pertence ao F1-002. FR-005 exige que `forja doctor` reporte cada componente, mas a CLI será implementada no F1-009; `herod` e `memd` pertencem a fases posteriores. A camada DX da base desktop pertence ao F1-010 por decisão do ADR-0032.

O inventário de RPM da imagem `forjaos:testing` produzida pelo workflow `daily-image` de 2026-11-12 (run 43201943595) contém `podman`, `distrobox`, `steam`, `firewalld`, `audit`, `btop`, `nvtop` e `forjaos-branding`. Não contém Docker CE, VS Code, `forja`, `herod`, `memd` nem `gamescope` como RPM. Esse inventário não mede Flatpaks nem executáveis instalados fora do RPM.

O PRD pede o RPM oficial do VS Code, mas a [licença do produto Microsoft](https://code.visualstudio.com/license) difere da licença MIT do código-fonte. O DoD local de `image/AGENTS.md` proíbe embarcar pacote proprietário na imagem sem decisão explícita. A [documentação oficial de instalação Linux](https://code.visualstudio.com/docs/setup/linux) oferece RPM e repositório da Microsoft; adicionar esse repositório também requer decisão pela regra 12 do `AGENTS.md`.

## Decisão proposta

1. F1-001 entrega apenas o conjunto de pacotes da base e a política de serviços que podem ser instalados e testados sem componentes ainda inexistentes. A lista de remoção identifica pacotes presentes nas duas variantes e preserva Steam, codecs e suporte de controles. O CI inspeciona os RPMs e o estado de habilitação dos serviços na imagem construída.
2. F1-002 mede e aprova o limite de 6 GB na ISO real. F1-009 implementa `forja doctor` e verifica a presença dos componentes. F1-010 entrega os componentes DX conforme ADR-0032. As unidades `herod` e `memd` entram quando seus próprios componentes forem implementados, com limites de recursos.
3. Pacotes ou repositórios de terceiros e software com licença fora da política atual não entram na imagem por inferência do FR-005. Uma decisão própria deverá definir a instalação do RPM oficial do VS Code, Docker CE e demais componentes não disponíveis na base, inclusive se ocorrerá por recipe ou na imagem. Instalar pelo usuário não equivale a embarcar o binário na imagem.
4. O FR-004 a FR-007 permanecem requisitos do produto. O fechamento de F1-001 atesta apenas a parcela definida no item 1; os gates completos permanecem atribuídos aos itens dependentes acima. A rastreabilidade do roadmap precisa registrar explicitamente essas dependências antes do merge de F1-001.

## Consequências

- F1-001 pode ser revisado com evidência real sem declarar que a ISO, o doctor ou daemons futuros já existem.
- O PRD mantém o conteúdo de release; este ADR altera a ordem e o critério de fechamento do item de roadmap.
- A composição final de pacotes e licenças segue pendente da decisão citada no item 3.
