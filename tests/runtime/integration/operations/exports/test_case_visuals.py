import csv
import json

from crime_research_kit._runtime.adapters.ops.evidence.reports.analysis.pages.clustered_rules import (
    cluster_for,
    semantic_facets,
)
from tests.helpers import load_ledger_cli


def load_tcr():
    return load_ledger_cli()


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_cluster_rules_prioritize_ranges_and_emit_activity_facets():
    cid, label = cluster_for("event", "Subproject 3 university grant for LSD materials")

    assert cid == "SP_001_020"
    assert label == "Subprojects 001-020"
    assert set(semantic_facets("Subproject 3 university grant for LSD materials")) >= {
        "activity_academic_front",
        "activity_drug_chemical_bio",
    }


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
        "index.html",
        "manifest.json",
        "static/app.css",
        "static/app.js",
        "data/evidence_readiness.js",
        "data/cluster_overview.js",
        "data/cluster_detail.js",
        "data/cluster_detail.context.js",
        "data/cluster_detail.all.js",
        "data/source_subproject.js",
        "data/relationship_network.js",
        "data/relationship_network.context.js",
        "data/relationship_network.all.js",
        "data/timeline_movement.js",
        "data/claim_source_matrix.js",
        "consoles/evidence_readiness.html",
        "consoles/cluster_overview.html",
        "consoles/cluster_detail.html",
        "consoles/source_subproject.html",
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

    github_out = case_dir / "github_export"
    for name in expected:
        assert (github_out / name).exists(), name
    assert (github_out / ".nojekyll").exists()

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    github_manifest = json.loads((github_out / "manifest.json").read_text(encoding="utf-8"))
    assert github_manifest == manifest
    assert manifest["include_private"] is False
    assert manifest["default_mode"] == "public"
    assert manifest["available_modes"] == ["public"]
    assert manifest["contains_private_bundle"] is False
    assert manifest["modes"]["public"]["data_prefix"] == "data"
    assert manifest["modes"]["public"]["audit_prefix"] == "audit"
    assert manifest["main"] == "index.html"
    assert manifest["consoles"] == [
        "evidence_readiness",
        "cluster_overview",
        "cluster_detail",
        "source_subproject",
        "relationship_network",
        "timeline_movement",
        "claim_source_matrix",
    ]
    assert manifest["nav_groups"] == [
        {
            "id": "evidence_overview",
            "title": "Evidence Overview",
            "consoles": ["evidence_readiness", "cluster_overview", "claim_source_matrix"],
        },
        {
            "id": "relationship_graphs",
            "title": "Relationship Graphs",
            "consoles": ["cluster_detail", "relationship_network"],
        },
        {
            "id": "timeline_source_map",
            "title": "Timeline & Source Map",
            "consoles": ["timeline_movement", "source_subproject"],
        },
    ]
    assert manifest["cluster_policy"]["default_edge_visibility"].startswith("default edges")
    assert "static/app.js" in manifest["artifacts"]
    assert "data/relationship_network.context.js" in manifest["artifacts"]

    main_html = (out / "index.html").read_text(encoding="utf-8")
    network_html = (out / "consoles" / "relationship_network.html").read_text(encoding="utf-8")
    network_data = (out / "data" / "relationship_network.js").read_text(encoding="utf-8")
    cluster_data = (out / "data" / "cluster_overview.js").read_text(encoding="utf-8")
    static_js = (out / "static" / "app.js").read_text(encoding="utf-8")

    assert not (out / "deck.html").exists()
    assert not (out / "explorer.html").exists()
    assert "<iframe" not in main_html
    assert "data-crk-nav-toggle" in main_html
    assert "data-crk-sidebar" in main_html
    assert "data-crk-mode-option=\"public\"" in main_html
    assert "data-crk-mode-option=\"private\"" in main_html
    assert "Internal data was not bundled" in main_html
    assert "data-deck" not in main_html
    assert "deck-slide" not in main_html
    assert "crk-nav-group" in main_html
    assert ">Main</a>" in main_html
    assert "static/app.js" in main_html
    assert "type=\"application/json\"" not in main_html
    assert "Evidence Readiness" in main_html
    assert "Subproject Matrix" not in main_html
    assert not (out / "data" / "subproject_matrix.js").exists()
    assert not (out / "consoles" / "subproject_matrix.html").exists()
    assert not (out / "data" / "private").exists()
    assert not (out / "audit" / "private").exists()
    assert not (github_out / "data" / "private").exists()
    assert not (github_out / "audit" / "private").exists()
    assert "Relationship Network" in main_html
    assert "Evidence Overview" in main_html
    assert "Relationship Graphs" in main_html
    assert "Timeline &amp; Source Map" in main_html
    assert "visual-index-group" in main_html
    assert "data-visual-kind=\"cytoscape-network\"" in network_html
    assert "data-crk-sidebar" in network_html
    assert "../index.html" in network_html
    assert "../static/app.js" in network_html
    assert "../data/relationship_network.js" in network_html
    assert "type=\"application/json\"" not in network_html
    assert "window.__CRK_VISUAL_DATA__" in network_data
    assert "\"graph_variants\":[\"default\",\"context\",\"all\"]" in network_data
    assert "\"overview_mode\":\"cluster_aggregate\"" in network_data
    assert "\"node_id\":\"CLUSTER:" in network_data
    assert "\"show_all_nodes\":true" in network_data
    assert "\"evidence_footprint_score\":" in cluster_data
    assert "\"record_count\":" in cluster_data
    assert "\"relationship_count\":" in cluster_data
    assert "\"default_relationship_count\":" in cluster_data
    assert "Cluster evidence footprint" in static_js
    assert "Strongest" in static_js
    assert "Full" in static_js
    assert "crkVisualMode" in static_js
    assert "data/private" in static_js
    assert "Layered Knowledge Graph" not in main_html + network_html
    assert "Data preview" not in network_html

    cluster_rows = read_csv(out / "audit" / "cluster_overview.csv")
    assert {"evidence_footprint_score", "record_count", "relationship_count", "default_relationship_count"} <= set(cluster_rows[0])
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
    github_out = case_dir / "github_export"
    github_manifest = json.loads((github_out / "manifest.json").read_text(encoding="utf-8"))
    assert github_manifest == manifest
    assert manifest["include_private"] is True
    assert manifest["default_mode"] == "public"
    assert manifest["available_modes"] == ["public", "private"]
    assert manifest["contains_private_bundle"] is True
    assert manifest["modes"]["public"]["data_prefix"] == "data"
    assert manifest["modes"]["private"]["data_prefix"] == "data/private"
    assert manifest["modes"]["private"]["audit_prefix"] == "audit/private"
    assert "public-export rows only" in manifest["scope"]
    assert "internal review" in manifest["modes"]["private"]["scope"]
    network_html = (out / "consoles" / "relationship_network.html").read_text(encoding="utf-8")
    network_data = (out / "data" / "relationship_network.all.js").read_text(encoding="utf-8")
    private_network_data = (out / "data" / "private" / "relationship_network.all.js").read_text(encoding="utf-8")
    assert (github_out / ".nojekyll").exists()
    assert (github_out / "data" / "private" / "relationship_network.all.js").exists()
    assert (github_out / "audit" / "private" / "people_edges.csv").exists()
    assert "data-crk-private-available=\"true\"" in network_html
    assert "Public data loads first" in network_html
    assert '"include_private":false' in network_data
    assert '"include_private":true' in private_network_data
    people_edges = read_csv(out / "audit" / "people_edges.csv")
    private_people_edges = read_csv(out / "audit" / "private" / "people_edges.csv")
    assert all("E_PRIVATE" not in {row["src_entity_id"], row["dst_entity_id"]} for row in people_edges)
    assert any("E_PRIVATE" in {row["src_entity_id"], row["dst_entity_id"]} for row in private_people_edges)
