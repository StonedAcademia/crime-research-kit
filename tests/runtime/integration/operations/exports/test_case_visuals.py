import csv
import json

from tests.helpers import load_ledger_cli


def load_tcr():
    return load_ledger_cli()


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
        "notes": "Synthetic visual source.",
        "public_export": True,
    })


def append_person(tcr, case_dir, entity_id, name, public=True):
    tcr.append_jsonl(tcr.record_path(case_dir, "entities"), {
        "entity_id": entity_id,
        "entity_type": "person",
        "name": name,
        "display_name": name,
        "aliases": [],
        "status": "confirmed" if public else "candidate",
        "role_tags": ["person_mentioned"],
        "privacy_level": "public_figure" if public else "unknown",
        "living_status": "unknown",
        "source_ids": ["SA"],
        "claim_ids": ["C_A"],
        "public_export": public,
        "notes": "Synthetic person.",
    })


def build_visual_case(tmp_path):
    tcr = load_tcr()
    case_dir = tmp_path / "case"
    tcr.main(["init-case", str(case_dir), "--title", "Visual Case"])
    append_source(tcr, case_dir, "SA", "A")
    append_source(tcr, case_dir, "SB", "B")
    append_person(tcr, case_dir, "E_A", "Public A")
    append_person(tcr, case_dir, "E_B", "Public B")
    append_person(tcr, case_dir, "E_PRIVATE", "Private Person", public=False)
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
        "entity_ids": ["E_A", "E_B", "E_PRIVATE"],
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
    return tcr, case_dir


def test_export_case_visuals_writes_curated_package(tmp_path):
    tcr, case_dir = build_visual_case(tmp_path)
    out = tmp_path / "visuals"

    tcr.main(["export-case-visuals", str(case_dir), "--out-dir", str(out)])

    expected = [
        "deck.html",
        "explorer.html",
        "manifest.json",
        "static/app.css",
        "static/app.js",
        "data/evidence_readiness.js",
        "data/cluster_overview.js",
        "data/cluster_detail.js",
        "data/cluster_detail.context.js",
        "data/cluster_detail.all.js",
        "data/source_subproject.js",
        "data/subproject_matrix.js",
        "data/relationship_network.js",
        "data/relationship_network.context.js",
        "data/relationship_network.all.js",
        "data/timeline_movement.js",
        "data/claim_source_matrix.js",
        "consoles/evidence_readiness.html",
        "consoles/cluster_overview.html",
        "consoles/cluster_detail.html",
        "consoles/source_subproject.html",
        "consoles/subproject_matrix.html",
        "consoles/relationship_network.html",
        "consoles/timeline_movement.html",
        "consoles/claim_source_matrix.html",
        "audit/readiness_rows.csv",
        "audit/source_quality.csv",
        "audit/cluster_overview.csv",
        "audit/cluster_detail_edges.csv",
        "audit/source_subproject_edges.csv",
        "audit/subproject_matrix.csv",
        "audit/cluster_timeline.csv",
        "audit/hub_nodes.csv",
        "audit/facet_counts.csv",
        "audit/relationship_nodes.csv",
        "audit/relationship_edges.csv",
        "audit/people_edges.csv",
        "audit/timeline_events.csv",
        "audit/claim_source_matrix.csv",
    ]
    for name in expected:
        assert (out / name).exists(), name

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["include_private"] is False
    assert manifest["consoles"] == [
        "evidence_readiness",
        "cluster_overview",
        "cluster_detail",
        "source_subproject",
        "subproject_matrix",
        "relationship_network",
        "timeline_movement",
        "claim_source_matrix",
    ]
    assert manifest["cluster_policy"]["default_edge_visibility"].startswith("default edges")
    assert "static/app.js" in manifest["artifacts"]
    assert "data/relationship_network.context.js" in manifest["artifacts"]

    deck_html = (out / "deck.html").read_text(encoding="utf-8")
    explorer_html = (out / "explorer.html").read_text(encoding="utf-8")
    network_html = (out / "consoles" / "relationship_network.html").read_text(encoding="utf-8")
    network_data = (out / "data" / "relationship_network.js").read_text(encoding="utf-8")

    assert "<iframe" not in deck_html
    assert "data-crk-nav-toggle" in deck_html
    assert "data-crk-sidebar" in deck_html
    assert "data-deck-slide-nav" in deck_html
    assert "data-deck-stage" in deck_html
    assert "static/app.js" in deck_html
    assert "type=\"application/json\"" not in deck_html
    assert "Evidence Readiness" in deck_html
    assert "Relationship Network" in explorer_html
    assert "data-crk-nav-toggle" in explorer_html
    assert "static/app.js" in explorer_html
    assert "data-visual-kind=\"cytoscape-network\"" in network_html
    assert "data-crk-sidebar" in network_html
    assert "../static/app.js" in network_html
    assert "../data/relationship_network.js" in network_html
    assert "type=\"application/json\"" not in network_html
    assert "window.__CRK_VISUAL_DATA__" in network_data
    assert "\"graph_variants\":[\"default\",\"context\",\"all\"]" in network_data
    assert "Layered Knowledge Graph" not in deck_html + explorer_html + network_html
    assert "Data preview" not in network_html

    people_edges = read_csv(out / "audit" / "people_edges.csv")
    assert any(row["src_entity_id"] == "E_A" and row["dst_entity_id"] == "E_B" for row in people_edges)
    assert all("E_PRIVATE" not in {row["src_entity_id"], row["dst_entity_id"]} for row in people_edges)
    relationship_edges = read_csv(out / "audit" / "relationship_edges.csv")
    assert {"cluster_id", "cluster_label", "edge_weight", "edge_visibility", "facet_types"} <= set(relationship_edges[0])
    relationship_nodes = read_csv(out / "audit" / "relationship_nodes.csv")
    assert {"cluster_id", "cluster_label", "hub_role", "node_visibility"} <= set(relationship_nodes[0])


def test_export_case_visuals_include_private_uses_internal_scope(tmp_path):
    tcr, case_dir = build_visual_case(tmp_path)
    out = tmp_path / "internal-visuals"

    tcr.main(["export-case-visuals", str(case_dir), "--out-dir", str(out), "--include-private"])

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["include_private"] is True
    assert "internal review" in manifest["scope"]
    network_html = (out / "consoles" / "relationship_network.html").read_text(encoding="utf-8")
    network_data = (out / "data" / "relationship_network.all.js").read_text(encoding="utf-8")
    assert '"include_private":true' in network_data
    people_edges = read_csv(out / "audit" / "people_edges.csv")
    assert any("E_PRIVATE" in {row["src_entity_id"], row["dst_entity_id"]} for row in people_edges)
