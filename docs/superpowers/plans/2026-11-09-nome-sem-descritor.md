# Nome sem descritor (ADR-031) Implementation Plan

**Goal:** Remover o descritor "DeveloperOS" do nome do SO, que passa a ser só "ForjaOS".

**Architecture:** Um ADR novo revoga o descritor do ADR-004; PRD, ADR-028 e o mapa de substituições do gerador de specs são alinhados.

**Tech Stack:** Markdown, Python (`scripts/gen_tela_specs.py`).

---

### Task 1: ADR-031 e alinhamento do PRD (ADR-004, FR-003)

**Files:**
- Create: `docs/adr/0031-nome-sem-descritor.md`
- Modify: `docs/PRD.md` (linha do ADR-004 e FR-003), `docs/adr/0028-precedencia-prototipo-prd.md`, `scripts/gen_tela_specs.py`

- Prova: `python3 scripts/gen_tela_specs.py --check` verde e `grep -rn 'ForjaOS (DeveloperOS)' docs/PRD.md scripts` vazio.
- DoD: PRD e ADR-028 sem o descritor; specs de tela inalteradas.
- Commit: `adr(docs): drop DeveloperOS descriptor from the product name (ADR-031)`
