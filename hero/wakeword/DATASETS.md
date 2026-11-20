# Dados para wake words do ForjaOS

Os oito classificadores de Guará, Tupã, Jaci, Iara, Ipê, Boto, Curió e Arara
precisam ser treinados pelo projeto. Guarde os áudios e os arquivos derivados
fora do repositório; publique somente modelos com procedência verificável e
métricas agregadas. Nenhum dos conjuntos abaixo fornece, por si só, a validação
das oito frases por 20 locutores reais exigida em FR-081.

Os datasets de treino e validação (incluindo os 1,3 GB do SLR28 e os 4,85 GB
do Common Voice) **não entram na ISO**. Eles permanecem em armazenamento local
de desenvolvimento. A imagem final recebe apenas os componentes de inferência
e os modelos aprovados, respeitando as licenças e os critérios de validação.

**Situação em 15/11/2026:** Rodrigo informou que as gravações dos 20 locutores
não estarão disponíveis nesta etapa. A coleta e a validação FR-081 ficam
pendentes; o trabalho de software e de preparação dos dados pode prosseguir.
Não substitua essa evidência por áudio sintético ou por frases genéricas do
Common Voice.

O índice local dos candidatos negativos pt-BR pode ser reproduzido com
`python3 hero/wakeword/index_common_voice.py <arquivo-pt.tar.gz> <pasta-privada>`.
Ele lê apenas `train.tsv`, `dev.tsv` e `test.tsv`, usa o valor real
`Portuguese (Brasil)` da coluna `variant` e exclui frases que contêm os oito
nomes de ativação. Na cópia de 27.0 de 15/11/2026, foram 6.111 candidatos de
treino, 1.484 de desenvolvimento e 976 de teste, sem locutores repetidos
entre as divisões. O manifesto privado está em
`D:\ForjaOS\datasets\wakeword\derived\`; ele não extrai áudio nem substitui
as gravações autorizadas de FR-081. Em 19/11/2026, uma nova execução em
`derived\verified-2026-11-19\` conferiu que os 8.571 caminhos apontam para
entradas MP3 regulares no tar, sem extração; o manifesto gerado foi idêntico
ao anterior. Isso verifica presença no arquivo, não integridade da decodificação,
licença de cada gravação ou cobertura das frases por 20 locutores reais.

Em 19/11/2026, os 8.571 candidatos foram decodificados para WAV PCM mono
16 kHz/16 bits em `D:\ForjaOS\datasets\wakeword\derived\negative-wavs-2026-11-19\`.
O manifesto `negative-wavs.tsv` mantém os códigos anônimos e as divisões da
origem; `conversion-summary.json` registra hash, contagens e duração. Foram
convertidos 6.111 clipes de treino (7,0326 h), 1.484 de desenvolvimento
(1,8384 h) e 976 de teste (1,3484 h). O teste de fala negativa ainda fica
6,6516 h abaixo do mínimo de 8 h. Nenhum WAV foi copiado para o repositório.
Common Voice continua sendo apenas fala negativa: não valida as oito frases,
não substitui as gravações humanas autorizadas e seus locutores não devem ser
reidentificados. O registro agregado está em
[`docs/evidence/f4-002/negative-conversion-2026-11-19.md`](../../docs/evidence/f4-002/negative-conversion-2026-11-19.md).

O ruído do OpenSLR SLR28 está em pasta privada separada; 1.260 WAVs foram
normalizados para PCM mono 16 kHz/16 bits, somando 6,805 h. Veja
`D:\ForjaOS\datasets\wakeword\derived\slr28-noise-wavs-2026-11-19\`.
Esse material sozinho não alcança as 8 h de ambiente exigidas; a medição de FAR
aguarda gravações adicionais e os positivos humanos autorizados.

| Uso | Fonte | Licença e limite |
| --- | --- | --- |
| Exemplos positivos sintéticos | [Piper sample generator](https://github.com/dscripka/piper-sample-generator), com vozes pt-BR verificadas uma a uma | Verificar a licença de cada voz usada; gerar as frases do ForjaOS localmente. |
| Fala negativa em português | [Common Voice Scripted Speech 27.0 — português](https://mozilladatacollective.com/datasets/cmu5wui2w00e8nq07idithpm6) | CC0-1.0; o catálogo contém variante pt-BR. Os termos proíbem reidentificar locutores e redistribuir o dataset. |
| Reverberação simulada | [OpenSLR SLR26](https://www.openslr.org/26/) | Apache-2.0; arquivo de 16 kHz com 178 MB. |
| Reverberação real e ruído | [OpenSLR SLR28](https://www.openslr.org/28/) | Apache-2.0; arquivo de 1,3 GB com áudio de 16 kHz. |

Para a validação, cada um dos 20 voluntários precisa gravar as frases de
ativação e amostras negativas em ambientes e microfones variados, com
autorização explícita para treinar, avaliar e distribuir os modelos resultantes.
Registre por amostra somente um código de participante, frase, ambiente e
dispositivo. Separe locutores de treino e validação; não publique gravações ou
identidades sem autorização específica. Os critérios de falso positivo,
latência e consumo continuam em FR-080/FR-081.

Quando houver gravações, guarde-as em uma pasta privada fora do repositório.
Crie ali um `manifest.tsv` com as colunas `speaker_code`, `phrase`, `path`,
`environment` e `device`. `path` aponta para WAV PCM mono de 16 kHz e 16 bits,
relativo ao manifesto. Uma linha corresponde a uma gravação. Execute
`python3 hero/wakeword/validate_corpus.py /caminho/privado/manifest.tsv` para
conferir formato e cobertura de 20 códigos distintos por frase. O script não
atesta que a voz seja humana nem que haja consentimento; essa revisão é manual.

O treinador usa um segundo manifesto privado em
`$XDG_DATA_HOME/hero/wakeword-training/manifest.tsv`, com as colunas
`split`, `label`, `path`, `source`, `phrase` e `speaker_code`. `split` é
`train`, `dev` ou `test`; `label` é `wake` ou `negative`; `source` é `human`,
`piper`, `common_voice` ou `noise`. `path` continua relativo ao manifesto e
aponta para WAV PCM mono de 16 kHz/16 bits. Em amostras positivas, `phrase`
deve corresponder exatamente ao nome treinado. Use códigos anônimos por
participante e mantenha cada participante em uma única divisão. Áudio e
manifestos ficam fora do repositório. O treinador carrega o WAV em memória e
não cria cópias de áudio; checkpoints, modelo candidato e métricas ficam na
pasta privada `wakeword-training/<nome>/`.

Para montar esse TSV sem distribuir locutores entre divisões, use
`python3 hero/wakeword/prepare_manifest.py Guará <corpus-humano.tsv> <negativos-wav.tsv> <raiz-privada>/manifest-guara.tsv`.
O manifesto humano segue as colunas do `validate_corpus.py`; o manifesto
negativo contém `source`, `speaker_code` e `path`, com `source` igual a
`common_voice` ou `noise`. Os WAVs permanecem nos diretórios privados de
origem, sob uma pasta ancestral comum à saída. Passe o arquivo gerado ao
treinador com `--manifest`; a raiz do manifesto pode ser diferente da pasta
privada usada para checkpoints. O gerador exige 20 códigos
humanos para a frase, WAV PCM mono 16 kHz/16 bits, divisões de locutor
determinísticas e amostras positivas/negativas em treino, desenvolvimento e
teste. Ele não converte MP3, não extrai arquivos de datasets e não verifica
consentimento; a revisão da procedência continua manual.

Para nomes da lista FR-021, o treinador exige pelo menos 20 participantes
humanos distintos no conjunto positivo. Em qualquer modelo, a promoção exige
ao menos oito horas de áudio negativo de teste, taxa observada de falsos
positivos de no máximo 1 por 8 horas e latência p95 de até 300 ms. Esses
números são resultados do conjunto informado; a revisão manual ainda precisa
confirmar consentimento e procedência. Métricas de dados Piper/Common Voice não
substituem a validação comunitária FR-081. O WeKws fixado é baixado para o
cache privado do usuário apenas no primeiro treino; a imagem recebe o
treinador e o lock, não o PyTorch nem o corpus.

**Motivo da troca de motor:** os [modelos pré-treinados do openWakeWord](https://github.com/dscripka/openWakeWord#license)
e as [features negativas prontas](https://huggingface.co/datasets/davidscripka/openwakeword_features)
estão sob CC BY-NC-SA 4.0. A licença dos dois ONNX compartilhados de extração
(`melspectrogram.onnx` e `embedding_model.onnx`) segue sem esclarecimento
explícito do mantenedor na [questão upstream #338](https://github.com/dscripka/openWakeWord/issues/338).
Em 19/11/2026, as [questões #348](https://github.com/dscripka/openWakeWord/issues/348)
e [#357](https://github.com/dscripka/openWakeWord/issues/357) também estavam
abertas, sem uma licença separada declarada para esses artefatos. A descrição
da arquitetura no README menciona Apache 2.0 para o modelo do Google que
inspirou o extrator, mas não substitui a licença dos arquivos ONNX distribuídos.
Treinar apenas os oito classificadores não resolve essa dúvida. Antes de
embarcar o runtime, é necessária procedência e licença permissiva verificáveis
para os dois modelos compartilhados, ou uma implementação independente com
pesos de origem permissiva comprovada.

## Avaliação de alternativas em 18/11/2026

- `openWakeWord` permanece na versão publicada 0.6.0 (fevereiro de 2024).
  O [README upstream](https://github.com/dscripka/openWakeWord#license) distingue
  código Apache-2.0 de modelos pré-treinados CC BY-NC-SA 4.0, mas não esclarece
  a licença dos arquivos compartilhados; a [questão #338](https://github.com/dscripka/openWakeWord/issues/338)
  continua aberta. A afirmação de que o embedding foi reimplementado a partir
  de um modelo Google Apache-2.0 não basta para atribuir licença aos arquivos
  ONNX distribuídos.
- `sherpa-onnx` oferece keyword spotting configurável, mas os
  [modelos KWS publicados](https://k2-fsa.github.io/sherpa/onnx/kws/index.html)
  são para inglês e chinês. Eles não comprovam detecção das oito frases pt-BR.
- [WeKws](https://github.com/wenet-e2e/wekws) é Apache-2.0 e tem treino a
  partir de dados próprios e exportação ONNX. Uma prova local em Python 3.14,
  PyTorch 2.11 e ONNX Runtime, usando MDTC inicializado sem pesos externos,
  exportou 35.073 parâmetros para 277.279 bytes. A saída de 100 quadros teve
  diferença absoluta máxima de 3,58e-7 entre PyTorch e ONNX Runtime. O
  exportador atual produziu opset 18 apesar do pedido de opset 13; a
  compatibilidade desse formato com a imagem Linux ainda deve ser conferida.
  Essa prova verifica apenas exportação e inferência de pesos aleatórios: não
  verifica português, acurácia, falso positivo, consumo nem latência.

Em 19/11/2026, Rodrigo aprovou WeKws como substituto de openWakeWord em
ADR-012/FR-080. O código fonte Apache-2.0 foi fixado localmente no commit
`6a45aeb994dd81c0969ff877a5a7c46d60ed0c86`; nenhum peso pré-treinado
do upstream será incorporado. A troca resolve o bloqueio dos ONNX
compartilhados de openWakeWord, mas não equivale a um modelo pt-BR validado.
Continuam necessários treino com dados de procedência verificada, métricas
FR-080/081 e as 20 gravações reais por frase.

`worker.py` agora faz inferência WeKws em quadros PCM de 80 ms recebidos por
stdin. `features.py` fornece a mesma extração log-mel determinística ao treino
e à inferência; o ONNX deve ter `input`, `cache`, `output`, `r_cache` e metadados
`cache_dim`/`cache_len`/`feature_type=forja-logmel-v1`. O runtime mínimo fixa NumPy e ONNX Runtime em
`runtime/uv.lock`. A prova com pesos aleatórios exportados pelo WeKws oficial
teve diferença máxima de `5,96e-8` entre os escores PyTorch e ONNX Runtime
em três blocos de streaming. Isso verifica contrato e continuidade do cache,
não português, acurácia, falso positivo, consumo nem latência. O `Containerfile`
copia o worker e o `herod` assina o fluxo PCM compartilhado. A imagem local foi
construída e o worker executou um ONNX de prova no Linux. O [ensaio sintético
AEC](../../docs/evidence/f4-001/wekws-aec-synthetic-2026-11-19.md) não detectou
o Piper isolado em duas execuções e detectou outra fala sintética simultânea.
O classificador de prova tem falsos positivos e não é distribuído. Nenhum
classificador é embarcado antes da avaliação exigida.

Em 19/11/2026, a [questão #338](https://github.com/dscripka/openWakeWord/issues/338)
continuava aberta sem resposta do mantenedor sobre a licença dos ONNX
compartilhados. As [questões #348](https://github.com/dscripka/openWakeWord/issues/348)
e [#357](https://github.com/dscripka/openWakeWord/issues/357) reiteravam a
mesma dúvida. O [README upstream](https://github.com/dscripka/openWakeWord/blob/main/README.md#license)
continuava distinguindo código Apache-2.0 de modelos pré-treinados CC BY-NC-SA
4.0 sem classificar expressamente esses dois artefatos. WeKws elimina a
dependência desses ONNX; os modelos próprios ainda aguardam a validação FR-081.
