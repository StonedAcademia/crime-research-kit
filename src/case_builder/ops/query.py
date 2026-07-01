"""Ledger reads with privacy filtering, retrieval, and name linking."""

from __future__ import annotations

from typing import Sequence

from ..casefile import RECORD_FILES, CasefileError, load_records
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


def index_case(
    case_dir: str,
    *,
    include_private: bool = False,
    qdrant_url: str = "http://localhost:6333",
    collection: str | None = None,
    embed_model: str = "BAAI/bge-small-en-v1.5",
) -> OpResult:
    return local_op(
        "index_case",
        _index_case,
        case_dir,
        include_private=include_private,
        qdrant_url=qdrant_url,
        collection=collection,
        embed_model=embed_model,
    )


def query_case(
    case_dir: str,
    query_text: str,
    *,
    include_private: bool = False,
    qdrant_url: str = "http://localhost:6333",
    collection: str | None = None,
    embed_model: str = "BAAI/bge-small-en-v1.5",
    top_k: int = 8,
) -> OpResult:
    return local_op(
        "query_case",
        _query_case,
        case_dir,
        query_text,
        include_private=include_private,
        qdrant_url=qdrant_url,
        collection=collection,
        embed_model=embed_model,
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
