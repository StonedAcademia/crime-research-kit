"""Read-only crk:// resources for cheap case context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crime_research_kit._runtime.adapters.interfaces.mcp.context import ServerContext, default_skill_root, resolve_case
from crime_research_kit._runtime.adapters.ops import extraction as extraction_ops
from crime_research_kit._runtime.adapters.ops import query as query_ops

REFERENCE_ALLOW_LIST = frozenset({"controlled_vocabularies", "topic_extraction_templates"})


def case_json_resource(ctx: ServerContext, case: str) -> str:
    return (Path(resolve_case(ctx, case)) / "case.json").read_text(encoding="utf-8")


def records_resource(ctx: ServerContext, case: str, record_type: str) -> str:
    result = query_ops.get_records(resolve_case(ctx, case), record_type)
    if not result.ok:
        raise ValueError("; ".join(result.errors))
    rows = result.data.get("records", [])
    return "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)


def packet_resource(ctx: ServerContext, case: str, name: str) -> str:
    result = extraction_ops.read_packet(resolve_case(ctx, case), name)
    if not result.ok:
        raise ValueError("; ".join(result.errors))
    return json.dumps(result.data["packet"], ensure_ascii=False, indent=2, sort_keys=True)


def reference_resource(ctx: ServerContext, name: str) -> str:
    if name not in REFERENCE_ALLOW_LIST:
        available = ", ".join(sorted(REFERENCE_ALLOW_LIST))
        raise ValueError(f"Unknown reference: {name!r}. Available: {available}")
    skill_root = ctx.skill_root or default_skill_root(ctx.repo_root)
    return (skill_root / "references" / f"{name}.md").read_text(encoding="utf-8")


def register(mcp: Any, ctx: ServerContext) -> None:
    @mcp.resource("crk://cases/{case}/case.json")
    def case_json(case: str) -> str:
        """Case metadata JSON."""
        return case_json_resource(ctx, case)

    @mcp.resource("crk://cases/{case}/records/{record_type}")
    def records(case: str, record_type: str) -> str:
        """Public-safe JSONL rows for one record type."""
        return records_resource(ctx, case, record_type)

    @mcp.resource("crk://cases/{case}/staging/extractions/{name}")
    def packet(case: str, name: str) -> str:
        """A staged extraction packet awaiting review."""
        return packet_resource(ctx, case, name)

    @mcp.resource("crk://references/{name}")
    def reference(name: str) -> str:
        """Skill reference documents."""
        return reference_resource(ctx, name)
