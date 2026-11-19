# F4-001 — Wake word e fala Piper no AEC virtual (19/11/2026)

O worker WeKws recebe quadros PCM mono s16le de 80 ms do mesmo `MicStream`
usado pelo PTT. O extrator log-mel local alimenta um ONNX com cache de streaming.
Antes de emitir `wake`, o worker exige escore acima do limiar configurado e
fala em pelo menos quatro dos últimos oito quadros, medida por RMS > 400. O
teste unitário rejeita silêncio e pulsos curtos mesmo quando um modelo simulado
retorna escore alto.

## Ensaio privado

- WeKws Apache-2.0 no commit `6a45aeb994dd81c0969ff877a5a7c46d60ed0c86`;
  pesos inicializados do zero, sem pesos do upstream.
- Modelo **apenas de prova**, treinado com cinco frases positivas e oito
  negativas geradas pela voz Piper Cadu. Treino de 50 épocas com variações
  sintéticas de velocidade, volume e ruído. O modelo acertou as cinco amostras
  positivas de treino, mas marcou duas das oito negativas com escore acima de
  0,8. **Não satisfaz acurácia, falso positivo, licença de distribuição nem
  validação FR-080/081; não é embarcado.**
- O Piper pronunciou “Guará, você está aí?” três vezes. O PCM atravessou o
  sink AEC dedicado; o script conferiu no grafo PipeWire que o player estava
  ligado a `forjaos.hero.aec.sink`. O monitor do sink físico virtual simulou
  o eco digital no microfone. Todas as amostras e os escores ficaram em memória.
- Limiar do worker de prova: 0,8. Em duas execuções sem segunda fonte, o áudio
  bruto gerou eventos de wake (4 e 1); a saída AEC gerou **zero** eventos nas
  duas. Em uma execução adicional, uma segunda fala Piper com a mesma frase
  entrou diretamente no sink físico de teste, fora da referência AEC, durante
  a reprodução. A saída AEC gerou 3 eventos de wake. A multiplicidade reflete
  a instabilidade do classificador de prova e não mede uma taxa de acerto.
- O worker Python teve 9 testes aprovados, incluindo sessão ONNX real e
  rejeição de silêncio/ruído breve. A exportação oficial WeKws mais os
  metadados da extração local produziu o ONNX de prova em opset 18.

## Imagem local

`docker build -f image/Containerfile -t forjaos:f4-001-wekws .` terminou após
ajustes para a base Fedora/Qt atual. A imagem local tem ID
`sha256:c22429a8a1dc7f0751c5867cf4c18175edbae63f38b8c90b0a985f04d4d82d92`.
O build passou pelo `bootc container lint` e pelo contrato de pacotes/serviços.
Na imagem, o ambiente isolado carregou NumPy 2.5.4, ONNX Runtime 1.32.0 e o
ONNX de prova em opset 18. O executável instalado
`/usr/libexec/forjaos/hero-wakeword` processou a frase Piper por stdin, sem
arquivo de áudio, com saída `wake` e código 0. O checker de branding executado
na imagem retornou zero achados. A suíte shell passou; a suíte de 146 testes
Python no Linux passou com nove testes pulados por ambiente.

Scripts, pesos, PCM transitório e logs agregados do ensaio ficam em
`D:\ForjaOS\validation\f4-001\`. Nenhum áudio ou modelo de prova entra no Git
ou na imagem. O ensaio mostra a rota de supressão e a possibilidade de barge-in
na topologia virtual. Microfone físico, fala humana, sala, latência de ativação
e sessão Plasma ficam para a validação final de hardware; os oito modelos e
suas métricas pertencem a F4-002.
