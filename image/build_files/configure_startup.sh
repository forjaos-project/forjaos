#!/usr/bin/env bash
set -euo pipefail

root=${1:-/}
xdg="$root/etc/xdg"
units="$root/usr/lib/systemd/user"
links="$xdg/systemd/user/default.target.wants"

# These two scripts implement the base GPU workaround and first-user setup.
# Keep their execution while replacing only the visible systemd unit names.
for name in dynamic-fixes user-setup; do
  test -f "$root/usr/libexec/bazzite-$name"
  old_link="$links/bazzite-$name.service"
  if test -L "$old_link"; then
    test "$(readlink "$old_link")" = "/usr/lib/systemd/user/bazzite-$name.service"
  else
    test -L "$links/forjaos-$name.service"
  fi
done

for name in dynamic-fixes user-setup; do
  case "$name" in
    dynamic-fixes) memory=256M; quota=50% ;;
    user-setup) memory=1G; quota=100% ;;
  esac
  cat > "$units/forjaos-$name.service" <<EOF
[Unit]
Description=ForjaOS $name user setup
ConditionUser=!@system

[Service]
Type=oneshot
ExecStart=/usr/libexec/forjaos-$name
MemoryMax=$memory
CPUQuota=$quota
Nice=10

[Install]
WantedBy=default.target
EOF
  printf '#!/usr/bin/env bash\nexec /usr/libexec/bazzite-%s "$@"\n' "$name" > "$root/usr/libexec/forjaos-$name"
  chmod 0755 "$root/usr/libexec/forjaos-$name"
  rm -f -- "$links/bazzite-$name.service"
  ln -sfn "/usr/lib/systemd/user/forjaos-$name.service" "$links/forjaos-$name.service"
done

rm -f -- "$xdg/autostart/bazzite-announcement.desktop"
cat > "$xdg/kcm-about-distrorc" <<'EOF'
[General]
LogoPath=/usr/share/pixmaps/system-logo-white.png
Name=ForjaOS
Website=https://github.com/forjaos-project/forjaos
Variant=Desktop Edition
EOF
