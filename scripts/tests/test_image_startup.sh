#!/usr/bin/env bash
set -euo pipefail

root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT
mkdir -p "$root/etc/xdg/autostart" "$root/etc/xdg/systemd/user/default.target.wants" "$root/usr/lib/systemd/user" "$root/usr/libexec"
printf '[Desktop Entry]\nName=Bazzite Announcements\n' > "$root/etc/xdg/autostart/bazzite-announcement.desktop"
printf '[General]\nName=Bazzite\n' > "$root/etc/xdg/kcm-about-distrorc"
for name in dynamic-fixes user-setup; do
  printf '[Service]\nExecStart=/usr/libexec/bazzite-%s\n' "$name" > "$root/usr/lib/systemd/user/bazzite-$name.service"
  touch "$root/usr/libexec/bazzite-$name"
  ln -s "/usr/lib/systemd/user/bazzite-$name.service" "$root/etc/xdg/systemd/user/default.target.wants/bazzite-$name.service"
done

bash image/build_files/configure_startup.sh "$root"
test ! -e "$root/etc/xdg/autostart/bazzite-announcement.desktop"
grep -q '^Name=ForjaOS$' "$root/etc/xdg/kcm-about-distrorc"
for name in dynamic-fixes user-setup; do
  test ! -e "$root/etc/xdg/systemd/user/default.target.wants/bazzite-$name.service"
  test "$(readlink "$root/etc/xdg/systemd/user/default.target.wants/forjaos-$name.service")" = "/usr/lib/systemd/user/forjaos-$name.service"
  grep -q "^ExecStart=/usr/libexec/forjaos-$name$" "$root/usr/lib/systemd/user/forjaos-$name.service"
  grep -q "^exec /usr/libexec/bazzite-$name" "$root/usr/libexec/forjaos-$name"
  grep -q '^MemoryMax=' "$root/usr/lib/systemd/user/forjaos-$name.service"
  grep -q '^CPUQuota=' "$root/usr/lib/systemd/user/forjaos-$name.service"
  grep -q '^Nice=' "$root/usr/lib/systemd/user/forjaos-$name.service"
done

echo 'startup replacement: ok'
