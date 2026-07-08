"""Case loading context for analysis chart exports."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from crime_research_kit._runtime.core.casefile import case_path, ensure_case, read_jsonl, record_path

from crime_research_kit._runtime.adapters.ops.evidence.public_gate import enforce_public_output_gate
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.paths import analysis_graph, parse_cluster_bridge_audit, read_cluster_metadata
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.vocabulary import VocabPacks, load_case_packs
from crime_research_kit._runtime.adapters.ops.evidence.reports.common import entity_display, read_csv_dicts, reject_legacy_export_dir
from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import public_rows, source_independence_key


@dataclass
class AnalysisContext:
    cdir: Path
    out: Path
    include_private: bool
    case_title: str
    sources: list[dict[str, Any]]
    entities: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    events: list[dict[str, Any]]
    event_links: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    source_by_id: dict[str, dict[str, Any]]
    claim_by_id: dict[str, dict[str, Any]]
    entity_by_id: dict[str, dict[str, Any]]
    people: list[dict[str, Any]]
    people_by_id: dict[str, dict[str, Any]]
    clusters_dir: Path
    cluster_by_person: dict[str, str]
    cluster_summary: dict[str, dict[str, Any]]
    cluster_labels: dict[str, str]
    audit_bridges: list[dict[str, Any]]
    graph: dict[str, Any]
    graph_meta: dict[str, dict[str, Any]]
    packs: VocabPacks
    cluster_members: dict[str, list[str]]
    cluster_ids: list[str]

    def node_label(self, node_id: str) -> str:
        return str(self.graph_meta.get(node_id, {}).get("label", node_id))

    def path_label(self, steps: list[tuple[str, str, dict[str, Any]]]) -> str:
        if not steps:
            return ""
        return " -> ".join([self.node_label(steps[0][0]), *[self.node_label(step[1]) for step in steps]])

    def source_rows_for_ids(self, source_ids: Iterable[str]) -> list[dict[str, Any]]:
        return [self.source_by_id[sid] for sid in source_ids if sid in self.source_by_id]

    def independent_source_count(self, source_rows: list[dict[str, Any]]) -> int:
        return len({source_independence_key(source) for source in source_rows})


def load_analysis_context(args: argparse.Namespace) -> AnalysisContext:
    ensure_case(args.case_dir)
    if not getattr(args, "skip_public_gate", False):
        enforce_public_output_gate(args.case_dir, getattr(args, "gate_name", "export-case-visuals"), args.include_private)
    cdir = case_path(args.case_dir)
    packs = load_case_packs(cdir)
    include_private = args.include_private
    if not args.out_dir:
        raise SystemExit("Standalone analysis chart exports are retired; use export-case-visuals.")
    out = Path(args.out_dir).expanduser().resolve()
    reject_legacy_export_dir(out)
    out.mkdir(parents=True, exist_ok=True)

    case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
    case_title = str(case_meta.get("title", cdir.name))
    sources = public_rows(read_jsonl(record_path(cdir, "sources")), include_private)
    entities = public_rows(read_jsonl(record_path(cdir, "entities")), include_private)
    claims = public_rows(read_jsonl(record_path(cdir, "claims")), include_private)
    events = public_rows(read_jsonl(record_path(cdir, "events")), include_private)
    event_links = public_rows(read_jsonl(record_path(cdir, "event_links")), include_private)
    relationships = public_rows(read_jsonl(record_path(cdir, "relationships")), include_private)

    source_by_id = {str(source.get("source_id")): source for source in sources}
    claim_by_id = {str(claim.get("claim_id")): claim for claim in claims}
    entity_by_id = {str(entity.get("entity_id")): entity for entity in entities}
    people = [entity for entity in entities if entity.get("entity_type") == "person"]
    people_by_id = {str(person.get("entity_id")): person for person in people}

    clusters_dir = Path(args.clusters_dir).expanduser().resolve() if args.clusters_dir else cdir / "exports" / "clusters"
    cluster_by_person: dict[str, str] = {}
    if (clusters_dir / "people_clusters.csv").exists():
        for row in read_csv_dicts(clusters_dir / "people_clusters.csv"):
            cluster_by_person[str(row.get("entity_id"))] = str(row.get("cluster_id") or "")
    if not cluster_by_person:
        for idx, person in enumerate(sorted(people, key=entity_display), start=1):
            cluster_by_person[str(person.get("entity_id"))] = f"P{idx}"

    cluster_summary, cluster_labels = read_cluster_metadata(clusters_dir)
    audit_cluster_labels, audit_bridges = parse_cluster_bridge_audit(cdir)
    cluster_labels.update(audit_cluster_labels)
    graph, graph_meta = analysis_graph(entities, events, event_links, relationships, packs=packs)
    for person_id, cluster_id in cluster_by_person.items():
        if person_id in graph_meta:
            graph_meta[person_id]["cluster_id"] = cluster_id

    cluster_members: dict[str, list[str]] = {}
    for person_id, cluster_id in cluster_by_person.items():
        if person_id in people_by_id:
            cluster_members.setdefault(cluster_id, []).append(person_id)

    return AnalysisContext(
        cdir=cdir,
        out=out,
        include_private=include_private,
        case_title=case_title,
        sources=sources,
        entities=entities,
        claims=claims,
        events=events,
        event_links=event_links,
        relationships=relationships,
        source_by_id=source_by_id,
        claim_by_id=claim_by_id,
        entity_by_id=entity_by_id,
        people=people,
        people_by_id=people_by_id,
        clusters_dir=clusters_dir,
        cluster_by_person=cluster_by_person,
        cluster_summary=cluster_summary,
        cluster_labels=cluster_labels,
        audit_bridges=audit_bridges,
        graph=graph,
        graph_meta=graph_meta,
        packs=packs,
        cluster_members=cluster_members,
        cluster_ids=sorted(cluster_members),
    )
