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
configuração privada foi alterada entre os ensaios abaixo; a versão atual usa
o sink AEC como caminho de reprodução e o monitor de `forja-test-sink` como
captura digital de eco.

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

## Reprodução dedicada ao sink AEC

Um segundo ensaio usou `monitor.mode = false`: Piper reproduziu em
`forja-hero-aec-sink`; o módulo encaminhou o áudio a `forja-test-sink` e usou
esse sinal como referência. A captura continuou no monitor do sink físico de
teste. Assim, a referência passou pelo caminho de reprodução descrito na
[documentação do PipeWire](https://pipewire.pages.freedesktop.org/pipewire/page_module_echo_cancel.html).

```text
forja-test-sink:monitor_MONO -> echo-cancel-capture:input_MONO
echo-cancel-playback:output_MONO -> forja-test-sink:playback_MONO
Piper (3 frases): RMS bruto 3.242,6; RMS AEC 102,3
Primeiros 1.920 ms: pico RMS bruto 8.503,6; pico RMS AEC 884,5
Piper + tom adicional fora da referência: RMS bruto 3.608,0; RMS AEC 1.292,7
```

O resultado variou entre execuções: outra execução de três frases deu RMS
bruto 3.528,4 e RMS AEC 302,4. O tom adicional de 1 kHz entrou diretamente
no sink físico de teste, sem passar pela referência AEC; seu nível residual
maior indica que o filtro não suprimiu todo sinal adicional. Isso é um ensaio
digital controlado, não uma simulação acústica fiel de microfone, sala e voz
humana. Não mede o escore de wake word nem demonstra que o pico inicial
remanescente está abaixo do limiar de ativação. A topologia dedicada é candidata
para integração e teste; ainda não satisfaz FR-073 por si só.

No último ensaio, `capture.props` ficou sem `target.object` e as fontes/sinks
AEC receberam `priority.session = 1`. O WirePlumber ligou
`forja-test-source:capture_MONO` a `echo-cancel-capture:input_MONO`, sem
autoconexão da fonte AEC nela mesma; o sink AEC continuou ligado ao sink físico
virtual de teste. A fonte AEC entregou 2.560 bytes ao `pw-cat`. Isso testa a
seleção automática **com uma fonte virtual disponível**, não a troca de
microfone físico, dispositivos ausentes ou reconexão durante a sessão.

## Fragmento de imagem e daemon

Uma cópia exata de `image/pipewire/forja-hero-echo-cancel.conf` foi carregada
como fragmento de `forja-test.conf` no PipeWire isolado. O `herod` compilado
passou a usar `--target=forjaos.hero.aec.source`. O PipeWire ligou a fonte
virtual de teste ao capturador AEC e a fonte filtrada ao `pw-cat` do HERO.
`StartPushToTalk` retornou `recording`, o estado D-Bus foi `gravando` e o kill
switch encerrou `pw-cat` e voltou a `ocioso`. Um `pw-cat` apontado para um alvo
inexistente com `node.dont-fallback=true` recebeu 0 bytes em 1 s; o alvo AEC
presente entregou 2.560 bytes. O ensaio não instalou a imagem completa.

Sem o fragmento AEC, o mesmo daemon recusou `StartPushToTalk` com
`pipewire_capture_unavailable` e não iniciou `pw-cat`. Com o fragmento, o
supervisor Python ligou a reprodução ao sink AEC e recusou reprodução quando
o sink configurado estava ausente. Essas verificações são de início de fluxo;
não provam o comportamento diante de remoção do módulo durante a fala.

Um teste adicional no mesmo grafo confirmou que o link do `pw-cat` existe
antes do envio do primeiro quadro PCM. O supervisor passou a identificar cada
player por nome único, exigir que todos os seus links apontem ao sink AEC antes
da primeira escrita e conferir novamente entre blocos. Com o alvo removido
após uma checagem de disponibilidade simulada, ele retornou
`reprodução fora do sink AEC do HERO` antes de escrever áudio. A fala normal
terminou pelo sink AEC. Ainda não foi testada a remoção do módulo durante um
bloco já entregue ao PipeWire.

Após a alteração, `cargo fmt`, Clippy e 77 testes Rust passaram. A medição
Linux isolada do `llvm-cov` foi 77,86% de linhas. Em uma janela de captura AEC
de 2.560 bytes, `strace -ff` observou PCM apenas em `stdout` e nenhuma abertura
de arquivo regular para escrita de áudio. A observação não cobre toda a sessão
nem os outros processos do grafo.

Com a mesma cópia do fragmento, um loopback virtual fez o monitor do sink de
teste atuar como microfone com eco digital. Três frases Piper tiveram RMS bruto
3.348,2 e RMS AEC 384,2; nos primeiros 1.920 ms, o pico RMS caiu de 8.111,5
para 3.256,0. A redução foi variável e esse pico ainda precisa ser avaliado
pelo detector wake real. O loopback é somente um substituto digital para o
caminho acústico; não comprova supressão em sala, voz humana nem latência.

## Tela bloqueada e verificação atual

No D-Bus privado, `org.freedesktop.ScreenSaver.GetActive = true` agora faz
`AskText` retornar `locked` também para conversa. O estado permanece `ocioso`,
sem histórico ou ação pendente. `GetActive = false` mantém a solicitação de
confirmação para ações `alterar`. Isso testa a política do daemon, não uma
sessão Plasma bloqueada com `loginctl lock-session`.

Com a verificação adicional do link de reprodução, `cargo fmt --check`,
Clippy e 77 testes Rust passaram. O perfil Linux isolado atual do `llvm-cov`
apontou 77,65% de linhas. O `hero-speak` foi exercitado com worker TTS
sintético e grafo PipeWire privado: fala válida ligada ao sink AEC, sink
ausente recusado na checagem inicial e alvo ausente após checagem simulada
recusado antes do envio de PCM. Não houve build da imagem completa.

O fragmento AEC continua carregado sem consumidor. Antes do primeiro
`pw-cat`, a fonte virtual de microfone e os nós AEC estavam `suspended`.
Cinco segundos após encerrar todos os consumidores, a fonte virtual e a saída
AEC voltaram a `suspended`; o nó intermediário `forjaos.hero.aec.capture`
ficou `idle`, sem porta ativa. Isso indica que o grafo não processava a fonte
virtual naquele instante, conforme os [estados de nó do PipeWire](https://pipewire.pages.freedesktop.org/pipewire/group__pw__node.html).
Ainda falta verificar o indicador e o dispositivo físico após o kill switch
em uma sessão Plasma.
