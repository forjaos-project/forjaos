#!/usr/bin/env bash
# check-branding.sh — FR-002 / G4: nenhuma marca Fedora, Bazzite ou Bluefin visível na imagem ForjaOS.
#
# ESTADO: STUB. A implementação real é o item F0-004 do roadmap (docs/STATUS.md). Até lá, este script
# documenta o que vai verificar e sai 0 para não bloquear o CI de documentação.
#
# O que a versão real fará (sobre a imagem OCI construída, via `podman run --rm <imagem> …` ou sobre o rootfs extraído):
#   1. /etc/os-release: NAME="ForjaOS", ID=forjaos, PRETTY_NAME começa com "ForjaOS"; ID_LIKE="fedora" é permitido (FR-003).
#   2. Pacotes proibidos presentes: fedora-logos, fedora-release-identity-*, bazzite-branding*, bluefin-*; exige forjaos-branding.
#   3. Strings em superfícies visíveis: /usr/share/plymouth/themes/default.plymouth, /etc/sddm.conf.d/*, /usr/share/wallpapers (default),
#      /usr/share/plasma/look-and-feel (padrão), /usr/share/kde-settings, /etc/motd, /etc/issue, Discover/Flatpak remotes nomeados.
#      Falha se encontrar (case-insensitive) "Fedora", "Bazzite", "Bluefin", "Universal Blue" fora de /usr/share/licenses e docs legais.
#   4. GRUB: /boot/grub2/themes e /etc/default/grub não referenciam tema Fedora; entradas de boot usam "ForjaOS".
#   5. Ícones: /usr/share/icons/hicolor/*/apps/fedora-logo* ausentes; start-here aponta para o logo ForjaOS.
#   6. Saída em modo --json para o CI e lista de ocorrências com caminho e linha.
#
# Uso previsto: scripts/check-branding.sh [--image ghcr.io/<org>/forjaos-nvidia-open:testing | --rootfs <dir>] [--json]
set -euo pipefail
echo "check-branding: STUB — implementação real é a tarefa F0-004 (ver docs/STATUS.md). Nada verificado."
exit 0
