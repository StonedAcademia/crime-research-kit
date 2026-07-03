"""Public operation catalog metadata for the SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class SafetyTier(str, Enum):
    """Safety tier assigned to SDK operation specifications."""

    READ = "read"
    STAGED_WRITE = "staged_write"
    CANONICAL_GATED = "canonical_gated"
    PUBLIC_EXPORT = "public_export"
    INTERNAL_SERVICE = "internal_service"


@dataclass(frozen=True, slots=True)
class OperationSpec:
    """Public metadata for an SDK operation."""

    name: str
    domain: str
    safety_tier: SafetyTier
    request_model: str
    result_model: str = "OperationResult"
    summary: str = ""
    requires_case: bool = True
    side_effects: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    cli_command: str | None = None
    cli_aliases: tuple[str, ...] = field(default_factory=tuple)
    mcp_tool: str | None = None
    skill_api_name: str | None = None
    http_route: str | None = None
    optional_extra: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "safety_tier", SafetyTier(self.safety_tier))
        object.__setattr__(self, "side_effects", tuple(self.side_effects))
        object.__setattr__(self, "tags", tuple(self.tags))
        object.__setattr__(self, "cli_aliases", tuple(self.cli_aliases))

    @classmethod
    def from_tags(
        cls,
        name: str,
        *,
        domain: str = "",
        safety_tier: SafetyTier = SafetyTier.READ,
        request_model: str = "OperationRequest",
        summary: str = "",
        requires_case: bool = True,
        tags: Iterable[str] = (),
    ) -> "OperationSpec":
        """Build an operation spec from any iterable of tags."""
        return cls(
            name=name,
            domain=domain,
            safety_tier=safety_tier,
            request_model=request_model,
            summary=summary,
            requires_case=requires_case,
            tags=tuple(tags),
        )


_T = SafetyTier
_ROWS = (
    ("cases.create", "cases", _T.STAGED_WRITE, "CreateCaseRequest", "case workspace|record files", "crk-ledger init-case", "", "initCase", "POST /v1/cases", "", ""),
    ("cases.list", "cases", _T.READ, "ListCasesRequest", "", "", "list_cases", "", "", "", ""),
    ("case.info", "cases", _T.READ, "CaseInfoRequest", "", "", "case_info", "", "", "", ""),
    ("records.list", "records", _T.READ, "ListRecordsRequest", "", "", "get_records", "", "", "", ""),
    ("records.source_text", "records", _T.READ, "SourceTextRequest", "", "", "get_source_text", "", "", "", ""),
    ("reports.evidence_board", "reports", _T.PUBLIC_EXPORT, "EvidenceBoardRequest", "exports/evidence_board.md", "crk-ledger report", "run_report", "reportCase", "POST /v1/cases/{case_slug}:report", "", ""),
    ("sources.add", "sources", _T.STAGED_WRITE, "AddSourceRequest", "records/sources.jsonl", "crk-ledger add-source", "add_source", "addSource", "POST /v1/cases/{case_slug}/sources", "", ""),
    ("sources.ingest_url", "sources", _T.STAGED_WRITE, "IngestUrlRequest", "raw source text|records/sources.jsonl", "crk-ledger ingest-url", "ingest_url", "ingestUrl", "POST /v1/cases/{case_slug}/sources:ingest-url", "", ""),
    ("sources.discover", "sources", _T.STAGED_WRITE, "DiscoverSourcesRequest", "staging/candidates/source_leads.json", "cr-kit discover-sources", "discover_sources", "", "", "web-local", "optional"),
    ("sources.parse", "sources", _T.STAGED_WRITE, "ParseSourceRequest", "raw/sources text", "cr-kit parse-source", "parse_source", "", "", "documents", "optional"),
    ("sources.ocr", "sources", _T.STAGED_WRITE, "OcrSourceRequest", "raw/sources text", "cr-kit ocr-source", "ocr_source", "", "", "documents", "optional"),
    ("sources.preserve", "sources", _T.STAGED_WRITE, "PreserveSourceRequest", "source preservation report|source metadata", "crk-ledger preserve-source", "", "preserveSource", "", "", ""),
    ("extractions.draft", "extractions", _T.STAGED_WRITE, "DraftExtractionRequest", "staging/extractions/*.json", "crk-ledger draft-extraction", "draft_extraction", "draftExtraction", "POST /v1/cases/{case_slug}/extractions:draft", "", ""),
    ("extractions.list", "extractions", _T.READ, "ListExtractionsRequest", "", "", "list_staged_packets", "", "", "", ""),
    ("extractions.read", "extractions", _T.READ, "ReadExtractionRequest", "", "", "", "", "", "", ""),
    ("extractions.save", "extractions", _T.STAGED_WRITE, "SaveExtractionRequest", "staging/extractions/*.json", "", "save_extraction_packet", "", "", "", ""),
    ("extractions.import_reviewed", "extractions", _T.CANONICAL_GATED, "ImportReviewedExtractionRequest", "canonical JSONL records", "crk-ledger import-extraction", "import_extraction", "importExtraction", "POST /v1/cases/{case_slug}/extractions:import", "", ""),
    ("extractions.ner_suggest", "extractions", _T.STAGED_WRITE, "NerSuggestRequest", "staging/candidates/ner_suggestions.json", "crk-ledger ner-suggest", "", "nerSuggest", "POST /v1/cases/{case_slug}/candidates:ner-suggest", "", "lead_only"),
    ("names.link", "names", _T.STAGED_WRITE, "LinkNamesRequest", "private unverified links|research brief", "crk-ledger link-names", "link_names", "linkNames", "POST /v1/cases/{case_slug}/links:names", "", "lead_only"),
    ("records.plan_public_records", "records", _T.STAGED_WRITE, "PlanPublicRecordsRequest", "staging/candidates/public_records_plan.json", "crk-ledger plan-public-records", "plan_public_records", "planPublicRecords", "", "", ""),
    ("records.index_transcript", "records", _T.STAGED_WRITE, "IndexTranscriptRequest", "staging/candidates/transcript_index.json", "crk-ledger index-transcript", "", "indexTranscript", "", "", ""),
    ("records.plan_open_records", "records", _T.STAGED_WRITE, "PlanOpenRecordsRequest", "staging/candidates/open_records_plan.json", "crk-ledger plan-open-records", "", "planOpenRecords", "", "", ""),
    ("review.validate", "review", _T.READ, "ValidateCaseRequest", "", "crk-ledger validate", "", "validateCase", "POST /v1/cases/{case_slug}:validate", "", ""),
    ("review.dedupe", "review", _T.STAGED_WRITE, "DedupeRecordsRequest", "staging/candidates/dedupe_report.json", "crk-ledger dedupe", "", "dedupeRecords", "POST /v1/cases/{case_slug}:dedupe", "", ""),
    ("review.resolve_identities", "review", _T.STAGED_WRITE, "ResolveIdentitiesRequest", "staging/candidates/identity_resolution.json", "crk-ledger resolve-identities", "", "resolveIdentities", "", "", ""),
    ("review.audit_contradictions", "review", _T.STAGED_WRITE, "AuditContradictionsRequest", "exports/claim_contradiction_audit.json", "crk-ledger audit-contradictions", "", "auditContradictions", "", "", ""),
    ("review.narrative_readiness", "review", _T.STAGED_WRITE, "NarrativeReadinessRequest", "exports/narrative_readiness_review.json", "crk-ledger review-narrative-readiness", "", "reviewNarrativeReadiness", "", "", ""),
    ("review.audit_privacy_redactions", "review", _T.STAGED_WRITE, "AuditPrivacyRedactionsRequest", "exports/privacy_redaction_audit.json", "crk-ledger audit-privacy-redactions", "", "auditPrivacyRedactions", "", "", ""),
    ("review.audit_public_export", "review", _T.PUBLIC_EXPORT, "AuditPublicExportRequest", "exports/public_export_audit.json", "crk-ledger audit-public-export", "", "auditPublicExport", "POST /v1/cases/{case_slug}:audit-public-export", "", ""),
    ("review.audit_source_independence", "review", _T.STAGED_WRITE, "AuditSourceIndependenceRequest", "exports/source_independence_report.json", "crk-ledger audit-source-independence", "", "auditSourceIndependence", "POST /v1/cases/{case_slug}:audit-source-independence", "", "source-independence"),
    ("exports.manim", "exports", _T.PUBLIC_EXPORT, "ExportManimRequest", "exports/manim/*.csv", "crk-ledger export-manim", "export_manim", "exportManim", "POST /v1/cases/{case_slug}/exports:manim", "", ""),
    ("exports.timeline", "exports", _T.PUBLIC_EXPORT, "ExportTimelineRequest", "data/exports/timeline/*", "crk-ledger export-timeline", "", "exportTimeline", "POST /v1/cases:export-timeline", "", ""),
    ("exports.case_charts", "exports", _T.PUBLIC_EXPORT, "ExportCaseChartsRequest", "exports/charts/*", "crk-ledger export-case-charts", "export_case_charts", "exportCaseCharts", "POST /v1/cases/{case_slug}/exports:charts", "", ""),
    ("exports.analysis_charts", "exports", _T.PUBLIC_EXPORT, "ExportAnalysisChartsRequest", "exports/analysis_charts/*", "crk-ledger export-analysis-charts", "export_analysis_charts", "exportAnalysisCharts", "POST /v1/cases/{case_slug}/exports:analysis-charts", "", ""),
    ("exports.people_clusters", "exports", _T.PUBLIC_EXPORT, "ExportPeopleClustersRequest", "exports/clusters/*", "crk-ledger export-people-clusters", "", "exportPeopleClusters", "POST /v1/cases/{case_slug}/exports:people-clusters", "runtime:igraph+leidenalg", "optional"),
    ("workflows.plan", "workflows", _T.INTERNAL_SERVICE, "WorkflowPlanRequest", "workflow run state", "cr-kit plan", "", "", "", "agentic", "workflow"),
    ("workflows.resume", "workflows", _T.INTERNAL_SERVICE, "WorkflowResumeRequest", "workflow run state", "cr-kit resume", "", "", "", "agentic", "workflow"),
    ("retrieval.index", "retrieval", _T.INTERNAL_SERVICE, "IndexCaseRequest", "local retrieval index", "cr-kit index-case", "", "", "", "retrieval", "optional"),
    ("retrieval.query", "retrieval", _T.INTERNAL_SERVICE, "QueryCaseRequest", "", "cr-kit query-case", "query_case", "", "", "retrieval", "optional"),
    ("memory.remember_research_actions", "memory", _T.INTERNAL_SERVICE, "RememberResearchActionsRequest", "local memory store", "cr-kit remember-research-actions", "", "", "", "memory-local", "optional"),
)


def _split(value: str) -> tuple[str, ...]:
    return tuple(item for item in value.split("|") if item)


def _spec(row: tuple) -> OperationSpec:
    name, domain, tier, request, effects, cli, mcp, skill, http, extra, tags = row
    aliases = ("source-independence",) if name == "review.audit_source_independence" else ()
    return OperationSpec(
        name=name,
        domain=domain,
        safety_tier=tier,
        request_model=request,
        side_effects=_split(effects),
        tags=_split(tags),
        cli_command=cli or None,
        cli_aliases=aliases,
        mcp_tool=mcp or None,
        skill_api_name=skill or None,
        http_route=http or None,
        optional_extra=extra or None,
        requires_case=not name.startswith(("cases.list", "exports.timeline")),
    )


OPERATION_SPECS: tuple[OperationSpec, ...] = tuple(sorted((_spec(row) for row in _ROWS), key=lambda spec: spec.name))
OPERATION_BY_NAME: dict[str, OperationSpec] = {spec.name: spec for spec in OPERATION_SPECS}


def list_operations() -> tuple[OperationSpec, ...]:
    """Return the currently promoted SDK operation specifications."""
    return OPERATION_SPECS


def get_operation(name: str) -> OperationSpec:
    """Return a catalog entry by public SDK operation name."""
    return OPERATION_BY_NAME[name]


def operations_by_domain(domain: str) -> tuple[OperationSpec, ...]:
    """Return catalog entries for one operation domain."""
    return tuple(spec for spec in OPERATION_SPECS if spec.domain == domain)


__all__ = [
    "OPERATION_BY_NAME",
    "OPERATION_SPECS",
    "OperationSpec",
    "SafetyTier",
    "get_operation",
    "list_operations",
    "operations_by_domain",
]
