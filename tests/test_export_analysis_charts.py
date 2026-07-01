import csv
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TCR_PATH = REPO_ROOT / ".agents/skills/truecrime-cult-research/scripts/tcr.py"


def load_tcr():
    spec = importlib.util.spec_from_file_location("tcr", TCR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def append_source(tcr, case_dir, source_id, grade="B"):
    tcr.append_jsonl(tcr.record_path(case_dir, "sources"), {
        "source_id": source_id,
        "title": f"Synthetic source {source_id}",
        "source_type": "news_article",
        "author": "Demo Reporter",
        "publisher": "Demo Daily",
        "date_published": "1970-01-01",
        "date_accessed": "2026-06-30",
        "url": f"https://example.test/{source_id.lower()}",
        "archive_url": None,
        "raw_path": None,
        "text_path": None,
        "reliability_grade": grade,
        "independence_group": "Demo Daily",
        "notes": "Synthetic analysis source.",
        "public_export": True,
    })


def append_person(tcr, case_dir, entity_id, name):
    tcr.append_jsonl(tcr.record_path(case_dir, "entities"), {
        "entity_id": entity_id,
        "entity_type": "person",
        "name": name,
        "display_name": name,
        "aliases": [],
        "status": "confirmed",
        "role_tags": ["person_mentioned"],
        "privacy_level": "public_figure",
        "living_status": "unknown",
        "source_ids": ["SA"],
        "claim_ids": ["C_A"],
        "public_export": True,
        "notes": "Synthetic person.",
    })


def test_export_analysis_charts_writes_extended_chart_package(tmp_path):
    tcr = load_tcr()
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", "Analysis Case"])

    append_source(tcr, case_dir, "SA", "A")
    append_source(tcr, case_dir, "SB", "B")
    append_person(tcr, case_dir, "E_A", "Public A")
    append_person(tcr, case_dir, "E_B", "Public B")
    tcr.append_jsonl(tcr.record_path(case_dir, "claims"), {
        "claim_id": "C_A",
        "claim": "Synthetic claim supported by two sources.",
        "claim_type": "event",
        "status": "corroborated",
        "confidence": 0.85,
        "source_ids": ["SA", "SB"],
        "contradicts": [],
        "supports": [],
        "privacy_review": "clear",
        "public_export": True,
        "notes": "Synthetic claim.",
    })
    tcr.append_jsonl(tcr.record_path(case_dir, "events"), {
        "event_id": "EV_A",
        "title": "Synthetic event",
        "event_type": "timeline_anchor",
        "start_date": "1970",
        "end_date": None,
        "date_precision": "year",
        "place_ids": [],
        "entity_ids": ["E_A", "E_B"],
        "artifact_ids": [],
        "claim_ids": ["C_A"],
        "source_ids": ["SA"],
        "confidence": 0.8,
        "status": "single_source",
        "public_export": True,
        "notes": "Synthetic event.",
    })
    tcr.append_jsonl(tcr.record_path(case_dir, "event_links"), {
        "event_link_id": "EL_A",
        "event_id": "EV_A",
        "entity_id": "E_A",
        "relation_type": "participant",
        "relationship_class": "personnel_bridge",
        "basis": "Synthetic event link.",
        "claim_ids": ["C_A"],
        "source_ids": ["SA"],
        "confidence": 0.8,
        "status": "single_source",
        "public_export": True,
        "notes": "Synthetic event link.",
    })
    tcr.append_jsonl(tcr.record_path(case_dir, "relationships"), {
        "rel_id": "R_A",
        "src_entity_id": "E_A",
        "dst_entity_id": "E_B",
        "relation_type": "co_participant_in_event",
        "relationship_class": "personnel_bridge",
        "start_date": "1970",
        "end_date": None,
        "claim_ids": ["C_A"],
        "source_ids": ["SA", "SB"],
        "confidence": 0.85,
        "status": "corroborated",
        "public_export": True,
        "notes": "Synthetic relationship.",
    })

    out = tmp_path / "analysis"
    tcr.main(["export-analysis-charts", str(case_dir), "--out-dir", str(out)])

    expected = [
        "analysis_charts.html",
        "01_cluster_bridge_sankey.html",
        "02_layered_knowledge_graph.html",
        "13_layered_knowledge_graph_v2.html",
        "03_evidence_confidence_heatmap.html",
        "04_bridge_fragility.html",
        "05_claim_corroboration_matrix.html",
        "06_source_quality_dashboard.html",
        "07_sixdof_path_atlas.html",
        "08_contradiction_boundary_overlay.html",
        "09_temporal_cluster_swimlanes.html",
        "10_relationship_type_treemap.html",
        "11_person_source_bipartite.html",
        "12_public_narrative_readiness.html",
        "cluster_bridge_sankey_nodes.csv",
        "cluster_bridge_sankey_links.csv",
        "layered_knowledge_graph_nodes.csv",
        "layered_knowledge_graph_edges.csv",
        "layered_knowledge_graph_v2_nodes.csv",
        "layered_knowledge_graph_v2_edges.csv",
        "layered_knowledge_graph_v2_layers.csv",
        "evidence_confidence_heatmap.csv",
        "evidence_confidence_heatmap_aggregate.csv",
        "bridge_fragility.csv",
        "bridge_fragility_segments.csv",
        "claim_corroboration_matrix.csv",
        "claim_corroboration_edges.csv",
        "source_quality_dashboard.csv",
        "sixdof_path_atlas.csv",
        "sixdof_path_segments.csv",
        "contradiction_boundary_overlay.csv",
        "temporal_cluster_swimlanes.csv",
        "relationship_type_treemap.csv",
        "person_source_bipartite_nodes.csv",
        "person_source_bipartite_edges.csv",
        "public_narrative_readiness.csv",
    ]
    for name in expected:
        assert (out / name).exists(), name
    index_html = (out / "analysis_charts.html").read_text(encoding="utf-8")
    assert "01_cluster_bridge_sankey.html" in index_html
    assert "Open interactive chart" in index_html
    chart_pages = [name for name in expected if name.endswith(".html") and name != "analysis_charts.html"]
    for name in chart_pages:
        chart_html = (out / name).read_text(encoding="utf-8")
        assert "<svg" in chart_html
        assert "data-search" in chart_html
        assert "data-inspector" in chart_html
        assert "Data preview" in chart_html
        assert "chart-tooltip" in chart_html
        assert "click-flash" in chart_html
        assert "is-related" in chart_html
        assert "selectedPulse" in chart_html

    heatmap = read_csv(out / "evidence_confidence_heatmap.csv")
    assert heatmap[0]["claim_id"] == "C_A"
    assert heatmap[0]["source_count"] == "2"
    assert heatmap[0]["readiness"] == "public_ready"

    bipartite_edges = read_csv(out / "person_source_bipartite_edges.csv")
    assert any(row["person_id"] == "E_A" and row["source_id"] == "SA" for row in bipartite_edges)

    layered_edges = read_csv(out / "layered_knowledge_graph_edges.csv")
    assert layered_edges[0]["relationship_class"] == "personnel_bridge"

    layered_v2_edges = read_csv(out / "layered_knowledge_graph_v2_edges.csv")
    assert layered_v2_edges[0]["readiness"] in {"public_ready", "usable_with_context", "source_note_required"}
    assert "caveat" in layered_v2_edges[0]

    layered_v2_layers = read_csv(out / "layered_knowledge_graph_v2_layers.csv")
    assert {row["layer"] for row in layered_v2_layers} >= {"person", "event"}

    relation_buckets = read_csv(out / "relationship_type_treemap.csv")
    assert any(row["relationship_class"] == "personnel_bridge" for row in relation_buckets)

    readiness = read_csv(out / "public_narrative_readiness.csv")
    assert {row["record_type"] for row in readiness} >= {"claim", "event", "event_link", "relationship"}
