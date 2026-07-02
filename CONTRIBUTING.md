# Contributing to Crime Research Kit

Crime Research Kit is built for public-interest, source-backed research. Every
contribution should make the project safer, clearer, easier to operate, or more
reliable without weakening the evidence and privacy model.

## Safety Contract

- Treat every claim as unverified until it has traceable source support.
- Do not infer guilt, motive, cult membership, or hidden control from proximity
  or co-mention.
- Keep private-person details, minors, addresses, contact details, medical
  information, and weak allegations out of public exports by default.
- Never use AI-generated summaries as evidence. AI may organize or extract, but
  the cited evidence must be a human-authored source or original record.
- Preserve uncertainty in `status`, `confidence`, and notes instead of smoothing
  disputed facts into certainty.

## Development Workflow

- Start from `dev` or a focused typed branch such as `docs/*`, `feat/*`,
  `fix/*`, `gov/*`, `test/*`, `chore/*`, or `ci/*`.
- Check `git status --short --branch` before work, before staging, and before
  committing.
- Keep commits small and reviewable. Stage paths explicitly and do not sweep in
  unrelated dirty files.
- Prefer Moon tasks for repeatable local work:

```bash
moon run crk:check
moon run crk:test-governance
moon run crk:test
```

- For targeted pytest runs, use the uv-backed editable environment:

```bash
uv run --cache-dir .uv-cache --no-project --with-editable '.[dev]' -- python -m pytest <path>
```

## Pull Request Checklist

- Contributions are submitted under the repository license,
  AGPL-3.0-only.
- The PR explains the user-facing or operator-facing reason for the change.
- Safety-sensitive behavior keeps claims source-backed and privacy-reviewed.
- Docs, schemas, examples, and runbooks are updated when behavior or commands
  change.
- The PR description lists the validation commands that passed.
- Generated or local files stay untracked: `.uv-cache/`, `.venv/`, `*.egg-info/`,
  `data/cases/`, `data/exports/`, and `dist/`.
- New dependencies are optional unless the core package contract intentionally
  changes.

## Agent Standards

Agents working in this repository must follow `AGENTS.md` in addition to this
guide.

- Read the relevant code, docs, schemas, and task definitions before editing.
- Prefer existing repo patterns over new abstractions.
- Preserve unrelated user or generated work; never revert changes you did not
  make unless explicitly asked.
- Stage only the intended files and verify the staged set before committing.
- Run the narrowest meaningful validation first, then broader gates when the
  change touches shared behavior, docs governance, packaging, or CI.
- For research data or public outputs, list contradictions, missing evidence,
  privacy blockers, and source-chain caveats instead of making unsupported
  narrative claims.

## Review Expectations

Reviewers should prioritize correctness, safety regressions, evidence
provenance, privacy risk, broken workflows, and missing tests. Style and
formatting feedback should be tied to maintainability, readability, or the
public operator experience.
