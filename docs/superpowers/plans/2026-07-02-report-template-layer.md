# Report Template Layer Implementation Plan (Stage 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Report builders stop emitting HTML/SVG strings; they produce typed pydantic models rendered through Jinja2 templates with prebuilt Tailwind CSS/TS assets — exports stay self-contained and offline-viewable, no Node on operator machines.

**Architecture:** Three layers. (1) **Data models** in `core/models/reports/`: `ReportPage`/`Dashboard` for pages, and `SvgDoc` — a typed list of drawing primitives (`Rect`, `Circle`, `Line`, `Path`, `Text`, `Group`) — for figures. (2) **Geometry builders**: each legacy `render_*_svg` f-string function splits into a pure `build_*_figure(...) -> SvgDoc` that keeps ALL layout math and a shared generic renderer; markup knowledge leaves Python entirely. (3) **Templates**: a single generic `svg.j2` renders any `SvgDoc`; `page.html.j2`/`dashboard.html.j2` render pages with compiled Tailwind CSS and TS-built JS inlined at export time from committed package data. A parity harness (XML element/label comparison against the legacy renderers on the synthetic case) gates every figure migration before the legacy code is deleted.

**Tech Stack:** pydantic + jinja2 (required deps from stage 1), Tailwind CSS v4 + esbuild (dev-time only, via a moon task; compiled output committed), htmx vendored into the JS bundle (progressive enhancement — static exports never require a server), pytest + xml.etree for parity.

**Spec:** `docs/superpowers/specs/2026-07-02-src-skills-stabilization-design.md` (Stage 4 section).

**Sequencing:** requires stage 1 (merged). Execute AFTER stage 2 (`refactor/vocab-registry-packs`) merges — both touch `reports/analysis/` builders; rebase this branch if stage 2 is in flight. Stage 3 is independent.

**Execution status (2026-07-03):** all sequencing prerequisites are satisfied — stage 2 merged at `0eebbe9`, stage 3 at `0a08867`. Task 1 is COMPLETE (commit `8ed36e9`, merged at `a8760da`): the delivered `core/models/reports/` interfaces match this plan's Interfaces block exactly, so Tasks 2-9 consume them as written. Resume at Task 2. Stage 2's pack threading means `specs.py`/builder line numbers referenced below may have drifted — the read-first instructions in each task govern, not the line numbers.

**Recorded decisions:**
- **One generic SVG template, not one per figure.** Markup emission concentrates in `svg.j2`; the 13 legacy figure renderers become geometry builders. This is what makes parity provable and keeps directory shape sane.
- **htmx is vendored, not load-bearing.** Exports are static files opened from disk; filtering/toggle interactions are plain TS (feature parity with the current `interactions.py` script). htmx ships in the bundle for future server-backed surfaces but nothing in a static export depends on it.
- **Compiled assets are committed** (`templates_data/static/`); the moon task `crk:frontend-build` regenerates them at dev time. Operators and CI never need Node. A governance test pins that the committed assets exist, are non-trivial, and are referenced by the renderer — it does NOT rebuild them.

## Global Constraints

- Branch: `feat/report-template-layer`, cut from `dev` (after stage 2 merges).
- Exports remain public-safe by default and self-contained offline (no external URLs in rendered HTML — governance-testable); `--include-private` semantics untouched.
- Parity gate before deleting any legacy renderer: content parity (element counts per tag+class, sorted text labels, table row counts, filter term sets) on `data/examples/synthetic_case` — NOT byte parity (timestamps/attribute order may differ).
- Modules under 200 non-comment LOC; dirs max 4 files (README/`__init__` exempt in src/), max 3 child dirs; new src/ dirs need READMEs. Check shape before creating anything.
- Failed template rendering fails the export command; write to temp file then move on success (no partial exports left behind).
- Test command form: `uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest <path> -q` — abbreviated `PYTEST <path>`.
- Commits end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Report data models

**Files:**
- Create: `src/core/models/reports/__init__.py`, `page.py`, `figures.py`, `README.md` (`core/models/` has 2 child dirs — `reports/` is the 3rd, at the limit)
- Test: `tests/runtime/unit/test_record_models.py` is in a full dir set — extend `tests/runtime/unit/test_record_models.py`? No: models tests belong together but that file is record-scoped. `tests/runtime/unit/` is at 4 files/3 dirs — extend the EXISTING `tests/runtime/unit/test_record_models.py` with a clearly-sectioned reports-model block (same package under test; acceptable cohesion; watch its 200-LOC ceiling and report if tight).

