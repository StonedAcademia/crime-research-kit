<p align="center">
  <img src="docs/assets/trcr-banner.svg" alt="TRCR Kit banner" width="100%">
</p>

<h1 align="center">True Crime / Cult-Origin Research Kit</h1>

<p align="center">
  <strong>Turn public sources into source-traceable case files, timelines, relationship graphs, contradiction audits, and public-ready evidence boards.</strong>
</p>

<p align="center">
  <a href="#index">Index</a> |
  <a href="#quick-start">Quick start</a> |
  <a href="#what-you-can-build">What you can build</a> |
  <a href="#document-structure">Docs</a> |
  <a href="#public-interest-boundaries">Safety</a>
</p>

TRCR is a local-first research kit for public-interest, documentary-style work
around true crime, high-control groups, cult-origin networks, missing-person
leads, public records, timelines, and source provenance. It helps an agent or
researcher move from a pile of articles, transcripts, PDFs, and archive links
into a structured case ledger where every claim can point back to sources,
reliability grades, confidence/status, privacy review, and export decisions.

This is not a rumor engine. AI can help organize, search, OCR, index, and draft
extraction packets, but **AI-generated summaries are never evidence**. Claims
only become public-facing material after source support, validation,
contradiction review, source-independence review, and privacy review.

## Index

| Need | Start here |
| --- | --- |
| Install the kit or troubleshoot setup | [Initial App Install](docs/runbook/install.md) |
| Walk through a source-backed case workflow | [Case Workflow](docs/runbook/case-workflow.md) |
| Operate the self-hosted local stack | [Self-Hosted Deployment](docs/runbook/self-hosted-deployment.md) |
| Check public-output blockers | [Public Output Readiness](docs/runbook/public-output-readiness.md) |
| Generate evidence boards, Manim CSVs, charts, timelines, or bundles | [Export Artifacts](docs/runbook/export-artifacts.md) |
| Integrate the MCP server | [MCP Server](docs/mcp-server.md) |
| Understand the LangGraph case-builder boundary | [Case Builder LangGraph](docs/case-builder-langgraph.md) |
| Build against the machine-facing contract | [Skill API Spec](docs/skill-api-spec.md) |

## Document Structure

| Path | Purpose |
| --- | --- |
| `README.md` | Project orientation, safety boundary, capability summary, and links. |
| `docs/runbook/` | Operator procedures and repeatable workflows. Long command sequences belong here. |
| `docs/schemas/` | JSON Schemas for case-ledger records. |
| `docs/lanes.json` | Canonical lane and extraction-template vocabulary. |
| `docs/superpowers/` | Planning/spec history for larger implementation phases. |
| `.agents/skills/` | Repo-local skills and reusable workflow instructions. |
| `src/case_builder/` | Optional case-builder app, LangGraph runner, MCP surface, retrieval, memory, and ops wrappers. |
| `deployment/` | Self-hosted stack, deployment scripts, and local-service configuration. |
| `data/examples/` | Tracked synthetic fixtures. Generated case work belongs in ignored `data/cases/`. |

Keep the README focused on orientation. Move install matrices, deployment
operations, full case walkthroughs, export manifests, public-readiness
checklists, troubleshooting tables, and local-service command sequences into
runbooks.

## What You Can Build

| Goal | TRCR output |
| --- | --- |
| Source ledger | `records/sources.jsonl` with URL/path, source type, reliability grade, hashes, archive context, and public/private flags. |
| Claim matrix | One assertion per row in `records/claims.jsonl`, tied to source IDs, confidence, status, contradictions, and privacy review. |
| Timeline | Events with date precision, source support, related entities, and Manim-ready CSV export. |
| Relationship graph | Source-stated entity relationships and event links without inferring guilt, membership, motive, or hidden control from proximity. |
| Contradiction audit | Reports for corrections, denials, retractions, court findings, disputed dates, and unsupported public claims. |
| Source independence review | Detection of repeated wire copy, press-release reuse, shared publishers, and same-source chains. |
| Privacy audit | Redaction blockers for living private people, minors, addresses, contact info, medical details, and weak allegations. |
| Local RAG/context retrieval | Optional local-first parsing, OCR, Qdrant/LlamaIndex retrieval, and workflow memory without hosted vector services. |
| Public-safe exports | Evidence boards, Manim CSVs, charts, timelines, and public-safe bundle exports. |

