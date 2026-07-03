"""People clustering export command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from crime_research_kit._runtime.core.casefile import case_path, ensure_case

from crime_research_kit._runtime.adapters.ops.evidence.public_gate import enforce_public_output_gate
from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.render import render_page, write_html
from crime_research_kit._runtime.adapters.ops.evidence.reports.case_charts.command import export_case_charts
from crime_research_kit._runtime.adapters.ops.evidence.reports.clusters.renderers import build_people_clusters_page
from crime_research_kit._runtime.adapters.ops.evidence.reports.common import entity_display, read_csv_dicts
from crime_research_kit._runtime.adapters.ops.evidence.reports.weights import evidence_edge_weight, kernel_affinity_matrix, leiden_partition, parse_float, weighted_distances
from crime_research_kit._runtime.adapters.ops.evidence.ledger.markdown import md_table
from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import write_csv


def export_people_clusters(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    enforce_public_output_gate(args.case_dir, "export-people-clusters", args.include_private)
    cdir = case_path(args.case_dir)
    out = Path(args.out_dir).expanduser().resolve() if args.out_dir else cdir / "exports" / "clusters"
    charts_dir = Path(args.charts_dir).expanduser().resolve() if args.charts_dir else cdir / "exports" / "charts"
    out.mkdir(parents=True, exist_ok=True)
    export_case_charts(argparse.Namespace(case_dir=args.case_dir, out_dir=str(charts_dir), include_private=args.include_private, skip_public_gate=True))
    case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
    case_title = str(case_meta.get("title", cdir.name))
    nodes = read_csv_dicts(charts_dir / "people_nodes.csv")
    raw_edges = read_csv_dicts(charts_dir / "people_edges.csv")
    node_ids = [str(node["entity_id"]) for node in nodes]
    node_by_id = {str(node["entity_id"]): node for node in nodes}
    weighted_edges = _weighted_edges(raw_edges)
    cluster_by_id = _clusters(node_ids, node_by_id, weighted_edges, args.resolution, args.seed)
    dist = weighted_distances(node_ids, weighted_edges)
    kernel, sigma = kernel_affinity_matrix(node_ids, dist, args.sigma)
    kde_by_id = {node_id: round(sum(kernel[(node_id, other)] for other in node_ids) / max(1, len(node_ids)), 6) for node_id in node_ids}
    degree, weighted_degree = _degrees(node_ids, weighted_edges)
    cluster_rows = _cluster_rows(nodes, cluster_by_id, kde_by_id, degree, weighted_degree)
    summary_rows = _summary_rows(cluster_by_id, node_by_id, kde_by_id, weighted_edges)
    kernel_rows = _kernel_rows(node_ids, node_by_id, kernel)
    edge_rows = _edge_rows(weighted_edges, cluster_by_id)
    _write_outputs(out, cluster_rows, summary_rows, edge_rows, kernel_rows, node_ids)
    write_html(out / "people_clusters.html", render_page(build_people_clusters_page(case_title, nodes, edge_rows, cluster_by_id, kde_by_id, args.include_private)))
    _write_report(out, case_title, args, sigma, summary_rows)
    print(f"Exported Leiden people clusters to {out}")


def _weighted_edges(raw_edges: list[dict[str, str]]) -> list[dict[str, Any]]:
    weighted_edges = []
    for edge in raw_edges:
        row: dict[str, Any] = dict(edge)
        row["edge_weight"] = evidence_edge_weight(row)
        weighted_edges.append(row)
    return weighted_edges


def _clusters(node_ids: list[str], node_by_id: dict[str, dict[str, Any]], weighted_edges: list[dict[str, Any]], resolution: float, seed: int) -> dict[str, str]:
    communities = leiden_partition(node_ids, weighted_edges, resolution=resolution, seed=seed)
    communities = sorted(communities, key=lambda community: (-len(community), min(entity_display(node_by_id[node_id]) for node_id in community)))
    cluster_by_id = {}
    for idx, community in enumerate(communities, start=1):
        for node_id in community:
            cluster_by_id[node_id] = f"C{idx}"
    return cluster_by_id


def _degrees(node_ids: list[str], weighted_edges: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, float]]:
    degree = {node_id: 0 for node_id in node_ids}
    weighted_degree = {node_id: 0.0 for node_id in node_ids}
    for edge in weighted_edges:
        weight = parse_float(edge.get("edge_weight"), 0.0)
        for node_id in (str(edge["src_entity_id"]), str(edge["dst_entity_id"])):
            if node_id in degree:
                degree[node_id] += 1
                weighted_degree[node_id] += weight
    return degree, weighted_degree


def _cluster_rows(nodes: list[dict[str, Any]], cluster_by_id: dict[str, str], kde_by_id: dict[str, float], degree: dict[str, int], weighted_degree: dict[str, float]) -> list[dict[str, Any]]:
    rows = []
    for node in nodes:
        node_id = str(node["entity_id"])
        rows.append({"cluster_id": cluster_by_id.get(node_id, ""), "entity_id": node_id, "name": entity_display(node), "status": node.get("status", ""), "public_export": node.get("public_export", ""), "kde_density": kde_by_id.get(node_id, 0.0), "degree": degree.get(node_id, 0), "weighted_degree": round(weighted_degree.get(node_id, 0.0), 6), "claim_ids": node.get("claim_ids", ""), "source_ids": node.get("source_ids", "")})
    return sorted(rows, key=lambda row: (row["cluster_id"], -float(row["kde_density"]), row["name"]))


def _summary_rows(cluster_by_id: dict[str, str], node_by_id: dict[str, dict[str, Any]], kde_by_id: dict[str, float], weighted_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for cluster_id in sorted(set(cluster_by_id.values())):
        members = [node_id for node_id, cid in cluster_by_id.items() if cid == cluster_id]
        internal_weight = boundary_weight = 0.0
        for edge in weighted_edges:
            src = str(edge["src_entity_id"])
            dst = str(edge["dst_entity_id"])
            weight = parse_float(edge.get("edge_weight"), 0.0)
            if src in members and dst in members:
                internal_weight += weight
            elif src in members or dst in members:
                boundary_weight += weight
        rows.append({"cluster_id": cluster_id, "size": len(members), "members": ";".join(entity_display(node_by_id[node_id]) for node_id in sorted(members, key=lambda nid: entity_display(node_by_id[nid]))), "mean_kde_density": round(sum(kde_by_id[node_id] for node_id in members) / max(1, len(members)), 6), "internal_edge_weight": round(internal_weight, 6), "boundary_edge_weight": round(boundary_weight, 6)})
    return rows


def _kernel_rows(node_ids: list[str], node_by_id: dict[str, dict[str, Any]], kernel: dict[tuple[str, str], float]) -> list[dict[str, Any]]:
    rows = []
    for node_id in node_ids:
        row = {"entity_id": node_id, "name": entity_display(node_by_id[node_id])}
        for other in node_ids:
            row[other] = kernel[(node_id, other)]
        rows.append(row)
    return rows


def _edge_rows(weighted_edges: list[dict[str, Any]], cluster_by_id: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for edge in weighted_edges:
        src = str(edge["src_entity_id"])
        dst = str(edge["dst_entity_id"])
        rows.append({**edge, "src_cluster_id": cluster_by_id.get(src, ""), "dst_cluster_id": cluster_by_id.get(dst, ""), "same_cluster": cluster_by_id.get(src) == cluster_by_id.get(dst), "edge_weight": edge["edge_weight"]})
    return rows


def _write_outputs(out: Path, cluster_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]], edge_rows: list[dict[str, Any]], kernel_rows: list[dict[str, Any]], node_ids: list[str]) -> None:
    write_csv(out / "people_clusters.csv", cluster_rows, ["cluster_id", "entity_id", "name", "status", "public_export", "kde_density", "degree", "weighted_degree", "claim_ids", "source_ids"])
    write_csv(out / "cluster_summary.csv", summary_rows, ["cluster_id", "size", "members", "mean_kde_density", "internal_edge_weight", "boundary_edge_weight"])
    write_csv(out / "people_cluster_edges.csv", edge_rows, ["src_entity_id", "dst_entity_id", "src_name", "dst_name", "src_cluster_id", "dst_cluster_id", "same_cluster", "connection_types", "statuses", "confidence", "edge_weight", "event_ids", "rel_ids", "claim_ids", "source_ids", "public_export", "notes"])
    write_csv(out / "people_kernel_matrix.csv", kernel_rows, ["entity_id", "name", *node_ids])


def _write_report(out: Path, case_title: str, args: argparse.Namespace, sigma: float, summary_rows: list[dict[str, Any]]) -> None:
    report_lines = [
        f"# Leiden people clustering: {case_title}",
        "",
        f"Scope: {'public and private/internal rows' if args.include_private else 'public-export rows only'}",
        f"Leiden resolution: {args.resolution}",
        f"Leiden seed: {args.seed}",
        f"Kernel sigma: {sigma:.6f}",
        "",
        "## Files",
        "",
        "- `people_clusters.html`",
        "- `people_clusters.csv`",
        "- `cluster_summary.csv`",
        "- `people_cluster_edges.csv`",
        "- `people_kernel_matrix.csv`",
        "- `clusters.md`",
        "",
        "## Clusters",
        "",
        md_table(["Cluster", "Size", "Mean KDE", "Internal Weight", "Boundary Weight", "Members"], [[row["cluster_id"], row["size"], row["mean_kde_density"], row["internal_edge_weight"], row["boundary_edge_weight"], row["members"]] for row in summary_rows]),
        "",
        "## Interpretation Guardrails",
        "",
        "- Leiden clusters organize current graph structure; they are not evidence of a unified conspiracy.",
        "- Kernel density is graph-neighborhood density over evidence-weighted edges, not geographic density.",
        "- Weak `co_mentioned_with` edges are downweighted and remain lead-only.",
        "- Non-public rows remain for internal review unless separately privacy-reviewed.",
    ]
    (out / "clusters.md").write_text("\n".join(str(line) for line in report_lines) + "\n", encoding="utf-8")
