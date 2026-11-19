# Captura sintética sob `strace` — 18/11/2026

Os testes Rust `voice::tests::capture_reads_pcm_from_a_pipe_and_stops_the_child` e `voice::tests::stt_pipe_accepts_local_reply_and_rejects_invalid_input` passaram separadamente sob `strace -ff -e trace=openat,openat2,creat,write,pwrite64 -s 0 -y`, com `PYTHONDONTWRITEBYTECODE=1`. Cada traço acompanhou três processos. A captura registrou 13 chamadas `write`; o STT, 15. Todas tinham destino `pipe` ou `anon_inode:[eventfd]`. Não houve `creat` nem `pwrite64`, nem escrita em descritor de arquivo regular. `-s 0` impediu que bytes de áudio entrassem nos traços.

Esta é uma prova limitada aos fluxos sintéticos de captura e STT por pipe. Ainda falta repetir com `pw-cat` conectado a um servidor PipeWire real e com o worker STT de produção para satisfazer FR-077.

Em 19/11/2026, após a captura passar a usar um dono contínuo, o teste
`voice::tests::one_microphone_process_feeds_push_to_talk_and_another_consumer`
também passou sob o mesmo filtro `strace`. Três processos foram acompanhados;
as 18 chamadas `write` tiveram destino `pipe` ou `anon_inode:[eventfd]`.
Não houve escrita em arquivo regular. Essa prova inclui a distribuição de
quadros a dois consumidores sintéticos, mas não substitui a prova PipeWire real.
