"""Ledger reads with privacy filtering, retrieval, and name linking."""

from __future__ import annotations

from typing import Sequence

from ..casefile import RECORD_FILES, CasefileError, find_source, load_records, resolve_case_path
from ..config import embed_model as default_embed_model
from ..config import qdrant_url as default_qdrant_url
from ..retrieval import index_case as _index_case
from ..retrieval import query_case as _query_case
from .policy import filter_public
from .result import OpResult, local_op
from .runner import TrcrRunner


def get_records(case_dir: str, record_type: str, *, include_private: bool = False) -> OpResult:
    if record_type not in RECORD_FILES:
        valid = ", ".join(sorted(RECORD_FILES))
        return OpResult(name="get_records", ok=False, errors=[f"Unknown record type: {record_type}. Known types: {valid}"])
    try:
        rows = load_records(case_dir, record_type)
    except CasefileError as exc:
        return OpResult(name="get_records", ok=False, errors=[str(exc)])
    visible = filter_public(rows, include_private=include_private)
    return OpResult(
        name="get_records",
        data={
            "record_type": record_type,
            "count": len(visible),
            "records": visible,
            "filtered": len(rows) - len(visible),
        },
    )


def get_source_text(
    case_dir: str,
    source_id: str,
    *,
    include_private: bool = False,
    max_chars: int | None = None,
) -> OpResult:
    try:
        source = find_source(case_dir, source_id)
    except CasefileError as exc:
        return OpResult(name="get_source_text", ok=False, errors=[str(exc)])
    if source.get("public_export") is False and not include_private:
        return OpResult(
            name="get_source_text",
            ok=False,
            errors=[f"Source {source_id} is public_export=false; pass include_private=True for internal review."],
        )
    text_path = resolve_case_path(case_dir, source.get("text_path"))
    if not text_path or not text_path.exists():
        return OpResult(name="get_source_text", ok=False, errors=[f"Source {source_id} has no readable text_path."])
    text = text_path.read_text(encoding="utf-8")
    truncated = max_chars is not None and len(text) > max_chars
    return OpResult(
        name="get_source_text",
        data={
            "source_id": source_id,
            "text": text[:max_chars] if truncated else text,
            "text_path": str(source.get("text_path")),
            "truncated": truncated,
        },
    )


def index_case(
    case_dir: str,
    *,
    include_private: bool = False,
    qdrant_url: str | None = None,
    collection: str | None = None,
    embed_model: str | None = None,
) -> OpResult:
    return local_op(
        "index_case",
        _index_case,
        case_dir,
        include_private=include_private,
        qdrant_url=default_qdrant_url(qdrant_url),
        collection=collection,
        embed_model=default_embed_model(embed_model),
    )


def query_case(
    case_dir: str,
    query_text: str,
    *,
    include_private: bool = False,
    qdrant_url: str | None = None,
    collection: str | None = None,
    embed_model: str | None = None,
    top_k: int = 8,
) -> OpResult:
    return local_op(
        "query_case",
        _query_case,
        case_dir,
        query_text,
        include_private=include_private,
        qdrant_url=default_qdrant_url(qdrant_url),
        collection=collection,
        embed_model=default_embed_model(embed_model),
        top_k=top_k,
    )


def link_names(
    runner: TrcrRunner,
    case_dir: str,
    *,
    names: Sequence[str] = (),
    names_file: str | None = None,
) -> OpResult:
    args = ["link-names", case_dir]
    for name in names:
        args.extend(["--name", name])
    if names_file:
        args.extend(["--names-file", names_file])
    return runner.run("link_names", args)
