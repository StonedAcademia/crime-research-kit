"""Runtime access to the canonical lane registry."""

from __future__ import annotations

import copy
import json
from importlib.resources import files
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

from crime_research_kit._runtime.core.paths import source_repo_root

try:
    from importlib.resources.abc import Traversable
except ImportError:  # Python 3.10 exposes Traversable from importlib.abc.
    from importlib.abc import Traversable


def default_lanes_path(repo_root: Path | None = None) -> Path | Traversable:
    root = repo_root or source_repo_root(Path(__file__).resolve())
    if root is None:
        return files("crime_research_kit._runtime.core.lanes").joinpath("registry_data")
    checkout_path = root / "docs" / "registry"
    if repo_root is not None or checkout_path.exists():
        return checkout_path
    return files("crime_research_kit._runtime.core.lanes").joinpath("registry_data")


def load_lanes(path: Path | None = None) -> dict[str, Any]:
    if path is not None:
        return _read_lanes(path)
    return copy.deepcopy(_load_default_lanes())


@lru_cache(maxsize=1)
def _load_default_lanes() -> dict[str, Any]:
    return _read_lanes(default_lanes_path())


def _join(path: Any, name: str):
    return path / name if isinstance(path, Path) else path.joinpath(name)


def _read_lanes(path: Any) -> dict[str, Any]:
    if path.is_dir():
        return _read_sharded_lanes(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _read_sharded_lanes(path: Any) -> dict[str, Any]:
    index = json.loads(_join(path, "index.json").read_text(encoding="utf-8"))
    lanes: dict[str, Any] = {}
    templates: dict[str, Any] = {}
    for shard in index["lane_shards"]:
        lanes.update(json.loads(_join(path, shard).read_text(encoding="utf-8")))
    for shard in index["template_shards"]:
        templates.update(json.loads(_join(path, shard).read_text(encoding="utf-8")))
    return {
        "version": index["version"],
        "fallback_source_lanes": index["fallback_source_lanes"],
        "fallback_public_record_lanes": index["fallback_public_record_lanes"],
        "lanes": lanes,
        "templates": templates,
    }


def lane_records(
    *,
    public_record_plan: bool | None = None,
    source_lane_inference: bool | None = None,
) -> dict[str, dict[str, Any]]:
    lanes = load_lanes()["lanes"]
    out: dict[str, dict[str, Any]] = {}
    for lane_id, row in lanes.items():
        if public_record_plan is not None and bool(row.get("public_record_plan")) != public_record_plan:
            continue
        if source_lane_inference is not None and bool(row.get("source_lane_inference")) != source_lane_inference:
            continue
        out[lane_id] = copy.deepcopy(row)
    return out


def lane_names(
    *,
    public_record_plan: bool | None = None,
    source_lane_inference: bool | None = None,
) -> list[str]:
    return list(lane_records(public_record_plan=public_record_plan, source_lane_inference=source_lane_inference))


def template_records() -> dict[str, dict[str, Any]]:
    return copy.deepcopy(load_lanes()["templates"])


def fallback_source_lanes() -> list[str]:
    return list(load_lanes()["fallback_source_lanes"])


def fallback_public_record_lanes() -> list[str]:
    return list(load_lanes()["fallback_public_record_lanes"])


def lane_triggers(*, source_lane_inference: bool = True) -> dict[str, tuple[str, ...]]:
    records = lane_records(source_lane_inference=True) if source_lane_inference else lane_records()
    return {lane_id: tuple(row.get("triggers") or ()) for lane_id, row in records.items()}


def infer_lanes(subject: str | None, explicit_lanes: Sequence[str] | None = None) -> list[str]:
    if explicit_lanes:
        return _dedupe([str(lane) for lane in explicit_lanes])
    text = (subject or "").casefold()
    matches: list[tuple[int, str]] = []
    for lane_id, triggers in lane_triggers().items():
        positions = [text.find(trigger.casefold()) for trigger in triggers if trigger.casefold() in text]
        if positions:
            matches.append((min(positions), lane_id))
    matches.sort(key=lambda item: item[0])
    lanes = [lane_id for _position, lane_id in matches]
    return _dedupe(lanes or fallback_source_lanes())


def validate_lane_names(lanes: Sequence[str], *, public_record_plan: bool = False) -> list[str]:
    allowed = set(lane_names(public_record_plan=True if public_record_plan else None))
    unknown = [lane for lane in lanes if lane not in allowed]
    if unknown:
        raise ValueError(f"Unknown lane(s): {', '.join(sorted(unknown))}")
    return _dedupe(list(lanes))


def public_record_plan(lane: str, subject: str) -> dict[str, Any]:
    records = lane_records()
    if lane not in records:
        raise ValueError(f"Unknown lane: {lane}")
    row = records[lane]
    if not row.get("public_record_plan"):
        raise ValueError(f"Lane is not valid for public-record planning: {lane}")
    triggers = list(row.get("triggers") or [])
    return {
        "lane": lane,
        "skill": row["skill"],
        "template": row["template"],
        "source_types": list(row.get("source_types") or []),
        "notes": row["notes"],
        "suggested_queries": [f'"{subject}" {term}' for term in triggers[:5]],
        "recommended_next_commands": [
            "add-source or ingest-url each public source before extraction",
            f"draft_extraction with template {row['template']} for lane-specific packets",
            "validate after imports",
        ],
    }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out
