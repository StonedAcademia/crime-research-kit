"""Case-level CSV and Markdown report commands."""

from __future__ import annotations

import argparse
import json
from typing import Any

from crime_research_kit._runtime.core.casefile import case_path, ensure_case, read_jsonl, record_path

from crime_research_kit._runtime.adapters.ops.evidence.ledger.markdown import md_table
from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import flatten


def report(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    claims = read_jsonl(record_path(args.case_dir, "claims"))
    events = read_jsonl(record_path(args.case_dir, "events"))
    event_links = read_jsonl(record_path(args.case_dir, "event_links"))
    entities = read_jsonl(record_path(args.case_dir, "entities"))
    rels = read_jsonl(record_path(args.case_dir, "relationships"))
    redactions = read_jsonl(record_path(args.case_dir, "redactions"))
    case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
    by_status: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        by_status.setdefault(claim.get("status", "unknown"), []).append(claim)

    content = [f"# Evidence board: {case_meta.get('title', cdir.name)}", ""]
    content += ["## Source ledger", ""]
    content.append(md_table(["ID", "Grade", "Type", "Title", "Publisher", "Date"], [[s.get("source_id", ""), s.get("reliability_grade", ""), s.get("source_type", ""), s.get("title", ""), s.get("publisher", ""), s.get("date_published", "")] for s in sources]))
    content += ["", "## Entities", ""]
    content.append(md_table(["ID", "Type", "Name", "Roles", "Privacy", "Public"], [[e.get("entity_id", ""), e.get("entity_type", ""), e.get("display_name") or e.get("name", ""), flatten(e.get("role_tags")), e.get("privacy_level", ""), str(e.get("public_export", True))] for e in entities]))
    content += ["", "## Events", ""]
    content.append(md_table(["ID", "Date", "Type", "Title", "Status", "Sources"], [[ev.get("event_id", ""), ev.get("start_date", ""), ev.get("event_type", ""), ev.get("title", ""), ev.get("status", ""), flatten(ev.get("source_ids"))] for ev in events]))
    content += ["", "## Event links", ""]
    content.append(md_table(["ID", "Entity", "Relation", "Event", "Basis", "Status", "Public"], [[link.get("event_link_id", ""), link.get("entity_id", ""), link.get("relation_type", ""), link.get("event_id", ""), link.get("basis", ""), link.get("status", ""), str(link.get("public_export", True))] for link in event_links]))
    content += ["", "## Relationships", ""]
    content.append(md_table(["ID", "Source", "Relation", "Target", "Status", "Sources"], [[r.get("rel_id", ""), r.get("src_entity_id", ""), r.get("relation_type", ""), r.get("dst_entity_id", ""), r.get("status", ""), flatten(r.get("source_ids"))] for r in rels]))
    content += ["", "## Claims by status", ""]
    for status, rows in sorted(by_status.items()):
        content += [f"### {status}", ""]
        content.append(md_table(["ID", "Confidence", "Claim", "Sources", "Public"], [[c.get("claim_id", ""), str(c.get("confidence", "")), c.get("claim", ""), flatten(c.get("source_ids")), str(c.get("public_export", True))] for c in rows]))
        content.append("")
    content += ["## Redactions / public-output exclusions", ""]
    content.append(md_table(["Record", "Field", "Reason", "Replacement"], [[r.get("record_id", ""), r.get("field", ""), r.get("reason", ""), r.get("public_replacement", "")] for r in redactions]))

    out = cdir / "exports" / "evidence_board.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(content) + "\n", encoding="utf-8")
    print(f"Wrote evidence board: {out}")
