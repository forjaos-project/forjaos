# ADR-025 — Avaliação do Hermes Agent nas rotas código e pesquisa

**Status:** decidido — Hermes não adotado nesta versão · **Data:** 2026-11-18 · **Relacionados:** F3-008, FR-097

## Contexto

O FR-097 pede uma comparação de 20 tarefas entre o loop próprio do HERO e Hermes Agent nas rotas `código` e `pesquisa`. A decisão precisa considerar qualidade da resposta, latência, classificação de rota e capacidade de concluir uma tarefa que usa ferramentas.

## Decisão

1. Manter o loop próprio do HERO como motor das rotas `código` e `pesquisa` nesta versão.
2. Não encaminhar essas rotas ao Hermes até que o ciclo de uso de ferramenta retorne uma resposta final de forma consistente.
3. Repetir a avaliação com tarefas que exijam leitura de arquivos e consulta de fontes depois que o ciclo do Hermes estiver corrigido. O ensaio atual não comprova qualidade de recuperação independente.

## Método

- 20 prompts pareados: 10 de código e 10 de pesquisa. Os dados necessários para responder foram incluídos nos prompts para isolar o loop de resposta.
- Mesmo modelo local nos dois lados: `qwen3.5:4b`, contexto publicado de 262.144 tokens, servido pelo Ollama 0.40.16; GPU GeForce RTX 5060 com 8 GiB.
- Raciocínio nativo desativado no pareamento: HERO usou `think:false`; Hermes usou `reasoning_effort: none`, que o perfil Ollama traduz para essa opção.
- HERO foi executado pelo D-Bus com seu binário Linux compilado no WSL. O binário do ensaio incluiu temporariamente `think:false`, pois o Ollama devolvia o texto em `message.thinking` e deixava `message.content` vazio sem essa opção. A alteração foi removida do código-fonte após o build.
- Hermes Agent 0.17.0 rodou em modo CLI, com ferramentas desativadas durante as 20 tarefas para manter o pareamento de respostas textuais. O modo com terminal foi avaliado separadamente em uma tarefa de leitura do snapshot.
- A pontuação textual conta marcadores esperados presentes literalmente na resposta. É uma medida reproduzível de cobertura, mas não substitui revisão semântica.

## Resultado

| Motor | Respostas com todos os marcadores | Cobertura literal | Latência mediana | Latência p95 | Rotas HERO corretas |
| --- | ---: | ---: | ---: | ---: | ---: |
| Loop próprio do HERO | 14/20 | 61/67 | 0,49 s | 0,79 s | 19/20 |
| Hermes Agent, sem ferramentas | 11/20 | 43/67 | 11,43 s | 18,40 s | n/a |

O HERO classificou R01 como `código` embora a solicitação fosse pesquisa sobre o requisito FR-097; a menção literal à rota `código` acionou essa classificação. O erro está incluído nos 19/20.

No ensaio de ferramenta em C01, Hermes leu o arquivo, mas não concluiu a resposta. Com `reasoning_effort: none`, terminou com resposta vazia após duas chamadas de ferramenta. Com raciocínio habilitado, fez sete chamadas e encerrou no limite de oito iterações, também sem responder. A execução mais recente levou 25,76 s.

## Consequências

- A comparação textual favorece o loop próprio em cobertura e latência; o teste de ferramenta não demonstrou um ciclo utilizável no Hermes 0.17.0 com Ollama e Qwen3.5 4B.
- O conjunto forneceu contexto dentro do prompt. Portanto, os números não medem busca em arquivos, navegação web ou pesquisa independente.
- A classificação incorreta de R01 deve ser considerada em uma futura revisão do roteador, separada desta decisão sobre o Hermes.
- Não houve alteração permanente no código do HERO nem avaliação em Plasma ou hardware de referência.
