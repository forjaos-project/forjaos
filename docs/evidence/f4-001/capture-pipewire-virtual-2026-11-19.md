# Captura com PipeWire isolado — 19/11/2026

Em WSL, um servidor PipeWire 1.6.2 e o gerenciador WirePlumber 0.5.13
rodaram em um socket privado, com uma fonte virtual `forja-test-source`.
Os pacotes foram extraídos em `D:\ForjaOS\validation\f4-001\pipewire-runtime`;
nenhum serviço do sistema foi instalado ou alterado. O cliente `pw-cat`
executou os mesmos argumentos de captura usados por `MicStream::start`:
PCM `s16`, mono, 16 kHz, saída `-` (stdout). Em 2 s, 63.488 bytes
atravessaram o pipe e foram contados sem gravar o PCM em arquivo.

Repeti a captura sob `strace -ff -e trace=openat,openat2,creat,write,pwrite64
-yy -s 0`, também por 2 s. Foram contados 59.392 bytes de PCM no pipe.
Das 18 chamadas `write` do `pw-cat`, 15 escreveram no pipe de stdout,
duas em `eventfd` e uma em `/proc/<pid>/task/<tid>/comm` para nomear uma
thread. Não houve `creat`, `pwrite64` ou escrita em arquivo regular.
O código 124 é o término esperado pelo `timeout` após 2 s. Os traços
sanitizados ficaram na pasta privada de validação em `D:`; `-s 0` omitiu
o conteúdo dos buffers.

Essa prova cobre o transporte `pw-cat` ↔ PipeWire com fonte virtual e a
ausência de escrita de áudio em arquivo pelo cliente durante a janela
observada. Não cobre microfone físico, sessão Plasma, wake word, worker
STT de produção nem eventual escrita por outros processos. A validação
com hardware Linux de referência continua pendente.

## Integração com `herod`

O binário Linux de `herod` da branch em `6f1a4de` também foi executado em
uma sessão D-Bus privada, com `HOME` e diretórios de estado privados em `D:`.
Após o WirePlumber ficar pronto, o nó `forjaos.hero.microphone` ligou à
fonte virtual. `StartPushToTalk` retornou `recording` e o estado D-Bus
passou a `gravando`. Desligar `MicrophoneEnabled` durante a captura levou
o estado a `ocioso` e encerrou o processo filho `pw-cat`. Na primeira
tentativa, com o gerenciador de sessão iniciado ao mesmo tempo que o
daemon, ainda não havia PCM e o PTT retornou `pipewire_capture_unavailable`;
o teste bem-sucedido esperou o gerenciador concluir a ligação. Esse
resultado não demonstra uma latência de inicialização garantida.

A repetição completa sob `strace -ff -s 0 -y -e
trace=openat,openat2,creat,write,pwrite64` acompanhou os processos da
sessão. O `pw-cat` filho fez 21 escritas de PCM no pipe de stdout, uma em
`eventfd` e uma em `/proc` para nomear thread. O `herod` escreveu apenas
`enabled\n` e `disabled\n` no arquivo privado de estado do microfone,
além de seis escritas em `eventfd`. O WirePlumber persistiu 288 bytes de
propriedades de stream (volume, mute e canais) em seu diretório privado;
o conteúdo foi inspecionado e não contém amostras PCM. Não foi observada
escrita de áudio em arquivo regular. Os traços com conteúdo dos buffers
omitido permanecem em `D:\ForjaOS\validation\f4-001\pipewire-runtime`.

A fonte virtual não é um microfone físico. O teste encerrou a captura pelo
kill switch antes de chamar STT e não valida wake word, TTS, Plasma ou
hardware Linux de referência.
