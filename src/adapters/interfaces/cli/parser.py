"""Ledger CLI parser."""

from __future__ import annotations

import argparse

from adapters.ops.casework.records import extractions, validation, workspace
from adapters.ops.casework.records.intake import suggestions, web
from adapters.ops.casework.records.names import command as names_command
from adapters.ops.casework.records.planning import open_records, public_records, transcripts
from adapters.ops.evidence.quality import contradictions, dedupe, identity, preservation
from adapters.ops.evidence.quality.safety import privacy, public_export, readiness, source_independence
from adapters.ops.evidence.reports import case_outputs, timeline
from adapters.ops.evidence.reports.analysis.command import entry as analysis_charts
from adapters.ops.evidence.reports.case_charts import command as case_charts
from adapters.ops.evidence.reports.clusters import command as clusters


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="True Crime / Cult-Origin Research CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init-case", help="Create a case workspace")
    p.add_argument("case_dir")
    p.add_argument("--title", default=None)
    p.add_argument("--scope", default=None)
    p.add_argument("--public-interest", default=None)
    p.set_defaults(func=workspace.init_case)

    p = sub.add_parser("add-source", help="Register a source manually")
    p.add_argument("case_dir")
    p.add_argument("--title", required=True)
    p.add_argument("--url", default=None)
    p.add_argument("--source-type", default="news_article")
    p.add_argument("--reliability-grade", default="C", choices=["A", "B", "C", "D", "X"])
    p.add_argument("--author", default=None)
    p.add_argument("--publisher", default=None)
    p.add_argument("--date-published", default=None)
    p.add_argument("--archive-url", default=None)
    p.add_argument("--notes", default="")
    p.add_argument("--no-public-export", action="store_true")
    p.set_defaults(func=workspace.add_source)

    p = sub.add_parser("ingest-url", help="Fetch URL, extract text, and register as a source")
    p.add_argument("case_dir")
    p.add_argument("url")
    p.add_argument("--title", default=None)
    p.add_argument("--source-type", default="news_article")
    p.add_argument("--reliability-grade", default="C", choices=["A", "B", "C", "D", "X"])
    p.add_argument("--author", default=None)
    p.add_argument("--publisher", default=None)
    p.add_argument("--date-published", default=None)
    p.add_argument("--archive-url", default=None)
    p.add_argument("--notes", default="")
    p.add_argument("--timeout", type=int, default=25)
    p.add_argument("--no-public-export", action="store_true")
    p.set_defaults(func=web.ingest_url)

    p = sub.add_parser("draft-extraction", help="Create a structured extraction JSON packet for a source")
    p.add_argument("case_dir")
    p.add_argument("source_id")
    p.add_argument("--excerpt-chars", type=int, default=6000)
    p.add_argument(
        "--template",
        choices=sorted(extractions.EXTRACTION_TEMPLATE_FILES),
        default="generic",
        help="Extraction packet template.",
    )
    p.set_defaults(func=extractions.draft_extraction)

    p = sub.add_parser("ner-suggest", help="Generate crude named-entity/date suggestions from source text")
    p.add_argument("case_dir")
    p.add_argument("--source-id", default=None)
    p.add_argument("--limit", type=int, default=80)
    p.set_defaults(func=suggestions.ner_suggest)

    p = sub.add_parser("link-names", help="Link a list of names to existing events and co-mentions")
    p.add_argument("case_dir")
    p.add_argument("--name", action="append", default=[], help="Name to link. Use 'Primary|Alias|Alias' for aliases.")
    p.add_argument("--names-file", action="append", default=[], help="File with one name per line. Aliases use '|'.")
    p.set_defaults(func=names_command.link_names)

    p = sub.add_parser("import-extraction", help="Import a filled extraction JSON packet into JSONL records")
    p.add_argument("case_dir")
    p.add_argument("extraction_json")
    p.set_defaults(func=extractions.import_extraction)

    p = sub.add_parser("validate", help="Validate case records")
    p.add_argument("case_dir")
    p.set_defaults(func=validation.validate)

    p = sub.add_parser("dedupe", help="Report duplicate candidate entities, sources, or claims")
    p.add_argument("case_dir")
    p.add_argument("--record-type", choices=["all", "entities", "sources", "claims"], default="all")
    p.add_argument("--min-key-chars", type=int, default=12, help="Minimum normalized key length for candidate matching.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/dedupe_report_<date>.json.")
    p.set_defaults(func=dedupe.dedupe)

    p = sub.add_parser("preserve-source", help="Hash and report preservation metadata for an existing source")
    p.add_argument("case_dir")
    p.add_argument("source_id")
    p.add_argument("--archive-url", default=None, help="Archive URL to store on the source before preservation reporting.")
    p.add_argument("--content-type", default=None, help="Content type to store on the source before preservation reporting.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/source_preservation/<source_id>.json.")
    p.set_defaults(func=preservation.preserve_source)

    p = sub.add_parser("resolve-identities", help="Report candidate duplicate or ambiguous identity records without merging")
    p.add_argument("case_dir")
    p.add_argument("--min-key-chars", type=int, default=8, help="Minimum normalized name/alias length for identity candidate matching.")
    p.add_argument("--include-merged", action="store_true", help="Include entity rows already marked status=merged.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/identity_resolution_<date>.json.")
    p.set_defaults(func=identity.resolve_identities)

    p = sub.add_parser("audit-contradictions", help="Report explicit and likely claim contradictions without mutating claims")
    p.add_argument("case_dir")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/claim_contradiction_audit.json.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in contradiction checks.")
    p.add_argument("--min-overlap", type=float, default=0.45, help="Minimum token overlap for likely contradiction pair checks.")
    p.add_argument("--fail-on-flags", action="store_true", help="Exit nonzero when any contradiction flag is found.")
    p.set_defaults(func=contradictions.audit_contradictions)

    p = sub.add_parser("plan-public-records", help="Write a public-record source-lane plan for a subject")
    p.add_argument("case_dir")
    p.add_argument("--subject", required=True, help="Person, organization, place, event, or question subject to route.")
    p.add_argument("--question", default="", help="Optional research question or scope note.")
    p.add_argument("--lane", action="append", choices=sorted(public_records.PUBLIC_RECORD_LANES), default=[], help="Force one or more source lanes instead of keyword inference.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/public_records_plan_<subject>_<date>.json.")
    p.set_defaults(func=public_records.plan_public_records)

    p = sub.add_parser("index-transcript", help="Index timestamp and speaker-line candidates from a source text transcript")
    p.add_argument("case_dir")
    p.add_argument("source_id")
    p.add_argument("--max-segments", type=int, default=200, help="Maximum transcript segments to include in the candidate report.")
    p.add_argument("--include-private", action="store_true", help="Include a source marked public_export=false for internal review.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/transcript_index_<source_id>_<date>.json.")
    p.set_defaults(func=transcripts.index_transcript)

    p = sub.add_parser("plan-open-records", help="Write a FOIA/open-records request plan for an agency and subject")
    p.add_argument("case_dir")
    p.add_argument("--subject", required=True, help="Subject of the request.")
    p.add_argument("--agency", required=True, help="Agency or public body receiving the request.")
    p.add_argument("--jurisdiction", default=None, help="Jurisdiction or office scope to include in the plan.")
    p.add_argument("--law", default=None, help="FOIA, sunshine, or open-records law to cite once confirmed.")
    p.add_argument("--date-range", default=None, help="Date range or temporal scope for responsive records.")
    p.add_argument("--record", action="append", default=[], help="Requested record category. Repeat for multiple categories.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/open_records_plan_<subject>_<date>.json.")
    p.set_defaults(func=open_records.plan_open_records)

    p = sub.add_parser("review-narrative-readiness", help="Report public narrative readiness gaps across claims, events, and relationships")
    p.add_argument("case_dir")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in readiness checks.")
    p.add_argument("--require-spans", action="store_true", help="Flag claims/events without source_span_ids.")
    p.add_argument("--min-independent-sources", type=int, default=2, help="Independent source count expected for corroborated claims and allegations.")
    p.add_argument("--fail-on-blockers", action="store_true", help="Exit nonzero when blocker issues are found.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/narrative_readiness_review.json.")
    p.set_defaults(func=readiness.review_narrative_readiness)

    p = sub.add_parser("audit-privacy-redactions", help="Report privacy and redaction issues before public output")
    p.add_argument("case_dir")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in the scan.")
    p.add_argument("--require-redaction-log", action="store_true", help="Warn when no redaction records exist.")
    p.add_argument("--warn-only", action="store_true", help="Write the report but do not exit nonzero on issues.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/privacy_redaction_audit.json.")
    p.set_defaults(func=privacy.audit_privacy_redactions)

    p = sub.add_parser("audit-public-export", help="Fail if public exports include unsafe or unsupported records")
    p.add_argument("case_dir")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/public_export_audit.json.")
    p.add_argument("--warn-only", action="store_true", help="Write the report but do not exit nonzero on issues.")
    p.set_defaults(func=public_export.audit_public_export)

    p = sub.add_parser("audit-source-independence", aliases=["source-independence"], help="Report source-chain, wire-copy, and press-release independence risks")
    p.add_argument("case_dir")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/source_independence_report.json.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in record support checks.")
    p.add_argument("--min-title-chars", type=int, default=16, help="Minimum normalized title length for repeated-copy checks.")
    p.add_argument("--fail-on-flags", action="store_true", help="Exit nonzero when any source-independence flag is found.")
    p.set_defaults(func=source_independence.source_independence)

    p = sub.add_parser("export-manim", help="Export public-safe Manim-ready CSVs")
    p.add_argument("case_dir")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private analysis only.")
    p.set_defaults(func=case_outputs.export_manim)

    p = sub.add_parser("export-timeline", help="Export cross-case timeline and claim corroboration CSVs")
    p.add_argument("cases_root", help="A cases directory or a single case workspace")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to <kit>/data/exports/timeline for a cases root.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.set_defaults(func=timeline.export_timeline)

    p = sub.add_parser("export-case-charts", help="Export people-only graph and subcase timeline chart artifacts")
    p.add_argument("case_dir")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to data/cases/<case>/exports/charts.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.set_defaults(func=case_charts.export_case_charts)

    p = sub.add_parser("export-analysis-charts", help="Export extended analysis chart CSVs and dashboard")
    p.add_argument("case_dir")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to data/cases/<case>/exports/analysis_charts.")
    p.add_argument("--clusters-dir", default=None, help="Cluster CSV directory. Defaults to data/cases/<case>/exports/clusters.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.set_defaults(func=analysis_charts.export_analysis_charts)

    p = sub.add_parser("export-people-clusters", help="Run evidence-weighted Leiden clustering and graph-kernel/KDE analysis on people graph")
    p.add_argument("case_dir")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to data/cases/<case>/exports/clusters.")
    p.add_argument("--charts-dir", default=None, help="People chart input/output directory. Defaults to data/cases/<case>/exports/charts.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.add_argument("--resolution", type=float, default=1.0, help="Leiden resolution parameter.")
    p.add_argument("--seed", type=int, default=7, help="Leiden random seed.")
    p.add_argument("--sigma", type=float, default=None, help="Kernel bandwidth. Defaults to median finite graph distance.")
    p.set_defaults(func=clusters.export_people_clusters)

    p = sub.add_parser("report", help="Write Markdown evidence board")
    p.add_argument("case_dir")
    p.set_defaults(func=case_outputs.report)

    return parser
