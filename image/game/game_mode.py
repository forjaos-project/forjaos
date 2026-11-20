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
POWER_PROFILES = "org.freedesktop.UPower.PowerProfiles"
POWER_PROFILES_PATH = "/org/freedesktop/UPower/PowerProfiles"


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


def user_service_active(service: str) -> bool:
    return systemctl("is-active", "--quiet", service).returncode == 0


def stop_memory_for_game() -> bool:
    if not user_service_active("memd.service"):
        return False
    result = systemctl("stop", "memd.service")
    if result.returncode:
        print("Modo Jogo: não foi possível pausar a Memória.", file=sys.stderr)
    return True


def restore_memory_after_game(was_active: bool) -> None:
    if was_active and not user_service_active("memd.service"):
        result = systemctl("start", "memd.service")
        if result.returncode:
            print("Modo Jogo: não foi possível restaurar a Memória.", file=sys.stderr)


def unload_ollama_models() -> None:
    cli = Path.home() / ".brew/bin/ollama"
    if not cli.is_file():
        found = shutil.which("ollama")
        if not found:
            return
        cli = Path(found)
    try:
        result = subprocess.run([str(cli), "ps"], capture_output=True, text=True,
                                check=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"Modo Jogo: não foi possível consultar modelos Ollama: {error}.", file=sys.stderr)
        return
    if result.returncode:
        print("Modo Jogo: não foi possível consultar modelos Ollama.", file=sys.stderr)
        return

    models = []
    for line in result.stdout.splitlines():
        columns = line.split()
        if not columns or columns[0].upper() == "NAME":
            continue
        model = columns[0]
        if len(model) <= 128 and all(char.isalnum() or char in "._:/-" for char in model):
            models.append(model)
    for model in dict.fromkeys(models):
        try:
            stopped = subprocess.run([str(cli), "stop", model], capture_output=True, text=True,
                                     check=False, timeout=15)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f"Modo Jogo: falha ao descarregar {model}: {error}.", file=sys.stderr)
            continue
        if stopped.returncode:
            print(f"Modo Jogo: falha ao descarregar {model}.", file=sys.stderr)


def set_performance_profile() -> str | None:
    """Select the performance profile and return the previous profile for restoration."""
    try:
        import dbus

        bus = dbus.SystemBus()
        proxy = bus.get_object(POWER_PROFILES, POWER_PROFILES_PATH)
        properties = dbus.Interface(proxy, "org.freedesktop.DBus.Properties")
        active = str(properties.Get(POWER_PROFILES, "ActiveProfile"))
        available = properties.Get(POWER_PROFILES, "Profiles")
        if not any(str(profile.get("Profile")) == "performance" for profile in available):
            print("Modo Jogo: perfil performance indisponível.", file=sys.stderr)
            return None
        if active != "performance":
            properties.Set(POWER_PROFILES, "ActiveProfile",
                           dbus.String("performance", variant_level=1))
            return active
        return None
    except Exception as error:
        print(f"Modo Jogo: perfil de energia indisponível: {error}", file=sys.stderr)
        return None


def restore_power_profile(previous: str | None) -> None:
    """Restore only when the profile is still the one selected by Game Mode."""
    if previous is None or previous == "performance":
        return
    try:
        import dbus

        bus = dbus.SystemBus()
        proxy = bus.get_object(POWER_PROFILES, POWER_PROFILES_PATH)
        properties = dbus.Interface(proxy, "org.freedesktop.DBus.Properties")
        active = str(properties.Get(POWER_PROFILES, "ActiveProfile"))
        if active == "performance":
            properties.Set(POWER_PROFILES, "ActiveProfile",
                           dbus.String(previous, variant_level=1))
    except Exception as error:
        print(f"Modo Jogo: não foi possível restaurar o perfil de energia: {error}",
              file=sys.stderr)


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
    memd_was_active = stop_memory_for_game()
    unload_ollama_models()
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

    previous_power_profile = set_performance_profile()

    try:
        stop.wait()
    finally:
        if notifications is not None and cookie is not None:
            try:
                notifications.UnInhibit(cookie)
            except Exception:
                pass  # Closing the session bus also releases this inhibition.
        restore_power_profile(previous_power_profile)
        restore_memory_after_game(memd_was_active)


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
