# TRCR Case Mapping For Educational Paths

Use existing TRCR ledgers. Keep original education-source details in `notes` when no dedicated field exists.

## Entities

Create `entities` for:

- Target individual: `entity_type: person`; `role_tags`: `subject`, `student`, `alumnus`, `graduate`, `faculty`, `researcher`, `trainee`, `credential_holder` as supported.
- Schools, universities, seminaries, academies, training programs, labs, departments, professional boards: `entity_type: institution` or `organization`.
- Student organizations, academic societies, clubs, fraternities/sororities, research groups: `entity_type: group` only when source-supported and relevant.
- Publications, theses, dissertations, CVs, court exhibits, yearbook pages: usually `artifacts`, not entities, unless the document itself becomes a node in the story.

Privacy defaults:

- Living private persons in school contexts are `private_person` by default.
- Minors are `minor` and `public_export: false` unless already central to widely reported public records and essential to the public-interest purpose.
- Public officials, executives, public religious leaders, expert witnesses, authors, and professors may be `limited_purpose_public` or `public_figure` only for their public-role education facts.

## Sources

Use `sources.jsonl` for each biography, filing, archive page, institutional page, court record, licensing record, article, CV, or catalog page.

Important source notes:

- Institution, page title, archive URL, access date, publication date, class year, program, page/volume, filing/exhibit number, docket number, or licensing-board profile ID.
- Whether the source is official, self-published, secondary reporting, archival, or lead-only.
- Whether the source states attendance, graduation, degree, certificate, training, affiliation, or appointment.

## Claims

Create one claim per specific education assertion. Examples:

- `<Person> attended <Institution> during <period>.`
- `<Person> received <degree/certificate> from <Institution> in <year>.`
- `<Person> was listed as a faculty member at <Institution> as of <date>.`
- `<Person> claimed in <source> to have studied <subject> at <Institution>.`
- `<Source A> says <degree>; <Source B> contradicts or narrows that claim.`

Use:

- `claim_type: background` for neutral education history.
- `claim_type: timeline` for enrollment/graduation/appointment chronology.
- `claim_type: relationship` for attendance, alumni, faculty, mentor, or institutional affiliation.
- `claim_type: legal` for sworn/court/licensing-board education claims or credential discipline.
- `claim_type: other` for credential disputes that do not fit cleanly.

Status guidance:

- `verified`: official institutional/government/court/licensing source directly supports the fact and identity match is clear.
- `single_source`: one source supports the fact.
- `corroborated`: multiple independent sources align.
- `disputed`: sources conflict or a credential has been challenged/corrected.
- `unverified`: self-report, lead-only, unclear identity match, or vague wording.
- `excluded_from_public_script`: private student record, minor detail, unnecessary classmates, or sensitive school detail.

## Relationships

Use `relationships.jsonl` for links directly supported by public sources:

- `attended`
- `graduated_from`
- `received_degree_from`
- `studied_at`
- `trained_at`
- `certified_by`
- `licensed_by`
- `taught_at`
- `faculty_at`
- `researcher_at`
- `appointed_to`
- `affiliated_with`
- `member_of_student_group`
- `published_with_affiliation`
- `claimed_education_at`
- `honorary_degree_from`
- `credential_disputed_by`

Set `start_date` and `end_date` only when directly supported. If a source provides only a class year or "as of" profile date, put that in notes and avoid implying a full attendance period.

## Events

Use `events.jsonl` for dated education-path events:

- `enrollment`
- `attendance_period`
- `graduation`
- `degree_awarded`
- `certificate_awarded`
- `training_completed`
- `academic_appointment`
- `faculty_departure`
- `publication`
- `dissertation_completed`
- `license_granted`
- `license_revoked`
- `credential_dispute`
- `public_bio_published`
- `correction_or_retraction`

Attach entity IDs for the person and institution. Attach artifact IDs for key documents such as CVs, court exhibits, commencement programs, licensing records, dissertations, and archived profiles.

## Artifacts

Use `artifacts.jsonl` for material documents:

- Official biography, CV/resume, court exhibit, expert report CV, dissertation, thesis, yearbook page, commencement program, institutional profile, license record, archive page, publication bio.
- `artifact_type: document` for filings, biographies, CVs, catalogs, and programs.
- `artifact_type: publication` for dissertations, books, articles, school newspapers, and institutional reports.
- `sensitivity: medium` or `high` for documents containing private classmates, addresses, signatures, student IDs, grade/discipline details, or minor information.

## Contradictions And Currency

Record contradictions when:

- One source says "graduated" and another says only "attended."
- Degree name, institution, year, or program differs across sources.
- An institution renamed, merged, closed, or changed accreditation status.
- A biography was corrected, removed, archived, or superseded.
- A credential was suspended, revoked, expired, honorary, or only claimed.

Prefer notes like: `Source says attended, not graduated; do not upgrade without a degree-award source.`
