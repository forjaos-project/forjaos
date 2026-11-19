# F4-001 — Fonte AEC virtual no PipeWire isolado (19/11/2026)

O módulo oficial [`libpipewire-module-echo-cancel`](https://pipewire.pages.freedesktop.org/pipewire/page_module_echo_cancel.html)
foi carregado no runtime PipeWire 1.6.2 isolado em
`D:\ForjaOS\validation\f4-001\pipewire-runtime`, com WirePlumber 0.5.13.
Foi necessário extrair nesse diretório privado o pacote Ubuntu
`libwebrtc-audio-processing-1-3` (1.3-3build2), pois a biblioteca AEC não
carregava sem `libwebrtc-audio-processing-1.so.3`. Nenhum pacote do host ou
arquivo `/etc` foi alterado.

Na primeira configuração, `monitor.mode = true` usou a fonte de captura virtual
`forja-test-source`, o sink virtual `forja-test-sink` e a fonte filtrada
`forja-hero-aec-source`. Executado com
`dbus-run-session -- bash /mnt/d/ForjaOS/validation/f4-001/pipewire-runtime/hero-aec-smoke.sh`.
O script inicia e encerra somente seus processos PipeWire e WirePlumber. A
configuração privada atual usa o monitor de `forja-test-sink` como captura para
um ensaio digital de eco, mantendo o mesmo sink como referência AEC.

Resultado observado:

```text
node.name = "forja-test-source"
node.name = "forja-test-sink"
node.name = "forja-hero-aec-source"
node.name = "forja-hero-aec-sink"
forja-test-source:capture_MONO -> echo-cancel-capture:input_MONO
forja-test-sink:monitor_MONO -> forja-hero-aec-sink:input_MONO
aec_pcm_frame_bytes=2560
```

O quadro foi lido somente em memória e corresponde a 80 ms de PCM mono 16 kHz
de 16 bits. O teste comprova que o módulo carrega, os nós se ligam e a fonte
filtrada é capturável.

No ensaio digital seguinte, um tom de 500 Hz foi reproduzido no sink virtual:
RMS bruto 3.670,2 e RMS AEC 417,7. Essa redução **não se repetiu com fala**.
A voz local Piper `pt_BR-cadu-medium` sintetizou em memória a frase “Guará,
você está aí?”. Após conversão para 16 kHz, a reprodução única apresentou RMS
bruto 3.040,6 e RMS AEC 2.914,3. Três repetições da mesma frase apresentaram
RMS bruto 3.678,8 e RMS AEC 3.537,6. O teste foi executado por
`run-piper-aec.py` (Python privado em `D:\ForjaOS\validation\f4-001\piper-env`),
que iniciou `hero-aec-smoke.sh` com argumento `piper`. Os scripts passaram PCM apenas por
memória e pipes; este ensaio não foi auditado com `strace`.

Portanto, **essa configuração não demonstra a supressão do nome pronunciado
pelo Piper** e não deve ser ligada ao `herod` como solução de FR-073. A ausência
de um microfone e de uma sala reais impede concluir se o módulo AEC é inadequado
em outra topologia. Faltam teste da própria wake word, barge-in com voz humana,
latência e sessão Plasma. A captura atual de `herod` ainda usa a fonte padrão.
