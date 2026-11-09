"""Testes de scripts/roadmap.py — só stdlib (unittest)."""
import json, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import roadmap  # noqa: E402

SAMPLE = {
    "project": "ForjaOS", "updated_at": "2026-11-08",
    "phases": [
        {"id": "0", "name": "Fundação", "weeks": "1–2", "dod": "Imagem builda no Actions", "status": "doing"},
        {"id": "1", "name": "Imagem instalável", "weeks": "3–8", "dod": "Pendrive → dual boot", "status": "todo"},
    ],
    "items": [
        {"id": "GOV-001", "fr": ["ADR-026"], "phase": "0", "title": "Metodologia", "status": "done", "pr": None, "merged_at": "2026-11-08"},
        {"id": "F0-001", "fr": ["FR-001"], "phase": "0", "title": "Containerfile mínimo", "status": "todo"},
        {"id": "F0-002", "fr": ["FR-002"], "phase": "0", "title": "check-branding real", "status": "blocked", "notes": "depende do F0-001"},
        {"id": "F1-001", "fr": ["FR-010"], "phase": "1", "title": "ISO", "status": "todo"},
    ],
    "deliveries": [{"date": "2026-11-08", "pr": None, "items": ["GOV-001"], "summary": "Governança"}],
}


PAR = {
    "project": "ForjaOS", "updated_at": "2026-11-08",
    "phases": [{"id": "0", "name": "Fundação", "weeks": "1–2", "dod": "x", "status": "doing"}],
    "items": [
        {"id": "P-A", "fr": ["FR-001"], "phase": "0", "title": "Containerfile", "status": "todo", "scope": "image/"},
        {"id": "P-B", "fr": ["FR-051"], "phase": "0", "title": "Logo", "status": "todo", "scope": "brand/"},
        {"id": "P-C", "fr": ["FR-002"], "phase": "0", "title": "Workflow", "status": "todo", "scope": ".github/", "depends_on": ["P-A"]},
        {"id": "P-D", "fr": ["FR-003"], "phase": "0", "title": "Build", "status": "todo", "scope": "image/build/"},
    ],
    "deliveries": [],
}


def copy(d):
    return json.loads(json.dumps(d))


class RoadmapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "docs" / "roadmap").mkdir(parents=True)
        (self.tmp / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "roadmap_template.html", self.tmp / "scripts" / "roadmap_template.html")
        self.json = self.tmp / "docs" / "roadmap" / "roadmap.json"
        self.json.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    # --- validate ---
    def test_validate_ok(self):
        self.assertEqual(roadmap.validate(SAMPLE), [])

    def test_validate_bad_status(self):
        bad = copy(SAMPLE); bad["items"][0]["status"] = "maybe"
        self.assertTrue(any("status" in e for e in roadmap.validate(bad)))

    def test_validate_unknown_phase(self):
        bad = copy(SAMPLE); bad["items"][0]["phase"] = "9"
        self.assertTrue(any("phase" in e for e in roadmap.validate(bad)))

    def test_validate_duplicate_id(self):
        bad = copy(SAMPLE); bad["items"][1]["id"] = "GOV-001"
        self.assertTrue(any("duplicado" in e for e in roadmap.validate(bad)))

    def test_validate_delivery_unknown_item(self):
        bad = copy(SAMPLE); bad["deliveries"][0]["items"] = ["NOPE-1"]
        self.assertTrue(any("NOPE-1" in e for e in roadmap.validate(bad)))

    # --- queries ---
    def test_current_phase_is_first_doing(self):
        self.assertEqual(roadmap.current_phase(SAMPLE)["id"], "0")

    def test_next_task_is_first_todo_of_current_phase(self):
        self.assertEqual(roadmap.next_task(SAMPLE)["id"], "F0-001")

    def test_next_task_falls_back_to_blocked(self):
        d = copy(SAMPLE); d["items"][1]["status"] = "done"
        self.assertEqual(roadmap.next_task(d)["id"], "F0-002")

    # --- render ---
    def test_status_md_contains_sections(self):
        md = roadmap.render_status(SAMPLE)
        for s in ("GERADO", "Fase atual", "Feito", "Em andamento", "Próxima tarefa", "F0-001", "Bloqueios", "F0-002"):
            self.assertIn(s, md)

    def test_html_is_self_contained_and_has_data(self):
        tpl = (ROOT / "scripts" / "roadmap_template.html").read_text(encoding="utf-8")
        html = roadmap.render_html(SAMPLE, tpl)
        self.assertNotIn("cdn.tailwindcss.com", html)
        self.assertIn('type="application/json"', html)
        self.assertIn("F0-001", html)
        self.assertNotIn("{{", html)
        self.assertIn("&lt;", roadmap.render_html({**copy(SAMPLE), "items": [{**SAMPLE["items"][0], "title": "<b>x</b>"}]}, tpl))

    def test_template_colors_come_from_palette(self):
        palette = (ROOT / "brand" / "palette.json").read_text(encoding="utf-8").lower()
        allowed = set(re.findall(r"#[0-9a-f]{6}\b", palette))
        tpl = (ROOT / "scripts" / "roadmap_template.html").read_text(encoding="utf-8").lower()
        used = set(re.findall(r"#[0-9a-f]{6}\b", tpl))
        self.assertTrue(used, "template sem cores?")
        self.assertEqual(used - allowed, set(), f"cores fora do palette: {used - allowed}")

    # --- build / check ---
    def test_build_writes_and_check_detects_drift(self):
        roadmap.build(self.tmp)
        status = self.tmp / "docs" / "STATUS.md"
        self.assertTrue(status.exists())
        self.assertTrue((self.tmp / "docs" / "roadmap" / "index.html").exists())
        self.assertEqual(roadmap.check(self.tmp), 0)
        status.write_text(status.read_text(encoding="utf-8") + "\nedit manual\n", encoding="utf-8")
        self.assertEqual(roadmap.check(self.tmp), 1)

    # --- trabalho em paralelo: schema ---
    def test_validate_doing_requires_agent_and_scope(self):
        bad = copy(SAMPLE); bad["items"][1]["status"] = "doing"
        errs = roadmap.validate(bad)
        self.assertTrue(any("agent" in e for e in errs))
        self.assertTrue(any("scope" in e for e in errs))

    def test_validate_rejects_unknown_agent(self):
        bad = copy(SAMPLE); bad["items"][1].update(status="doing", agent="gpt", scope="image/")
        self.assertTrue(any("agent" in e for e in roadmap.validate(bad)))

    def test_validate_rejects_unknown_dependency(self):
        bad = copy(SAMPLE); bad["items"][1]["depends_on"] = ["NOPE-9"]
        self.assertTrue(any("NOPE-9" in e for e in roadmap.validate(bad)))

    def test_updated_at_is_optional_and_derived(self):
        d = copy(PAR); d.pop("updated_at", None)
        self.assertEqual(roadmap.validate(d), [])
        d["items"][0]["merged_at"] = "2026-12-01"
        self.assertEqual(roadmap.last_updated(d), "2026-12-01")

    # --- trabalho em paralelo: disponíveis ---
    def test_available_respects_dependencies(self):
        ids = [it["id"] for it in roadmap.available(PAR)]
        self.assertIn("P-A", ids)
        self.assertIn("P-B", ids)
        self.assertNotIn("P-C", ids, "P-C depende de P-A, que não está feito")

    def test_available_respects_busy_scope(self):
        d = copy(PAR); roadmap._set(d, "P-A", status="doing", agent="claude", scope="image/")
        ids = [it["id"] for it in roadmap.available(d)]
        self.assertNotIn("P-A", ids)
        self.assertNotIn("P-D", ids, "P-D usa image/build/, sobreposto a image/")
        self.assertIn("P-B", ids)

    def test_available_sees_claims_from_other_branches(self):
        other = [{"id": "P-B", "status": "doing", "agent": "codex", "scope": "brand/"}]
        ids = [it["id"] for it in roadmap.available(PAR, extra_doing=other)]
        self.assertNotIn("P-B", ids)
        self.assertIn("P-A", ids)

    def test_whole_repo_scope_blocks_everything(self):
        self.assertTrue(roadmap.scopes_overlap(".", "brand/"))
        self.assertTrue(roadmap.scopes_overlap("image/", "image/build/"))
        self.assertFalse(roadmap.scopes_overlap("image/", "brand/"))

    # --- trabalho em paralelo: claim / done ---
    def test_claim_sets_doing_agent_scope(self):
        self.json.write_text(json.dumps(PAR, ensure_ascii=False), encoding="utf-8")
        roadmap.claim(self.tmp, "P-A", agent="codex", date="2026-11-10")
        it = next(i for i in json.loads(self.json.read_text(encoding="utf-8"))["items"] if i["id"] == "P-A")
        self.assertEqual((it["status"], it["agent"], it["scope"], it["claimed_at"]), ("doing", "codex", "image/", "2026-11-10"))

    def test_claim_rejects_unmet_dependency(self):
        self.json.write_text(json.dumps(PAR, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(SystemExit):
            roadmap.claim(self.tmp, "P-C", agent="claude")

    def test_claim_rejects_busy_scope(self):
        d = copy(PAR); roadmap._set(d, "P-A", status="doing", agent="claude", scope="image/")
        self.json.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(SystemExit):
            roadmap.claim(self.tmp, "P-D", agent="codex")

    def test_claim_requires_scope(self):
        d = copy(PAR); d["items"][1].pop("scope")
        self.json.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(SystemExit):
            roadmap.claim(self.tmp, "P-B", agent="codex")
        roadmap.claim(self.tmp, "P-B", agent="codex", scope="brand/")

    def test_done_touches_only_its_item(self):
        d = copy(PAR); roadmap._set(d, "P-A", status="doing", agent="claude", scope="image/")
        self.json.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        roadmap.done(self.tmp, "P-A", pr=12, summary="Containerfile", date="2026-11-11")
        after = json.loads(self.json.read_text(encoding="utf-8"))
        it = next(i for i in after["items"] if i["id"] == "P-A")
        self.assertEqual((it["status"], it["pr"], it["merged_at"], it["summary"]), ("done", 12, "2026-11-11", "Containerfile"))
        self.assertEqual(after["deliveries"], d["deliveries"], "done não pode anexar em deliveries (conflito entre PRs)")
        self.assertEqual(after.get("updated_at"), d.get("updated_at"), "done não pode mexer em updated_at (conflito entre PRs)")

    def test_done_requires_claim(self):
        self.json.write_text(json.dumps(PAR, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(SystemExit):
            roadmap.done(self.tmp, "P-A", pr=1, summary="x")

    def test_done_items_appear_as_deliveries(self):
        d = copy(PAR); roadmap._set(d, "P-A", status="done", agent="claude", scope="image/", pr=12, merged_at="2026-11-11", summary="Containerfile")
        md = roadmap.render_status(d)
        self.assertIn("PR #12", md)
        self.assertIn("Containerfile", md)
        self.assertIn("Disponíveis agora", md)

    def test_two_parallel_branches_merge_without_conflict(self):
        repo = self.tmp / "repo"
        (repo / "docs" / "roadmap").mkdir(parents=True)
        def git(*a):
            return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo, capture_output=True, text=True)
        git("init", "-q", "-b", "main")
        roadmap.save(repo, copy(PAR)); git("add", "."); git("commit", "-qm", "base")
        git("checkout", "-qb", "a")
        roadmap.claim(repo, "P-A", agent="claude", date="2026-11-10")
        roadmap.done(repo, "P-A", pr=1, summary="A", date="2026-11-10")
        git("commit", "-qam", "a")
        git("checkout", "-q", "main"); git("checkout", "-qb", "b")
        roadmap.claim(repo, "P-B", agent="codex", date="2026-11-10")
        roadmap.done(repo, "P-B", pr=2, summary="B", date="2026-11-10")
        git("commit", "-qam", "b")
        git("checkout", "-q", "main")
        self.assertEqual(git("merge", "-q", "--no-edit", "a").returncode, 0)
        r = git("merge", "-q", "--no-edit", "b")
        self.assertEqual(r.returncode, 0, "PRs paralelos conflitaram no roadmap.json: " + r.stdout + r.stderr)
        merged = roadmap.load(repo)
        self.assertEqual(roadmap.validate(merged), [])
        self.assertEqual({i["id"] for i in merged["items"] if i["status"] == "done"} >= {"P-A", "P-B"}, True)

    def test_branch_doing_reads_claims_from_refs(self):
        repo = self.tmp / "repo2"
        (repo / "docs" / "roadmap").mkdir(parents=True)
        def git(*a):
            return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo, capture_output=True, text=True)
        git("init", "-q", "-b", "main")
        roadmap.save(repo, copy(PAR)); git("add", "."); git("commit", "-qm", "base")
        git("checkout", "-qb", "feat/b")
        roadmap.claim(repo, "P-B", agent="codex", date="2026-11-10"); git("commit", "-qam", "claim")
        git("checkout", "-q", "main")
        found = roadmap.branch_doing(repo, prefix="refs/heads/")
        self.assertEqual([(i["id"], i["agent"], i["branch"]) for i in found], [("P-B", "codex", "feat/b")])

    def test_generated_files_must_not_change_in_branch(self):
        self.assertEqual(roadmap.generated_touched(["scripts/x.py", "docs/STATUS.md", "docs/roadmap/index.html"]),
                         ["docs/STATUS.md", "docs/roadmap/index.html"])
        self.assertEqual(roadmap.generated_touched(["docs/roadmap/roadmap.json"]), [])

    def test_build_fails_on_invalid_json(self):
        bad = copy(SAMPLE); bad["items"][0]["status"] = "maybe"
        self.json.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(SystemExit):
            roadmap.build(self.tmp)


if __name__ == "__main__":
    unittest.main()