**Interfaces:**
- Produces (imported by all later tasks from `core.models.reports`):

`figures.py`:

```python
"""Typed SVG figure model: geometry primitives rendered by the generic svg.j2 template."""

from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field


class _El(BaseModel):
    css_class: str = ""
    data: dict[str, str] = Field(default_factory=dict)  # data-* attributes (e.g. filter queries)
    title: str = ""  # accessible hover title; empty = omit


class Rect(_El):
    kind: Literal["rect"] = "rect"
    x: float
    y: float
    width: float
    height: float
    rx: float = 0.0
    fill: str = ""


class Circle(_El):
    kind: Literal["circle"] = "circle"
    cx: float
    cy: float
    r: float
    fill: str = ""


class Line(_El):
    kind: Literal["line"] = "line"
    x1: float
    y1: float
    x2: float
    y2: float
    stroke: str = ""
    stroke_width: float = 1.0


class Path(_El):
    kind: Literal["path"] = "path"
    d: str
    fill: str = ""
    stroke: str = ""
    stroke_width: float = 1.0


class Text(_El):
    kind: Literal["text"] = "text"
    x: float
    y: float
    content: str
    anchor: Literal["start", "middle", "end"] = "start"
    font_size: float = 12.0


class Group(_El):
    kind: Literal["group"] = "group"
    transform: str = ""
    children: list["SvgElement"] = Field(default_factory=list)


SvgElement = Union[Rect, Circle, Line, Path, Text, Group]
Group.model_rebuild()


class SvgDoc(BaseModel):
    width: float
    height: float
    view_box: str = ""  # empty = derive "0 0 {width} {height}"
    css_class: str = ""
    elements: list[SvgElement] = Field(default_factory=list)
```

`page.py`:

```python
"""Typed report page and dashboard models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.models.reports.figures import SvgDoc


class TableBlock(BaseModel):
    columns: list[str]
    rows: list[dict[str, str]]
    limit: int = 25


class ReportPage(BaseModel):
    slug: str
    title: str
    case_title: str
    summary: str = ""
    include_private: bool = False
    generated_at: str = ""
    filters: list[str] = Field(default_factory=list)
    figure: SvgDoc | None = None
    legacy_figure_svg: str = ""  # transitional escape hatch; deleted in the final task
    table: TableBlock | None = None
    notes: list[str] = Field(default_factory=list)


class Dashboard(BaseModel):
    case_title: str
    include_private: bool = False
    generated_at: str = ""
    pages: list[ReportPage] = Field(default_factory=list)
```

- [x] **Step 1: Write failing tests** (append to `tests/runtime/unit/test_record_models.py`):

```python
def test_svg_doc_round_trips_nested_groups():
    from core.models.reports import Group, Rect, SvgDoc, Text

    doc = SvgDoc(width=100, height=50, elements=[
        Group(transform="translate(10,0)", children=[
            Rect(x=0, y=0, width=10, height=10, css_class="node", data={"query": "alpha"}),
            Text(x=5, y=20, content="Alpha", anchor="middle"),
        ]),
    ])
    dumped = doc.model_dump()
    assert dumped["elements"][0]["children"][0]["kind"] == "rect"
    from core.models.reports import SvgDoc as _SvgDoc

    assert _SvgDoc.model_validate(dumped) == doc


def test_report_page_defaults():
    from core.models.reports import ReportPage

    page = ReportPage(slug="x", title="X", case_title="Case")
    assert page.figure is None and page.filters == [] and page.include_private is False
```

Run: `PYTEST tests/runtime/unit/test_record_models.py -q` — Expected: FAIL (`ModuleNotFoundError: core.models.reports`).

- [x] **Step 2: Create the modules** (code above; `__init__.py` re-exports `SvgDoc`, all primitives, `ReportPage`, `TableBlock`, `Dashboard`; README describes the three-layer split).

- [x] **Step 3: Run** `PYTEST tests/runtime/unit/test_record_models.py tests/quality/governance/test_repository_shape.py -q` — PASS.

- [x] **Step 4: Commit** — `feat(models): add typed report page and svg figure models`

---

### Task 2: Frontend source + committed compiled assets + moon task

