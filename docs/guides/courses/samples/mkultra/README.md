# MKUltra Source-Traceable Course

This course uses MKUltra as the target case for learning CRK from a greenfield
workstation through source capture, agent operation, and public-output review.
It is intentionally controversy-heavy, so each lesson separates documented
facts, testimony, disputed claims, metadata-only leads, and unsupported
inferences.

The local course case is `data/cases/mkultra_course`. That path is ignored by
git. In the 2026-07-02 source-capture pass, reachable public PDFs and HTML
documents were downloaded into `raw/downloads/`, extracted text was written to
`raw/sources/`, and blocked direct downloads were registered as metadata-only
sources.

## Lessons

| Lesson | File |
| --- | --- |
| Greenfield Windows/WSL, Linux, and macOS install | [01-greenfield-install.md](01-greenfield-install.md) |
| Source capture, preservation, and citation workflow | [02-source-capture.md](02-source-capture.md) |
| Operate the case as a skill, MCP server, and CLI | [03-agent-workflows.md](03-agent-workflows.md) |
| Tested full-stack E2E workflow | [04-tested-full-stack-workflow.md](04-tested-full-stack-workflow.md) |
| Source manifest and citation tables | [sources/](sources/) |
| Screenshot capture plan | [assets/](assets/) |

## Subcases

| Subcase | Working Question | Primary Source Boundary |
| --- | --- | --- |
| Authorization and secrecy | What did official records say MKULTRA was authorized to do, and how was it controlled? | Senate hearing, CIA IG report, Rockefeller Commission. |
| Domestic unwitting testing | What can be supported about drug testing on unwitting U.S. citizens? | CIA IG report, Senate hearing, Rockefeller Commission. |
| Institutional research channels | Which universities, hospitals, foundations, and cutouts are source-stated? | Senate hearing and National Security Archive context, then primary records when available. |
| MKSEARCH, OFTEN, and CHICKWIT | How did later or adjacent chemical/behavioral research relate to MKULTRA? | Senate material for the record; DoD memo remains metadata-only in this pass. |
| Frank Olson | What is established by official oversight records, and what remains disputed by later sources? | Rockefeller Commission plus archive/testimony context, separated by claim status. |
| Controversy boundary cases | How should Finders, Jonestown, Manson-related testimony, Gateway, and STAR GATE be handled? | Boundary records and testimony only until exact primary support exists. |

## People And Institutions Portfolio

| Entity | Neutral Role For This Course | Citation Starter |
| --- | --- | --- |
| Allen W. Dulles | DCI who authorized MKULTRA in 1953. | `S_CIA_MKULTRA_IG_1963` lines 49-52; `S_SENATE_MKULTRA_1977` lines 3888-3889. |
| Richard Helms | CIA official tied by oversight records to the proposal and later record destruction order. | `S_SENATE_MKULTRA_1977` lines 241-247 and 3861-3868. |
| Sidney Gottlieb | TSD official named in oversight and archive records for MKULTRA administration and file destruction. | `S_SENATE_MKULTRA_1977` lines 3861-3865; `S_NSARCHIVE_MKULTRA_CONTEXT_2024` lines 101-107. |
| George Hunter White | Federal narcotics agent described by archive context as operating CIA safehouses. | `S_NSARCHIVE_MKULTRA_CONTEXT_2024` lines 101-103 and 123. |
| Dr. D. Ewen Cameron | Psychiatrist tied by archive context to Allan Memorial Institute experiments. | `S_NSARCHIVE_MKULTRA_CONTEXT_2024` lines 104-105 and 133. |
| Charles Geschickter | Georgetown-linked researcher and foundation operator described in archive context. | `S_NSARCHIVE_MKULTRA_CONTEXT_2024` lines 106-107 and 132. |
| Dr. Harris Isbell | Public Health Service Hospital researcher discussed in Senate questioning. | `S_SENATE_MKULTRA_1977` lines 1373-1379. |
| Frank Olson | Army scientist whose 1953 death is treated as an official-finding and dispute-analysis subcase. | `S_ROCKEFELLER_COMMISSION_1975` lines 2413-2422; `S_NSARCHIVE_MKULTRA_CONTEXT_2024` line 124. |
| House witnesses, 2026 | Stephen Kinzer, Tom O'Neill, and Elizabeth Ginexi as hearing witnesses, not automatic fact sources. | `S_HOUSE_OVERSIGHT_MKULTRA_2026` lines 34-53. |

## Timeline Backbone

| Date | Event Or Source-Supported Milestone | Citation Starter |
| --- | --- | --- |
| 1949-09-27 | A National Security Archive document list identifies an early CIA security validation team record. | `S_NSARCHIVE_MKULTRA_CONTEXT_2024` lines 136-140. |
| 1953-04-13 | MKULTRA was approved by the DCI. | `S_SENATE_MKULTRA_1977` lines 3888-3889. |
| 1955 | TSD initiated covert testing on unwitting U.S. citizens, according to the CIA IG report. | `S_CIA_MKULTRA_IG_1963` lines 600-611. |
| 1963-07-26 | CIA Inspector General report reviewed MKULTRA and recommended ending U.S. covert testing. | `S_CIA_MKULTRA_IG_1963` lines 17-39 and 607-611. |
| 1966-1972 | MKSEARCH funding covered a continuation of MKULTRA-related work. | `S_SENATE_MKULTRA_1977` lines 8416-8422. |
| 1967 | Rockefeller Commission reported that all CIA drug testing programs ended in 1967. | `S_ROCKEFELLER_COMMISSION_1975` lines 2413-2422. |
| 1973-01 | Senate record says MKULTRA records were destroyed at Helms' instruction. | `S_SENATE_MKULTRA_1977` lines 239-247 and 3861-3865. |
| 1975-06 | Rockefeller Commission issued oversight findings on CIA activities within the United States. | `S_ROCKEFELLER_COMMISSION_1975` lines 2408-2422. |
| 1977-08-03 | Senate committees held the MKULTRA hearing used as the course anchor. | `S_SENATE_MKULTRA_1977` source metadata. |
| 2024-12-23 | National Security Archive published a new scholarly MKULTRA document collection notice. | `S_NSARCHIVE_MKULTRA_CONTEXT_2024` lines 82-90 and 109-121. |
| 2026-06-30 | House Oversight held a hearing with Kinzer, O'Neill, and Ginexi testimony. | `S_HOUSE_OVERSIGHT_MKULTRA_2026` lines 34-53. |

## Historical Forensic Facts To Teach

- Record destruction is a source problem, not a license to fill gaps. The
  course marks missing files, survivorship bias, and metadata-only items.
- Government records can document program structure while still containing
  redactions, OCR errors, and institutional self-reporting limits.
- Testimony is extracted as speaker claims. It needs independent support before
  it becomes a higher-confidence case claim.
- FBI Vault PDFs for the Finders were captured, but the text sidecars are scan
  placeholders. OCR is required before exact-text citation.
- Jonestown is included only as a boundary example. The FBI history page
  supports Jonestown facts, not a hidden MKUltra relationship.
- Public exports must pass source support, contradiction review, independence
  review, privacy review, and public-output audit.
