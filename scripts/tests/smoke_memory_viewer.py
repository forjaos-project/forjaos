"""Linux offscreen software smoke; synthetic data, never hardware acceptance."""

import json
import os
from pathlib import Path
import resource
import sqlite3
import sys
import tempfile
import time

from PySide6.QtCore import QObject, QTimer, QCoreApplication, QEvent
from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hero-memory/visualizer"))
import viewer  # noqa: E402


def main():
    with tempfile.TemporaryDirectory(prefix="forja-viewer-") as temp:
        home = Path(temp)
        vault_path = home / "ForjaOS/vault"
        (vault_path / "graph").mkdir(parents=True)
        (vault_path / "daily").mkdir()
        (vault_path / "daily/demo.md").write_text("# Decisão game-api\nMemória local.", encoding="utf-8")
        graph = {"nodes": [{"id": f"node-{i}", "label": f"Entidade {i}",
                            "source_file": "daily/demo.md", "node_type": "note",
                            "modified_at": int(time.time())} for i in range(10000)],
                 "links": [{"source": f"node-{i}", "target": f"node-{(i + j) % 10000}"}
                           for i in range(10000) for j in (1, 7, 31)]}
        (vault_path / "graph/graph.json").write_text(json.dumps(graph), encoding="utf-8")
        del graph
        database = home / "memory.db"
        db = sqlite3.connect(database)
        db.executescript("CREATE TABLE notes(id TEXT, path TEXT, modified_at INTEGER);"
                         "CREATE VIRTUAL TABLE note_search USING fts5(id UNINDEXED, path UNINDEXED, title, content);")
        db.execute("INSERT INTO notes VALUES ('demo','daily/demo.md',?)", (int(time.time()),))
        db.execute("INSERT INTO note_search VALUES ('demo','daily/demo.md','Decisão game-api','Memória local')")
        db.commit()
        db.close()
        viewer.VAULT = vault_path
        started = time.monotonic()
        app = QGuiApplication([])
        QFontDatabase.addApplicationFont(str(ROOT / "brand/fonts/PlusJakartaSans-VF.ttf"))
        engine = QQmlApplicationEngine()
        vault = viewer.Vault()
        vault._database = database
        engine.rootContext().setContextProperty("vault", vault)
        engine.load(str(ROOT / "hero-memory/visualizer/viewer.qml"))
        assert engine.rootObjects(), "QML failed to load"
        root = engine.rootObjects()[0]
        assert isinstance(root, QQuickWindow)
        frame = []
        root.frameSwapped.connect(lambda: frame.append(time.monotonic() - started) if not frame else None)
        root.setProperty("viewIndex", 1)
        canvas = root.findChild(QObject, "graphCanvas")
        QTimer.singleShot(0, vault.refresh)
        result = {}

        def probe():
            positions = canvas.property("layoutPositions").toVariant()
            elapsed = time.monotonic() - started
            if len(positions) == 10000 and vault.timeline:
                assert vault.search("decisao")[0]["path"] == "daily/demo.md"
                assert vault.previewNote("../memory.db") == ""
                result.update(first_frame_ms=round(frame[0] * 1000) if frame else None,
                              layout_ms=round(elapsed * 1000), nodes=len(positions),
                              max_rss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1))
                destination = os.environ.get("FORJA_VIEWER_CAPTURE")
                if destination:
                    assert root.grabWindow().save(destination)
                timer.stop()
                app.quit()
            elif elapsed > 40:
                result["error"] = "layout timed out"
                timer.stop()
                app.quit()

        timer = QTimer()
        timer.setInterval(200)
        timer.timeout.connect(probe)
        timer.start()
        app.aboutToQuit.connect(vault.close)
        app.exec()
        engine.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        print(json.dumps(result))
        assert result.get("nodes") == 10000, result


if __name__ == "__main__":
    main()
