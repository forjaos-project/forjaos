#!/usr/bin/python3
"""Local read-only QML viewer for the ForjaOS Markdown vault."""

import json
import os
from datetime import datetime, timedelta
import sqlite3
from index import read_hits, read_preview, safe_path
from pathlib import Path
import re
import shutil
import subprocess
import sys

from PySide6.QtCore import QObject, Property, Signal, Slot, QThread, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QDesktopServices
from PySide6.QtQml import QQmlApplicationEngine


HOME = Path.home()
VAULT = HOME / "ForjaOS" / "vault"
SECRET_ASSIGNMENT = re.compile(
    r"(?i)^\s*[A-Z0-9_]*(API[_-]?KEY|ACCESS[_-]?TOKEN|TOKEN|SECRET|PASSWORD|PASSWD|AUTHORIZATION)\s*[:=].*$"
)
BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+=*")
TOKEN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})\b")


def redact(text):
    safe = []
    for line in text.splitlines():
        if SECRET_ASSIGNMENT.search(line):
            safe.append("[SEGREDO REDIGIDO]")
        else:
            safe.append(TOKEN.sub("[REDACTED]", BEARER.sub(r"\1[REDACTED]", line)))
    return "\n".join(safe)


class Loader(QThread):
    ready = Signal(object)

    def __init__(self, operation, parent):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            self.ready.emit((self.operation(), ""))
        except (OSError, ValueError, sqlite3.Error, subprocess.SubprocessError):
            self.ready.emit((None, "Não foi possível ler a memória local. Verifique memd e o índice."))


class Vault(QObject):
    changed = Signal()
    graphChanged = Signal()

    def __init__(self):
        super().__init__()
        self._collectors = []
        self._notes = []
        self._graph = {"nodes": [], "links": []}
        self._collector_status = "Carregando memória local…"
        self._day = datetime.now().strftime("%Y-%m-%d")
        self._preview = ""
        self._workers = []
        self._database = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "hero/memory.db"
        self._refreshing = False

    def _start(self, operation, callback):
        worker = Loader(operation, self)
        self._workers.append(worker)
        worker.ready.connect(callback)
        worker.finished.connect(lambda: self._workers.remove(worker))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def close(self):
        for worker in list(self._workers):
            worker.wait()

    @Slot()
    def refresh(self):
        if self._refreshing:
            return
        self._refreshing = True
        def loaded(reply):
            result, error = reply
            self._refreshing = False
            if result is not None:
                self._collectors, graph = result
                if graph != self._graph:
                    self._graph = graph
                    self.graphChanged.emit()
            self._collector_status = error or "Índice local · leitura somente · FTS5"
            self.changed.emit()
            self.selectDay(self._day)
        self._start(lambda: (self._load_collectors(), self._load_graph()), loaded)

    @Property(str, notify=changed)
    def day(self):
        return self._day

    @Property(str, notify=changed)
    def preview(self):
        return self._preview

    @Slot(str)
    def selectDay(self, day):
        try:
            start = datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            self._collector_status = "Data inválida. Use AAAA-MM-DD."
            self.changed.emit()
            return
        self._day = day
        def loaded(reply):
            rows, error = reply
            if day != self._day:
                return
            self._notes = rows or []
            self._preview = redact(read_preview(VAULT, f"daily/{day}.md"))
            if error:
                self._collector_status = error
            self.changed.emit()
        self._start(lambda: read_hits(self._database, since=int(start.timestamp()),
                    until=int((start + timedelta(days=1)).timestamp())), loaded)

    @Slot(str, result=str)
    def previewNote(self, relative):
        return redact(read_preview(VAULT, relative))

    @Slot(str, result="QVariantList")
    def related(self, entity):
        return [link for link in self._graph["links"]
                if link.get("source") == entity or link.get("target") == entity][:100]

    @Slot(str, result=bool)
    def openNote(self, relative):
        path = safe_path(VAULT, relative)
        return bool(path and path.is_file() and path.suffix == ".md"
                    and QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))))

    @staticmethod
    def _load_collectors():
        binary = shutil.which("forja")
        if not binary:
            return []
        try:
            result = subprocess.run(
                [binary, "memory", "collectors", "status", "--json"],
                check=True, capture_output=True, text=True, timeout=10,
            )
            collectors = json.loads(result.stdout)
            if not isinstance(collectors, list):
                return []
            return [item for item in collectors if isinstance(item, dict)]
        except (OSError, subprocess.SubprocessError, ValueError):
            return []

    @staticmethod
    def _load_graph():
        path = VAULT / "graph" / "graph.json"
        try:
            if path.is_symlink() or path.stat().st_size > 32 * 1024 * 1024:
                return {"nodes": [], "links": []}
            graph = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(graph, dict):
                return {"nodes": [], "links": []}
            nodes, links = graph.get("nodes", []), graph.get("links", [])
            if not isinstance(nodes, list) or not isinstance(links, list):
                return {"nodes": [], "links": []}
            return {"nodes": [node for node in nodes[:10000] if isinstance(node, dict) and isinstance(node.get("id"), str)],
                    "links": [link for link in links[:30000] if isinstance(link, dict)
                              and isinstance(link.get("source"), str) and isinstance(link.get("target"), str)]}
        except (OSError, UnicodeError, ValueError):
            return {"nodes": [], "links": []}

    @Property("QVariantList", notify=changed)
    def timeline(self):
        return self._notes[:500]

    @Property("QVariantList", notify=graphChanged)
    def nodes(self):
        return self._graph["nodes"]

    @Property("QVariantList", notify=graphChanged)
    def links(self):
        return self._graph["links"]

    @Property("QVariantList", notify=changed)
    def collectors(self):
        return self._collectors

    @Property(str, notify=changed)
    def collectorStatus(self):
        return self._collector_status

    @Slot(str, bool, result=bool)
    def setCollector(self, source, enabled):
        if source not in {"shell", "git", "hero", "windows", "code", "notes"}:
            self._collector_status = "Origem de coletor inválida."
            self.changed.emit()
            return False
        binary = shutil.which("forja")
        if not binary:
            self._collector_status = "Comando forja indisponível nesta sessão."
            self.changed.emit()
            return False
        def update():
            subprocess.run(
                [binary, "memory", "collectors", "enable" if enabled else "disable", source, "--json"],
                check=True, capture_output=True, text=True, timeout=15,
            )
            return self._load_collectors()
        def loaded(reply):
            collectors, error = reply
            if collectors is not None:
                self._collectors = collectors
                self.refresh()
            self._collector_status = error or f"Coletor {source}: {'ativo' if enabled else 'inativo'}."
            self.changed.emit()
        self._start(update, loaded)
        return True

    @Slot(str, result="QVariantList")
    def search(self, query):
        try:
            return read_hits(self._database, query=query, limit=100)
        except (OSError, sqlite3.Error):
            self._collector_status = "Busca indisponível. Reconstrua o índice com forja memory rebuild."
            self.changed.emit()
            return []



def main():
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    vault = Vault()
    engine.rootContext().setContextProperty("vault", vault)
    qml_path = Path(__file__).with_name("viewer.qml")
    engine.load(str(qml_path))
    if not engine.rootObjects():
        return 1
    QTimer.singleShot(0, vault.refresh)
    refresh_timer = QTimer()
    refresh_timer.setInterval(30000)
    refresh_timer.timeout.connect(vault.refresh)
    refresh_timer.start()
    app.aboutToQuit.connect(vault.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
