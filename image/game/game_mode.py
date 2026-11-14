#!/usr/bin/env python3
"""User-session Game Mode: detect launchers and hold scoped desktop settings."""

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading


GAME_PROCESSES = frozenset({"steam", "gamescope"})
TARGET = "hero-game.target"
POLL_SECONDS = 5


def runtime_dir() -> Path:
    root = os.environ.get("XDG_RUNTIME_DIR")
    if not root:
        raise RuntimeError("XDG_RUNTIME_DIR indisponível; abra uma sessão de usuário.")
    path = Path(root) / "forjaos"
    path.mkdir(mode=0o700, exist_ok=True)
    if path.is_symlink() or path.stat().st_uid != os.getuid():
        raise RuntimeError("Diretório de execução do Modo Jogo não pertence ao usuário.")
    return path


def gaming_process_running(proc_root: Path = Path("/proc"), uid: int | None = None) -> bool:
    uid = os.getuid() if uid is None else uid
    try:
        entries = proc_root.iterdir()
        for entry in entries:
            if not entry.name.isdecimal():
                continue
            try:
                if entry.stat().st_uid == uid and (entry / "comm").read_text().strip() in GAME_PROCESSES:
                    return True
            except (OSError, UnicodeError):
                continue  # The process may have exited between discovery and inspection.
    except OSError:
        return False
    return False


def systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", "--user", *args], capture_output=True,
                          text=True, check=False)


def is_active() -> bool:
    return systemctl("is-active", "--quiet", TARGET).returncode == 0


def change_mode(action: str, runtime: Path) -> int:
    manual = runtime / "game-mode-manual"
    suppressed = runtime / "game-mode-suppressed"
    if action == "on":
        result = systemctl("start", TARGET)
        if result.returncode == 0:
            manual.touch(mode=0o600)
            suppressed.unlink(missing_ok=True)
    else:
        # An explicit off wins until the current Steam/gamescope process exits.
        if gaming_process_running():
            suppressed.touch(mode=0o600)
        else:
            suppressed.unlink(missing_ok=True)
        manual.unlink(missing_ok=True)
        result = systemctl("stop", TARGET)
    if result.returncode:
        print(result.stderr.strip() or "Não foi possível alterar o Modo Jogo.", file=sys.stderr)
    return result.returncode


def watch_once(runtime: Path, game_running: bool, active: bool) -> None:
    manual = runtime / "game-mode-manual"
    suppressed = runtime / "game-mode-suppressed"
    if game_running:
        if not active and not suppressed.exists():
            systemctl("start", TARGET)
    else:
        suppressed.unlink(missing_ok=True)
        if active and not manual.exists():
            systemctl("stop", TARGET)


def watch(runtime: Path) -> None:
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    while not stop.is_set():
        watch_once(runtime, gaming_process_running(), is_active())
        stop.wait(POLL_SECONDS)
    if is_active() and not (runtime / "game-mode-manual").exists():
        systemctl("stop", TARGET)


def game_session() -> None:
    """Keep KDE's DND inhibition and the power-profile hold for this target."""
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    cookie = None
    notifications = None
    try:
        import dbus

        bus = dbus.SessionBus()
        notifications = dbus.Interface(
            bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications"),
            dbus_interface="org.freedesktop.Notifications",
        )
        cookie = notifications.Inhibit("forjaos-game", "Modo Jogo", dbus.Dictionary({}, signature="sv"))
    except Exception as error:
        print(f"Modo Jogo: Não perturbe indisponível: {error}", file=sys.stderr)

    power = None
    if shutil.which("powerprofilesctl"):
        try:
            power = subprocess.Popen(
                ["powerprofilesctl", "launch", "--profile", "performance", "--reason",
                 "ForjaOS Game Mode", "--appid", "forjaos-game", "/usr/bin/sleep", "infinity"],
                start_new_session=True,
            )
            try:
                status = power.wait(timeout=0.2)
                print(f"Modo Jogo: perfil performance indisponível (código {status}).",
                      file=sys.stderr)
                power = None
            except subprocess.TimeoutExpired:
                pass
        except OSError as error:
            print(f"Modo Jogo: perfil de energia indisponível: {error}", file=sys.stderr)
    else:
        print("Modo Jogo: powerprofilesctl indisponível.", file=sys.stderr)

    try:
        stop.wait()
    finally:
        if power is not None and power.poll() is None:
            try:
                os.killpg(power.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                power.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(power.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                power.wait()
        if notifications is not None and cookie is not None:
            try:
                notifications.UnInhibit(cookie)
            except Exception:
                pass  # Closing the session bus also releases this inhibition.


def main() -> int:
    parser = argparse.ArgumentParser(description="Modo Jogo do ForjaOS")
    parser.add_argument("action", choices=["on", "off", "status", "watch", "session"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.action == "session":
        game_session()
        return 0
    try:
        runtime = runtime_dir()
        if args.action == "watch":
            watch(runtime)
            return 0
        if args.action == "status":
            active = is_active()
            if args.json:
                print(json.dumps({"game_mode": "on" if active else "off",
                                  "automatic": gaming_process_running()}))
            else:
                print("Modo Jogo ativo" if active else "Modo Jogo desligado")
            return 0
        result = change_mode(args.action, runtime)
        if args.json:
            print(json.dumps({"game_mode": args.action if result == 0 else "error"}))
        elif result == 0:
            print("Modo Jogo ativo" if args.action == "on" else "Modo Jogo desligado")
        return result
    except (OSError, RuntimeError) as error:
        print(f"Modo Jogo: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
