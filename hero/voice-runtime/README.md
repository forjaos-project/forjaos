# Runtime local de voz do HERO

`voice-worker` usa Python 3.14 e instala no primeiro uso, com `uv`, as
dependências fixadas em `requirements.txt` e seus hashes. A imagem leva o código
e o lock, mas não leva o modelo STT nem as vozes. Para STT, o instalador baixa
o `Systran/faster-whisper-small` de uma revisão fixa, verifica tamanho e
SHA-256 dos quatro arquivos e guarda o modelo em
`$XDG_DATA_HOME/hero/models/`. Para TTS, a voz Piper deve estar previamente
instalada e selecionada com `forja mascot voices download|voice`.

O worker usa somente pipes para áudio:

- `voice-worker stt-server`: lê uma linha JSON por gravação, com
  `sample_rate: 16000` e `pcm_s16le_base64`, e responde uma linha JSON com
  `status` e `text`. Aceita até 30 s de PCM mono e sai após 5 min ocioso.
- `voice-worker tts --model /caminho/voz.onnx`: lê texto UTF-8 do stdin (até
  4000 caracteres) e emite linhas JSON com blocos PCM, taxa de amostragem e
  eventos de visema derivados dos alinhamentos de fonemas do Piper. O último
  evento é `done`. Encerrar o processo interrompe a síntese.

Nenhuma gravação nem saída sintetizada é gravada em arquivo. O modelo e as
dependências são arquivos persistentes permitidos; áudio de entrada e saída
fica somente na memória dos processos. O Piper 1.8.0 é GPL-3.0-or-later;
o faster-whisper 1.2.1 é MIT. Vozes possuem licenças próprias, e o catálogo
`forja mascot voices` só inclui duas vozes pt-BR CC0 verificadas.

`hero-speak --model /caminho/voz.onnx` lê texto do stdin, supervisiona o
worker TTS e envia os blocos PCM ao `pw-cat` em modo raw. Emite no stdout os
visemas com deslocamento por bloco. `SIGTERM`/`SIGINT` interrompem os dois
processos; o teste sintético de cancelamento não exige dispositivo de áudio.
O `pw-cat` envia a fala ao sink `forjaos.hero.aec.sink`; o daemon captura da
fonte filtrada `forjaos.hero.aec.source`. O daemon não inicia a captura sem a
fonte AEC e confere o link antes de aceitar o primeiro quadro; o supervisor
não inicia a reprodução sem o sink AEC. A imagem carrega
o módulo de cancelamento de eco do PipeWire com prioridade baixa para seus
nós virtuais.

O `herod` usa o `voice-worker stt-server` após a captura de PTT pelo PipeWire,
classifica o texto no Policy Engine, processa conversas na rota local
`conversa-de-voz` e aciona `hero-speak` com a voz selecionada em `persona.toml`.
Ações de tier `alterar` exigem uma confirmação falada em novo PTT; delegação de
código longa exige modo texto. O PTT durante a reprodução envia SIGTERM
ao supervisor, que encerra Piper e PipeWire. O overlay mostra transcrição e
resposta; o atalho global de PTT mostra a resposta em notificação. Ainda faltam
wake word, supressão do próprio TTS, visemas no QML e medição no Linux de referência.
