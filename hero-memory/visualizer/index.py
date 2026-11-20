"""Read-only queries against memd's derived index; never scans the vault."""

from pathlib import Path, PurePosixPath
import re
import sqlite3


def node_type(path):
    for source, kind in (("shell", "command"), ("git", "commit"),
                         ("hero", "conversation"), ("windows", "window")):
        if path.startswith(f"daily/collectors/{source}/"):
            return kind
    return "repository" if path.startswith("projects/") else "note"


def read_hits(database, query=None, since=0, until=253402300799, limit=500):
    if not database.is_file():
        return []
    match = ""
    parameters = [since, until]
    if query is not None:
        terms = re.findall(r"[^\W_]+", query, re.UNICODE)
        if not terms:
            return []
        match = " AND note_search MATCH ?"
        parameters.append(" AND ".join(f'"{term}"' for term in terms))
    parameters.append(max(1, min(limit, 500)))
    db = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.2)
    try:
        rows = db.execute(
            "SELECT n.path, s.title, substr(s.content, 1, 240), n.modified_at "
            "FROM notes n JOIN note_search s ON s.id = n.id "
            "WHERE n.modified_at >= ? AND n.modified_at < ?" + match +
            " ORDER BY n.modified_at DESC, n.id LIMIT ?", parameters,
        ).fetchall()
    finally:
        db.close()
    return [{"path": path, "title": title, "excerpt": excerpt,
             "modified": modified, "node_type": node_type(path)}
            for path, title, excerpt, modified in rows]


def safe_path(vault, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative or ":" in relative:
        return None
    current = vault
    for part in path.parts:
        if part.startswith("."):
            return None
        current = current / part
        if current.is_symlink():
            return None
    try:
        current.resolve().relative_to(vault.resolve())
    except ValueError:
        return None
    return current


def read_preview(vault, relative):
    path = safe_path(vault, relative)
    try:
        if path is None or path.suffix != ".md" or path.stat().st_size > 2 * 1024 * 1024:
            return ""
        return path.read_text(encoding="utf-8")[:65536]
    except (OSError, UnicodeError):
        return ""
