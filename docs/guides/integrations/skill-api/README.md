# Skill API Reference

The skill API is a local CLI plus JSONL filesystem contract. The same
operation names and payload shapes can later be wrapped by HTTP or MCP without
changing the case ledger.

## Shards

| Topic | File |
|---|---|
| Purpose, safety, data model, and generated paths | [Overview](contract/overview.md) |
| Controlled vocabularies, templates, preservation, citations, and dedupe | [Record conventions](contract/record-conventions.md) |
| Common envelope and core case/source/extraction operations | [Core operations](operations/core.md) |
| Dedupe, audit, public-records, transcript, FOIA, and readiness operations | [Review operations](operations/review-planning.md) |
| Manim, timeline, chart, analysis, and cluster exports | [Export artifacts](exports/artifacts.md) |
| Future HTTP route mapping, versioning, and open questions | [HTTP and versioning](exports/http-versioning.md) |

## Covered Skills

The primary implementation is
`crk-ledger`. Adjacent repo-local
skills extend the same case ledger for source packets and public-output review:

- `corporate-financial-records`
- `educational-path-records`
- `legal-court-records`
- `identity-resolution`
- `source-capture-preservation`
- `claim-contradiction-audit`
- `public-records-router`
- `licensing-professional-records`
- `media-transcript-intelligence`
- `property-location-records`
- `missing-persons-case`
- `geographical-location-intelligence`
- `foia-open-records-planning`
- `narrative-readiness-review`
- `privacy-redaction-audit`
- `source-independence-audit`
