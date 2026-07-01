# True Crime / Cult-Origin Research Kit for Codex

A reusable Codex skill and project scaffold for building a data-first, evidence-informed research system around true crime, high-control groups, cult origins, related people, places, events, objects, sources, claims, and contradictions.

This kit is designed for public-interest research and documentary-style educational work. It is **not** designed for harassment, doxxing, vigilante investigation, private-person targeting, or making unsourced accusations.

## What this gives you

- A Codex skill at `.agents/skills/truecrime-cult-research/SKILL.md`
- A repository-level `AGENTS.md` with persistent project rules for Codex
- JSON schemas under `docs/schemas/` for sources, entities, claims, events, event links, relationships, places, artifacts, and quotes
- A Python CLI tool for creating case folders, ingesting URLs, staging extractions, importing structured data, validating records, and exporting Manim-ready CSVs
- Templates for case briefs, source notes, extraction packets, redaction logs, and evidence boards
- A repeatable workflow for using news articles, eyewitness accounts, court/public records, archives, and disconfirming sources
- Skill-facing references for controlled vocabularies, citation locators, topic extraction templates, source independence, and public-export auditing

## Recommended install

From this repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

The core CLI mostly uses the Python standard library. Optional packages improve extraction and validation:

```bash
pip install beautifulsoup4 trafilatura jsonschema pandas networkx
```

## Quick start

Create a case workspace:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py init-case data/cases/sample_case --title "Sample Case"
```

Add or ingest a public URL:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py ingest-url data/cases/sample_case "https://example.com/news-story" --source-type news_article --reliability-grade B
```

Create an extraction packet for Codex to fill:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction data/cases/sample_case SOURCE_ID
```

After Codex fills the staged JSON extraction, import it:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction data/cases/sample_case data/cases/sample_case/staging/extractions/SOURCE_ID_extraction.json
```

Validate and export:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate data/cases/sample_case
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-manim data/cases/sample_case
python .agents/skills/truecrime-cult-research/scripts/tcr.py report data/cases/sample_case
```

Build a cross-case timeline and claim corroboration index:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-timeline tc-c-kit/data/cases
```

This writes public-safe cross-case artifacts to `tc-c-kit/data/exports/timeline/`:

- `cases.csv`
- `timeline.csv`
- `corroborations.csv`
- `timeline.md`

For internal review of non-public, disputed, excluded, or unverified rows, opt in explicitly:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-timeline tc-c-kit/data/cases --include-private --out-dir tc-c-kit/data/exports/timeline_internal
```

`tc-c-kit/data/cases/` and `tc-c-kit/data/exports/` are local/generated working areas and
are ignored by Git except for `.gitkeep` placeholders. Keep reusable fixtures in
`tc-c-kit/data/examples/` instead.

Build case-level chart artifacts for a people-only graph and subcase timeline:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-case-charts tc-c-kit/data/cases/<case_slug>
```

This writes public-safe chart artifacts to `data/cases/<case_slug>/exports/charts/`:

- `people_graph.html`
- `people_nodes.csv`
- `people_edges.csv`
- `subcase_timelines.html`
- `subcase_timelines.csv`
- `subcase_summary.csv`

Run evidence-weighted Leiden clustering plus graph-kernel/KDE density over the
people graph:

```bash
cd tc-c-kit
uv run --extra dev --with igraph --with leidenalg \
  python ../.agents/skills/truecrime-cult-research/scripts/tcr.py export-people-clusters data/cases/<case_slug> --include-private
```

This writes internal-review clustering artifacts to
`data/cases/<case_slug>/exports/clusters/`:

- `people_clusters.html`
- `people_clusters.csv`
- `cluster_summary.csv`
- `people_cluster_edges.csv`
- `people_kernel_matrix.csv`
- `clusters.md`