**Files:**
- Create: `frontend/package.json`, `frontend/app.ts`, `frontend/styles.css`, `frontend/README.md` (root-level dir; repo root already exceeds nominal dir limits via overrides — confirm `PYTEST tests/quality/governance/test_repository_shape.py -q` stays green after creating, and report BLOCKED if the root is actually capped)
- Create (committed build output): `src/adapters/ops/evidence/reports/analysis/pages/templates_data/static/app.css`, `.../static/app.js`, plus `templates_data/README.md` (`pages/` has 4 files + 0 dirs — `templates_data/` is its 1st child dir)
- Modify: `.moon/tasks/tooling.yml` (add `frontend-build`), `pyproject.toml` (package-data), `.gitignore` (only `frontend/node_modules/`)

**Interfaces:**
- Produces: committed `static/app.css` (Tailwind build of `styles.css` scanning the templates) and `static/app.js` (esbuild bundle of `app.ts` with htmx vendored). Later tasks inline these files' contents into rendered pages. Moon task `crk:frontend-build` regenerates them.

- [ ] **Step 1: Frontend source**

`frontend/package.json`:

```json
{
  "name": "crk-report-frontend",
  "private": true,
  "scripts": {
    "build": "npm run build:css && npm run build:js",
    "build:css": "tailwindcss -i styles.css -o ../src/adapters/ops/evidence/reports/analysis/pages/templates_data/static/app.css --minify --content '../src/adapters/ops/evidence/reports/analysis/pages/templates_data/**/*.j2'",
    "build:js": "esbuild app.ts --bundle --minify --outfile=../src/adapters/ops/evidence/reports/analysis/pages/templates_data/static/app.js"
  },
  "devDependencies": {
    "@tailwindcss/cli": "^4.0.0",
    "esbuild": "^0.24.0",
    "htmx.org": "^2.0.0"
  }
}
```

`frontend/styles.css`:

```css
@import "tailwindcss";

@layer components {
  .crk-muted { @apply text-sm text-slate-500; }
  .crk-table-wrap { @apply overflow-x-auto rounded border border-slate-200; }
  .crk-filter-btn { @apply rounded border border-slate-300 px-2 py-1 text-xs; }
  .crk-filter-btn[aria-pressed="true"] { @apply bg-slate-800 text-white; }
}
```

`frontend/app.ts` — feature parity with the current `pages/interactions.py` script. FIRST read `src/adapters/ops/evidence/reports/analysis/pages/interactions.py` and transcribe its behaviors (filter buttons toggling `aria-pressed` and hiding non-matching `[data-query]` elements/rows, plus whatever else it does — enumerate each behavior in your report). Skeleton:

```typescript
import "htmx.org";

function applyFilters(): void {
  const active = Array.from(document.querySelectorAll<HTMLButtonElement>("[data-query][aria-pressed='true']"))
    .map((b) => (b.dataset.query ?? "").toLowerCase());
  document.querySelectorAll<HTMLElement>("[data-filterable]").forEach((el) => {
    const hay = (el.dataset.filterable ?? el.textContent ?? "").toLowerCase();
    el.hidden = active.length > 0 && !active.some((q) => hay.includes(q));
  });
}

document.addEventListener("click", (event) => {
  const btn = (event.target as HTMLElement).closest<HTMLButtonElement>("button[data-query]");
  if (!btn) return;
  btn.setAttribute("aria-pressed", btn.getAttribute("aria-pressed") === "true" ? "false" : "true");
  applyFilters();
});
```

- [ ] **Step 2: Moon task** in `.moon/tasks/tooling.yml`, following the file's existing task shape:

```yaml
  frontend-build:
    command: "npm"
    args: ["run", "build"]
    options:
      cwd: "frontend"
    deps: []
```

First run `npm install` inside `frontend/` (gitignore `node_modules/`), then `moon run crk:frontend-build` (or `cd frontend && npm run build` if the moon wiring needs iteration — the committed assets are the deliverable; note in the report which invocation produced them).

- [ ] **Step 3: Register package data** in `pyproject.toml`:

```toml
"adapters.ops.evidence.reports.analysis.pages" = [
  "templates_data/static/*",
  "templates_data/layouts/*.j2",
  "templates_data/figures/*.j2",
]
```

- [ ] **Step 4: Governance pin** — add to `tests/quality/governance/platform/test_packaging_policy.py` (mind its LOC ceiling):

