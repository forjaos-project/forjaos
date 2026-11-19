#!/usr/bin/python3
"""Global toggle for the local HERO push-to-talk capture."""

import json
import sys

from PySide6.QtCore import QCoreApplication, QEventLoop, QObject, SLOT, QTimer, Slot
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage


BUS_NAME = "org.forjaos.Hero"
OBJECT_PATH = "/org/forjaos/Hero"
INTERFACE = "org.forjaos.Hero"


class VoiceResult(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.loop = QEventLoop()
        self.text = ""
        self.failed = False
        self.done = False

    @Slot(str)
    def transcribed(self, text: str) -> None:
        self.text = text
        self.done = True
        self.loop.quit()

    @Slot(str)
    def failed_result(self, _reason: str) -> None:
        self.failed = True
        self.done = True
        self.loop.quit()


def notify(bus: QDBusConnection, body: str) -> None:
    notifications = QDBusInterface(
        "org.freedesktop.Notifications", "/org/freedesktop/Notifications",
        "org.freedesktop.Notifications", bus,
    )
    if notifications.isValid():
        notifications.call("Notify", "ForjaOS HERO", 0, "audio-input-microphone", "HERO", body, [], {}, 5000)


def main() -> int:
    _app = QCoreApplication(sys.argv)
    bus = QDBusConnection.sessionBus()
    hero = QDBusInterface(BUS_NAME, OBJECT_PATH, INTERFACE, bus)
    if not bus.isConnected() or not hero.isValid():
        return 1

    result = VoiceResult()
    bus.connect(BUS_NAME, OBJECT_PATH, INTERFACE, "VoiceTranscribed", "s", result, SLOT("transcribed(QString)"))
    bus.connect(BUS_NAME, OBJECT_PATH, INTERFACE, "VoiceFailed", "s", result, SLOT("failed_result(QString)"))
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
    if result.text:
        notify(bus, result.text[:4000])
        return 0
    notify(bus, "Não foi possível transcrever a gravação local.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