## Public-Interest Boundaries

TRCR is designed for lawful, public-source research. It is not designed for
harassment, doxxing, private-person targeting, vigilante investigation, or
making unsourced accusations.

Core guardrails:

- Treat every claim as unverified until it has traceable source support.
- Do not label anyone a suspect, perpetrator, accomplice, cult member, or
  person of interest unless a cited official/legal/news source uses that label.
- Do not infer guilt, motive, membership, or hidden control from proximity.
- Keep private addresses, contact details, minor-sensitive details, medical
  details, and weak allegations out of public exports.
- Search for contradictions, corrections, retractions, denials, and
  disconfirming evidence before marking claims as corroborated.

## What This Gives You

- A Codex skill at `.agents/skills/truecrime-cult-research/SKILL.md`.
- A repository-level `AGENTS.md` with persistent project rules for Codex.
- JSON schemas under `docs/schemas/` for sources, entities, claims, events,
  event links, relationships, places, artifacts, quotes, source spans, and
  redactions.
- A Python CLI for creating case folders, ingesting URLs, staging extraction
  packets, importing structured records, validating ledgers, auditing public
  readiness, and exporting Manim-ready CSVs.
- Local-first case-builder helpers for SearXNG discovery, Docling parsing,
  OCRmyPDF OCR, LlamaIndex/Qdrant retrieval, and Mem0 OSS workflow memory.
- Templates for case briefs, source notes, extraction packets, redaction logs,
  public-record plans, source-independence reviews, and evidence boards.
- Operator runbooks under `docs/runbook/` for install, case workflow,
  self-hosted deployment, public-output readiness, and artifact exports.
- Repeatable workflows for news articles, eyewitness accounts, court/public
  records, transcripts, archives, property/location records, FOIA planning,
  contradictions, and disconfirming sources.

## Quick start

Install the development environment, then create a small sample case:

```bash
moon run trcr:install-dev
```

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

Use [Case Workflow](docs/runbook/case-workflow.md) for the full source-review
loop, [Export Artifacts](docs/runbook/export-artifacts.md) for every export
command, and [Initial App Install](docs/runbook/install.md) for manual install,
optional extras, case-builder, local retrieval, OCR, and memory setup.

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
domain-heavy packets to adjacent skills only when their lane applies.

Canonical lane/template metadata lives in `docs/lanes.json`. Generated
reference tables live in
`.agents/skills/truecrime-cult-research/references/lane_registry.md` and
`.agents/skills/public-records-router/references/routing_matrix.md`.

Adjacent skills write source-traceable entities, claims, events, relationships,
artifacts, and notes back into the same TRCR case structure.

## App And Integration References

| Surface | Reference |
| --- | --- |
| Case-builder and LangGraph workflow | [docs/case-builder-langgraph.md](docs/case-builder-langgraph.md) |
| MCP server for Codex, Claude Code, and Claude Desktop | [docs/mcp-server.md](docs/mcp-server.md) |
| Local parsing, OCR, retrieval, and memory setup | [docs/runbook/install.md](docs/runbook/install.md) |
| Self-hosted SearXNG, Qdrant, Ollama, OCR, MCP, and app runtime | [docs/runbook/self-hosted-deployment.md](docs/runbook/self-hosted-deployment.md) |
| Case workspace layout and full source workflow | [docs/runbook/case-workflow.md](docs/runbook/case-workflow.md) |

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

Every public-facing claim should reduce to:

```text
Claim → source(s) → reliability grade → confidence → privacy review → visualization output
```

If that chain breaks, the claim stays out of the public script.
