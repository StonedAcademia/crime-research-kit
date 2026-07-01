"""Deterministic pipeline nodes between planning and export, over the ops core."""

from __future__ import annotations

from ..ops import case as case_ops
from ..ops import exports as export_ops
from ..ops import extraction as extraction_ops
from ..ops import query as query_ops
from ..ops import review as review_ops
from ..ops import sources as source_ops
from ..ops.result import OpResult
from ..ops.runner import TrcrRunner
from .nodes import required_case_dir
from .state import GraphState


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


def source_capture_node(runner: TrcrRunner):
    def node(state: GraphState) -> GraphState:
        urls = state.get("source_urls") or []
        if not urls:
            return {"status": "source_capture_skipped"}
        case_dir = required_case_dir(state)
        results = [source_ops.ingest_url(runner, case_dir, url) for url in urls]
        return merge_results(state, results, "sources_captured")

    return node


def parse_or_ocr_node(runner: TrcrRunner):
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


def draft_packets_node(runner: TrcrRunner):
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
