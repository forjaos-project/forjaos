#!/usr/bin/python3
"""Local read-only QML viewer for the ForjaOS Markdown vault."""

import json
from pathlib import Path
import re
import sys

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


HOME = Path.home()
VAULT = HOME / "ForjaOS" / "vault"
SECRET_ASSIGNMENT = re.compile(
    r"(?i)^\s*[A-Z0-9_]*(API[_-]?KEY|ACCESS[_-]?TOKEN|TOKEN|SECRET|PASSWORD|PASSWD|AUTHORIZATION)\s*[:=].*$"
)
BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+=*")
TOKEN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})\b")


def redact(text):
    safe = []
    for line in text.splitlines():
        if SECRET_ASSIGNMENT.search(line):
            safe.append("[SEGREDO REDIGIDO]")
        else:
            safe.append(TOKEN.sub("[REDACTED]", BEARER.sub(r"\1[REDACTED]", line)))
    return "\n".join(safe)


class Vault(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._notes = self._load_notes()
        self._graph = self._load_graph()

    @staticmethod
    def _load_notes():
        notes = []
        if not VAULT.exists():
            return notes
        for path in VAULT.rglob("*.md"):
            try:
                if any(part.startswith(".") for part in path.relative_to(VAULT).parts):
                    continue
                if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
                    continue
                content = redact(path.read_text(encoding="utf-8"))
                title = next((line[2:].strip() for line in content.splitlines()
                              if line.startswith("# ") and line[2:].strip()), path.stem)
                notes.append({"title": title, "path": path.relative_to(VAULT).as_posix(),
                              "excerpt": " ".join(content.split())[:240],
                              "modified": path.stat().st_mtime})
            except (OSError, UnicodeError, ValueError):
                continue
        return sorted(notes, key=lambda item: item["modified"], reverse=True)

    @staticmethod
    def _load_graph():
        path = VAULT / "graph" / "graph.json"
        try:
            graph = json.loads(path.read_text(encoding="utf-8"))
            nodes, links = graph.get("nodes", []), graph.get("links", [])
            if not isinstance(nodes, list) or not isinstance(links, list):
                return {"nodes": [], "links": []}
            return {"nodes": nodes[:10000], "links": links[:30000]}
        except (OSError, UnicodeError, ValueError):
            return {"nodes": [], "links": []}

    @Property("QVariantList", notify=changed)
    def timeline(self):
        return self._notes[:500]

    @Property("QVariantList", notify=changed)
    def nodes(self):
        return self._graph["nodes"]

    @Property("QVariantList", notify=changed)
    def links(self):
        return self._graph["links"]

    @Slot(str, result="QVariantList")
    def search(self, query):
        query = query.strip().casefold()
        if not query:
            return []
        terms = query.split()
        matches = []
        for note in self._notes:
            haystack = (note["title"] + " " + note["excerpt"] + " " + note["path"]).casefold()
            if not all(term in haystack for term in terms):
                try:
                    full_path = VAULT / note["path"]
                    content = redact(full_path.read_text(encoding="utf-8")).casefold()
                    if not all(term in content or term in haystack for term in terms):
                        continue
                except (OSError, UnicodeError):
                    continue
            matches.append(note)
            if len(matches) == 100:
                break
        return matches


def main():
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("vault", Vault())
    qml_path = Path(__file__).with_name("viewer.qml")
    engine.load(str(qml_path))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
