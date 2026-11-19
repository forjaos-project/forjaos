#!/usr/bin/python3
"""Launch the HERO command overlay in an unlocked Plasma session."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import (
    QCoreApplication,
    QLocale,
    QObject,
    Property,
    QRunnable,
    SIGNAL,
    QThreadPool,
    QTimer,
    QUrl,
    Signal,
    SLOT,
    Slot,
)
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage, QDBusPendingCallWatcher, QDBusVariant
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QTranslator
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket


BUS_NAME = "org.forjaos.Hero"
OBJECT_PATH = "/org/forjaos/Hero"
INTERFACE = "org.forjaos.Hero"
SCREEN_SAVER = "org.freedesktop.ScreenSaver"
SCREEN_SAVER_PATH = "/ScreenSaver"
DEFAULTS = {
    "heroState": "indisponível",
    "wifi": "indisponível",
    "bluetooth": "indisponível",
    "vpn": "indisponível",
    "vpnName": "",
    "gameMode": "indisponível",
    "firewall": "indisponível",
    "securityServices": [],
    "dnd": "indisponível",
    "cpu": "—",
    "ram": "—",
    "ramPercent": 0,
    "gpu": "indisponível",
    "vram": "indisponível",
    "vramPercent": 0,
    "containers": [],
    "models": [],
    "audit": [],
    "rxRate": "—",
    "txRate": "—",
    "latency": "sem teste ativo",
    "lan": "varredura desativada",
}


def _command(args: list[str], timeout: float = 1.0) -> str:
    try:
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "LC_ALL": "C.UTF-8"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _command_result(args: list[str], timeout: float = 1.0) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "LC_ALL": "C.UTF-8"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return result.returncode == 0, result.stdout.strip()


def _service_state(name: str) -> str:
    _, state = _command_result(["systemctl", "is-active", name])
    return "ativo" if state == "active" else "inativo" if state in {"inactive", "failed"} else "indisponível"


def _network_counters() -> tuple[int, int]:
    received = sent = 0
    try:
        for line in Path("/proc/net/dev").read_text(encoding="ascii").splitlines()[2:]:
            interface, counters = line.split(":", 1)
            if interface.strip() == "lo":
                continue
            values = counters.split()
            received += int(values[0])
            sent += int(values[8])
    except (OSError, ValueError, IndexError):
        pass
    return received, sent


def _cpu_counters() -> tuple[int, int]:
    try:
        values = Path("/proc/stat").read_text(encoding="ascii").splitlines()[0].split()[1:]
        total = sum(int(value) for value in values)
        idle = int(values[3]) + (int(values[4]) if len(values) > 4 else 0)
        return total, idle
    except (OSError, ValueError, IndexError):
        return 0, 0


class SnapshotSignals(QObject):
    finished = Signal(dict)


class SnapshotWorker(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = SnapshotSignals()

    def run(self) -> None:
        snapshot = {**DEFAULTS, "audit": []}
        snapshot["cpuCounters"] = _cpu_counters()
        snapshot["networkCounters"] = _network_counters()

        try:
            memory = {}
            for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
                key, value = line.split(":", 1)
                memory[key] = int(value.split()[0])
            total = memory.get("MemTotal", 0)
            available = memory.get("MemAvailable", total)
            used = max(0, total - available)
            if total:
                snapshot["ram"] = f"{used / 1_048_576:.1f} GB"
                snapshot["ramPercent"] = round(used * 100 / total)
        except (OSError, ValueError, IndexError):
            pass

        nm_ok, active = _command_result(["nmcli", "--terse", "--fields", "NAME,TYPE", "connection", "show", "--active"])
        connections = [line.rsplit(":", 1) for line in active.splitlines() if ":" in line]
        wireless = next((name for name, kind in connections if kind == "802-11-wireless"), "")
        vpn = next((name for name, kind in connections if kind in {"vpn", "wireguard"}), "") if nm_ok else ""
        radio = _command(["nmcli", "radio", "wifi"])
        snapshot["wifi"] = wireless if wireless else ("ligado · sem conexão" if radio == "enabled" else "desligado" if radio == "disabled" else "indisponível")
        snapshot["vpn"] = vpn if vpn else ("desconectada" if nm_ok else "indisponível")
        snapshot["vpnName"] = vpn

        inhibited = _command(["busctl", "--user", "get-property", "org.freedesktop.Notifications", "/org/freedesktop/Notifications", "org.freedesktop.Notifications", "Inhibited"])
        snapshot["dnd"] = "ativo" if inhibited == "b true" else "desligado" if inhibited == "b false" else "indisponível"

        bluetooth = _command(["bluetoothctl", "show"])
        if bluetooth:
            powered = next((line.split(":", 1)[1].strip() for line in bluetooth.splitlines() if line.strip().startswith("Powered:")), "")
            snapshot["bluetooth"] = "ligado" if powered == "yes" else "desligado" if powered == "no" else "indisponível"

        game = _command(["systemctl", "--user", "is-active", "hero-game.target"])
        snapshot["gameMode"] = "ativo" if game == "active" else "desligado" if game in {"inactive", "failed"} else "indisponível"
        firewall = _command(["firewall-cmd", "--state"])
        snapshot["firewall"] = "ativo" if firewall == "running" else "inativo" if firewall else "indisponível"
        services = [
            {"name": "firewalld", "status": snapshot["firewall"]},
            {"name": "auditd", "status": _service_state("auditd.service")},
            {"name": "journald", "status": _service_state("systemd-journald.service")},
        ]
        for package, service in (("crowdsec", "crowdsec.service"), ("suricata", "suricata.service")):
            installed, _ = _command_result(["rpm", "-q", package])
            if installed:
                services.append({"name": package, "status": _service_state(service)})
        snapshot["securityServices"] = services

        gpu = _command([
            "nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ])
        if gpu:
            fields = [value.strip() for value in gpu.splitlines()[0].split(",")]
            if len(fields) == 3:
                snapshot["gpu"] = f"{fields[0]}%"
                snapshot["vram"] = f"{int(fields[1]) / 1024:.1f} / {int(fields[2]) / 1024:.0f} GB"
                snapshot["vramPercent"] = round(int(fields[1]) * 100 / max(1, int(fields[2])))

        containers = _command(["podman", "ps", "--format", "{{.Names}}\t{{.Status}}"], timeout=1.5)
        if not containers:
            containers = _command(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"], timeout=1.5)
        snapshot["containers"] = [
            {"name": line.split("\t", 1)[0], "status": line.split("\t", 1)[1] if "\t" in line else "rodando"}
            for line in containers.splitlines()[:4]
        ]

        models = _command(["ollama", "list"])
        snapshot["models"] = [line.split()[0] for line in models.splitlines()[1:5] if line.split()]

        # AuditEvent does not contain prompts or audio; only expose a short local summary.
        audit = _command(["journalctl", "--user", "-t", "hero-audit", "-n", "3", "--no-pager", "-o", "json"])
        for line in audit.splitlines():
            try:
                event = json.loads(line)
                message = json.loads(event.get("MESSAGE", "{}"))
                tool = str(message.get("tool", ""))[:48]
                tier = str(message.get("tier", ""))[:16]
                decision = str(message.get("decision", ""))[:32]
                if tool:
                    snapshot["audit"].append({"tool": tool, "tier": tier, "decision": decision})
            except (ValueError, TypeError):
                continue

        try:
            self.signals.finished.emit(snapshot)
        except RuntimeError:
            # The overlay may close while a background probe is still running.
            pass


class HeroBackend(QObject):
    changed = Signal()
    messageAdded = Signal(str, str, str, str, str, bool)
    requestFinished = Signal()
    voiceTranscribed = Signal(str)
    voiceAnswer = Signal(str)
    voiceIgnored = Signal(str)
    voiceError = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        screen = QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry() if screen else None
        self.windowHeight = max(1, geometry.height() - 32) if geometry else 928
        self.windowX = geometry.x() + geometry.width() - 536 if geometry else 0
        self.windowY = geometry.y() + 16 if geometry else 16
        self._values = dict(DEFAULTS)
        self._english = QLocale.system().language() == QLocale.Language.English
        self._language = "en-US" if self._english else "pt-BR"
        self._last_cpu: tuple[int, int] | None = None
        self._last_network: tuple[int, int] | None = None
        self._last_sample = 0.0
        self._busy = False
        self._ptt_starting = False
        self._ptt_recording = False
        self._ptt_stop_requested = False
        self._pending_id = ""
        self._request_started = 0.0
        self._closed = False
        self._pool = QThreadPool.globalInstance()
        self._bus = QDBusConnection.sessionBus()
        self._hero = QDBusInterface(BUS_NAME, OBJECT_PATH, INTERFACE, self._bus, self)
        self._bus.connect(BUS_NAME, OBJECT_PATH, INTERFACE, "VoiceTranscribed", "s", self, SLOT("_on_voice_transcribed(QString)"))
        self._bus.connect(BUS_NAME, OBJECT_PATH, INTERFACE, "VoiceAnswer", "s", self, SLOT("_on_voice_answer(QString)"))
        self._bus.connect(BUS_NAME, OBJECT_PATH, INTERFACE, "VoiceIgnored", "s", self, SLOT("_on_voice_ignored(QString)"))
        self._bus.connect(BUS_NAME, OBJECT_PATH, INTERFACE, "VoiceFailed", "s", self, SLOT("_on_voice_failed(QString)"))
        self._notifications: QDBusInterface | None = None
        self._notification_ids: dict[int, str] = {}
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(2000)
        self._refresh_timer.timeout.connect(self.refresh)
        self.refresh()
        self._refresh_timer.start()

    @Property(int, constant=True)
    def overlayHeight(self) -> int:
        return self.windowHeight

    @Property(int, constant=True)
    def overlayX(self) -> int:
        return self.windowX

    @Property(int, constant=True)
    def overlayY(self) -> int:
        return self.windowY

    @Property(str, notify=changed)
    def heroState(self) -> str:
        runtime = os.environ.get("XDG_RUNTIME_DIR", "")
        path = Path(runtime) / "forjaos" / "herod.sock" if runtime else None
        if not path:
            return "desligado"
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(0.15)
                connection.connect(str(path))
                data = connection.recv(256).decode("utf-8", errors="replace").splitlines()[0]
            state = str(json.loads(data).get("state", "indisponível"))
            if self._english:
                return {
                    "desligado": "off", "ocioso": "idle", "escutando": "listening",
                    "gravando": "recording", "transcrevendo": "transcribing",
                    "pensando": "thinking", "falando": "speaking", "erro": "error",
                }.get(state, "unavailable")
            return state
        except (OSError, ValueError, IndexError):
            return "desligado"

    @Property(str, notify=changed)
    def wifi(self) -> str:
        return self._values["wifi"]

    @Property(str, notify=changed)
    def bluetooth(self) -> str:
        return self._values["bluetooth"]

    @Property(str, notify=changed)
    def vpn(self) -> str:
        return self._values["vpn"]

    @Property(str, notify=changed)
    def vpnPrompt(self) -> str:
        name = self._values.get("vpnName", "")
        return f"Desligue VPN {name}" if name else ""

    @Property(str, notify=changed)
    def wifiPrompt(self) -> str:
        value = self._values["wifi"]
        if value in {"indisponível", "unavailable"}:
            return ""
        return "Ative o Wi-Fi" if value.startswith(("desligado", "off")) else "Desative o Wi-Fi"

    @Property(str, notify=changed)
    def bluetoothPrompt(self) -> str:
        value = self._values["bluetooth"]
        if value in {"indisponível", "unavailable"}:
            return ""
        return "Ative o Bluetooth" if value.startswith(("desligado", "off")) else "Desative o Bluetooth"

    @Property(str, notify=changed)
    def gameModePrompt(self) -> str:
        value = self._values["gameMode"]
        if value in {"indisponível", "unavailable"}:
            return ""
        return "Desative o Modo Jogo" if value in {"ativo", "on"} else "Ative o Modo Jogo"

    @Property(str, notify=changed)
    def gameMode(self) -> str:
        return self._values["gameMode"]

    @Property(str, notify=changed)
    def firewall(self) -> str:
        return self._values["firewall"]

    @Property("QVariantList", notify=changed)
    def securityServices(self) -> list:
        return self._values["securityServices"]

    @Property(str, notify=changed)
    def dnd(self) -> str:
        return self._values["dnd"]

    @Property(str, notify=changed)
    def cpu(self) -> str:
        return self._values["cpu"]

    @Property(str, notify=changed)
    def ram(self) -> str:
        return self._values["ram"]

    @Property(int, notify=changed)
    def ramPercent(self) -> int:
        return self._values["ramPercent"]

    @Property(str, notify=changed)
    def gpu(self) -> str:
        return self._values["gpu"]

    @Property(str, notify=changed)
    def vram(self) -> str:
        return self._values["vram"]

    @Property(int, notify=changed)
    def vramPercent(self) -> int:
        return self._values["vramPercent"]

    @Property("QVariantList", notify=changed)
    def containers(self) -> list:
        return self._values["containers"]

    @Property("QVariantList", notify=changed)
    def models(self) -> list:
        return self._values["models"]

    @Property("QVariantList", notify=changed)
    def audit(self) -> list:
        return self._values["audit"]

    @Property(str, notify=changed)
    def rxRate(self) -> str:
        return self._values["rxRate"]

    @Property(str, notify=changed)
    def txRate(self) -> str:
        return self._values["txRate"]

    @Property(str, notify=changed)
    def latency(self) -> str:
        return self._values["latency"]

    @Property(str, notify=changed)
    def lan(self) -> str:
        return self._values["lan"]

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=changed)
    def microphoneEnabled(self) -> bool:
        return self._hero.isValid() and bool(self._hero.property("MicrophoneEnabled"))

    @Slot()
    def toggleMicrophone(self) -> None:
        if not self._hero.isValid():
            return
        properties = QDBusInterface(BUS_NAME, OBJECT_PATH, "org.freedesktop.DBus.Properties", self._bus, self)
        call = properties.asyncCallWithArgumentList(
            "Set", [INTERFACE, "MicrophoneEnabled", QDBusVariant(not self.microphoneEnabled)]
        )
        watcher = QDBusPendingCallWatcher(call, self)
        watcher.finished.connect(lambda finished: (self.changed.emit(), finished.deleteLater()))

    @Slot()
    def startPushToTalk(self) -> None:
        if self._busy or self._ptt_starting or self._ptt_recording:
            return
        state = self.heroState
        if state not in {"ocioso", "idle", "falando", "speaking"}:
            self.voiceIgnored.emit(state)
            return
        if not self.microphoneEnabled:
            return
        self._ptt_starting = True
        self._ptt_stop_requested = False
        watcher = QDBusPendingCallWatcher(self._hero.asyncCall("StartPushToTalk"), self)
        watcher.finished.connect(self._push_to_talk_started)

    def _push_to_talk_started(self, watcher: QDBusPendingCallWatcher) -> None:
        self._ptt_starting = False
        try:
            reply = json.loads(str(watcher.reply().arguments()[0])) if not watcher.isError() else {}
        except (ValueError, TypeError, IndexError):
            reply = {}
        watcher.deleteLater()
        if reply.get("status") != "recording":
            self._ptt_stop_requested = False
            if reply.get("status") != "busy":
                self.voiceError.emit(QCoreApplication.translate("main", "Não foi possível iniciar a gravação local."))
            return
        self._ptt_recording = True
        if self._ptt_stop_requested:
            self.stopPushToTalk()

    @Slot()
    def stopPushToTalk(self) -> None:
        if self._ptt_starting:
            self._ptt_stop_requested = True
            return
        if not self._ptt_recording:
            return
        self._ptt_recording = False
        self._ptt_stop_requested = False
        watcher = QDBusPendingCallWatcher(self._hero.asyncCall("StopPushToTalk"), self)
        watcher.finished.connect(self._push_to_talk_stopped)

    def _push_to_talk_stopped(self, watcher: QDBusPendingCallWatcher) -> None:
        try:
            reply = json.loads(str(watcher.reply().arguments()[0])) if not watcher.isError() else {}
        except (ValueError, TypeError, IndexError):
            reply = {}
        watcher.deleteLater()
        if reply.get("status") != "transcribing":
            self.voiceError.emit(QCoreApplication.translate("main", "Não foi possível transcrever a gravação local."))

    @Slot(str)
    def _on_voice_transcribed(self, text: str) -> None:
        self.voiceTranscribed.emit(text)

    @Slot(str)
    def _on_voice_answer(self, answer: str) -> None:
        self.voiceAnswer.emit(answer)

    @Slot(str)
    def _on_voice_ignored(self, state: str) -> None:
        self.voiceIgnored.emit(state)

    @Slot(str)
    def _on_voice_failed(self, _reason: str) -> None:
        self.voiceError.emit(QCoreApplication.translate("main", "Não foi possível concluir o turno de voz local."))

    @Property(str, notify=changed)
    def pendingId(self) -> str:
        return self._pending_id

    def refresh(self) -> None:
        if self._closed or getattr(self, "_refreshing", False):
            return
        worker = SnapshotWorker()
        worker.signals.finished.connect(self._apply_snapshot)
        worker.signals.finished.connect(self._snapshot_finished)
        self._snapshot_worker = worker
        self._refreshing = True
        self._pool.start(worker)

    @Slot(dict)
    def _snapshot_finished(self, _: dict) -> None:
        self._refreshing = False
        self._snapshot_worker = None

    @Slot(dict)
    def _apply_snapshot(self, snapshot: dict) -> None:
        now = __import__("time").monotonic()
        elapsed = max(0.1, now - self._last_sample) if self._last_sample else 2.0
        counters = snapshot.pop("cpuCounters", (0, 0))
        previous = self._last_cpu
        if previous and counters[0] > previous[0]:
            total = counters[0] - previous[0]
            idle = counters[1] - previous[1]
            snapshot["cpu"] = f"{max(0, min(100, round((total - idle) * 100 / total)))}%"
        self._last_cpu = counters

        network = snapshot.pop("networkCounters", (0, 0))
        previous_network = self._last_network
        if previous_network:
            received = max(0, network[0] - previous_network[0]) / elapsed / 125_000
            sent = max(0, network[1] - previous_network[1]) / elapsed / 125_000
            snapshot["rxRate"] = f"↓ {received:.0f} Mb/s"
            snapshot["txRate"] = f"↑ {sent:.0f} Mb/s"
        self._last_network = network
        self._last_sample = now
        self._values.update(snapshot)
        if self._english:
            translations = {
                "wifi": {"indisponível": "unavailable", "desligado": "off", "ligado · sem conexão": "on · not connected"},
                "bluetooth": {"indisponível": "unavailable", "desligado": "off", "ligado": "on"},
                "vpn": {"desconectada": "disconnected"},
                "gameMode": {"ativo": "on", "desligado": "off", "indisponível": "unavailable"},
                "firewall": {"ativo": "on", "inativo": "off", "indisponível": "unavailable"},
                "dnd": {"ativo": "on", "desligado": "off", "indisponível": "unavailable"},
                "gpu": {"indisponível": "unavailable"},
                "vram": {"indisponível": "unavailable"},
                "latency": {"sem teste ativo": "no active test"},
                "lan": {"varredura desativada": "scan disabled"},
            }
            for key, mapping in translations.items():
                self._values[key] = mapping.get(self._values[key], self._values[key])
            service_labels = {"ativo": "on", "inativo": "off", "indisponível": "unavailable"}
            self._values["securityServices"] = [
                {"name": item["name"], "status": service_labels.get(item["status"], item["status"])}
                for item in self._values["securityServices"]
            ]
        self.changed.emit()

    @Slot(str)
    def sendText(self, text: str) -> None:
        query = text.strip()
        if not query or self._busy or len(query) > 4000:
            return
        if not self._hero.isValid() or not self._bus.isConnected():
            self.messageAdded.emit(query, QCoreApplication.translate("main", "O serviço HERO não está disponível nesta sessão."), "", "", "erro", False)
            return
        self._busy = True
        self._request_started = time.monotonic()
        self._pending_id = ""
        self.changed.emit()
        self.messageAdded.emit(query, "", "", "", "pensando", True)
        call = self._hero.asyncCallWithArgumentList(
            "AskText",
            [query, str(Path.home()), json.dumps({"language": self._language})],
        )
        watcher = QDBusPendingCallWatcher(call, self)
        watcher.finished.connect(lambda finished: self._handle_reply(finished, query, False))

    def _handle_reply(self, watcher: QDBusPendingCallWatcher, query: str, confirmed: bool) -> None:
        failed = watcher.isError()
        arguments = watcher.reply().arguments() if not failed else []
        watcher.deleteLater()
        if failed:
            result = {"status": "error", "answer": QCoreApplication.translate("main", "Não foi possível conversar com o serviço HERO.")}
        else:
            try:
                result = json.loads(str(arguments[0]))
            except (ValueError, TypeError, IndexError):
                result = {"status": "error", "answer": QCoreApplication.translate("main", "O serviço HERO retornou uma resposta inválida.")}
        status = str(result.get("status", "error"))
        tool = str(result.get("tool", ""))[:80]
        tier = str(result.get("tier", ""))[:16]
        answer = str(result.get("answer", QCoreApplication.translate("main", "Não houve resposta.")))[:4000]
        if tool and status not in {"confirmation_required", "confirmation_unavailable"} and self._request_started:
            answer = f"{answer} · {time.monotonic() - self._request_started:.1f} s"
            self._request_started = 0.0
        self._pending_id = str(result.get("confirmation_id", "")) if status == "confirmation_required" else ""
        if status == "confirmation_required":
            self._request_started = 0.0
        self._busy = False
        self.changed.emit()
        self.messageAdded.emit(query, answer, tool, tier, status, False)
        if self._pending_id:
            self._notify_confirmation(answer, tool, tier)

    @Slot(bool)
    def confirmAction(self, approved: bool) -> None:
        if not self._pending_id or self._busy:
            return
        pending_id = self._pending_id
        self._pending_id = ""
        self._request_started = time.monotonic() if approved else 0.0
        self._close_notifications(pending_id)
        self._busy = True
        self.changed.emit()
        watcher = QDBusPendingCallWatcher(
            self._hero.asyncCallWithArgumentList("ConfirmAction", [pending_id, approved]), self
        )
        watcher.finished.connect(lambda finished: self._handle_reply(finished, "", True))

    def _notify_confirmation(self, answer: str, tool: str, tier: str) -> None:
        if self._notifications is None:
            bus_interface = self._bus.interface()
            if bus_interface is None or not bus_interface.isServiceRegistered(
                "org.freedesktop.Notifications"
            ).value():
                return
            self._notifications = QDBusInterface(
                "org.freedesktop.Notifications",
                "/org/freedesktop/Notifications",
                "org.freedesktop.Notifications",
                self._bus,
                self,
            )
            self._notifications.connect(
                SIGNAL("ActionInvoked(uint,QString)"), self._notification_action
            )
        if not self._notifications.isValid():
            return
        summary = (
            f"{answer[:220]}\nTool: {tool} · tier {tier}"
            if self._english
            else f"{answer[:220]}\nFerramenta: {tool} · tier {tier}"
        )
        watcher = QDBusPendingCallWatcher(
            self._notifications.asyncCallWithArgumentList(
                "Notify",
                [
                    "ForjaOS HERO",
                    0,
                    "dialog-question",
                    "Confirmation required" if self._english else "Confirmação necessária",
                    summary,
                    ["approve", "Confirm" if self._english else "Confirmar", "deny", "Decline" if self._english else "Recusar"],
                    {},
                    120000,
                ],
            ),
            self,
        )

        def remember_id(finished: QDBusPendingCallWatcher) -> None:
            failed = finished.isError()
            arguments = finished.reply().arguments() if not failed else []
            finished.deleteLater()
            if arguments and self._pending_id:
                self._notification_ids[int(arguments[0])] = self._pending_id

        watcher.finished.connect(remember_id)

    @Slot("uint", str)
    def _notification_action(self, notification_id: int, action: str) -> None:
        pending = self._notification_ids.pop(notification_id, "")
        if pending and pending == self._pending_id:
            self.confirmAction(action == "approve")

    def _close_notifications(self, pending_id: str) -> None:
        if self._notifications is None:
            return
        for notification_id, mapped_id in list(self._notification_ids.items()):
            if mapped_id == pending_id:
                self._notifications.asyncCallWithArgumentList("CloseNotification", [notification_id])
                self._notification_ids.pop(notification_id, None)

    @Slot()
    def closeOverlay(self) -> None:
        self._closed = True
        self._refresh_timer.stop()
        if self._pending_id and self._hero.isValid():
            self._close_notifications(self._pending_id)
            self._hero.asyncCallWithArgumentList("ConfirmAction", [self._pending_id, False])
            self._pending_id = ""


def _session_unlocked(bus: QDBusConnection) -> bool:
    saver = QDBusInterface(SCREEN_SAVER, SCREEN_SAVER_PATH, SCREEN_SAVER, bus)
    if not bus.isConnected() or not saver.isValid():
        return False
    reply = saver.call("GetActive")
    return reply.type() != QDBusMessage.MessageType.ErrorMessage and reply.arguments() == [False]


class LockWatcher(QObject):
    def __init__(self, root: QObject) -> None:
        super().__init__()
        self.root = root

    @Slot(bool)
    def active_changed(self, active: bool) -> None:
        if active:
            self.root.close()


def _toggle_existing() -> bool:
    name = "forjaos-hero-overlay"
    client = QLocalSocket()
    client.connectToServer(name)
    if client.waitForConnected(150):
        client.write(b"toggle\n")
        client.waitForBytesWritten(150)
        client.disconnectFromServer()
        return True
    QLocalServer.removeServer(name)
    return False


def main() -> int:
    app = QApplication(sys.argv)
    bus = QDBusConnection.sessionBus()
    if not _session_unlocked(bus):
        return 0
    if _toggle_existing():
        return 0
    app.setApplicationName("ForjaOS HERO")
    root_dir = Path("/usr/share/forjaos/hero-overlay")
    if not root_dir.exists():
        root_dir = Path(__file__).resolve().parent
    translator = QTranslator(app)
    translator.load(QLocale.system(), "hero-overlay", "_", str(root_dir / "i18n"))
    app.installTranslator(translator)
    backend = HeroBackend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("hero", backend)
    engine.load(QUrl.fromLocalFile(str(root_dir / "main.qml")))
    if not engine.rootObjects():
        return 1
    root = engine.rootObjects()[0]
    lock_watcher = LockWatcher(root)
    if not bus.connect(SCREEN_SAVER, SCREEN_SAVER_PATH, SCREEN_SAVER, "ActiveChanged", "b", lock_watcher, SLOT("active_changed(bool)")):
        root.close()
        return 1
    if not _session_unlocked(bus):
        root.close()
        return 0
    server = QLocalServer(app)
    if not server.listen("forjaos-hero-overlay"):
        return 1

    def handle_connection() -> None:
        client = server.nextPendingConnection()
        if client:
            client.readyRead.connect(lambda: root.close())

    server.newConnection.connect(handle_connection)
    root.closing.connect(lambda _: backend.closeOverlay())
    if not _session_unlocked(bus):
        root.close()
        return 0
    root.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
