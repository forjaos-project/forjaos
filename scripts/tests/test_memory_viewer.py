import importlib.util
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "hero-memory/visualizer/index.py"
spec = importlib.util.spec_from_file_location("memory_index", SOURCE)
index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(index)


class MemoryIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "memory.db"
        with closing(sqlite3.connect(self.db)) as db, db:
            db.executescript("""
                CREATE TABLE notes(id TEXT, path TEXT, modified_at INTEGER);
                CREATE VIRTUAL TABLE note_search USING fts5(id UNINDEXED, path UNINDEXED, title, content);
            """)
            for path, title, stamp in [("daily/collectors/git/a.md", "Decisão game-api", 200),
                                       ("notes/b.md", "Outra decisão", 100)]:
                db.execute("INSERT INTO notes VALUES (?, ?, ?)", (path, path, stamp))
                db.execute("INSERT INTO note_search VALUES (?, ?, ?, ?)",
                           (path, path, title, "conteúdo completo além do resumo"))

    def test_timeline_uses_index_and_date_bounds(self):
        rows = index.read_hits(self.db, since=150, until=250)
        self.assertEqual([row["path"] for row in rows], ["daily/collectors/git/a.md"])
        self.assertEqual(rows[0]["node_type"], "commit")
        self.assertEqual(rows[0]["modified"], 200)

    def test_search_uses_fts_accents_and_full_content(self):
        self.assertEqual(len(index.read_hits(self.db, query="decisao")), 2)
        self.assertEqual(len(index.read_hits(self.db, query="além resumo")), 2)
        self.assertEqual(index.read_hits(self.db, query="' OR *"), [])

    def test_missing_index_is_read_only(self):
        missing = self.db.with_name("missing.db")
        self.assertEqual(index.read_hits(missing), [])
        self.assertFalse(missing.exists())

    def test_preview_rejects_traversal_and_symlink_ancestors(self):
        vault = Path(self.temp.name) / "vault"
        vault.mkdir()
        (vault / "note.md").write_text("# Nota", encoding="utf-8")
        self.assertEqual(index.read_preview(vault, "note.md"), "# Nota")
        self.assertEqual(index.read_preview(vault, "../memory.db"), "")
        self.assertEqual(index.read_preview(vault, str(self.db)), "")
        try:
            (vault / "linked").symlink_to(vault, target_is_directory=True)
        except OSError:
            return
        self.assertEqual(index.read_preview(vault, "linked/note.md"), "")


if __name__ == "__main__":
    unittest.main()
