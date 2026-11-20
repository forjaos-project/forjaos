# F4-002 — Conversão de negativos Common Voice (19/11/2026)

## Resultado

O arquivo Common Voice 27.0 pt-BR foi lido sem extrair o corpus completo. Os
8.571 caminhos já conferidos no índice privado foram extraídos e decodificados
com FFmpeg para WAV PCM mono, 16 kHz e 16 bits. Metadados incorporados ao áudio
foram removidos. O manifesto privado mantém o split de origem e os códigos
anônimos de locutor.

| Split | Clipes | Locutores | Duração negativa |
| --- | ---: | ---: | ---: |
| Treino | 6.111 | 62 | 7,0326 h |
| Desenvolvimento | 1.484 | 75 | 1,8384 h |
| Teste | 976 | 295 | 1,3484 h |
| **Total** | **8.571** | — | **10,2194 h** |

Os arquivos e `negative-wavs.tsv` permanecem fora do Git em
`D:\ForjaOS\datasets\wakeword\derived\negative-wavs-2026-11-19\`.
`conversion-summary.json` nessa pasta registra a soma SHA-256 do arquivo-fonte
(`d5c6e70d669378ce8178b2a0f03e3281d67c4ee5ddd5200718221b28e0b93e60`), bytes,
contagens e horas. Nenhum WAV ou código de locutor foi incluído neste registro.

Também foram normalizados os 1.260 WAVs de ruído ambiental do OpenSLR SLR28,
somando 6,805 h: 843 clipes `pointsource_noises` (5,912 h) e 417
`real_rirs_isotropic_noises` (0,893 h). Os dados e `noise-wavs.tsv` permanecem
fora do Git em `D:\ForjaOS\datasets\wakeword\derived\slr28-noise-wavs-2026-11-19\`.
Fontes multicanal com layout não declarado foram reduzidas pelo canal 0. O
resumo privado registra o SHA-256 do ZIP
(`3b50cfde915b3984738169b4beb341e9f6b8062ae4c2076146c5db71c2c05dc7`).

## Limites

- O teste de fala Common Voice tem 1,3484 h; os ruídos SLR28 somam 6,805 h.
  Juntos dão 8,1534 h negativos se todos os ruídos forem reservados ao teste,
  mas o áudio ambiente sozinho ainda fica 1,195 h abaixo do critério literal.
- Os manifestos negativos ainda não foram combinados com positivos humanos
  nem divididos para treino. Nenhuma taxa de falsos positivos foi medida.
- São amostras de fala negativa. Elas não contêm as oito frases wake word e
  não substituem gravações humanas autorizadas.
- A licença CC0-1.0 do dataset e as restrições de uso da Mozilla Data
  Collective continuam aplicáveis. Não reidentificar locutores nem redistribuir
  o corpus.
- Esta conversão não treina, promove ou embarca modelos.
