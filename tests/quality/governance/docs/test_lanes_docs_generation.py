from pathlib import Path

from crime_research_kit._runtime.core.lanes import docs as lane_docs
from crime_research_kit._runtime.core.lanes.registry import default_lanes_path, load_lanes
from tests.helpers import KIT_ROOT

ROOT = KIT_ROOT
LANE_REGISTRY_DOC = ROOT / ".agents" / "skills" / "truecrime-cult-research" / "references" / "lane_registry.md"
ROUTING_MATRIX_DOC = ROOT / ".agents" / "skills" / "public-records-router" / "references" / "routing_matrix.md"


def test_lane_registry_doc_matches_renderer():
    rendered = lane_docs.render_lane_registry_markdown(load_lanes()) + "\n"

    assert LANE_REGISTRY_DOC.read_text(encoding="utf-8") == rendered


def test_routing_matrix_doc_matches_renderer():
    rendered = lane_docs.render_routing_matrix_markdown(load_lanes()) + "\n"

    assert ROUTING_MATRIX_DOC.read_text(encoding="utf-8") == rendered


def test_lane_generation_uses_checkout_paths_after_runtime_move():
    generated = lane_docs.generated_paths()

    assert default_lanes_path() == ROOT / "docs" / "registry"
    assert generated[LANE_REGISTRY_DOC] == lane_docs.render_lane_registry_markdown(load_lanes()) + "\n"
    assert generated[ROUTING_MATRIX_DOC] == lane_docs.render_routing_matrix_markdown(load_lanes()) + "\n"
