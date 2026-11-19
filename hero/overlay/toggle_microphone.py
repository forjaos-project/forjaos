#!/usr/bin/python3
"""Toggle the HERO capture gate from the global Plasma shortcut."""

import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage, QDBusVariant


def main() -> int:
    _app = QCoreApplication(sys.argv)
    bus = QDBusConnection.sessionBus()
    hero = QDBusInterface("org.forjaos.Hero", "/org/forjaos/Hero", "org.forjaos.Hero", bus)
    if not bus.isConnected() or not hero.isValid():
        return 1
    enabled = hero.property("MicrophoneEnabled")
    if not isinstance(enabled, bool):
        return 1
    properties = QDBusInterface(
        "org.forjaos.Hero", "/org/forjaos/Hero", "org.freedesktop.DBus.Properties", bus
    )
    reply = properties.call("Set", "org.forjaos.Hero", "MicrophoneEnabled", QDBusVariant(not enabled))
    return 0 if reply.type() != QDBusMessage.MessageType.ErrorMessage else 1


if __name__ == "__main__":
    raise SystemExit(main())
