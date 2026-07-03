"""Namespace-backed handlers for the case-builder CLI."""

from __future__ import annotations

import argparse

from crime_research_kit._runtime.adapters.ops.evidence import query as query_ops
from crime_research_kit._runtime.adapters.ops.result import OpResult
from crime_research_kit._runtime.core.config import CrkSettings
from crime_research_kit._runtime.core.memory import remember_research_actions
from crime_research_kit.sdk import CrkClient, OperationResult, WorkflowPlanRequest, WorkflowResumeRequest


def unwrap(result: OpResult) -> dict[str, object]:
    if not result.ok:
        raise SystemExit("\n".join(result.errors) or f"{result.name} failed")
    return result.data


def unwrap_sdk(result: OperationResult) -> dict[str, object]:
    if result.data:
        return result.data
    if not result.ok:
        raise SystemExit("\n".join(error.message for error in result.errors) or f"{result.operation} failed")
    return result.data


def _env_override(settings: CrkSettings, field: str) -> object | None:
    """Return a settings value only when the environment explicitly set it."""
    return getattr(settings, field) if field in settings.model_fields_set else None


def run_plan_command(args: argparse.Namespace) -> dict[str, object]:
    request = WorkflowPlanRequest(
        case_dir=args.case_dir,
        title=args.title,
        subject=args.subject,
        lanes=args.lane,
        source_urls=args.source_url,
        source_ids=args.source_id,
        index=args.index,
        thread_id=args.thread,
        llm=args.llm,
        execute=args.execute,
        runner=args.runner,
        checkpoint=args.checkpoint,
        model_spec=args.settings.model_spec if args.llm else None,
        qdrant_url=args.settings.qdrant_url,
        embed_model=args.settings.embed_model,
    )
    return unwrap_sdk(CrkClient().workflows.plan(request))


def run_resume_command(args: argparse.Namespace) -> dict[str, object]:
    request = WorkflowResumeRequest(
        case_dir=args.case_dir,
        thread_id=args.thread,
        approved_packets=args.approve_packet,
        rejected_packets=args.reject_packet,
        reject_reason=args.reason,
        export_approved=args.approve_export,
        execute=args.execute,
        llm=args.llm,
        model_spec=args.settings.model_spec if args.llm else None,
        qdrant_url=_env_override(args.settings, "qdrant_url"),
        embed_model=_env_override(args.settings, "embed_model"),
    )
    return unwrap_sdk(CrkClient().workflows.resume(request))


def run_discover_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap_sdk(
        CrkClient()
        .case(args.case_dir)
        .sources.discover(
            query=args.query,
            searxng_url=args.searxng_url or args.settings.searxng_url,
            limit=args.limit,
            out=args.out,
        )
    )


def run_parse_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap_sdk(CrkClient().case(args.case_dir).sources.parse(args.source_id, force=args.force))


def run_ocr_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap_sdk(CrkClient().case(args.case_dir).sources.ocr(args.source_id, language=args.language, force=args.force))


def run_index_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(
        query_ops.index_case(
            args.case_dir,
            include_private=args.include_private,
            qdrant_url=args.qdrant_url or args.settings.qdrant_url,
            collection=args.collection,
            embed_model=args.embed_model or args.settings.embed_model,
        )
    )


def run_query_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(
        query_ops.query_case(
            args.case_dir,
            args.query,
            include_private=args.include_private,
            qdrant_url=args.qdrant_url or args.settings.qdrant_url,
            collection=args.collection,
            embed_model=args.embed_model or args.settings.embed_model,
            top_k=args.top_k,
        )
    )


def run_remember_command(args: argparse.Namespace) -> dict[str, object]:
    return remember_research_actions(
        args.case_dir,
        provider=args.provider,
        limit=args.limit,
        qdrant_host=args.qdrant_host or args.settings.qdrant_host,
        qdrant_port=args.qdrant_port if args.qdrant_port is not None else args.settings.qdrant_port,
        llm_provider=args.llm_provider or args.settings.mem0_llm_provider,
        llm_model=args.llm_model or args.settings.mem0_llm_model,
        embedder_provider=args.embedder_provider or args.settings.embedder_provider,
        embedder_model=args.embedder_model or args.settings.embed_model,
    )