Build the extended analysis chart package for cluster bridges, claim/source
corroboration, source quality, path atlases, swimlanes, relationship-class
treemaps, and public narrative readiness:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py export-analysis-charts tc-c-kit/data/cases/<case_slug> --include-private
```

This writes review artifacts to `data/cases/<case_slug>/exports/analysis_charts/`,
including `analysis_charts.html`, `cluster_bridge_sankey_nodes.csv`,
`cluster_bridge_sankey_links.csv`, `evidence_confidence_heatmap.csv`,
`claim_corroboration_matrix.csv`, `source_quality_dashboard.csv`,
`sixdof_path_atlas.csv`, `relationship_type_treemap.csv`,
`person_source_bipartite_nodes.csv`, and `public_narrative_readiness.csv`.
The `relationship_class` column separates documented succession, method
diffusion, personnel bridges, narrative inheritance, contested overlap, and
hypotheses requiring more sources.

Link a list of names to existing events and co-mentions:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py link-names tc-c-kit/data/cases/<case_slug> --names-file names.txt --name "Primary Name|Known Alias"
```

`link-names` writes conservative, private-by-default co-mention records and a research brief under `notes/`. It does not make guilt, membership, motive, or participation claims from proximity.

Export a TRCR case to a Phanestead-readable UFB v2 bundle:

```bash
bun scripts/export_trcr_ufb.mjs tc-c-kit/data/cases/<case_slug> --out tc-c-kit/data/cases/<case_slug>/exports/ufb/<case_slug>.ufb_v2
```

The exporter writes a public-safe bundle by default. Use `--include-private`
only for internal testing artifacts.

## How to invoke the skill in Codex

Codex should discover repo skills under `.agents/skills`. You can invoke explicitly in Codex with something like:

```text
Use the $truecrime-cult-research skill. Build a case file for [topic]. Find public news sources, eyewitness accounts, and official records. Save sources, extract entities/events/claims, flag contradictions, and export Manim-ready CSVs.
```

Or ask:

```text
Use the truecrime-cult-research skill to create a data-first source map for the origins of [group/case]. Start with public news coverage and eyewitness accounts, but do not publish private-person details or infer guilt.
```

## Adjacent skill routing

Use `truecrime-cult-research` as the case ledger and safety baseline. Route
domain-heavy packets to adjacent skills when appropriate:

- `corporate-financial-records`: corporations, nonprofits, banks, shell companies, bankruptcies, investments, ownership/control, boards, officers, transactions, SEC/state filings, and financial records.
- `educational-path-records`: schools, degrees, training, credentials, academic appointments, alumni claims, student-era events, institution affiliations, and credential disputes.
- `legal-court-records`, `identity-resolution`, `source-capture-preservation`, and `claim-contradiction-audit`: court records, ambiguous identities, source preservation, and contradiction review.
- `public-records-router`, `licensing-professional-records`, `media-transcript-intelligence`, and `property-location-records`: source-lane planning, licenses, transcripts/media, and property/location records.
- `missing-persons-case`: missing-person candidates, last-seen/time-location matching, public bulletins, status updates, and unidentified-person comparisons.
- `geographical-location-intelligence`: evidence-item geography, event maps, routes, sightings, map/exhibit locators, and locations of interest.
- `foia-open-records-planning`, `narrative-readiness-review`, `privacy-redaction-audit`, and `source-independence-audit`: open-records planning and public-output readiness review.

Adjacent skills write source-traceable entities, claims, events, relationships,
artifacts, and notes back into the same TRCR case structure.

## LangGraph case-builder bootstrap

The optional `case_builder` app under `src/case_builder/` provides a small
LangGraph-compatible bootstrap workflow around the existing TRCR CLI. It keeps
the TRCR case ledger canonical, stops at a human review gate, and can be traced
with LangSmith when `LANGSMITH_TRACING=true`.

```bash
PYTHONPATH=src python -m case_builder.cli plan data/cases/example_case \
  --title "Example Case" \
  --subject "Jane Doe missing person last seen near Riverside Park map"
```

Install the package and optional orchestration dependencies with:

```bash
pip install -e '.[agentic]'
```

After installation, the same command is available as:

```bash
trcr-case-builder plan data/cases/example_case \
  --title "Example Case" \
  --subject "Jane Doe missing person last seen near Riverside Park map"
```

