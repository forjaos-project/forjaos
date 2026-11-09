#!/usr/bin/env python3
"""roadmap.py — fonte única: docs/roadmap/roadmap.json → docs/STATUS.md + docs/roadmap/index.html

Uso:
  python3 scripts/roadmap.py available                      # o que dá para pegar agora (lê branches remotas)
  python3 scripts/roadmap.py claim ID --agent claude|codex|human [--scope pasta/]
  python3 scripts/roadmap.py done ID --pr N --summary "texto" [--date AAAA-MM-DD]
  python3 scripts/roadmap.py validate [--branch [--base origin/main]]
  python3 scripts/roadmap.py build [--check]                # só na main (workflow roadmap-sync)

Só stdlib. Os arquivos gerados nunca são editados à mão nem commitados em PR (METHODOLOGY §6).
Schema do roadmap.json:
  project, updated_at? (legado; a data exibida é derivada),
  phases[]: id, name, weeks, dod, status (todo|doing|done|blocked)
  items[]:  id, fr[], phase, title, status, scope?, depends_on[]?, agent?, claimed_at?,
            pr?, merged_at?, summary?, notes?
  deliveries[]: date, pr (int|null), items[], summary   (legado, só leitura)

Trabalho em paralelo: cada PR altera apenas o PRÓPRIO item (claim/done). Nada de campos
compartilhados (updated_at, deliveries) nem arquivos gerados — assim PRs paralelos não conflitam.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html as _html
import json
import subprocess
import sys
from pathlib import Path

STATUSES = ("todo", "doing", "done", "blocked")
AGENTS = ("claude", "codex", "human")
GENERATED = ("docs/STATUS.md", "docs/roadmap/index.html")
STATUS_LABEL = {"todo": "a fazer", "doing": "em andamento", "done": "feito", "blocked": "bloqueado"}
GEN_MD = "<!-- GERADO por scripts/roadmap.py a partir de docs/roadmap/roadmap.json — NÃO EDITAR À MÃO -->"
GEN_HTML = "<!-- GERADO por scripts/roadmap.py a partir de docs/roadmap/roadmap.json — NÃO EDITAR À MÃO -->"


# ---------------------------------------------------------------- io
def paths(root: Path) -> dict[str, Path]:
    return {
        "json": root / "docs" / "roadmap" / "roadmap.json",
        "status": root / "docs" / "STATUS.md",
        "html": root / "docs" / "roadmap" / "index.html",
        "template": root / "scripts" / "roadmap_template.html",
    }


def load(root: Path) -> dict:
    return json.loads(paths(root)["json"].read_text(encoding="utf-8"))


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8")


def load_base(root: Path, ref: str = "origin/main") -> dict | None:
    """roadmap.json como está em `ref` (a fonte de verdade), não na cópia de trabalho."""
    try:
        r = _git(root, "show", f"{ref}:docs/roadmap/roadmap.json")
        return json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, ValueError):
        return None


def claim_guards(root: Path, item_id: str, base: str = "origin/main") -> list[str]:
    """Pré-condições do claim que dependem do git: branch própria, baseada em `base`, item ainda 'todo' nele."""
    try:
        if _git(root, "rev-parse", "--verify", "--quiet", base).returncode:
            return [f"não encontrei {base}; rode `git fetch origin`"]
        errors = []
        cur = _git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        if cur in ("main", "HEAD"):
            errors.append("crie a branch do item antes: git switch -c <tipo>/<ID>-<slug> origin/main (nunca claim na main)")
        if _git(root, "merge-base", "--is-ancestor", base, "HEAD").returncode:
            errors.append(f"a branch não contém {base} (base desatualizada); recrie a partir de {base} ou faça rebase")
        data = load_base(root, base)
        it = _by_id(data).get(item_id) if data else None
        if it and it["status"] != "todo":
            errors.append(f"{item_id} está '{it['status']}' em {base}; só itens 'todo' podem ser pegos")
        return errors
    except OSError:
        return []


def save(root: Path, data: dict) -> None:
    paths(root)["json"].write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- validate
def validate(data: dict) -> list[str]:
    errors: list[str] = []
    for key in ("project", "phases", "items", "deliveries"):
        if key not in data:
            errors.append(f"campo obrigatório ausente: {key}")
    if errors:
        return errors
    if "updated_at" in data:
        try:
            _dt.date.fromisoformat(data["updated_at"])
        except ValueError:
            errors.append(f"updated_at inválido: {data['updated_at']!r}")
    phase_ids: set[str] = set()
    for p in data["phases"]:
        for key in ("id", "name", "weeks", "dod", "status"):
            if key not in p:
                errors.append(f"fase sem campo {key}: {p}")
        if p.get("id") in phase_ids:
            errors.append(f"id de fase duplicado: {p.get('id')}")
        phase_ids.add(p.get("id"))
        if p.get("status") not in STATUSES:
            errors.append(f"fase {p.get('id')}: status inválido {p.get('status')!r}")
    item_ids: set[str] = set()
    for it in data["items"]:
        for key in ("id", "fr", "phase", "title", "status"):
            if key not in it:
                errors.append(f"item sem campo {key}: {it}")
        if it.get("id") in item_ids:
            errors.append(f"id de item duplicado: {it.get('id')}")
        item_ids.add(it.get("id"))
        if it.get("status") not in STATUSES:
            errors.append(f"item {it.get('id')}: status inválido {it.get('status')!r}")
        if it.get("phase") not in phase_ids:
            errors.append(f"item {it.get('id')}: phase desconhecida {it.get('phase')!r}")
        if not isinstance(it.get("fr"), list):
            errors.append(f"item {it.get('id')}: fr deve ser lista")
        if "agent" in it and it["agent"] not in AGENTS:
            errors.append(f"item {it.get('id')}: agent inválido {it['agent']!r} (use {', '.join(AGENTS)})")
        if it.get("status") == "doing":
            if not it.get("agent"):
                errors.append(f"item {it.get('id')}: doing sem agent")
            if not it.get("scope"):
                errors.append(f"item {it.get('id')}: doing sem scope")
        if not isinstance(it.get("depends_on", []), list):
            errors.append(f"item {it.get('id')}: depends_on deve ser lista")
    for it in data["items"]:
        for dep in it.get("depends_on", []) or []:
            if dep not in item_ids:
                errors.append(f"item {it.get('id')}: depends_on {dep} não existe")
            elif dep == it.get("id"):
                errors.append(f"item {it.get('id')}: depende de si mesmo")
    for d in data["deliveries"]:
        for key in ("date", "items", "summary"):
            if key not in d:
                errors.append(f"delivery sem campo {key}: {d}")
        for ref in d.get("items", []):
            if ref not in item_ids:
                errors.append(f"delivery {d.get('date')}: item {ref} não existe")
    return errors


# ---------------------------------------------------------------- queries
def current_phase(data: dict) -> dict | None:
    for status in ("doing", "todo"):
        for p in data["phases"]:
            if p["status"] == status:
                return p
    return data["phases"][-1] if data["phases"] else None


def next_task(data: dict) -> dict | None:
    phase = current_phase(data)
    if not phase:
        return None
    for status in ("todo", "blocked"):
        for it in data["items"]:
            if it["phase"] == phase["id"] and it["status"] == status:
                return it
    # fase atual esgotada: primeiro todo de qualquer fase posterior
    for it in data["items"]:
        if it["status"] == "todo":
            return it
    return None


def counts(data: dict) -> dict[str, int]:
    c = {s: 0 for s in STATUSES}
    for it in data["items"]:
        c[it["status"]] += 1
    c["total"] = len(data["items"])
    c["pct_done"] = round(100 * c["done"] / c["total"]) if c["total"] else 0
    return c


def last_updated(data: dict) -> str:
    dates = [data.get("updated_at") or ""]
    dates += [it.get(k) or "" for it in data["items"] for k in ("merged_at", "claimed_at")]
    dates += [d.get("date") or "" for d in data["deliveries"]]
    return max(dates) or "—"


def scopes_overlap(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    if a == "." or b == ".":
        return True
    a, b = a.rstrip("/") + "/", b.rstrip("/") + "/"
    return a.startswith(b) or b.startswith(a)


def _by_id(data: dict) -> dict[str, dict]:
    return {it["id"]: it for it in data["items"]}


def unmet_deps(data: dict, it: dict) -> list[str]:
    known = _by_id(data)
    return [d for d in it.get("depends_on", []) or [] if known.get(d, {}).get("status") != "done"]


def _doing(data: dict, extra_doing=()) -> list[dict]:
    out = {it["id"]: it for it in data["items"] if it["status"] == "doing"}
    for it in extra_doing:
        out.setdefault(it["id"], it)
    return list(out.values())


def available(data: dict, extra_doing=()) -> list[dict]:
    """Itens que um agente pode pegar agora: todo, na fase atual, dependências feitas,
    não pegos em outra branch e sem sobreposição de escopo com o que está em andamento."""
    phase = current_phase(data)
    doing = _doing(data, extra_doing)
    taken = {it["id"] for it in doing}
    out = []
    for it in data["items"]:
        if it["status"] != "todo" or it["id"] in taken or (phase and it["phase"] != phase["id"]):
            continue
        if unmet_deps(data, it):
            continue
        if any(scopes_overlap(it.get("scope"), d.get("scope")) for d in doing):
            continue
        out.append(it)
    return out


def branch_doing(root: Path, prefix: str = "refs/remotes/origin/") -> list[dict]:
    """Itens 'doing' no roadmap.json de cada branch (claims ainda não mergeados)."""
    def run(*args):
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8")
    try:
        r = run("for-each-ref", "--format=%(refname)", prefix)
    except OSError:
        return []
    found: dict[str, dict] = {}
    for ref in r.stdout.split():
        name = ref[len(prefix):]
        if name in ("HEAD", "main"):
            continue
        shown = run("show", f"{ref}:docs/roadmap/roadmap.json")
        if shown.returncode:
            continue
        try:
            items = json.loads(shown.stdout).get("items", [])
        except ValueError:
            continue
        for it in items:
            if it.get("status") == "doing" and it.get("id") not in found:
                found[it["id"]] = {**it, "branch": name}
    return list(found.values())


def generated_touched(files) -> list[str]:
    return sorted(f for f in files if f in GENERATED)


def deliveries(data: dict) -> list[dict]:
    """Entregas legadas + itens concluídos via `done` (agrupados por data e PR)."""
    out = [dict(d) for d in data["deliveries"]]
    groups: dict[tuple, dict] = {}
    for it in data["items"]:
        if it["status"] == "done" and it.get("summary"):
            key = (it.get("merged_at") or "", it.get("pr"))
            g = groups.setdefault(key, {"date": key[0], "pr": key[1], "items": [], "summary": []})
            g["items"].append(it["id"])
            g["summary"].append(it["summary"])
    for g in groups.values():
        out.append({**g, "summary": "; ".join(g["summary"])})
    return sorted(out, key=lambda d: d["date"])


def phase_name(data: dict, pid: str) -> str:
    for p in data["phases"]:
        if p["id"] == pid:
            return p["name"]
    return pid


# ---------------------------------------------------------------- render: STATUS.md
def _md_item(data: dict, it: dict) -> str:
    frs = ", ".join(it["fr"]) if it["fr"] else "—"
    extra = []
    if it.get("status") == "doing":
        extra.append(f"agente: {it.get('agent')} · escopo: {it.get('scope')}" + (f" · branch: {it['branch']}" if it.get("branch") else ""))
    if it.get("pr"):
        extra.append(f"PR #{it['pr']}")
    if it.get("merged_at"):
        extra.append(it["merged_at"])
    if it.get("notes"):
        extra.append(it["notes"])
    tail = f" — {' · '.join(extra)}" if extra else ""
    return f"- `{it['id']}` {it['title']} ({frs}) · fase {it['phase']}{tail}"


def render_status(data: dict) -> str:
    c = counts(data)
    phase = current_phase(data)
    nxt = next_task(data)
    lines = [
        GEN_MD,
        "",
        f"# Status — {data['project']}",
        "",
        f"**Atualizado em:** {last_updated(data)} · **Itens:** {c['done']}/{c['total']} feitos ({c['pct_done']} %) · "
        f"{c['doing']} em andamento · {c['todo']} a fazer · {c['blocked']} bloqueados",
        "",
        "Gerado na `main` pelo workflow `roadmap-sync` — não edite nem commite em PR. Visual: `docs/roadmap/index.html`. "
        "Fonte: `docs/roadmap/roadmap.json`. Antes de pegar tarefa: `git fetch origin && python3 scripts/roadmap.py available`.",
        "",
        "## Fase atual",
        "",
    ]
    if phase:
        lines += [f"**Fase {phase['id']} — {phase['name']}** (semanas {phase['weeks']}) · DoD: {phase['dod']}", ""]
    lines += ["## Próxima tarefa", ""]
    if nxt:
        lines += [
            f"**`{nxt['id']}` — {nxt['title']}**",
            "",
            f"- Requisitos: {', '.join(nxt['fr']) if nxt['fr'] else '—'}",
            f"- Fase: {nxt['phase']} — {phase_name(data, nxt['phase'])}",
            f"- Estado: {STATUS_LABEL[nxt['status']]}" + (f" — {nxt['notes']}" if nxt.get("notes") else ""),
            "",
            "Comece pelo gate *plan* (`docs/dev/METHODOLOGY.md §1`).",
            "",
        ]
    else:
        lines += ["Nenhuma tarefa pendente.", ""]
    lines += ["## Disponíveis agora (trabalho em paralelo)", ""]
    avail = available(data)
    for it in avail:
        deps = ", ".join(it.get("depends_on") or []) or "—"
        lines.append(f"- `{it['id']}` {it['title']} · escopo: {it.get('scope') or '(definir no claim)'} · depende de: {deps}")
    if not avail:
        lines.append("- (nenhuma — tudo pego ou esperando dependência)")
    lines += ["", "Pegar: `python3 scripts/roadmap.py claim <ID> --agent claude|codex` (METHODOLOGY §6).", ""]
    lines += ["## Em andamento", ""]
    doing = [it for it in data["items"] if it["status"] == "doing"]
    lines += [_md_item(data, it) for it in doing] or ["- (nada em andamento)"]
    lines += ["", "## Bloqueios", ""]
    blocked = [it for it in data["items"] if it["status"] == "blocked"]
    lines += [_md_item(data, it) for it in blocked] or ["- (nenhum)"]
    lines += ["", "## Feito", ""]
    done = [it for it in data["items"] if it["status"] == "done"]
    lines += [_md_item(data, it) for it in done] or ["- (nada ainda)"]
    lines += ["", "## A fazer (por fase)", ""]
    for p in data["phases"]:
        todo = [it for it in data["items"] if it["phase"] == p["id"] and it["status"] == "todo"]
        if todo:
            lines.append(f"### Fase {p['id']} — {p['name']} ({STATUS_LABEL[p['status']]})")
            lines.append("")
            lines += [_md_item(data, it) for it in todo]
            lines.append("")
    lines += ["## Entregas (mais recentes primeiro)", ""]
    dl = deliveries(data)
    for d in list(reversed(dl))[:10]:
        pr = f"PR #{d['pr']}" if d.get("pr") else "sem PR"
        lines.append(f"- **{d['date']}** · {pr} · {d['summary']} · itens: {', '.join(d['items'])}")
    if not dl:
        lines.append("- (nenhuma)")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- render: HTML
def _e(s) -> str:
    return _html.escape(str(s), quote=True)


def _pill(status: str) -> str:
    return f'<span class="pill pill-{status}">{_e(STATUS_LABEL[status])}</span>'


def _item_row(data: dict, it: dict) -> str:
    frs = ", ".join(it["fr"]) if it["fr"] else "—"
    pr = f'#{it["pr"]}' if it.get("pr") else "—"
    when = it.get("merged_at") or "—"
    bits = [it.get("notes") or ""]
    if it.get("agent"):
        bits.append(f"agente: {it['agent']}")
    if it.get("scope"):
        bits.append(f"escopo: {it['scope']}")
    if it.get("depends_on"):
        bits.append("depende de: " + ", ".join(it["depends_on"]))
    notes = " · ".join(b for b in bits if b)
    return (
        f'<tr data-phase="{_e(it["phase"])}" data-status="{_e(it["status"])}">'
        f'<td><code>{_e(it["id"])}</code></td>'
        f'<td>{_e(it["title"])}{(" <span class=note>" + _e(notes) + "</span>") if notes else ""}</td>'
        f'<td class="mono">{_e(frs)}</td>'
        f'<td class="mono">{_e(it["phase"])}</td>'
        f'<td>{_pill(it["status"])}</td>'
        f'<td class="mono">{_e(pr)}</td>'
        f'<td class="mono">{_e(when)}</td></tr>'
    )


def _rows(data: dict, status: str) -> str:
    rows = [_item_row(data, it) for it in data["items"] if it["status"] == status]
    return "\n".join(rows) or '<tr><td colspan="7" class="empty">— nenhum item —</td></tr>'


def _phases_nav(data: dict) -> str:
    out = []
    for p in data["phases"]:
        done = sum(1 for it in data["items"] if it["phase"] == p["id"] and it["status"] == "done")
        total = sum(1 for it in data["items"] if it["phase"] == p["id"])
        out.append(
            f'<a href="#fase-{_e(p["id"])}" class="nav-item" data-phase="{_e(p["id"])}">'
            f'<span class="dot dot-{_e(p["status"])}"></span>Fase {_e(p["id"])} · {_e(p["name"])}'
            f'<span class="count">{done}/{total}</span></a>'
        )
    return "\n".join(out)


def _phase_cards(data: dict) -> str:
    out = []
    for p in data["phases"]:
        items = [it for it in data["items"] if it["phase"] == p["id"]]
        done = sum(1 for it in items if it["status"] == "done")
        total = len(items)
        pct = round(100 * done / total) if total else 0
        out.append(
            f'<section class="card phase-card" id="fase-{_e(p["id"])}">'
            f'<div class="phase-head"><span class="phase-num">{_e(p["id"])}</span>'
            f'<div><h3>{_e(p["name"])}</h3><p class="meta">semanas {_e(p["weeks"])} · {_pill(p["status"])}</p></div></div>'
            f'<p class="dod"><strong>DoD:</strong> {_e(p["dod"])}</p>'
            f'<div class="bar"><span style="width:{pct}%"></span></div>'
            f'<p class="meta">{done}/{total} itens · {pct} %</p>'
            f'</section>'
        )
    return "\n".join(out)


def _deliveries(data: dict) -> str:
    out = []
    for d in reversed(deliveries(data)):
        pr = f'PR #{d["pr"]}' if d.get("pr") else "sem PR"
        out.append(
            f'<li><span class="tl-date mono">{_e(d["date"])}</span>'
            f'<div><strong>{_e(d["summary"])}</strong><br>'
            f'<span class="meta">{_e(pr)} · itens: {_e(", ".join(d["items"]))}</span></div></li>'
        )
    return "\n".join(out) or "<li><span class='meta'>nenhuma entrega registrada</span></li>"


def render_html(data: dict, template: str) -> str:
    c = counts(data)
    phase = current_phase(data)
    nxt = next_task(data)
    repl = {
        "GEN": GEN_HTML,
        "PROJECT": _e(data["project"]),
        "UPDATED": _e(last_updated(data)),
        "PHASE_ID": _e(phase["id"]) if phase else "—",
        "PHASE_NAME": _e(phase["name"]) if phase else "—",
        "PHASE_DOD": _e(phase["dod"]) if phase else "—",
        "PHASE_WEEKS": _e(phase["weeks"]) if phase else "—",
        "NEXT_ID": _e(nxt["id"]) if nxt else "—",
        "NEXT_TITLE": _e(nxt["title"]) if nxt else "nenhuma tarefa pendente",
        "NEXT_FR": _e(", ".join(nxt["fr"])) if nxt and nxt["fr"] else "—",
        "COUNTS_DONE": str(c["done"]), "COUNTS_DOING": str(c["doing"]), "COUNTS_TODO": str(c["todo"]),
        "COUNTS_BLOCKED": str(c["blocked"]), "COUNTS_TOTAL": str(c["total"]), "PCT_DONE": str(c["pct_done"]),
        "PHASES_NAV": _phases_nav(data),
        "PHASE_CARDS": _phase_cards(data),
        "DONE_ROWS": _rows(data, "done"),
        "DOING_ROWS": _rows(data, "doing"),
        "TODO_ROWS": _rows(data, "todo"),
        "BLOCKED_ROWS": _rows(data, "blocked"),
        "DELIVERIES": _deliveries(data),
        "DATA_JSON": json.dumps(data, ensure_ascii=False).replace("</", "<\\/"),
    }
    out = template
    for k, v in repl.items():
        out = out.replace("{{" + k + "}}", v)
    if "{{" in out:
        raise SystemExit("roadmap: placeholder não substituído no template: " + out[out.index("{{"):out.index("{{") + 40])
    return out


# ---------------------------------------------------------------- commands
def build(root: Path) -> None:
    p = paths(root)
    data = load(root)
    errors = validate(data)
    if errors:
        for e in errors:
            print("roadmap: " + e, file=sys.stderr)
        raise SystemExit(2)
    p["status"].parent.mkdir(parents=True, exist_ok=True)
    p["status"].write_text(render_status(data), encoding="utf-8")
    p["html"].write_text(render_html(data, p["template"].read_text(encoding="utf-8")), encoding="utf-8")
    print(f"roadmap: escrito {p['status'].relative_to(root)} e {p['html'].relative_to(root)}")


def check(root: Path) -> int:
    p = paths(root)
    data = load(root)
    errors = validate(data)
    if errors:
        for e in errors:
            print("roadmap: " + e, file=sys.stderr)
        return 2
    drift = 0
    expected = {
        p["status"]: render_status(data),
        p["html"]: render_html(data, p["template"].read_text(encoding="utf-8")),
    }
    for path, content in expected.items():
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if actual != content:
            print(f"roadmap: {path.relative_to(root)} difere do gerado — rode `python3 scripts/roadmap.py build`")
            drift = 1
    if not drift:
        print("roadmap: OK (gerados em dia)")
    return drift


def _set(data: dict, item_id: str, **fields) -> dict:
    it = _by_id(data).get(item_id)
    if it is None:
        raise SystemExit(f"roadmap: item desconhecido: {item_id}")
    it.update(fields)
    return it


def _save_valid(root: Path, data: dict) -> None:
    errors = validate(data)
    if errors:
        raise SystemExit("roadmap: " + "; ".join(errors))
    save(root, data)


def claim(root: Path, item_id: str, agent: str, scope: str | None = None, date: str | None = None,
          extra_doing=()) -> None:
    data = load(root)
    it = _by_id(data).get(item_id)
    if it is None:
        raise SystemExit(f"roadmap: item desconhecido: {item_id}")
    if agent not in AGENTS:
        raise SystemExit(f"roadmap: agent inválido {agent!r} (use {', '.join(AGENTS)})")
    if it["status"] != "todo":
        raise SystemExit(f"roadmap: {item_id} está '{it['status']}', só itens 'todo' podem ser pegos")
    other = next((d for d in extra_doing if d["id"] == item_id), None)
    if other:
        raise SystemExit(f"roadmap: {item_id} já foi pego por {other.get('agent')} na branch {other.get('branch')}")
    missing = unmet_deps(data, it)
    if missing:
        raise SystemExit(f"roadmap: {item_id} depende de itens não feitos: {', '.join(missing)}")
    scope = scope or it.get("scope")
    if not scope:
        raise SystemExit(f"roadmap: {item_id} sem scope — passe --scope <pasta/> (ou '.' para o repositório todo)")
    busy = [d for d in _doing(data, extra_doing) if scopes_overlap(scope, d.get("scope"))]
    if busy:
        b = busy[0]
        raise SystemExit(f"roadmap: escopo {scope} ocupado por {b['id']} ({b.get('agent')}, escopo {b.get('scope')})")
    _set(data, item_id, status="doing", agent=agent, scope=scope, claimed_at=date or _dt.date.today().isoformat())
    _save_valid(root, data)
    print(f"roadmap: {item_id} pego por {agent} (escopo {scope}). Commite e faça push da branch agora.")


def done(root: Path, item_id: str, pr: int | None, summary: str, date: str | None = None) -> None:
    data = load(root)
    it = _by_id(data).get(item_id)
    if it is None:
        raise SystemExit(f"roadmap: item desconhecido: {item_id}")
    if it["status"] != "doing":
        raise SystemExit(f"roadmap: {item_id} está '{it['status']}' — rode `claim` antes de `done`")
    _set(data, item_id, status="done", pr=pr, merged_at=date or _dt.date.today().isoformat(), summary=summary)
    _save_valid(root, data)
    print(f"roadmap: {item_id} concluído (PR {pr}). Não rode `build` na branch: a main regenera os gerados.")


def _git_fetch(root: Path) -> None:
    try:
        subprocess.run(["git", "fetch", "--quiet", "--prune", "origin"], cwd=root, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        pass


def check_branch(root: Path, base: str) -> int:
    r = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], cwd=root, capture_output=True,
                       text=True, encoding="utf-8")
    if r.returncode:
        print(f"roadmap: não consegui comparar com {base}: {r.stderr.strip()}", file=sys.stderr)
        return 2
    touched = generated_touched(r.stdout.split())
    if touched:
        print("roadmap: arquivos gerados alterados na branch (a main regenera; reverta-os): " + ", ".join(touched),
              file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--branch", action="store_true", help="também falha se a branch alterou arquivos gerados")
    v.add_argument("--base", default="origin/main")
    av = sub.add_parser("available")
    av.add_argument("--no-fetch", action="store_true")
    c = sub.add_parser("claim")
    c.add_argument("id")
    c.add_argument("--agent", required=True, choices=AGENTS)
    c.add_argument("--scope", default=None)
    c.add_argument("--no-fetch", action="store_true")
    dn = sub.add_parser("done")
    dn.add_argument("id")
    dn.add_argument("--pr", type=int, required=True)
    dn.add_argument("--summary", required=True)
    dn.add_argument("--date", default=None)
    b = sub.add_parser("build")
    b.add_argument("--check", action="store_true", help="não escreve; falha se gerados diferem")
    ns = ap.parse_args(argv)
    if ns.cmd == "validate":
        errors = validate(load(root))
        for e in errors:
            print("roadmap: " + e, file=sys.stderr)
        print("roadmap: OK" if not errors else f"roadmap: {len(errors)} erro(s)")
        if errors:
            return 2
        return check_branch(root, ns.base) if ns.branch else 0
    if ns.cmd == "available":
        if not ns.no_fetch:
            _git_fetch(root)
        data = load_base(root)
        if data is None:
            print("roadmap: aviso: origin/main indisponível, usando a cópia local (pode estar desatualizada)", file=sys.stderr)
            data = load(root)
        other = branch_doing(root)
        for it in _doing(data, other):
            print(f"em andamento: {it['id']} · {it.get('agent')} · escopo {it.get('scope')}"
                  + (f" · branch {it['branch']}" if it.get("branch") else ""))
        avail = available(data, other)
        for it in avail:
            print(f"disponível:   {it['id']} · escopo {it.get('scope') or '(definir no claim)'} · {it['title']}")
        if not avail:
            print("disponível:   (nenhum)")
        return 0
    if ns.cmd == "claim":
        if not ns.no_fetch:
            _git_fetch(root)
        errors = claim_guards(root, ns.id)
        if errors:
            raise SystemExit("roadmap: " + "; ".join(errors))
        claim(root, ns.id, ns.agent, ns.scope, extra_doing=branch_doing(root))
        return 0
    if ns.cmd == "done":
        done(root, ns.id, ns.pr, ns.summary, ns.date)
        return 0
    if ns.cmd == "build":
        if ns.check:
            return check(root)
        build(root)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
