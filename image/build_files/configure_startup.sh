#!/usr/bin/env bash
set -euo pipefail

root=${1:-/}
xdg="$root/etc/xdg"
units="$root/usr/lib/systemd/user"

# These two scripts implement the base GPU workaround and first-user setup.
# Keep their execution while replacing only the visible systemd unit names.
for name in dynamic-fixes user-setup; do
  test -f "$root/usr/libexec/bazzite-$name"
  base_unit="$units/bazzite-$name.service"
  test -f "$base_unit"
  grep -Fxq "ExecStart=/usr/libexec/bazzite-$name" "$base_unit"
  target=$(sed -n 's/^WantedBy=//p' "$base_unit")
  case "$target" in
    default.target|graphical-session-pre.target) ;;
    *) echo "unsupported Bazzite unit target for $name: $target" >&2; exit 1 ;;
  esac
  links="$xdg/systemd/user/$target.wants"
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
  base_unit="$units/bazzite-$name.service"
  target=$(sed -n 's/^WantedBy=//p' "$base_unit")
  links="$xdg/systemd/user/$target.wants"
  awk -v name="$name" -v memory="$memory" -v quota="$quota" '
    /^Description=/ { print "Description=ForjaOS " name " user setup"; next }
    $0 == "ExecStart=/usr/libexec/bazzite-" name {
      print "ExecStart=/usr/libexec/forjaos-" name
      print "MemoryMax=" memory
      print "CPUQuota=" quota
      print "Nice=10"
      next
    }
    { print }
  ' "$base_unit" > "$units/forjaos-$name.service"
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
