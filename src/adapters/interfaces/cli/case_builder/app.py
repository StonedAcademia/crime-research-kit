"""Typer application for the `cr-kit` console script."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from typing import Any

import typer
import typer._click as click
import typer.main

from adapters.interfaces.cli.commands import choice_enum, enum_value
from core.config import CrkSettings

from . import handlers

Runner = choice_enum("Runner", ["auto", "langgraph", "sequential"])
MemoryProvider = choice_enum("MemoryProvider", ["local", "mem0"])

app = typer.Typer(help="Bootstrap CRK case-building workflows.", no_args_is_help=True)


@app.callback()
def _root(ctx: typer.Context) -> None:
    ctx.obj = CrkSettings()


def build_click_command() -> click.Command:
    return typer.main.get_command(app)


def main(argv: list[str] | None = None) -> int:
    command = build_click_command()
    try:
        command.main(args=argv, standalone_mode=False)
    except click.exceptions.Abort as exc:
        raise SystemExit(1) from exc
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    return 0


def invoke(ctx: typer.Context, handler: Callable[[argparse.Namespace], dict[str, object]], **values: Any) -> None:
    values["settings"] = ctx.obj if isinstance(ctx.obj, CrkSettings) else CrkSettings()
    print(json.dumps(handler(argparse.Namespace(**values)), indent=2, sort_keys=True))


@app.command("plan", help="Plan and optionally execute the initial case-building workflow.")
def plan(
    ctx: typer.Context,
    case_dir: str = typer.Argument(...),
    title: str | None = typer.Option(None, "--title"),
    subject: str | None = typer.Option(None, "--subject"),
    lane: list[str] = typer.Option([], "--lane"),
    execute: bool = typer.Option(False, "--execute"),
    runner: Runner = typer.Option(Runner("auto"), "--runner"),
    source_url: list[str] = typer.Option([], "--source-url"),
    source_id: list[str] = typer.Option([], "--source-id"),
    index: bool = typer.Option(False, "--index"),
    checkpoint: bool = typer.Option(False, "--checkpoint"),
    thread: str | None = typer.Option(None, "--thread"),
    llm: bool = typer.Option(False, "--llm"),
) -> None:
    invoke(
        ctx,
        handlers.run_plan_command,
        case_dir=case_dir,
        title=title,
        subject=subject,
        lane=list(lane),
        execute=execute,
        runner=enum_value(runner),
        source_url=list(source_url),
        source_id=list(source_id),
        index=index,
        checkpoint=checkpoint,
        thread=thread,
        llm=llm,
    )


@app.command("discover-sources", help="Search local SearXNG and write lead-only source candidates.")
def discover_sources(
    ctx: typer.Context,
    case_dir: str = typer.Argument(...),
    query: str = typer.Option(..., "--query"),
    searxng_url: str | None = typer.Option(None, "--searxng-url"),
    limit: int = typer.Option(10, "--limit"),
    out: str | None = typer.Option(None, "--out"),
) -> None:
    invoke(ctx, handlers.run_discover_command, case_dir=case_dir, query=query, searxng_url=searxng_url, limit=limit, out=out)


@app.command("parse-source", help="Parse a registered local source artifact with Docling.")
def parse_source(
    ctx: typer.Context,
    case_dir: str = typer.Argument(...),
    source_id: str = typer.Argument(...),
    force: bool = typer.Option(False, "--force"),
) -> None:
    invoke(ctx, handlers.run_parse_command, case_dir=case_dir, source_id=source_id, force=force)


@app.command("ocr-source", help="OCR a registered PDF source with OCRmyPDF.")
def ocr_source(
    ctx: typer.Context,
    case_dir: str = typer.Argument(...),
    source_id: str = typer.Argument(...),
    language: str = typer.Option("eng", "--language"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    invoke(ctx, handlers.run_ocr_command, case_dir=case_dir, source_id=source_id, language=language, force=force)


@app.command("index-case", help="Build a local Qdrant/LlamaIndex evidence index.")
def index_case(
    ctx: typer.Context,
    case_dir: str = typer.Argument(...),
    include_private: bool = typer.Option(False, "--include-private"),
    qdrant_url: str | None = typer.Option(None, "--qdrant-url"),
    collection: str | None = typer.Option(None, "--collection"),
    embed_model: str | None = typer.Option(None, "--embed-model"),
) -> None:
    invoke(ctx, handlers.run_index_command, case_dir=case_dir, include_private=include_private, qdrant_url=qdrant_url, collection=collection, embed_model=embed_model)


@app.command("query-case", help="Query the local Qdrant/LlamaIndex evidence index.")
def query_case(
    ctx: typer.Context,
    case_dir: str = typer.Argument(...),
    query: str = typer.Argument(...),
    include_private: bool = typer.Option(False, "--include-private"),
    qdrant_url: str | None = typer.Option(None, "--qdrant-url"),
    collection: str | None = typer.Option(None, "--collection"),
    embed_model: str | None = typer.Option(None, "--embed-model"),
    top_k: int = typer.Option(8, "--top-k"),
) -> None:
    invoke(ctx, handlers.run_query_command, case_dir=case_dir, query=query, include_private=include_private, qdrant_url=qdrant_url, collection=collection, embed_model=embed_model, top_k=top_k)


@app.command("remember-research-actions", help="Store recent workflow actions in local memory.")
def remember_actions(
    ctx: typer.Context,
    case_dir: str = typer.Argument(...),
    provider: MemoryProvider = typer.Option(MemoryProvider("local"), "--provider"),
    limit: int = typer.Option(50, "--limit"),
    qdrant_host: str | None = typer.Option(None, "--qdrant-host"),
    qdrant_port: int | None = typer.Option(None, "--qdrant-port"),
    llm_provider: str | None = typer.Option(None, "--llm-provider"),
    llm_model: str | None = typer.Option(None, "--llm-model"),
    embedder_provider: str | None = typer.Option(None, "--embedder-provider"),
    embedder_model: str | None = typer.Option(None, "--embedder-model"),
) -> None:
    invoke(
        ctx,
        handlers.run_remember_command,
        case_dir=case_dir,
        provider=enum_value(provider),
        limit=limit,
        qdrant_host=qdrant_host,
        qdrant_port=qdrant_port,
        llm_provider=llm_provider,
        llm_model=llm_model,
        embedder_provider=embedder_provider,
        embedder_model=embedder_model,
    )


@app.command("resume", help="Resume a checkpointed case-builder run with review decisions.")
def resume(
    ctx: typer.Context,
    case_dir: str = typer.Argument(...),
    thread: str = typer.Option(..., "--thread"),
    approve_packet: list[str] = typer.Option([], "--approve-packet"),
    reject_packet: list[str] = typer.Option([], "--reject-packet"),
    reason: str | None = typer.Option(None, "--reason"),
    approve_export: bool = typer.Option(False, "--approve-export"),
    execute: bool = typer.Option(False, "--execute"),
    llm: bool = typer.Option(False, "--llm"),
) -> None:
    invoke(
        ctx,
        handlers.run_resume_command,
        case_dir=case_dir,
        thread=thread,
        approve_packet=list(approve_packet),
        reject_packet=list(reject_packet),
        reason=reason,
        approve_export=approve_export,
        execute=execute,
        llm=llm,
    )
