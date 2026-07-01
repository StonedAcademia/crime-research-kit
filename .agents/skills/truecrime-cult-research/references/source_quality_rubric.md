# Source quality rubric

## Grades

### A — Primary / official / contemporaneous

Examples:

- Court filings or judgments.
- Official reports.
- Original transcripts/audio/video with provenance.
- Archived letters/documents created at the time.
- Public records from the agency or institution that produced them.

Use caution: official does not always mean complete or unbiased.

### B — Strong secondary

Examples:

- Major investigative reporting with named sources/documents.
- Reputable local reporting with direct quotations and dates.
- Scholarly or expert work used for background/context.
- Books or documentaries with clear sourcing.

### C — Testimonial / interpretive

Examples:

- Eyewitness interview.
- Former member memoir.
- Documentary narration.
- Single-source article.

Eyewitness accounts can be important, but treat them as claims unless corroborated.

### D — Weak / lead-only

Examples:

- Forum posts.
- Unsourced blogs.
- Social media threads.
- Wiki pages.
- Repeated internet claims with no original source.

Use only to discover better sources.

### X — Exclude as evidence

Examples:

- AI-generated summaries.
- Fabricated or unverifiable content.
- Doxxing dumps.
- Unlawfully obtained private data.
- Content that lacks provenance and cannot be checked.

## Source independence

Two articles are not independent if one repeats the other. Check whether:

- They cite the same wire story.
- They quote the same press release.
- They use identical wording.
- One article clearly summarizes another.

Use `independence_group` on source records to mark shared provenance, such as
the same publisher, wire service, court docket, archival packet, author, press
release, or syndication chain. The tooling uses `independence_group` first,
then publisher, URL host, and source ID as fallbacks for independent-source
counts.

Do not mark a claim `corroborated` only because the same source was repeated in
several outlets. Use `export-analysis-charts` source-quality and corroboration
outputs, when available, to spot claims that still depend on a single
independence group.

## Eyewitness account fields

Record:

- Account type: firsthand, secondhand, unclear.
- Speaker identity status: named, anonymous, pseudonymous, redacted.
- Time gap: event date vs statement date.
- Corroboration status.
- Possible interest/bias if directly relevant and source-supported.
- Whether the account names living private people.
