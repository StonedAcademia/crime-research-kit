---
name: privacy-redaction-audit
description: Privacy and redaction workflow for TRCR cases. Use when Codex needs to detect private-person details, minors, addresses, contact information, medical details, financial identifiers, weak allegations, unsupported public claims, open redactions, and public-export blockers before sharing a case.
---

# Privacy Redaction Audit

## Operation vocabulary

Lane/template metadata is generated from `docs/registry/lanes.json`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `privacy-redaction` for this lane; CLI fallback: `tcr.py draft-extraction ... --template privacy-redaction`.


## Purpose

Use this skill before any public export, script, report, bundle, evidence board, or shared case review. It identifies privacy and redaction blockers; it does not make sensitive content safe by itself.

## Workflow

1. **Run the audit.** Use `audit-privacy-redactions` to write a JSON report.
2. **Review blockers.** Inspect private-person, minor, address/contact, weak allegation, source-support, and redaction-log issues.
3. **Draft a redaction packet.** Use `draft-extraction --template privacy-redaction` when source-backed redaction records need import.
4. **Update case records explicitly.** Mark unsafe rows `public_export: false`, set `privacy_review`, and add redaction rows in a separate deliberate edit/import.
5. **Re-run public export audit.** Use `audit-public-export` after changes.

## Commands

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-privacy-redactions tc-c-kit/data/cases/<case_slug> --warn-only
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template privacy-redaction
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export tc-c-kit/data/cases/<case_slug> --warn-only
```

## Redaction Rules

- Private-person details, minors, home addresses, phone/email, precise private locations, medical details, financial identifiers, and non-public relatives default to non-public.
- Weak allegations and unsupported private claims must not appear in public exports.
- Public records can still contain private details that require redaction.
- Prefer vague public-interest descriptions over exact private locations or identifiers.

## Output Expectations

A completed audit should leave `exports/privacy_redaction_audit.json`, redaction rows or explicit follow-up tasks, and a clear public-export decision for sensitive records.