```python
def test_report_frontend_assets_are_committed_and_selfcontained():
    static = KIT_ROOT / "src/adapters/ops/evidence/reports/analysis/pages/templates_data/static"
    css, js = (static / "app.css").read_text(encoding="utf-8"), (static / "app.js").read_text(encoding="utf-8")
    assert len(css) > 500 and len(js) > 500
    for text in (css, js):
        assert "http://" not in text and "https://" not in text.replace("https://htmx.org", "")  # no runtime CDN fetches; license-comment URLs tolerated via targeted replaces — tighten to the actual comment strings found
```

Adjust the URL-tolerance line to whatever license comments the real bundles contain (inspect them); the invariant is: no `fetch`/`src=`/`href=` pointing off-disk. State the final assertion in your report.

- [ ] **Step 5: Run** shape + packaging governance; **Commit** — `feat(frontend): add report asset pipeline with committed builds`

---

### Task 3: Jinja renderer + page/dashboard templates

**Files:**
- Create: `templates_data/layouts/page.html.j2`, `layouts/dashboard.html.j2`, `figures/svg.j2` (dirs from Task 2)
- Create: `src/adapters/ops/evidence/reports/analysis/pages/renderer.py` — WAIT: `pages/` is at 4 counted files. Instead REWRITE `pages/render.py` in place: it becomes the Jinja renderer while KEEPING the legacy functions (`render_analysis_chart_page`, `render_analysis_dashboard`, `chart_row_table`, `filter_terms`) untouched until the final cutover task. If the combined module exceeds 200 non-comment LOC, move the legacy functions verbatim to `pages/assets.py` temporarily (it is going away in the final task anyway) and note it.
- Test: `tests/runtime/unit/interfaces/test_report_renderer.py` (`interfaces/` has 3 files → 4, at limit)

**Interfaces:**
- Produces (from `adapters.ops.evidence.reports.analysis.pages.render`):
  - `render_page(page: ReportPage) -> str` — full self-contained HTML document: inlined `static/app.css` in `<style>`, `static/app.js` in `<script>`, figure via the `svg.j2` include or `page.legacy_figure_svg` verbatim, table block, filter buttons.
  - `render_dashboard(dash: Dashboard) -> str`
  - `_environment() -> jinja2.Environment` (package loader with checkout fallback, autoescape on)
  - `write_html(path: Path, html_text: str) -> None` — temp-file-then-`os.replace` atomic write.

- [ ] **Step 1: Failing tests**

```python
"""Jinja report renderer: self-contained pages from typed models."""

from __future__ import annotations

from core.models.reports import Rect, ReportPage, SvgDoc, TableBlock, Text
from adapters.ops.evidence.reports.analysis.pages.render import render_page


def _page() -> ReportPage:
    return ReportPage(
        slug="demo", title="Demo Chart", case_title="Case X", filters=["alpha", "beta"],
        figure=SvgDoc(width=100, height=40, elements=[
            Rect(x=1, y=2, width=10, height=5, css_class="node", data={"query": "alpha"}),
            Text(x=5, y=30, content="Alpha & Co", anchor="middle"),
        ]),
        table=TableBlock(columns=["name", "status"], rows=[{"name": "A", "status": "verified"}]),
    )


def test_render_page_is_self_contained_html():
    html_text = render_page(_page())
    assert html_text.startswith("<!doctype html>")
    assert "<style>" in html_text and "<script>" in html_text
    assert "http://" not in html_text and "https://" not in html_text


def test_render_page_escapes_and_carries_data_attrs():
    html_text = render_page(_page())
    assert "Alpha &amp; Co" in html_text
    assert 'data-query="alpha"' in html_text
    assert '<rect x="1.0" y="2.0"' in html_text or '<rect x="1" y="2"' in html_text


def test_render_page_renders_table_and_filters():
    html_text = render_page(_page())
    assert "<table" in html_text and "verified" in html_text
    assert html_text.count("crk-filter-btn") >= 2
```

Run — Expected: FAIL (`render_page` missing).

- [ ] **Step 2: Templates**

`figures/svg.j2` (generic primitive renderer — recursive macro):

