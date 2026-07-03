"""Evidence graph weighting and clustering helpers."""

from __future__ import annotations

import math
from typing import Any

from crime_research_kit._runtime.adapters.ops.evidence.reports.common import parse_cell_list


def parse_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def status_strength(statuses: list[str]) -> float:
    strengths = {
        "verified": 1.0,
        "corroborated": 0.95,
        "single_source": 0.75,
        "unverified": 0.25,
        "disputed": 0.2,
        "excluded_from_public_script": 0.15,
    }
    return max((strengths.get(status, 0.4) for status in statuses), default=0.4)


def connection_strength(connection_types: list[str]) -> float:
    direct_types = {
        "father_of",
        "founded",
        "founder_of",
        "co_participant_in_event",
        "official_source_describes_abuse_scheme_with",
        "headmaster_of",
        "taught_at",
        "associated_with",
        "opened",
        "co_opened_school",
        "shared_event_participants",
    }
    if any(kind in direct_types for kind in connection_types):
        return 1.0
    if "shared_event" in connection_types:
        return 0.75
    if "contextual_reference_same_event" in connection_types:
        return 0.55
    if "co_mentioned_with" in connection_types:
        return 0.25
    return 0.5


def evidence_edge_weight(edge: dict[str, Any]) -> float:
    connection_types = parse_cell_list(edge.get("connection_types"))
    statuses = parse_cell_list(edge.get("statuses"))
    claim_ids = parse_cell_list(edge.get("claim_ids"))
    confidence = parse_float(edge.get("confidence"), 0.0)
    claim_factor = 1.0 if claim_ids else 0.65
    weight = confidence * status_strength(statuses) * connection_strength(connection_types) * claim_factor
    return round(max(0.01, min(1.0, weight)), 6)


def median(values: list[float], default: float = 1.0) -> float:
    if not values:
        return default
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def weighted_distances(node_ids: list[str], edges: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    inf = float("inf")
    dist: dict[tuple[str, str], float] = {}
    for left in node_ids:
        for right in node_ids:
            dist[(left, right)] = 0.0 if left == right else inf
    for edge in edges:
        src = str(edge["src_entity_id"])
        dst = str(edge["dst_entity_id"])
        if src not in node_ids or dst not in node_ids:
            continue
        weight = parse_float(edge.get("edge_weight"), evidence_edge_weight(edge))
        cost = 1.0 / max(weight, 0.01)
        if cost < dist[(src, dst)]:
            dist[(src, dst)] = cost
            dist[(dst, src)] = cost
    for pivot in node_ids:
        for left in node_ids:
            left_pivot = dist[(left, pivot)]
            if math.isinf(left_pivot):
                continue
            for right in node_ids:
                alt = left_pivot + dist[(pivot, right)]
                if alt < dist[(left, right)]:
                    dist[(left, right)] = alt
    return dist


def kernel_affinity_matrix(
    node_ids: list[str],
    dist: dict[tuple[str, str], float],
    sigma: float | None,
) -> tuple[dict[tuple[str, str], float], float]:
    finite = [distance for (left, right), distance in dist.items() if left != right and not math.isinf(distance) and distance > 0]
    bandwidth = sigma if sigma and sigma > 0 else max(1.0, median(finite, default=1.0))
    kernel: dict[tuple[str, str], float] = {}
    denom = 2 * bandwidth * bandwidth
    for left in node_ids:
        for right in node_ids:
            distance = dist[(left, right)]
            if left == right:
                affinity = 1.0
            elif math.isinf(distance):
                affinity = 0.0
            else:
                affinity = math.exp(-(distance * distance) / denom)
            kernel[(left, right)] = round(affinity, 6)
    return kernel, bandwidth


def leiden_partition(
    node_ids: list[str],
    edges: list[dict[str, Any]],
    *,
    resolution: float,
    seed: int,
) -> list[list[str]]:
    if not node_ids:
        return []
    try:
        import igraph as ig  # type: ignore
        import leidenalg  # type: ignore
    except Exception as exc:
        raise SystemExit(
            "Leiden clustering requires igraph and leidenalg. "
            "Run with: cd tc-c-kit && uv run --extra dev --with igraph --with leidenalg "
            "crk-ledger export-people-clusters ..."
        ) from exc

    graph = ig.Graph()
    graph.add_vertices(len(node_ids))
    graph.vs["name"] = node_ids
    index = {node_id: idx for idx, node_id in enumerate(node_ids)}
    graph_edges: list[tuple[int, int]] = []
    weights: list[float] = []
    for edge in edges:
        src = str(edge["src_entity_id"])
        dst = str(edge["dst_entity_id"])
        if src in index and dst in index:
            graph_edges.append((index[src], index[dst]))
            weights.append(parse_float(edge.get("edge_weight"), evidence_edge_weight(edge)))
    if graph_edges:
        graph.add_edges(graph_edges)
        graph.es["weight"] = weights
        partition = leidenalg.find_partition(graph, leidenalg.RBConfigurationVertexPartition, weights=weights, resolution_parameter=resolution, seed=seed)
        communities = [[node_ids[idx] for idx in community] for community in partition]
    else:
        communities = [[node_id] for node_id in node_ids]
    return [sorted(community) for community in communities]