Each `src/case_builder` package directory has a local `README.md`; tests enforce
the 200 non-comment LOC ceiling for Python modules. See
`docs/case-builder-langgraph.md` for the workflow boundary and next nodes.

## Local document, retrieval, and memory stack

The case-builder app also exposes optional local-first commands for source
discovery, document parsing, OCR, evidence retrieval, and workflow memory. The
TRCR JSONL ledger remains canonical; these commands create parse artifacts,
candidate reports, local indexes, or workflow memories that can be rebuilt.

Install only the pieces you need:

```bash
pip install -e '.[web-local]'
pip install -e '.[documents]'
pip install -e '.[retrieval]'
pip install -e '.[memory-local]'
```

Recommended local services:

- SearXNG for source discovery at `http://localhost:8080`.
- Qdrant for evidence and memory vectors at `http://localhost:6333`.
- Ollama or another local LLM provider for Mem0 OSS.
- Tesseract/Ghostscript system packages for OCRmyPDF.

Useful commands:

```bash
trcr-case-builder discover-sources data/cases/<case_slug> --query "<case source query>"
trcr-case-builder parse-source data/cases/<case_slug> <SOURCE_ID>
trcr-case-builder ocr-source data/cases/<case_slug> <SOURCE_ID>
trcr-case-builder index-case data/cases/<case_slug>
trcr-case-builder query-case data/cases/<case_slug> "Which claims lack source spans?"
trcr-case-builder remember-research-actions data/cases/<case_slug> --provider local
trcr-case-builder remember-research-actions data/cases/<case_slug> --provider mem0
```

Workflow memory is operational context only. Do not treat Mem0 or local memory
rows as evidence; source-backed facts still need `source_ids`, optional
`source_span_ids`, staged extraction, validation, and public-output review.

## Core case-folder layout

```text
data/cases/<case_slug>/
  case.json
  raw/
    downloads/      # raw HTML or original downloaded files
    sources/        # extracted text files
  records/
    sources.jsonl
    entities.jsonl
    places.jsonl
    artifacts.jsonl
    claims.jsonl
    events.jsonl
    event_links.jsonl
    relationships.jsonl
    quotes.jsonl
    research_actions.jsonl
    redactions.jsonl
  staging/
    extractions/    # source extraction packets for Codex/LLM review
    candidates/     # entity suggestions and unresolved items
  exports/
    evidence_board.md
    manim/
      sources.csv
      people.csv
      events.csv
      event_links.csv
      relationships.csv
      claims.csv
      places.csv
```

This layout is intentionally ignored in Git. The tracked placeholder is
`data/cases/.gitkeep`; the safe demonstration fixture lives in `data/examples/synthetic_case/`.

## Key conventions

- `research_actions.jsonl` is an audit log for workflow steps such as source intake, extraction import, source-independence review, and public-export review.
- Use `records/source_spans.jsonl` plus `source_span_ids` on claims, events, relationships, event links, quotes, or artifacts when page, paragraph, timestamp, line, section, or URL-fragment locators are needed.
- Use `assertion_type` to preserve how a source frames an assertion: `source_stated_fact`, `allegation`, `denial`, `court_finding`, `self_report`, `biography_claim`, `lead_only`, or `expert_context`.
- Use `independence_group` on sources to avoid treating repeated wire stories, copied articles, shared dockets, or common archive packets as independent corroboration.
- Use `references/controlled_vocabularies.md` and `references/topic_extraction_templates.md` from the skill directory before creating new terms.
- Use JSON Schemas from `docs/schemas/` when validating machine-facing records.
- Before public output, run `validate`, review `public_export` and `privacy_review`, and use `audit-public-export` when available. `report` and `export-analysis-charts` provide the fallback public-readiness review surface.

See `docs/skill-api-spec.md` for the machine-facing CLI and JSONL contract.

## Key principle

Every video-ready sentence should reduce to:

```text
Claim → source(s) → reliability grade → confidence → privacy review → visualization output
```

If that chain breaks, the claim stays out of the public script.
