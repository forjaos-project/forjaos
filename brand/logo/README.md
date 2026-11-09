# Logo ForjaOS v1 (FR-053)

Bigorna em contorno (gradiente ciano→violeta) com o spark `<·>` no centro. Layout dos protótipos em `docs/telas/logo/`; cores de `brand/palette.json` (ADR-027). Todos os arquivos abaixo são **gerados**: não edite à mão.

## Arquivos

| Arquivo | O que é | Onde usar |
| --- | --- | --- |
| `forjaos-mark-on-dark.svg` | Marca em cor, com brilho, para fundo escuro | Plymouth (FR-056), GRUB (FR-012), barra superior do tema escuro |
| `forjaos-mark-on-light.svg` | Marca em cor, sem brilho, para fundo claro | Barra superior do tema claro, documentação impressa |
| `forjaos-mark-mono.svg` | Marca em uma cor (`currentColor`) | Ícone simbólico, bandeja, gravação, fundo de cor arbitrária |
| `forjaos-logo-on-dark.svg` | Marca + wordmark "ForjaOS", fundo escuro | SDDM (FR-057), site em modo escuro, apresentações |
| `forjaos-logo-on-light.svg` | Marca + wordmark, fundo claro | Site em modo claro, documentos |
| `forjaos-logo-mono.svg` | Marca + wordmark em uma cor | Uso em uma cor (camiseta, adesivo, rodapé) |
| `forjaos-icon.svg` | Ícone de aplicativo: placa escura arredondada + marca | Ícone do sistema (`LOGO=` do `os-release`, FR-003), lançadores, site |
| `forjaos-icon-small.svg` | Ícone simplificado para ≤ 32 px (traço grosso, sem nós, sem brilho, sem ponto central) | Origem dos PNGs de 16 a 32 px |
| `png/forjaos-<N>.png` | Ícone rasterizado em 16, 22, 24, 32, 48, 64, 128, 256 e 512 px | Tema de ícones hicolor, favicon (16 e 32), lojas |
| `src/wordmark.json` | Contornos do texto "ForjaOS" (Plus Jakarta Sans 700) | Entrada do gerador |

"Forja" usa `text-strong` e "OS" usa `accent-cyan` do tema correspondente. O nome é só **ForjaOS**, sem descritor (ADR-031).

A instalação desses arquivos na imagem (`/usr/share/icons/hicolor/`, `os-release`, Plymouth, SDDM) fica com os itens de `image/` e dos temas.

## Regenerar

```bash
python3 brand/logo/build_logo.py --png   # SVGs + PNGs (precisa de rsvg-convert)
python3 brand/logo/build_logo.py --check # confere se os SVGs versionados estão atualizados
python3 -m unittest discover -s brand/tests -p 'test_*.py'
```

O wordmark só precisa ser reextraído se a fonte ou o espaçamento mudarem:

```bash
npm pack @fontsource/plus-jakarta-sans && tar xzf fontsource-plus-jakarta-sans-*.tgz
pip install fonttools uharfbuzz
python3 brand/logo/extract_wordmark.py --font package/files/plus-jakarta-sans-latin-700-normal.woff
```

Até 24 px o spark aparece como um núcleo laranja de 3 a 4 px; a leitura `<>` começa em 32 px.
