"""Command-line entrypoint for the CRK case-builder agent app."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from adapters.ops.casework import sources as source_ops
from adapters.ops.evidence import query as query_ops
from adapters.ops.result import OpResult
from core.config import CrkSettings
from core.memory import remember_research_actions
from core.models.state import CaseBuilderState
from pipeline.app.service import resume_case_builder, run_case_builder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap CRK case-building workflows.")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="Plan and optionally execute the initial case-building workflow.")
    plan.add_argument("case_dir", help="Case directory, usually data/cases/<case_slug> from inside tc-c-kit.")
    plan.add_argument("--title", help="Case title to use if the case is initialized.")
    plan.add_argument("--subject", help="Seed subject, names, dates, places, or case question.")
    plan.add_argument("--lane", action="append", default=[], help="Force a public-record lane. Repeatable.")
    plan.add_argument("--execute", action="store_true", help="Run CRK commands instead of dry-running them.")
    plan.add_argument("--runner", choices=["auto", "langgraph", "sequential"], default="auto")
    plan.add_argument("--source-url", action="append", default=[], help="Public URL to capture. Repeatable.")
    plan.add_argument("--source-id", action="append", default=[], help="Existing source ID to draft a packet for. Repeatable.")
    plan.add_argument("--index", action="store_true", help="Build the local evidence index after import (execute mode).")
    plan.add_argument("--checkpoint", action="store_true", help="Persist run state to <case>/.runs/checkpoints.db (langgraph only).")
    plan.add_argument("--thread", default=None, help="Thread ID for checkpointed runs. Defaults to the run ID.")
    plan.add_argument("--llm", action="store_true", help="Enable LLM agent nodes (CRK_MODEL, default ollama:llama3.1).")
    plan.set_defaults(handler=run_plan_command)

    discover = sub.add_parser("discover-sources", help="Search local SearXNG and write lead-only source candidates.")
    discover.add_argument("case_dir")
    discover.add_argument("--query", required=True)
    discover.add_argument("--searxng-url", default=None)
    discover.add_argument("--limit", type=int, default=10)
    discover.add_argument("--out", default=None)
    discover.set_defaults(handler=run_discover_command)

    parse = sub.add_parser("parse-source", help="Parse a registered local source artifact with Docling.")
    parse.add_argument("case_dir")
    parse.add_argument("source_id")
    parse.add_argument("--force", action="store_true")
    parse.set_defaults(handler=run_parse_command)

    ocr = sub.add_parser("ocr-source", help="OCR a registered PDF source with OCRmyPDF.")
    ocr.add_argument("case_dir")
    ocr.add_argument("source_id")
    ocr.add_argument("--language", default="eng")
    ocr.add_argument("--force", action="store_true")
    ocr.set_defaults(handler=run_ocr_command)

    index = sub.add_parser("index-case", help="Build a local Qdrant/LlamaIndex evidence index.")
    index.add_argument("case_dir")
    index.add_argument("--include-private", action="store_true")
    index.add_argument("--qdrant-url", default=None)
    index.add_argument("--collection", default=None)
    index.add_argument("--embed-model", default=None)
    index.set_defaults(handler=run_index_command)

    query = sub.add_parser("query-case", help="Query the local Qdrant/LlamaIndex evidence index.")
    query.add_argument("case_dir")
    query.add_argument("query")
    query.add_argument("--include-private", action="store_true")
    query.add_argument("--qdrant-url", default=None)
    query.add_argument("--collection", default=None)
    query.add_argument("--embed-model", default=None)
    query.add_argument("--top-k", type=int, default=8)
    query.set_defaults(handler=run_query_command)

    remember = sub.add_parser("remember-research-actions", help="Store recent workflow actions in local memory.")
    remember.add_argument("case_dir")
    remember.add_argument("--provider", choices=["local", "mem0"], default="local")
    remember.add_argument("--limit", type=int, default=50)
    remember.add_argument("--qdrant-host", default=None)
    remember.add_argument("--qdrant-port", type=int, default=None)
    remember.add_argument("--llm-provider", default=None)
    remember.add_argument("--llm-model", default=None)
    remember.add_argument("--embedder-provider", default=None)
    remember.add_argument("--embedder-model", default=None)
    remember.set_defaults(handler=run_remember_command)

    resume = sub.add_parser("resume", help="Resume a checkpointed case-builder run with review decisions.")
    resume.add_argument("case_dir")
    resume.add_argument("--thread", required=True, help="Thread ID printed by the checkpointed plan run.")
    resume.add_argument("--approve-packet", action="append", default=[], help="Staged packet filename to approve. Repeatable.")
    resume.add_argument("--reject-packet", action="append", default=[], help="Staged packet filename to reject. Repeatable.")
    resume.add_argument("--reason", default=None, help="Reason recorded for rejected packets.")
    resume.add_argument("--approve-export", action="store_true", help="Approve the public export gate.")
    resume.add_argument("--execute", action="store_true", help="Run CRK commands instead of dry-running them.")
    resume.add_argument("--llm", action="store_true", help="Enable LLM agent nodes on the resumed run.")
    resume.set_defaults(handler=run_resume_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.settings = CrkSettings()
    result = args.handler(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def unwrap(result: OpResult) -> dict[str, object]:
    if not result.ok:
        raise SystemExit("\n".join(result.errors) or f"{result.name} failed")
    return result.data


def _env_override(settings: CrkSettings, field: str) -> object | None:
    """Return the settings value only if the environment explicitly set it.

    Used at resume time so unset fields don't clobber checkpointed values with
    ``CrkSettings`` defaults (see resume_case_builder's no-clobber guard).
    """
    return getattr(settings, field) if field in settings.model_fields_set else None


def run_plan_command(args: argparse.Namespace) -> dict[str, object]:
    state = CaseBuilderState(
        case_dir=args.case_dir,
        title=args.title,
        subject=args.subject,
        lanes=args.lane,
        source_urls=args.source_url,
        source_ids=args.source_id,
        index_enabled=args.index,
        thread_id=args.thread,
        llm_enabled=args.llm,
    )
    return run_case_builder(
        state,
        execute=args.execute,
        runner=args.runner,
        checkpoint=args.checkpoint,
        model_spec=args.settings.model_spec if args.llm else None,
        qdrant_url=args.settings.qdrant_url,
        embed_model=args.settings.embed_model,
    )


def run_resume_command(args: argparse.Namespace) -> dict[str, object]:
    rejected = [{"packet": name, "reason": args.reason} for name in args.reject_packet]
    return resume_case_builder(
        args.case_dir,
        thread_id=args.thread,
        approved_packets=args.approve_packet,
        rejected_packets=rejected,
        export_approved=args.approve_export,
        execute=args.execute,
        llm=args.llm,
        model_spec=args.settings.model_spec if args.llm else None,
        qdrant_url=_env_override(args.settings, "qdrant_url"),
        embed_model=_env_override(args.settings, "embed_model"),
    )


def run_discover_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(
        source_ops.discover_sources(
            args.case_dir,
            query=args.query,
            searxng_url=args.searxng_url or args.settings.searxng_url,
            limit=args.limit,
            out=args.out,
        )
    )


def run_parse_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(source_ops.parse_source(args.case_dir, args.source_id, force=args.force))


def run_ocr_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(source_ops.ocr_source(args.case_dir, args.source_id, language=args.language, force=args.force))


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


if __name__ == "__main__":
    raise SystemExit(main())
