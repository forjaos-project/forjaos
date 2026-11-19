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
as gravações autorizadas de FR-081. A presença de cada MP3 no arquivo ainda
precisa ser conferida antes de treinar.

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

**Bloqueio de licença:** os [modelos pré-treinados do openWakeWord](https://github.com/dscripka/openWakeWord#license)
e as [features negativas prontas](https://huggingface.co/datasets/davidscripka/openwakeword_features)
estão sob CC BY-NC-SA 4.0. A licença dos dois ONNX compartilhados de extração
(`melspectrogram.onnx` e `embedding_model.onnx`) segue sem esclarecimento
explícito do mantenedor na [questão upstream #338](https://github.com/dscripka/openWakeWord/issues/338).
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

Nenhum substituto foi aprovado para ADR-012. A escolha depende de um modelo
pt-BR treinado com dados de procedência verificada e das métricas FR-080/081;
a validação por 20 locutores reais segue pendente conforme acima.
