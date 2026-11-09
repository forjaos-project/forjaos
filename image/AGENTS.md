# image/ — imagem bootc do ForjaOS

**Escopo:** FR-001–FR-016 (imagem, base, instalação, dual boot), FR-020–FR-024 (wizard de 1º boot), FR-030–FR-034 (dev experience via recipes), FR-043 (`hero-game.target`), NFR-001/002/011/012/013/020–023/026.
**Equivale a:** `forjaos-image` do PRD §5.2 (ADR-026).

## Toolchain e testes
- `Containerfile` em `image/Containerfile`; `build_files/` (scripts de build), `system_files/` (overlay de `/usr` e `/etc`), `recipes/` (`ujust`), `firstboot/` (wizard QML).
- Testar: `scripts/run-shell-tests.sh`; `podman build -f image/Containerfile .` (CI); `scripts/check-branding.sh`; em VM: `bootc switch`, `systemd-analyze`, `free -m`, `ss -tlnp`.
- Shell: `set -euo pipefail` em todo script; testes em bash puro em `scripts/tests/`.

## DoD local
- `check-branding.sh` OK (zero Fedora/Bazzite/Bluefin visível — FR-002).
- `/etc/os-release` com `NAME="ForjaOS"`, `ID=forjaos`, `ID_LIKE="fedora"` (FR-003).
- Serviços habilitados/desabilitados exatamente como FR-006; `ss -tlnp` sem porta externa (NFR-012).
- Tamanho da ISO ≤ 6 GB (NFR-011).

## Nunca
- Desligar SELinux ou firewalld "para facilitar" (ADR-022).
- Adicionar repositório de terceiros, COPR ou pacote proprietário na imagem sem ADR (G4; proprietários só via instalador no 1º boot).
- Fixar número de kernel ou versão de driver (vem da base — ADR-001).
- Embarcar Fira Code ou tema Breeze como padrão visível.

## Telas desta pasta
`forjaos_wizard_de_primeiro_boot`, `forjaos_wizard_de_primeiro_boot_passo_6_resumo_conclus_o` (QML em `image/firstboot/`); layout de painel/dock do desktop em conjunto com `brand/`.

## Antes de começar aqui
1. `python3 scripts/roadmap.py available` → o item escolhido tem escopo desta pasta? Se não, pare.
2. `AGENTS.md` da raiz → regras e fluxo valem integralmente.
3. Telas desta pasta → leia a spec em `docs/design-system/telas/` **antes** do `code.html`.
