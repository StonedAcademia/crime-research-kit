"""Generate lane reference markdown from docs/registry/lanes.json."""

from __future__ import annotations

import argparse
from pathlib import Path

from .registry import load_lanes

MARKER = "<!-- Generated from docs/registry/lanes.json; edit the registry, not this table. -->"
CATEGORIES = ("public_record", "support", "review")


def render_lane_registry_markdown(registry: dict) -> str:
    lines = [
        MARKER,
        "",
        "# Lane Registry",
        "",
        "Lane and extraction-template metadata shared by CLI, MCP, and skills.",
        "",
    ]
    lanes = registry["lanes"]
    for category in CATEGORIES:
        rows = [(lane_id, row) for lane_id, row in sorted(lanes.items()) if row["category"] == category]
        if not rows:
            continue
        lines.extend([f"## {category.replace('_', ' ').title()}", "", _lane_table(rows), ""])
    lines.extend(["## Templates", "", "| Template | File | Notes |", "| --- | --- | --- |"])
    for template_id, row in sorted(registry["templates"].items()):
        lines.append(f"| `{template_id}` | `{row['template_file']}` | {_cell(row['notes'])} |")
    return "\n".join(lines)


def render_routing_matrix_markdown(registry: dict) -> str:
    lanes = [
        (lane_id, row)
        for lane_id, row in sorted(registry["lanes"].items())
        if row.get("public_record_plan")
    ]
    return "\n".join(
        [
            MARKER,
            "",
            "# Public Records Routing Matrix",
            "",
            "Use this matrix to choose the next skill and extraction template.",
            "",
            _lane_table(lanes),
            "",
            "## Safety Order",
            "",
            "1. Resolve identity ambiguity before collecting sensitive person-specific records.",
            "2. Preserve source metadata before extracting claims from unstable web sources.",
            "3. Treat legal allegations, license discipline, missing-person records, exact geography, and property/address records as privacy-sensitive until reviewed.",
            "4. Route contradictions and source-independence issues before public narration.",
        ]
    )


def _lane_table(rows: list[tuple[str, dict]]) -> str:
    lines = ["| Lane | Skill | Template | Public plan | Use For |", "| --- | --- | --- | --- | --- |"]
    for lane_id, row in rows:
        public_plan = "yes" if row.get("public_record_plan") else "no"
        lines.append(
            f"| `{lane_id}` | `{row['skill']}` | `{row['template']}` | {public_plan} | {_cell(row['notes'])} |"
        )
    return "\n".join(lines)


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def generated_paths(repo_root: Path | None = None) -> dict[Path, str]:
    root = repo_root or Path(__file__).resolve().parents[3]
    registry = load_lanes(root / "docs" / "registry" / "lanes.json")
    return {
        root / ".agents" / "skills" / "truecrime-cult-research" / "references" / "lane_registry.md": render_lane_registry_markdown(registry) + "\n",
        root / ".agents" / "skills" / "public-records-router" / "references" / "routing_matrix.md": render_routing_matrix_markdown(registry) + "\n",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate lane reference docs.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    mismatches = []
    for path, content in generated_paths().items():
        if args.write:
            path.write_text(content, encoding="utf-8")
        elif not path.exists() or path.read_text(encoding="utf-8") != content:
            mismatches.append(str(path))
    if mismatches:
        raise SystemExit("Generated lane docs are stale: " + ", ".join(mismatches))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
