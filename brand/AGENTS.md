# brand/ — identidade visual e temas

**Escopo:** FR-050–FR-058 (tema, layout, logo, mascote, wallpapers, Plymouth, SDDM, atalhos), FR-002 (rebranding), ADR-007 (licenças), ADR-027 (tokens).
**Equivale a:** `forjaos-brand` (ADR-026). Artes CC BY-SA 4.0 + `TRADEMARK.md`; código Apache-2.0. Pacote `forjaos-branding` rpm, release `brand-vX.Y.Z`.

## Fonte única
`brand/palette.json`. Tudo em `plasma/`, `sddm/`, `plymouth/`, `grub/`, `konsole/`, `vscode/`, `gtk/`, `qml/ForjaTheme.qml`, `tokens.css` é **gerado** dele (gerador = item F1-005). Até o gerador existir, qualquer arquivo de tema é escrito à mão **copiando valores do palette** e passa no `check-tokens.sh`.

## Toolchain e testes
- `scripts/check-tokens.sh` (obrigatório); `qmllint` em QML; SVG otimizado (`svgo`) com camadas nomeadas preservadas.
- `python3 brand/themes/build_themes.py --check` confirma que Plasma, SDDM, Plymouth, GRUB, Konsole, VS Code, GTK, QML e `tokens.css` continuam gerados da paleta.
- Captura de cada superfície (Plasma, SDDM, Plymouth, GRUB, Konsole, VS Code) no release (FR-051).
- Mascote: animação a 60 fps no plasmoid (FR-054, FR-123).

## DoD local
- Nenhum hex fora do palette; fontes só Plus Jakarta Sans / JetBrains Mono / Inter(dense).
- Logo em SVG mono/cor/dark/light + ícones 16–512 (FR-053).
- Mascote com camadas `body ears eyes mouth glow badge` e 15 visemes (FR-054, FR-084).
- Wallpapers 4K em `/usr/share/wallpapers/ForjaOS/` (FR-055).
- Licença de cada fonte, voz e arte verificada e registrada em `brand/LICENSES.md`.

## Nunca
- Fira Code, Roboto ou Noto como UI (ADR-027).
- Reutilizar arte, logo ou mascote de terceiros; nada de Marvel/"Jarvis" (ADR-006).
- Alterar um token existente sem ADR.

## Telas desta pasta
`forjaos_splash_plymouth`, `forjaos_bootloader_grub`, `forjaos_sddm_login`, `forjaos_desktop_principal_dock`, `forjaos_desktop_principal_modo_claro_alabaster_forge`, tema Konsole de `forjaos_terminal_konsole_dev_forja_doctor`.

## Antes de começar aqui
1. `python3 scripts/roadmap.py available` → o item escolhido tem escopo desta pasta? Se não, pare.
2. `AGENTS.md` da raiz → regras e fluxo valem integralmente.
3. Telas desta pasta → leia a spec em `docs/design-system/telas/` **antes** do `code.html`.
