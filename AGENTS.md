# Repository instructions for Codex

## Project purpose

This repository supports public-interest, documentary-style research into true crime and the origins of high-control groups/cults using structured evidence, source provenance, timelines, relationship graphs, and Manim-ready visualization exports.

## Core rules

- Treat every claim as unverified until it has at least one traceable source in `records/sources.jsonl`.
- Do not infer guilt, criminal responsibility, cult membership, motive, or intent from proximity alone.
- Do not label someone a suspect, perpetrator, cult member, accomplice, or person of interest unless a cited official/legal/news source uses that label. Prefer neutral labels like `person_mentioned`, `witness`, `former_member`, `leader`, `researcher`, `journalist`, `official`, or `relative`.
- Redact private-person details by default: home addresses, private phone/email, precise workplaces, school details, family-member identities, financial identifiers, medical details, and information about minors.
- Keep living private people out of public exports unless the public interest is clear and source support is strong.
- Separate firsthand eyewitness accounts, secondhand accounts, and commentary. Do not collapse them into a single “fact.”
- Search for contradictions, retractions, corrections, and disconfirming evidence before marking a claim as corroborated.
- Never use AI-generated summaries as evidence. AI may help extract or organize, but the cited source must be human-authored or an original record.
- When uncertainty remains, preserve it in `status`, `confidence`, and `notes` rather than smoothing it away.

## Build and validation

Run these after modifying scripts or schemas:

```bash
python -m compileall src .agents/skills/truecrime-cult-research/scripts
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate data/examples/synthetic_case
```

Optional when dev dependencies are installed:

```bash
pytest
```

## Branch workflow

- Check `git status --short --branch` before starting work and again before staging, committing, pushing, or switching branches.
- Most implementation work should happen on `dev` or a focused sub-branch, not directly on `main`.
- Use typed sub-branches such as `feat/*`, `fix/*`, `docs/*`, `gov/*`, `test/*`, `chore/*`, or `ci/*` for scoped work that can be reviewed, tested, and merged cleanly.
- Use `canary` and `hotfix/*` for stabilization work: tidy-up, release polish, gate fixes, small regressions, and last-mile corrections.
- Reserve `main` for primary deployments, release integration, and mainline maintenance work.
- For multi-file or long-running work, stage and commit frequently in cohesive slices after the relevant checks pass. Prefer several reviewable commits over one broad mixed snapshot.
- Stage paths explicitly for the intended change. Do not sweep unrelated dirty files into a commit, and do not revert user or generated work you did not create.
- Keep branch hygiene tight: branch before substantial edits, keep commit messages specific, and run the applicable branch gate before pushing or merging.
- Explicit user direction can override this workflow, but note the branch choice and keep the commit scope clear.

## Directory routing

- Skill instructions live in `.agents/skills/truecrime-cult-research/SKILL.md`.
- Case-builder app code lives in `src/`; keep each Python module under 200 non-comment LOC and keep a `README.md` in each Python-bearing directory.
- Source and entity schemas live in `docs/schemas/`, grouped by ledger domain.
- Name directories and files by the workflow, contract, or domain they serve. Do not use vague buckets such as `misc`, `stuff`, `old`, or catch-all holding areas to satisfy governance.
- Before and after moving files in a target directory, run the repository governance check for the affected paths with `pytest tests/governance/test_repository_shape.py -q` and inspect the reported file/dir counts.
- Case workspaces live in `data/cases/`, which is ignored except for `data/cases/.gitkeep`.
- Staged extraction JSON goes in `data/cases/<case>/staging/extractions/`.
- Public-safe exports go in `data/cases/<case>/exports/`; cross-case generated exports go in `data/exports/`. Both are local/generated artifacts.

## Definition of done for research tasks

A research task is not complete until:

1. The source list includes URLs/paths, publication metadata, source type, and reliability grade.
2. Entities, events, event links, places, claims, relationships, and quotes have stable IDs.
3. Each claim has source IDs and a confidence/status value.
4. Contradictions or missing evidence are explicitly listed.
5. Privacy review is complete before public exports.
6. Manim CSVs or an evidence-board Markdown file are exported if requested.
