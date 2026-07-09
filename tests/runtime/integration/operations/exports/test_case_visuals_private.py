import json

from tests.runtime.integration.operations.exports.helpers.case_visuals import build_visual_case, read_csv


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
