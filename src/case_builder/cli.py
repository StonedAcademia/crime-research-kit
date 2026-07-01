"""Command-line entrypoint for the TRCR case-builder agent app."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from .app.service import run_case_builder
from .memory import remember_research_actions
from .models.state import CaseBuilderState
from .ops import query as query_ops
from .ops import sources as source_ops
from .ops.result import OpResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap TRCR case-building workflows.")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="Plan and optionally execute the initial case-building workflow.")
    plan.add_argument("case_dir", help="Case directory, usually data/cases/<case_slug> from inside tc-c-kit.")
    plan.add_argument("--title", help="Case title to use if the case is initialized.")
    plan.add_argument("--subject", help="Seed subject, names, dates, places, or case question.")
    plan.add_argument("--lane", action="append", default=[], help="Force a public-record lane. Repeatable.")
    plan.add_argument("--execute", action="store_true", help="Run TRCR commands instead of dry-running them.")
    plan.add_argument("--runner", choices=["auto", "langgraph", "sequential"], default="auto")
    plan.set_defaults(handler=run_plan_command)

    discover = sub.add_parser("discover-sources", help="Search local SearXNG and write lead-only source candidates.")
    discover.add_argument("case_dir")
    discover.add_argument("--query", required=True)
    discover.add_argument("--searxng-url", default="http://localhost:8080")
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
    index.add_argument("--qdrant-url", default="http://localhost:6333")
    index.add_argument("--collection", default=None)
    index.add_argument("--embed-model", default="BAAI/bge-small-en-v1.5")
    index.set_defaults(handler=run_index_command)

    query = sub.add_parser("query-case", help="Query the local Qdrant/LlamaIndex evidence index.")
    query.add_argument("case_dir")
    query.add_argument("query")
    query.add_argument("--include-private", action="store_true")
    query.add_argument("--qdrant-url", default="http://localhost:6333")
    query.add_argument("--collection", default=None)
    query.add_argument("--embed-model", default="BAAI/bge-small-en-v1.5")
    query.add_argument("--top-k", type=int, default=8)
    query.set_defaults(handler=run_query_command)

    remember = sub.add_parser("remember-research-actions", help="Store recent workflow actions in local memory.")
    remember.add_argument("case_dir")
    remember.add_argument("--provider", choices=["local", "mem0"], default="local")
    remember.add_argument("--limit", type=int, default=50)
    remember.add_argument("--qdrant-host", default="localhost")
    remember.add_argument("--qdrant-port", type=int, default=6333)
    remember.add_argument("--llm-provider", default="ollama")
    remember.add_argument("--llm-model", default="llama3.1")
    remember.add_argument("--embedder-provider", default="huggingface")
    remember.add_argument("--embedder-model", default="BAAI/bge-small-en-v1.5")
    remember.set_defaults(handler=run_remember_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.handler(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def unwrap(result: OpResult) -> dict[str, object]:
    if not result.ok:
        raise SystemExit("\n".join(result.errors) or f"{result.name} failed")
    return result.data


def run_plan_command(args: argparse.Namespace) -> dict[str, object]:
    state = CaseBuilderState(
        case_dir=args.case_dir,
        title=args.title,
        subject=args.subject,
        lanes=args.lane,
    )
    return run_case_builder(state, execute=args.execute, runner=args.runner)


def run_discover_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(
        source_ops.discover_sources(
            args.case_dir,
            query=args.query,
            searxng_url=args.searxng_url,
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
            qdrant_url=args.qdrant_url,
            collection=args.collection,
            embed_model=args.embed_model,
        )
    )


def run_query_command(args: argparse.Namespace) -> dict[str, object]:
    return unwrap(
        query_ops.query_case(
            args.case_dir,
            args.query,
            include_private=args.include_private,
            qdrant_url=args.qdrant_url,
            collection=args.collection,
            embed_model=args.embed_model,
            top_k=args.top_k,
        )
    )


def run_remember_command(args: argparse.Namespace) -> dict[str, object]:
    return remember_research_actions(
        args.case_dir,
        provider=args.provider,
        limit=args.limit,
        qdrant_host=args.qdrant_host,
        qdrant_port=args.qdrant_port,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        embedder_provider=args.embedder_provider,
        embedder_model=args.embedder_model,
    )


if __name__ == "__main__":
    raise SystemExit(main())
