# Source Capture And Preservation Lanes

Use these lanes to decide how to register, capture, and grade a source before extraction.

## Capture Sources

- Original publisher URL, official document URL, court docket URL, agency record URL, archive page, PDF, transcript, image, or local file provided by the user.
- Internet Archive or other public web archives for capture date and original URL context.
- CourtListener/RECAP, SEC EDGAR, regulator portals, institutional repositories, newspaper archives, and public document repositories.

## Preservation Metadata

Capture when available:

- Original URL and archive URL.
- Capture timestamp and accessed date.
- Content type, file extension, source type, and reliability grade.
- Raw file path, extracted text path, SHA-256 hashes, and file sizes.
- Docket item, accession number, exhibit, page, paragraph, timestamp, or locator.
- Missing artifact, OCR, transcript, paywall, archive, or provenance warnings.

## Weak Or Excluded Sources

- AI summaries, search-result snippets, forum reposts, uncited social threads, scraped mirrors without provenance, and screenshots without origin.
- Private files, leaked material, credentials, account pages, sealed records, private contact/address data, or material involving minors without public-interest justification.

## Source Grading Defaults

- `A`: official public source, original public record, court filing, official report, regulator/source archive with clear provenance.
- `B`: reputable reporting or public archive with clear origin and source metadata.
- `C`: self-published source, memoir/interview, documentary, transcript, or page needing corroboration.
- `D`: lead-only social/forum/wiki/aggregator/repost without direct evidence chain.
- `X`: AI summary, fabricated/provenance-free content, or unlawfully obtained/private material.