```jinja
{% macro attrs(el) -%}
{%- if el.css_class %} class="{{ el.css_class }}"{% endif -%}
{%- for k, v in el.data.items() %} data-{{ k }}="{{ v }}"{% endfor -%}
{%- endmacro %}

{% macro element(el) -%}
{%- if el.kind == "rect" -%}
<rect x="{{ el.x }}" y="{{ el.y }}" width="{{ el.width }}" height="{{ el.height }}"{% if el.rx %} rx="{{ el.rx }}"{% endif %}{% if el.fill %} fill="{{ el.fill }}"{% endif %}{{ attrs(el) }}>{% if el.title %}<title>{{ el.title }}</title>{% endif %}</rect>
{%- elif el.kind == "circle" -%}
<circle cx="{{ el.cx }}" cy="{{ el.cy }}" r="{{ el.r }}"{% if el.fill %} fill="{{ el.fill }}"{% endif %}{{ attrs(el) }}>{% if el.title %}<title>{{ el.title }}</title>{% endif %}</circle>
{%- elif el.kind == "line" -%}
<line x1="{{ el.x1 }}" y1="{{ el.y1 }}" x2="{{ el.x2 }}" y2="{{ el.y2 }}"{% if el.stroke %} stroke="{{ el.stroke }}"{% endif %} stroke-width="{{ el.stroke_width }}"{{ attrs(el) }}/>
{%- elif el.kind == "path" -%}
<path d="{{ el.d }}"{% if el.fill %} fill="{{ el.fill }}"{% endif %}{% if el.stroke %} stroke="{{ el.stroke }}"{% endif %} stroke-width="{{ el.stroke_width }}"{{ attrs(el) }}/>
{%- elif el.kind == "text" -%}
<text x="{{ el.x }}" y="{{ el.y }}" text-anchor="{{ el.anchor }}" font-size="{{ el.font_size }}"{{ attrs(el) }}>{{ el.content }}</text>
{%- elif el.kind == "group" -%}
<g{% if el.transform %} transform="{{ el.transform }}"{% endif %}{{ attrs(el) }}>{% for child in el.children %}{{ element(child) }}{% endfor %}</g>
{%- endif -%}
{%- endmacro %}

{% macro svg(doc) -%}
<svg xmlns="http://www.w3.org/2000/svg" width="{{ doc.width }}" height="{{ doc.height }}" viewBox="{{ doc.view_box or ('0 0 ' ~ doc.width ~ ' ' ~ doc.height) }}"{% if doc.css_class %} class="{{ doc.css_class }}"{% endif %}>
{%- for el in doc.elements %}{{ element(el) }}{% endfor -%}
</svg>
{%- endmacro %}
```

