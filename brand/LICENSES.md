# Licenças dos recursos de `brand/`

Registro exigido pelo DoD de `brand/AGENTS.md`. Política geral no ADR-007: código próprio Apache-2.0, artes CC BY-SA 4.0, nome e logo também sob a política de marca própria do projeto.

| Recurso | Caminho | Licença | Origem |
| --- | --- | --- | --- |
| Logo ForjaOS v1 (marca, logotipo, ícone e PNGs) | `brand/logo/` | CC BY-SA 4.0 (arte, ADR-007); nome e logo também sujeitos à política de marca (ADR-007) | Arte própria do projeto |
| Gerador e extrator do logo | `brand/logo/build_logo.py`, `brand/logo/extract_wordmark.py` | Apache-2.0 (ADR-007) | Código próprio |
| Plus Jakarta Sans 700 (contornos do wordmark em `brand/logo/src/wordmark.json`) | `brand/logo/src/wordmark.json` | OFL-1.1 | The Plus Jakarta Sans Project Authors, https://github.com/tokotype/PlusJakartaSans; obtida via npm `@fontsource/plus-jakarta-sans` 5.3.0. A OFL permite incorporar os contornos em logotipos; o arquivo de fonte não é redistribuído aqui |
| Ferramentas do extrator (não distribuídas) | — | fontTools: MIT · uharfbuzz: Apache-2.0 | Usadas só para gerar `wordmark.json` |
