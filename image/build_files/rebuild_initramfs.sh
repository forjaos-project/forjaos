#!/usr/bin/env bash
# Embed the ForjaOS boot logo after replacing the inherited base artwork.
set -euo pipefail

logo=/usr/share/pixmaps/system-logo-white.png
[[ -s "$logo" ]] || { echo "missing ForjaOS boot logo: $logo" >&2; exit 1; }

found=0
for kernel_dir in /usr/lib/modules/*; do
    [[ -d "$kernel_dir" && -f "$kernel_dir/vmlinuz" ]] || continue
    found=1
    kernel=${kernel_dir##*/}
    image="$kernel_dir/initramfs.img"
    DRACUT_NO_XATTR=1 dracut --no-hostonly --kver "$kernel" --reproducible --add fido2 -f "$image"
    lsinitrd -f usr/share/pixmaps/system-logo-white.png "$image" | cmp - "$logo"
done

(( found == 1 )) || { echo "no installed kernel for initramfs rebuild" >&2; exit 1; }