(The `xmlns` URL is SVG's namespace identifier, not a network fetch — exempt it in the self-containment assertions: strip `xmlns="http://www.w3.org/2000/svg"` before checking.) Update Task 2's governance test and Step 1's `test_render_page_is_self_contained_html` accordingly — assert no `http` remains AFTER removing the xmlns declaration.

`layouts/page.html.j2`:

```jinja
{% import "figures/svg.j2" as figures %}<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ page.title }} - {{ page.case_title }}</title>
<style>{{ app_css }}</style>
</head>
<body class="crk-report">
<header>
<h1>{{ page.title }}</h1>
<p class="crk-muted">{{ page.case_title }} · generated {{ page.generated_at }}{% if page.include_private %} · INTERNAL REVIEW (includes private records){% endif %}</p>
{% if page.summary %}<p>{{ page.summary }}</p>{% endif %}
{% if page.filters %}<nav>{% for term in page.filters %}<button type="button" class="crk-filter-btn" data-query="{{ term }}" aria-pressed="false">{{ term }}</button>{% endfor %}</nav>{% endif %}
</header>
<main>
{% if page.figure %}{{ figures.svg(page.figure) }}{% elif page.legacy_figure_svg %}{{ page.legacy_figure_svg | safe }}{% endif %}
{% if page.table %}
<div class="crk-table-wrap"><table><thead><tr>{% for col in page.table.columns %}<th>{{ col.replace("_", " ").title() }}</th>{% endfor %}</tr></thead>
<tbody>{% for row in page.table.rows[:page.table.limit] %}<tr data-filterable="{{ row.values() | join(' ') }}">{% for col in page.table.columns %}<td>{{ row.get(col, "") }}</td>{% endfor %}</tr>{% endfor %}</tbody></table></div>
{% if page.table.rows | length > page.table.limit %}<p class="crk-muted">Showing {{ page.table.limit }} of {{ page.table.rows | length }} rows.</p>{% endif %}
{% endif %}
{% for note in page.notes %}<p class="crk-muted">{{ note }}</p>{% endfor %}
</main>
<script>{{ app_js }}</script>
</body>
</html>
```

`layouts/dashboard.html.j2` — same shell, looping `dash.pages` as a linked index (title, summary, `{{ page.slug }}.html` links); transcribe the information the legacy `render_analysis_dashboard` shows (read it first).

- [ ] **Step 3: Renderer implementation** (in `pages/render.py`, added alongside the untouched legacy functions):

```python
import os
import tempfile
from functools import lru_cache
from pathlib import Path

import jinja2

from core.models.reports import Dashboard, ReportPage


@lru_cache(maxsize=1)
def _environment() -> jinja2.Environment:
    package_dir = Path(__file__).resolve().parent / "templates_data"
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(package_dir)),
        autoescape=jinja2.select_autoescape(["html", "j2"]),
        undefined=jinja2.StrictUndefined,
    )


@lru_cache(maxsize=1)
def _static_assets() -> tuple[str, str]:
    static = Path(__file__).resolve().parent / "templates_data" / "static"
    return static.joinpath("app.css").read_text(encoding="utf-8"), static.joinpath("app.js").read_text(encoding="utf-8")


def render_page(page: ReportPage) -> str:
    css, js = _static_assets()
    return _environment().get_template("layouts/page.html.j2").render(page=page, app_css=css, app_js=js)


def render_dashboard(dash: Dashboard) -> str:
    css, js = _static_assets()
    return _environment().get_template("layouts/dashboard.html.j2").render(dash=dash, app_css=css, app_js=js)


def write_html(path: Path, html_text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(html_text)
    os.replace(tmp, path)
```

(`Path(__file__)` works both in checkout and installed wheel because `templates_data/` is package data inside this package — no dual resolution needed. `StrictUndefined` makes template/model drift a loud failure.)

- [ ] **Step 4: Run** the new test file + shape + packaging governance — PASS. **Commit** — `feat(reports): add jinja page renderer over typed models`

---

### Task 4: Pages cutover — specs build models, output writes via renderer (figures transitional)

**Files:**
- Modify: `src/adapters/ops/evidence/reports/analysis/pages/specs.py` (`build_analysis_chart_specs` returns `list[ReportPage]`; each spec's rendered-SVG string moves into `legacy_figure_svg`, table dicts into `TableBlock`, filter terms into `filters`)
- Modify: `src/adapters/ops/evidence/reports/analysis/command/output.py` (page/dashboard writes go through `render_page`/`render_dashboard` + `write_html`; CSV writing untouched)
- Modify: `src/adapters/ops/evidence/reports/analysis/command/manifest.py` only if it consumed spec dicts (read it; adapt field access to the model)
- Test: parity test in `tests/runtime/integration/operations/exports/` (check file count; join an existing exports test file if at 4)

**Interfaces:**
- Consumes: `ReportPage`/`TableBlock`/`Dashboard`, `render_page`, `render_dashboard`, `write_html`.
- Produces: `build_analysis_chart_specs(chart_data) -> list[ReportPage]`; the legacy `render_analysis_chart_page`/`chart_row_table` become unused by the analysis path (do NOT delete yet — the parity test still calls them, and case_charts/clusters still use their own legacy paths).

- [ ] **Step 1: Parity test first** (content parity, not bytes):

```python
"""Old and new analysis page pipelines agree on content for the synthetic case."""

from __future__ import annotations

import re
from pathlib import Path

SYNTHETIC_CASE = Path(__file__).resolve().parents[5] / "data" / "examples" / "synthetic_case"


def _signature(html_text: str) -> dict:
    return {
        "title": re.search(r"<title>(.*?)</title>", html_text).group(1),
        "row_count": html_text.count("<tr"),
        "filter_terms": sorted(set(re.findall(r'data-query="([^"]+)"', html_text))),
        "svg_count": html_text.count("<svg"),
    }


def test_new_pipeline_preserves_page_content(tmp_path):
    # Build chart_data exactly as the analysis command does (read command/entry.py + context.py
    # and reuse load_analysis_context via a Namespace, out=tmp_path). For each ReportPage from
    # build_analysis_chart_specs: render via render_page, and render the OLD page via
    # render_analysis_chart_page(case_title, include_private, old_spec_dict) — reconstruct the
    # old dict from the same chart_data using the pre-change function preserved in git if needed.
    ...
```

The honest mechanics: BEFORE changing `specs.py`, run the current pipeline on the synthetic case and pickle/JSON the per-page `_signature` dict to a committed fixture `tests/runtime/integration/operations/exports/analysis_page_signatures.json` (title/row_count/filter_terms/svg_count per page slug). The test then runs the NEW pipeline and compares signatures against the fixture. Replace the sketch above with that concrete fixture-comparison test — generate the fixture as this step's first action, while the legacy code is still primary, and commit it. `generated_at` timestamps are excluded from the signature by construction.

- [ ] **Step 2: Convert `specs.py`** — each entry in its `sorted([...])` list becomes `ReportPage(slug=..., title=..., summary=..., filters=filter_terms(...), legacy_figure_svg=render_*_svg(...), table=TableBlock(columns=..., rows=...))`. Keep calling the legacy SVG renderers for now — figure migration is Tasks 5-7. The old `chart_row_table` HTML call is replaced by structured `TableBlock` data (columns/rows already exist in the spec dicts; pass them through `flatten` for cell stringification as the old table did — read `chart_row_table` and reproduce its column/limit semantics in data).

- [ ] **Step 3: Convert `output.py` + `manifest.py`** page writes to `write_html(out / f"{page.slug}.html", render_page(page))` and the dashboard equivalent.

- [ ] **Step 4: Run** parity test + `PYTEST tests/runtime -q` + the end-to-end export:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable . -- crk-ledger export-analysis-charts data/examples/synthetic_case
```

Expected: parity signatures match the fixture; export completes. **Commit** — `refactor(reports): analysis pages render through typed models and jinja`

---

### Task 5: Figure migration — matrix family

**Files:**
- Modify: `src/adapters/ops/evidence/reports/analysis/svg/matrix.py` — each of its five `render_*_svg(...) -> str` functions becomes `build_*_figure(...) -> SvgDoc` with IDENTICAL layout math; a thin `render_*_svg` wrapper (`figures.svg(doc)` via the Jinja env) stays temporarily so nothing upstream breaks mid-task.
- Modify: `specs.py` — matrix-family pages switch from `legacy_figure_svg` to `figure=build_*_figure(...)`.
- Test: figure parity harness (new shared helper) + per-figure assertions.

**Interfaces:**
- Consumes: `SvgDoc` primitives, `svg.j2` (via a `render_svg_doc(doc) -> str` helper added to `pages/render.py`: `_environment().get_template("figures/svg.j2").module.svg(doc)` — expose it there).
- Produces: `build_claim_matrix_figure`, `build_fragility_figure`, `build_heatmap_figure`, `build_readiness_figure`, `build_source_quality_figure` (names = legacy names with `render_`→`build_` and `_svg`→`_figure`), each returning `SvgDoc`.

- [ ] **Step 1: Parity harness** (shared; put in the exports parity test file from Task 4):

```python
import xml.etree.ElementTree as ET


def svg_signature(svg_text: str) -> dict:
    root = ET.fromstring(svg_text)
    ns = "{http://www.w3.org/2000/svg}"
    counts: dict[str, int] = {}
    labels: list[str] = []
    for el in root.iter():
        tag = el.tag.replace(ns, "")
        key = f"{tag}.{el.get('class') or ''}"
        counts[key] = counts.get(key, 0) + 1
        if tag == "text" and (el.text or "").strip():
            labels.append(el.text.strip())
    return {"counts": dict(sorted(counts.items())), "labels": sorted(labels)}
```

Conversion recipe per legacy renderer (apply to each of the five):
1. Read the legacy function. Every f-string `<rect …>` append becomes `elements.append(Rect(...))`, `<text>` → `Text(...)`, `<g transform=…>` wrapping → `Group(children=[...])`, etc. Coordinates, sizes, class names, and `data-*` attributes transfer verbatim; `html.escape` calls DROP (Jinja autoescape owns escaping now).
2. The function's final `f"<svg …>…</svg>"` shell becomes the returned `SvgDoc(width=…, height=…, css_class=…)`.
3. Temporary wrapper: `def render_claim_matrix_svg(*a, **k): return render_svg_doc(build_claim_matrix_figure(*a, **k))`.
4. Parity assertion — with the synthetic case's `chart_data` inputs, `svg_signature(legacy_output_from_fixture)` == `svg_signature(render_svg_doc(build_*_figure(...)))`. The legacy output comes from the Task 4 committed fixture approach: extend the fixture generation to ALSO store each figure's `svg_signature` before this task's changes (do that as this task's first commit if Task 4 didn't already capture figure signatures — it captured only page-level `svg_count`; add per-figure signatures now, generated from the still-legacy code, committed, THEN convert).

- [ ] **Step 2-4:** Convert the five functions; flip `specs.py` matrix pages to `figure=`; run figure parity + page parity + `PYTEST tests/runtime -q` + the export command. **Commit** — `refactor(reports): matrix figures build typed svg models`

---

### Task 6: Figure migration — facets family

Same recipe as Task 5, applied to `svg/facets.py` (`render_bipartite_svg`, `render_boundary_overlay_svg`, `render_path_atlas_svg`, `render_swimlanes_svg`, `render_treemap_svg` → `build_*_figure`), fixture-first, wrappers, parity, `specs.py` flip, full suite + export.

**Commit** — `refactor(reports): facet figures build typed svg models`

---

### Task 7: Figure migration — network family + shared svg/base helpers

Same recipe for `svg/network/layers.py` (`render_layered_graph_svg`, `render_layered_graph_v2_svg`) and `svg/network/bridges.py` (`render_sankey_svg`). Then audit `svg/base.py`: string-emitting helpers (anything returning markup) convert to primitive-returning helpers or fold into the builders; pure-computation helpers (`short_label`, scales) stay. Fixture-first, parity, `specs.py` flip, suite + export.

**Commit** — `refactor(reports): network figures build typed svg models`

---

### Task 8: case_charts + clusters onto the shared pipeline

**Files:**
- Modify: `src/adapters/ops/evidence/reports/case_charts/people.py`, `timeline.py`, `command.py`; `src/adapters/ops/evidence/reports/clusters/renderers.py`, `command.py`

Read each module first. Apply the SAME split: page shells → `ReportPage` + `render_page` (their standalone CSS/JS, if any, is superseded by the shared assets — enumerate any chart-specific styles and add them to `frontend/styles.css`, rebuild assets via the moon task, commit the rebuilt `static/`); figure strings → `build_*_figure` + parity signatures (fixture-first, same harness). These commands' CLI/ops surfaces (`export_case_charts`, clusters command) must not change. Extend the signature fixture with these pages/figures before converting.

Run: full suite + `crk-ledger` case-charts and clusters export commands against the synthetic case. **Commit** — `refactor(reports): case charts and clusters render through the template layer`

---

### Task 9: Delete legacy renderers, drop the escape hatch, docs, verify

**Files:**
- Delete: legacy string-rendering functions — the `render_*_svg` wrappers in `svg/*` (keeping `build_*_figure`), `pages/interactions.py`, the CSS/`analysis_chart_files` parts of `pages/assets.py` (delete the module if nothing else remains — update `pages/` README), legacy `render_analysis_chart_page`/`render_analysis_dashboard`/`chart_row_table` in `render.py`
- Modify: `core/models/reports/page.py` — remove `legacy_figure_svg` (grep confirms no producers remain)
- Modify: `CHANGELOG.md`, `src/adapters/ops/evidence/reports/analysis/README.md` + `pages/README.md`

- [ ] **Step 1:** `grep -rn "legacy_figure_svg\|render_analysis_chart_page\|chart_row_table\|analysis_chart_css\|analysis_chart_script\|render_.*_svg" src/ tests/` — delete producers/consumers in dependency order; every hit must be gone or justified in the report.
- [ ] **Step 2:** CHANGELOG under `## [Unreleased]`:

```markdown
### Changed
- Analysis, case-chart, and cluster reports now render through typed pydantic models and Jinja2 templates with committed Tailwind/TS assets; output is byte-different but content-equivalent (element/label parity gated against the synthetic case) and remains fully offline-viewable.

### Removed
- Legacy f-string HTML/SVG renderers (`pages/interactions.py`, string-building `render_*_svg` functions) — replaced by `core.models.reports` figures and the `templates_data/` template layer.
```

- [ ] **Step 3:** Full verification: `moon run crk:check && moon run crk:test`, `crk-ledger export-analysis-charts data/examples/synthetic_case`, fresh-build wheel smoke (`deployment/scripts/checks/fresh_build.py`) proving `templates_data/` ships in the wheel and pages render from an installed package (add that import/render one-liner to the smoke check ONLY if fresh_build supports extension without violating its own governance pins — otherwise verify manually from a `/tmp` venv and record the transcript in the report).
- [ ] **Step 4: Commit** — `refactor(reports)!: remove legacy string renderers` — then finish the branch via superpowers:finishing-a-development-branch. Do not push tags.
