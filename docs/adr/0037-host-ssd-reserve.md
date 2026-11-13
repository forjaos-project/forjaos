# ADR-0037 — Reserva de espaço no SSD do host de desenvolvimento

**Status:** aceito · **Data:** 2026-11-12 · **Aprovação:** mantenedor, 2026-11-12 · **Relacionados:** GOV-012, NFR-040, NFR-042, F1-002

## Contexto

Os builds e testes locais da ISO do ForjaOS fizeram o C: do Windows cair de cerca de 160 GiB livres para 5 GiB. O VHDX do Docker Desktop com WSL 2 cresceu no SSD e a limpeza interna do Docker, sozinha, não devolveu o espaço ao Windows. O C: contém o Windows e é SSD; o D: é HD. Transferir o armazenamento ativo do Docker ao D: causaria contenção de I/O e travamentos durante os builds.

O Docker Desktop com backend WSL 2 não oferece o limite de uso de disco da interface disponível para outros backends. O tamanho virtual máximo do VHDX não equivale a uma reserva de espaço livre para o Windows. Uma verificação local, portanto, precisa usar o espaço livre real do C:.

## Decisão

1. O armazenamento ativo do Docker Desktop permanece no C: SSD. É proibido movê-lo para o D: HD para abrir espaço. Arquivos finais de evidência podem ir para o D: quando sua leitura não fizer parte do build ativo.
2. Antes de iniciar build de imagem/ISO, instalação em VM, expansão/compactação do VHDX ou outro teste local com alto consumo de disco no Windows, execute `powershell -NoProfile -File scripts/host/check-disk.ps1 -Mode Check`. O processo é bloqueado se houver menos de **160 GiB livres** no C:. A verificação deve ser repetida antes de cada execução pesada, inclusive após falhas.
3. O Windows executa `scripts/host/check-disk.ps1 -Mode Watch` a cada minuto enquanto o usuário estiver conectado. Se o C: tiver menos de **120 GiB livres**, o monitor solicita a parada normal do Docker Desktop, registra o evento e não o reinicia automaticamente. Não apaga containers, volumes ou imagens e não força a parada caso o comando normal falhe.
4. Os scripts do item 2 e 3 ficam versionados em `scripts/host/`. O instalador copia o monitor para o C: e registra a tarefa do Windows sem mover o VHDX. O teste de limiar usa simulação explícita e não para o Docker real.
5. Cada execução pesada deve ter consumo estimado e espaço temporário limitado ou descartável. Quem iniciar a tarefa acompanha o C: e interrompe o trabalho ao receber o bloqueio. Um novo build só recomeça depois de recuperar espaço e passar novamente no preflight.

## Limites

O monitor não garante uma reserva absoluta: um processo pode consumir mais de 120 GiB entre duas verificações, a tarefa pode falhar ou o usuário pode estar desconectado. Por isso, o preflight de 160 GiB e a observação durante o build continuam obrigatórios. O monitor protege especificamente a carga do Docker; outros programas não são interrompidos automaticamente.
