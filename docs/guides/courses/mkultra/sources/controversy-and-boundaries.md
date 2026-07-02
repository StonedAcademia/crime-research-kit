# Controversy And Boundary Handling

MKUltra attracts claims that mix official history, testimony, memoir,
declassified fragments, rumor, and speculation. This course keeps those lanes
visible without letting them become unsupported public claims.

## Boundary Table

| Lane | Source IDs | Allowed Course Use | Blocker Before Promotion |
| --- | --- | --- | --- |
| Frank Olson | `S_ROCKEFELLER_COMMISSION_1975`, `S_NSARCHIVE_MKULTRA_CONTEXT_2024`, `S_HOUSE_KINZER_TESTIMONY_2026` | Teach official finding, later dispute framing, and testimony separation. | Need claim-by-claim official source, family/litigation source, or deposition locator. |
| Manson / Jolly West testimony | `S_HOUSE_ONEILL_TESTIMONY_2026` | Teach how to extract witness testimony and denials as disputed claims. | Need primary records or independently corroborated reporting before any factual promotion. |
| Finders | `S_FBI_FINDERS_VAULT`, `S_FBI_FINDERS_PART_01` to `S_FBI_FINDERS_PART_04` | Teach source preservation and OCR-pending handling for FBI Vault scans. | OCR with exact locators, plus narrow claims only. |
| Jonestown | `S_FBI_JONESTOWN_HISTORY` | Teach boundary records: source supports Jonestown facts and Layton prosecution. | No MKUltra relationship claim without direct source support. |
| Gateway / STAR GATE | `S_CIA_GATEWAY_PROCESS_METADATA`, `S_CIA_STARGATE_OVERVIEW_METADATA` | Teach metadata-only capture and topic-boundary discipline. | Browser capture or archive copy plus relevance analysis. |
| DoD MKSEARCH memo | `S_DOD_MKSEARCH_1977_METADATA` | Teach blocked official source registration. | Retrieve the PDF or an archive copy before using it as evidence. |
| CIA Reading Room MKULTRA record | `S_CIA_MKULTRA_READINGROOM_METADATA` | Teach metadata-only CIA record handling. | Resolve redirect-loop capture or cite another accessible official copy. |

## Status Rules

Use these statuses in extraction packets:

| Evidence State | Claim Status |
| --- | --- |
| Exact official locator supports the point. | `source_supported` or `corroborated`, depending on independent support. |
| One strong source supports the point, no contradiction found yet. | `single_source`. |
| Witness says it, but official support is missing or contradictory. | `testimony_only` or `disputed`. |
| OCR failed or source is metadata-only. | `unverified` or `lead_only`. |
| Claim depends on proximity, co-mention, or speculation. | `excluded_from_public_script`. |

## Privacy And Defamation Guardrails

- Do not label a person as a perpetrator, cult member, handler, asset,
  accomplice, or person of interest unless the cited source uses that label.
- Do not infer hidden control from attendance, employment, testimony, a grant,
  or a shared institution.
- Keep private addresses, private contact details, medical details, minors,
  family-member identities, and weak allegations out of public exports.
- Prefer neutral roles such as `official`, `researcher`, `witness`,
  `journalist`, `institution`, `subject`, and `person_mentioned`.

## Review Prompts

Use these prompts before writing a script or public report:

```text
Audit data/cases/mkultra_course for claims that rely on testimony without
primary support. Mark each as testimony_only, disputed, lead_only, or excluded.
```

```text
Review Finders and Jonestown records as boundary records. Remove any public
claim that asserts an MKUltra relationship unless the exact source span states
that relationship.
```

```text
Run narrative-readiness, privacy-redaction, and source-independence review for
all MKUltra course subcases before exporting Manim CSVs or an evidence board.
```
