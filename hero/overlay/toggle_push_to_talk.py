#!/usr/bin/python3
"""Global toggle for the local HERO push-to-talk capture."""

import json
import os
import socket
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEventLoop, QObject, SLOT, QTimer, Slot
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage


BUS_NAME = "org.forjaos.Hero"
OBJECT_PATH = "/org/forjaos/Hero"
INTERFACE = "org.forjaos.Hero"
SCREEN_SAVER = "org.freedesktop.ScreenSaver"
SCREEN_SAVER_PATH = "/ScreenSaver"


class VoiceResult(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.loop = QEventLoop()
        self.answer = ""
        self.failed = False
        self.done = False

    @Slot(str)
    def answered(self, answer: str) -> None:
        self.answer = answer
        self.done = True
        self.loop.quit()

    @Slot(str)
    def failed_result(self, _reason: str) -> None:
        self.failed = True
        self.done = True
        self.loop.quit()


def notify(bus: QDBusConnection, body: str) -> None:
    saver = QDBusInterface(SCREEN_SAVER, SCREEN_SAVER_PATH, SCREEN_SAVER, bus)
    if not saver.isValid():
        return
    lock_reply = saver.call("GetActive")
    if lock_reply.type() == QDBusMessage.MessageType.ErrorMessage or lock_reply.arguments() != [False]:
        return
    notifications = QDBusInterface(
        "org.freedesktop.Notifications", "/org/freedesktop/Notifications",
        "org.freedesktop.Notifications", bus,
    )
    if notifications.isValid():
        notifications.call("Notify", "ForjaOS HERO", 0, "audio-input-microphone", "HERO", body, [], {}, 5000)


def hero_state() -> str:
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    if not runtime:
        return "indisponível"
    path = Path(runtime) / "forjaos" / "herod.sock"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(0.15)
            connection.connect(str(path))
            data = connection.recv(256).decode("utf-8", errors="replace").splitlines()[0]
        return str(json.loads(data).get("state", "indisponível"))
    except (OSError, ValueError, IndexError):
        return "indisponível"


def main() -> int:
    _app = QCoreApplication(sys.argv)
    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        return 1
    if hero_state() not in {"ocioso", "falando", "gravando"}:
        notify(bus, "Gatilho ignorado: HERO ocupado ou indisponível.")
        return 1
    hero = QDBusInterface(BUS_NAME, OBJECT_PATH, INTERFACE, bus)
    if not hero.isValid():
        return 1

    result = VoiceResult()
    connected_answer = bus.connect(BUS_NAME, OBJECT_PATH, INTERFACE, "VoiceAnswer", "s", result, SLOT("answered(QString)"))
    connected_failure = bus.connect(BUS_NAME, OBJECT_PATH, INTERFACE, "VoiceFailed", "s", result, SLOT("failed_result(QString)"))
    if not connected_answer or not connected_failure:
        return 1
    reply = hero.call("TogglePushToTalk")
    if reply.type() == QDBusMessage.MessageType.ErrorMessage:
        return 1
    try:
        status = json.loads(str(reply.arguments()[0])).get("status")
    except (ValueError, TypeError, IndexError):
        return 1
    if status == "recording":
        notify(bus, "Gravando. Pressione Super+Shift+M novamente para terminar.")
        return 0
    if status != "transcribing":
        notify(bus, "O microfone está desligado ou o HERO está ocupado.")
        return 1
    if not result.done:
        QTimer.singleShot(65_000, result.loop.quit)
        result.loop.exec()
    if result.answer:
        notify(bus, result.answer[:4000])
        return 0
    notify(bus, "Não foi possível concluir o turno de voz local.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
