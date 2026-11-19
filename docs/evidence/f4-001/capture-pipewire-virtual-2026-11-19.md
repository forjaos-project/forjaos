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
