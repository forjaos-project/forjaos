# Dados para wake words do ForjaOS

Os oito classificadores de Guará, Tupã, Jaci, Iara, Ipê, Boto, Curió e Arara
precisam ser treinados pelo projeto. Guarde os áudios e os arquivos derivados
fora do repositório; publique somente modelos com procedência verificável e
métricas agregadas. Nenhum dos conjuntos abaixo fornece, por si só, a validação
das oito frases por 20 locutores reais exigida em FR-081.

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

**Bloqueio de licença:** os [modelos pré-treinados do openWakeWord](https://github.com/dscripka/openWakeWord#license)
e as [features negativas prontas](https://huggingface.co/datasets/davidscripka/openwakeword_features)
estão sob CC BY-NC-SA 4.0. A licença dos dois ONNX compartilhados de extração
(`melspectrogram.onnx` e `embedding_model.onnx`) segue sem esclarecimento
explícito do mantenedor na [questão upstream #338](https://github.com/dscripka/openWakeWord/issues/338).
Treinar apenas os oito classificadores não resolve essa dúvida. Antes de
embarcar o runtime, é necessária procedência e licença permissiva verificáveis
para os dois modelos compartilhados, ou uma implementação independente com
pesos de origem permissiva comprovada.
