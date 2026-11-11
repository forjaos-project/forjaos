#!/usr/bin/env bash
set -euo pipefail

root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT
mkdir -p "$root/etc/xdg/autostart" "$root/etc/xdg/systemd/user/default.target.wants" "$root/usr/lib/systemd/user" "$root/usr/libexec"
printf '[Desktop Entry]\nName=Bazzite Announcements\n' > "$root/etc/xdg/autostart/bazzite-announcement.desktop"
printf '[General]\nName=Bazzite\n' > "$root/etc/xdg/kcm-about-distrorc"
for name in dynamic-fixes user-setup; do
  printf '[Unit]\nDescription=Bazzite setup\n[Service]\nType=simple\nExecStart=/usr/libexec/bazzite-%s\n[Install]\nWantedBy=default.target\n' "$name" > "$root/usr/lib/systemd/user/bazzite-$name.service"
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
  grep -q '^Type=simple$' "$root/usr/lib/systemd/user/forjaos-$name.service"
  grep -q "^exec /usr/libexec/bazzite-$name" "$root/usr/libexec/forjaos-$name"
  grep -q '^MemoryMax=' "$root/usr/lib/systemd/user/forjaos-$name.service"
  grep -q '^CPUQuota=' "$root/usr/lib/systemd/user/forjaos-$name.service"
  grep -q '^Nice=' "$root/usr/lib/systemd/user/forjaos-$name.service"
done

# Current Bazzite enables these units before the graphical session instead.
mkdir -p "$root/etc/xdg/systemd/user/graphical-session-pre.target.wants"
for name in dynamic-fixes user-setup; do
  rm -f -- "$root/etc/xdg/systemd/user/default.target.wants/forjaos-$name.service"
  printf '[Unit]\nDescription=Bazzite setup\nConditionEnvironment=XDG_SESSION_CLASS=user\n[Service]\nType=simple\nExecStart=/usr/libexec/bazzite-%s\n[Install]\nWantedBy=graphical-session-pre.target\n' "$name" > "$root/usr/lib/systemd/user/bazzite-$name.service"
  ln -s "/usr/lib/systemd/user/bazzite-$name.service" "$root/etc/xdg/systemd/user/graphical-session-pre.target.wants/bazzite-$name.service"
done

bash image/build_files/configure_startup.sh "$root"
for name in dynamic-fixes user-setup; do
  links="$root/etc/xdg/systemd/user/graphical-session-pre.target.wants"
  test ! -e "$links/bazzite-$name.service"
  test "$(readlink "$links/forjaos-$name.service")" = "/usr/lib/systemd/user/forjaos-$name.service"
  test ! -e "$root/etc/xdg/systemd/user/default.target.wants/forjaos-$name.service"
  grep -q '^WantedBy=graphical-session-pre.target$' "$root/usr/lib/systemd/user/forjaos-$name.service"
  grep -q '^ConditionEnvironment=XDG_SESSION_CLASS=user$' "$root/usr/lib/systemd/user/forjaos-$name.service"
done

echo 'startup replacement: ok'
