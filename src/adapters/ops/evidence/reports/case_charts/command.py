"""Per-case chart export command."""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path
from typing import Any

from core.casefile import case_path, ensure_case, read_jsonl, record_path

from adapters.ops.evidence.public_gate import enforce_public_output_gate
from adapters.ops.evidence.reports.case_charts.people import render_people_graph_html
from adapters.ops.evidence.reports.case_charts.timeline import render_subcase_timeline_html
from adapters.ops.evidence.reports.common import (
    SUBCASE_TITLES,
    best_pair_relation,
    entity_display,
    infer_subcase,
    merge_people_edge,
)
from adapters.ops.evidence.ledger.markdown import md_table
from adapters.ops.evidence.ledger.records import public_rows, write_csv
from adapters.ops.evidence.ledger.scoring import date_sort_key, evidence_level, grade_summary


def export_case_charts(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    if not getattr(args, "skip_public_gate", False):
        enforce_public_output_gate(args.case_dir, "export-case-charts", args.include_private)
    cdir = case_path(args.case_dir)
    include_private = args.include_private
    out = Path(args.out_dir).expanduser().resolve() if args.out_dir else cdir / "exports" / "charts"
    out.mkdir(parents=True, exist_ok=True)

    case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
    case_title = str(case_meta.get("title", cdir.name))
    sources = public_rows(read_jsonl(record_path(cdir, "sources")), include_private)
    entities = public_rows(read_jsonl(record_path(cdir, "entities")), include_private)
    claims = public_rows(read_jsonl(record_path(cdir, "claims")), include_private)
    events = public_rows(read_jsonl(record_path(cdir, "events")), include_private)
    event_links = public_rows(read_jsonl(record_path(cdir, "event_links")), include_private)
    relationships = public_rows(read_jsonl(record_path(cdir, "relationships")), include_private)
    source_by_id = {source.get("source_id"): source for source in sources}
    claim_by_id = {claim.get("claim_id"): claim for claim in claims}
    people = [entity for entity in entities if entity.get("entity_type") == "person"]
    people_by_id = {str(person.get("entity_id")): person for person in people}

    people_edges = _people_edges(relationships, events, event_links, people_by_id)
    people_nodes = _people_nodes(people, include_private, claim_by_id)
    write_csv(out / "people_nodes.csv", people_nodes, ["entity_id", "name", "display_name", "aliases", "status", "role_tags", "privacy_level", "living_status", "source_ids", "claim_ids", "public_export"])
    write_csv(out / "people_edges.csv", people_edges, ["src_entity_id", "dst_entity_id", "src_name", "dst_name", "connection_types", "event_ids", "rel_ids", "claim_ids", "source_ids", "statuses", "confidence", "public_export", "notes"])
    (out / "people_graph.html").write_text(render_people_graph_html(case_title, people_nodes, people_edges, include_private), encoding="utf-8")

    timeline_rows, subcase_rows = _subcase_rows(events, claim_by_id, source_by_id)
    write_csv(out / "subcase_summary.csv", subcase_rows, ["subcase_id", "subcase_title", "event_count", "claim_count", "first_date", "last_date"])
    write_csv(out / "subcase_timelines.csv", timeline_rows, ["subcase_id", "subcase_title", "event_id", "start_date", "end_date", "date_precision", "event_type", "title", "status", "confidence", "claim_ids", "evidence_levels", "source_grades", "source_ids", "public_export"])
    (out / "subcase_timelines.html").write_text(render_subcase_timeline_html(case_title, subcase_rows, timeline_rows, include_private), encoding="utf-8")
    _write_index(out, case_title, include_private, people_nodes, people_edges, subcase_rows)
    print(f"Exported case charts to {out}")


def _people_edges(
    relationships: list[dict[str, Any]],
    events: list[dict[str, Any]],
    event_links: list[dict[str, Any]],
    people_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    edge_map: dict[tuple[str, str], dict[str, Any]] = {}
    for rel in relationships:
        src_id = str(rel.get("src_entity_id", ""))
        dst_id = str(rel.get("dst_entity_id", ""))
        if src_id in people_by_id and dst_id in people_by_id:
            merge_people_edge(edge_map, src_id, dst_id, people_by_id=people_by_id, connection_type=str(rel.get("relation_type", "")), rel_ids=[str(rel.get("rel_id", ""))], claim_ids=[str(claim_id) for claim_id in rel.get("claim_ids", [])], source_ids=[str(source_id) for source_id in rel.get("source_ids", [])], statuses=[str(rel.get("status", ""))], confidence=rel.get("confidence", 0), public_export=rel.get("public_export", True) is not False, notes=[str(rel.get("notes", ""))] if rel.get("notes") else [])
    links_by_event: dict[str, list[dict[str, Any]]] = {}
    for link in event_links:
        links_by_event.setdefault(str(link.get("event_id", "")), []).append(link)
    for event in events:
        _event_people_edges(edge_map, event, links_by_event.get(str(event.get("event_id", "")), []), people_by_id)
    return sorted(edge_map.values(), key=lambda row: (row["src_name"], row["dst_name"]))


def _event_people_edges(
    edge_map: dict[tuple[str, str], dict[str, Any]],
    event: dict[str, Any],
    links: list[dict[str, Any]],
    people_by_id: dict[str, dict[str, Any]],
) -> None:
    event_id = str(event.get("event_id", ""))
    person_roles: dict[str, list[str]] = {}
    person_claims: dict[str, list[str]] = {}
    person_sources: dict[str, list[str]] = {}
    for entity_id in event.get("entity_ids", []) or []:
        entity_id = str(entity_id)
        if entity_id in people_by_id:
            person_roles.setdefault(entity_id, []).append("event_entity")
            person_claims.setdefault(entity_id, []).extend(str(cid) for cid in event.get("claim_ids", []) or [])
            person_sources.setdefault(entity_id, []).extend(str(sid) for sid in event.get("source_ids", []) or [])
    for link in links:
        entity_id = str(link.get("entity_id", ""))
        if entity_id in people_by_id:
            person_roles.setdefault(entity_id, []).append(str(link.get("relation_type", "")))
            person_claims.setdefault(entity_id, []).extend(str(cid) for cid in link.get("claim_ids", []) or [])
            person_sources.setdefault(entity_id, []).extend(str(sid) for sid in link.get("source_ids", []) or [])
    for src_id, dst_id in combinations(sorted(person_roles), 2):
        merge_people_edge(edge_map, src_id, dst_id, people_by_id=people_by_id, connection_type=best_pair_relation(person_roles[src_id], person_roles[dst_id]), event_ids=[event_id], claim_ids=sorted(set(person_claims.get(src_id, []) + person_claims.get(dst_id, []))), source_ids=sorted(set(person_sources.get(src_id, []) + person_sources.get(dst_id, []))), statuses=[str(event.get("status", ""))], confidence=event.get("confidence", 0), public_export=event.get("public_export", True) is not False, notes=[f"Shared event: {event.get('title', event_id)}"])


def _people_nodes(people: list[dict[str, Any]], include_private: bool, claim_by_id: dict[Any, dict[str, Any]]) -> list[dict[str, Any]]:
    people_nodes = []
    for person in people:
        node = dict(person)
        if not include_private:
            node["claim_ids"] = [claim_id for claim_id in node.get("claim_ids", []) if claim_id in claim_by_id]
        people_nodes.append(node)
    return sorted(people_nodes, key=lambda person: entity_display(person))


def _subcase_rows(
    events: list[dict[str, Any]],
    claim_by_id: dict[Any, dict[str, Any]],
    source_by_id: dict[Any, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    timeline_rows: list[dict[str, Any]] = []
    subcase_counts: dict[str, dict[str, Any]] = {}
    for event in events:
        event_claims = [claim_by_id[claim_id] for claim_id in event.get("claim_ids", []) if claim_id in claim_by_id]
        subcase_id = infer_subcase(event, event_claims)
        source_ids = set(str(source_id) for source_id in event.get("source_ids", []) or [])
        for claim in event_claims:
            source_ids.update(str(source_id) for source_id in claim.get("source_ids", []) or [])
        source_rows = [source_by_id[source_id] for source_id in sorted(source_ids) if source_id in source_by_id]
        timeline_rows.append(_timeline_row(event, event_claims, subcase_id, source_rows, source_by_id))
        _add_subcase_count(subcase_counts, subcase_id, event, event_claims)
    timeline_rows.sort(key=lambda row: (row["subcase_id"], date_sort_key(row.get("start_date")), row.get("event_id", "")))
    subcase_rows = sorted(subcase_counts.values(), key=lambda row: (date_sort_key(row.get("first_date")), row["subcase_id"]))
    return timeline_rows, subcase_rows


def _timeline_row(event: dict[str, Any], event_claims: list[dict[str, Any]], subcase_id: str, source_rows: list[dict[str, Any]], source_by_id: dict[Any, dict[str, Any]]) -> dict[str, Any]:
    return {
        "subcase_id": subcase_id,
        "subcase_title": SUBCASE_TITLES.get(subcase_id, subcase_id),
        "event_id": event.get("event_id", ""),
        "start_date": event.get("start_date", ""),
        "end_date": event.get("end_date", ""),
        "date_precision": event.get("date_precision", ""),
        "event_type": event.get("event_type", ""),
        "title": event.get("title", ""),
        "status": event.get("status", ""),
        "confidence": event.get("confidence", ""),
        "claim_ids": [claim.get("claim_id", "") for claim in event_claims],
        "evidence_levels": sorted({evidence_level(claim, [source_by_id[sid] for sid in claim.get("source_ids", []) if sid in source_by_id]) for claim in event_claims}),
        "source_grades": grade_summary(source_rows),
        "source_ids": [source.get("source_id", "") for source in source_rows],
        "public_export": event.get("public_export", True),
    }


def _add_subcase_count(subcase_counts: dict[str, dict[str, Any]], subcase_id: str, event: dict[str, Any], event_claims: list[dict[str, Any]]) -> None:
    summary = subcase_counts.setdefault(subcase_id, {"subcase_id": subcase_id, "subcase_title": SUBCASE_TITLES.get(subcase_id, subcase_id), "event_count": 0, "claim_count": 0, "first_date": "", "last_date": ""})
    summary["event_count"] += 1
    summary["claim_count"] += len(event_claims)
    if not summary["first_date"] or date_sort_key(event.get("start_date")) < date_sort_key(summary["first_date"]):
        summary["first_date"] = event.get("start_date", "")
    if not summary["last_date"] or date_sort_key(event.get("start_date")) > date_sort_key(summary["last_date"]):
        summary["last_date"] = event.get("start_date", "")


def _write_index(out: Path, case_title: str, include_private: bool, people_nodes: list[dict[str, Any]], people_edges: list[dict[str, Any]], subcase_rows: list[dict[str, Any]]) -> None:
    index = [
        f"# Case charts: {case_title}",
        "",
        f"Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}",
        "",
        "## Files",
        "",
        "- `people_graph.html`",
        "- `people_nodes.csv`",
        "- `people_edges.csv`",
        "- `subcase_timelines.html`",
        "- `subcase_timelines.csv`",
        "- `subcase_summary.csv`",
        "",
        "## People Graph",
        "",
        f"People: {len(people_nodes)}",
        f"Edges: {len(people_edges)}",
        "",
        "## Subcase Timelines",
        "",
        md_table(["Subcase", "Events", "Claims", "First", "Last"], [[row["subcase_title"], row["event_count"], row["claim_count"], row["first_date"], row["last_date"]] for row in subcase_rows]),
    ]
    (out / "charts.md").write_text("\n".join(index) + "\n", encoding="utf-8")
