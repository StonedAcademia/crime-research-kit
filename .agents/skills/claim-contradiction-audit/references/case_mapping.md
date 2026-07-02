# CRK Case Mapping For Claim Contradiction Audits

Use existing CRK ledgers. Do not rewrite claim status unless the source-backed basis is clear and cited.

## Reports

Run `audit-contradictions` to write `exports/claim_contradiction_audit.json`. Treat this as a review artifact. It does not change claims.

## Claims

Use fields consistently:

- `contradicts`: claim IDs directly contradicted by this claim or source.
- `supports`: claim IDs directly supported or narrowed by this claim.
- `assertion_type`: `allegation`, `denial`, `court_finding`, `source_stated_fact`, `lead_only`, or other controlled value.
- `status`: keep `disputed`, `unverified`, `single_source`, or `false_or_retracted` only when the source basis supports it.
- `source_span_ids`: precise anchors for the contradiction, correction, retraction, or finding.

## Events

Use events for dated contradiction milestones:

- `claim_disputed`
- `claim_corrected`
- `claim_retracted`
- `claim_denied`
- `court_finding_entered`
- `correction_published`
- `retraction_published`

## Relationships And Event Links

Avoid relationship rows unless a source directly ties an entity to another entity or event. For claim-to-claim review, prefer `claims[].contradicts`, `claims[].supports`, and notes.

## Redactions

Add redaction records when contradiction sources include private-person details, minors, addresses, contact details, medical details, financial identifiers, weak allegations, or unsupported private claims.

## Public Output

Public exports may mention disputed claims only when the evidence chain is clear and the dispute is represented accurately. Keep unresolved or weak private allegations out of public scripts.
