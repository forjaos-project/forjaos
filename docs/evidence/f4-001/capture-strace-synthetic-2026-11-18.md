# Captura sintética sob `strace` — 18/11/2026

O teste Rust `voice::tests::capture_reads_pcm_from_a_pipe_and_stops_the_child` passou sob `strace -ff -e trace=openat,openat2,creat,write,pwrite64 -s 0 -y`. O traço acompanhou três processos e registrou 13 chamadas `write`: todas tinham destino `pipe` ou `anon_inode:[eventfd]`. Não houve `creat` nem `pwrite64`, nem escrita em descritor de arquivo regular. `-s 0` impediu que os bytes de áudio entrassem no traço.

Esta é uma prova limitada ao fluxo sintético de captura por pipe. Ainda falta repetir com `pw-cat` conectado a um servidor PipeWire real e verificar o restante do fluxo de STT para satisfazer FR-077.
