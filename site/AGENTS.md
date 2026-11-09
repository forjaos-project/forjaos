# site/ — site, docs do usuário e download

**Escopo:** NFR-043 (docs pt-BR/en, cada subcomando `forja` documentado), NFR-051, G1 (instalação sem suporte), FR-014 (guia de gravação), FR-010 (download com checksum).
**Equivale a:** `forjaos-site` (ADR-026). Astro; GitHub Pages. Tema claro (Alabaster Forge) padrão, escuro alternável.

## Toolchain e testes
- `npm ci && npm run build` sem warnings; `scripts/check-tokens.sh` (CSS compilado a partir de `brand/palette.json`, sem Tailwind CDN em runtime).
- Lighthouse ≥ 90 em acessibilidade; links internos verificados no CI.
- Conteúdo de comandos gerado a partir do `--help` do CLI (não duplicar à mão).

## DoD local
- Header 64 px, sidebar 288 px, container 1520 px (palette › dimensions) — layout da spec `forjaos_docs_documenta_o_t_cnica_oficial`.
- pt-BR e en-US para toda página (NFR-051).
- Download aponta para GitHub Release com `SHA256SUMS` e assinatura (FR-010).
- Zero métrica inventada: números só com fonte em `docs/releases/` (NFR-033).

## Nunca
- Telemetria, analytics de terceiros ou cookies não essenciais (NFR-033).
- "24.04 LTS", "arm64", versões de kernel/driver fixas (ADR-028).
- Comparativos com concorrentes sem medição publicada (G2).

## Telas desta pasta
`forjaos_docs_documenta_o_t_cnica_oficial`, `forjaos_o_sistema_operacional_para_quem_desenvolve_e_joga`.

## Antes de começar aqui
1. `python3 scripts/roadmap.py available` → o item escolhido tem escopo desta pasta? Se não, pare.
2. `AGENTS.md` da raiz → regras e fluxo valem integralmente.
3. Telas desta pasta → leia a spec em `docs/design-system/telas/` **antes** do `code.html`.
