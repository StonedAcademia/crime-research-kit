"""Deterministic pipeline nodes between planning and export, over the ops core."""

from __future__ import annotations

from adapters.ops import case as case_ops
from adapters.ops import exports as export_ops
from adapters.ops import extraction as extraction_ops
from adapters.ops import query as query_ops
from adapters.ops import review as review_ops
from adapters.ops import sources as source_ops
from adapters.ops.result import OpResult
from adapters.ops.runner import CrkRunner
from pipeline.graph.nodes.base import required_case_dir
from pipeline.graph.state import GraphState


def merge_results(state: GraphState, results: list[OpResult], success_status: str) -> GraphState:
    planned = list(state.get("planned_commands") or [])
    tools = list(state.get("tool_results") or [])
    errors = list(state.get("errors") or [])
    ok = True
    for result in results:
        planned.append(result.command)
        tools.append(result.to_dict())
        errors.extend(result.errors)
        ok = ok and result.ok
    return {
        "planned_commands": planned,
        "tool_results": tools,
        "errors": errors,
        "status": success_status if ok else "error",
    }


def source_capture_node(runner: CrkRunner):
    def node(state: GraphState) -> GraphState:
        urls = state.get("source_urls") or []
        if not urls:
            return {"status": "source_capture_skipped"}
        case_dir = required_case_dir(state)
        results = [source_ops.ingest_url(runner, case_dir, url) for url in urls]
        return merge_results(state, results, "sources_captured")

    return node


def parse_or_ocr_node(runner: CrkRunner):
    def node(state: GraphState) -> GraphState:
        if runner.dry_run:
            return {"status": "parse_skipped_dry_run"}
        case_dir = required_case_dir(state)
        sources = query_ops.get_records(case_dir, "sources", include_private=True)
        if not sources.ok:
            return merge_results(state, [sources], "error")
        results: list[OpResult] = []
        extra_errors: list[str] = []
        for source in sources.data["records"]:
            if source.get("text_path") or not source.get("raw_path"):
                continue
            source_id = str(source.get("source_id"))
            try:
                if str(source["raw_path"]).lower().endswith(".pdf"):
                    results.append(source_ops.ocr_source(case_dir, source_id))
                else:
                    results.append(source_ops.parse_source(case_dir, source_id))
            except RuntimeError as exc:
                extra_errors.append(f"parse_or_ocr {source_id}: {exc}")
        merged = merge_results(state, results, "sources_parsed")
        merged["errors"] = [*merged["errors"], *extra_errors]
        return merged

    return node


def draft_packets_node(runner: CrkRunner):
    def node(state: GraphState) -> GraphState:
        case_dir = required_case_dir(state)
        source_ids = list(state.get("source_ids") or [])
        if not source_ids and not runner.dry_run:
            records = query_ops.get_records(case_dir, "sources", include_private=True)
            if records.ok:
                source_ids = [str(row["source_id"]) for row in records.data["records"] if row.get("source_id")]
        if not source_ids:
            return {"status": "draft_skipped_no_sources"}
        results = [extraction_ops.draft_extraction(runner, case_dir, source_id) for source_id in source_ids]
        merged = merge_results(state, results, "packets_drafted")
        if not runner.dry_run:
            listed = extraction_ops.list_packets(case_dir)
            if listed.ok:
                merged["packets"] = list(listed.data["packets"])
        return merged

    return node


def import_and_validate_node(runner: CrkRunner):
    def node(state: GraphState) -> GraphState:
        approved = state.get("approved_packets") or []
        if not approved:
            return {"status": "import_skipped_no_approved_packets"}
        case_dir = required_case_dir(state)
        results = [
            extraction_ops.import_extraction(
                runner,
                case_dir,
                f"{case_dir.rstrip('/')}/staging/extractions/{name}",
                confirm=True,
            )
            for name in approved
        ]
        results.append(case_ops.validate(runner, case_dir))
        return merge_results(state, results, "imported_and_validated")

    return node


def index_case_node(runner: CrkRunner):
    def node(state: GraphState) -> GraphState:
        if not state.get("index_enabled") or runner.dry_run:
            return {"status": "index_skipped"}
        case_dir = required_case_dir(state)
        try:
            result = query_ops.index_case(
                case_dir,
                qdrant_url=state.get("qdrant_url"),
                embed_model=state.get("embed_model"),
            )
        except Exception as exc:  # optional retrieval deps or Qdrant may be absent
            return {
                "status": "index_failed",
                "errors": [*(state.get("errors") or []), f"index_case: {exc}"],
            }
        return merge_results(state, [result], "case_indexed")

    return node


def readiness_audit_node(runner: CrkRunner):
    def node(state: GraphState) -> GraphState:
        case_dir = required_case_dir(state)
        results = [
            review_ops.audit_contradictions(runner, case_dir),
            review_ops.review_narrative_readiness(runner, case_dir),
            review_ops.audit_privacy_redactions(runner, case_dir),
            review_ops.audit_source_independence(runner, case_dir),
        ]
        return merge_results(state, results, "readiness_audited")

    return node


def export_bundle_node(runner: CrkRunner):
    def node(state: GraphState) -> GraphState:
        case_dir = required_case_dir(state)
        results = [export_ops.export_manim(runner, case_dir), case_ops.report(runner, case_dir)]
        merged = merge_results(state, results, "bundle_exported")
        merged["review_required"] = False
        return merged

    return node
