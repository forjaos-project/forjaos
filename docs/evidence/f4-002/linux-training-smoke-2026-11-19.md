# F4-002 — Smoke do treinador WeKws no Linux (19/11/2026)

## Ambiente e execução

- Ubuntu 26.04.1 LTS no WSL, Python 3.14.4, `uv` 0.13.7.
- `uv sync --locked --no-dev` instalou o runtime de `hero/wakeword/training-runtime`;
  `uv pip check` aprovou as 37 dependências instaladas.
- O treino foi forçado a CPU com `CUDA_VISIBLE_DEVICES=`. Um conjunto mínimo
  descartável de tons sintéticos cobriu `train`, `dev` e `test`, com duas
  amostras positivas e duas negativas por divisão. `train_model` terminou em
  29 épocas; `export_model` gerou ONNX de 177.971 bytes.
- ONNX Runtime abriu os tensores `input`, `cache`, `output` e `r_cache`. A saída
  PyTorch/ONNX foi comparada pelo próprio exportador. Inferência adicional com
  sequências de 8, 12, 64 e 128 quadros manteve as dimensões dinâmicas e o cache.

## Limites desta evidência

Este ensaio verifica instalação, treino mínimo, exportação e inferência do
software em Linux. Tons sintéticos não são fala e **não** medem reconhecimento,
FAR, latência de despertar, consentimento ou FR-080/081. O comando de promoção
não foi executado; nenhum modelo do ensaio foi embarcado. O modelo Piper local
não foi usado, pois seus metadados não declaram licença.

Os WAVs, checkpoint, ONNX e checkout WeKws do ensaio ficaram fora do repositório,
em `D:\ForjaOS\validation\f4-002-wakeword-smoke`. A instalação isolada ficou em
`D:\ForjaOS\validation\f4-002-wakeword-runtime`; o cache dedicado está em
`D:\ForjaOS\cache\f4-002-uv` (4,6 GiB medidos). O espaço livre de D: caiu de
938.277.834.752 para 933.310.570.496 bytes durante a instalação, redução de
4.967.264.256 bytes. O corpus Common Voice original não foi extraído.
