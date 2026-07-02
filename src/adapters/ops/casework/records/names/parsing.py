"""Parsing helpers for user-provided name lists."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def normalize_lookup(value: str | None) -> set[str]:
    if not value:
        return set()
    collapsed = re.sub(r"\s+", " ", value.strip().casefold())
    compact = re.sub(r"[^a-z0-9]+", "", collapsed)
    return {key for key in {collapsed, compact} if key}


def parse_name_entries(names: list[str] | None, names_files: list[str] | None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for names_file in names_files or []:
        path = Path(names_file).expanduser()
        if not path.exists():
            raise SystemExit(f"Missing names file: {path}")
        for line in path.read_text(encoding="utf-8").splitlines():
            _add_line(entries, line, str(path))
    for name in names or []:
        _add_line(entries, name, "--name")
    return [_strip_keys(entry) for entry in _merge_entries(entries)]


def _add_line(entries: list[dict[str, Any]], raw: str, origin: str) -> None:
    line = raw.strip()
    if not line or line.startswith("#"):
        return
    parts = [part.strip() for part in line.split("|") if part.strip()]
    if not parts:
        return
    aliases: list[str] = []
    seen_aliases: set[str] = set()
    for part in parts:
        key = part.casefold()
        if key in seen_aliases:
            continue
        seen_aliases.add(key)
        aliases.append(part)
    entries.append({"primary": parts[0], "aliases": aliases, "origin": origin})


def _merge_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for entry in entries:
        keys = set().union(*(normalize_lookup(alias) for alias in entry["aliases"]))
        matching = [idx for idx, existing in enumerate(merged) if keys & existing["keys"]]
        if not matching:
            merged.append({"primary": entry["primary"], "aliases": list(entry["aliases"]), "origin": entry["origin"], "keys": keys})
            continue
        base = merged[matching[0]]
        _merge_aliases(base, entry["aliases"])
        base["keys"].update(keys)
        _merge_origins(base, str(entry["origin"]))
        for idx in reversed(matching[1:]):
            other = merged.pop(idx)
            _merge_aliases(base, other["aliases"])
            base["keys"].update(other["keys"])
            _merge_origins(base, str(other["origin"]))
    return merged


def _merge_aliases(base: dict[str, Any], aliases: list[str]) -> None:
    alias_keys = {str(existing).casefold() for existing in base["aliases"]}
    for alias in aliases:
        if alias.casefold() not in alias_keys:
            base["aliases"].append(alias)
            alias_keys.add(alias.casefold())


def _merge_origins(base: dict[str, Any], origin_text: str) -> None:
    origins = str(base["origin"]).split(";")
    for origin in origin_text.split(";"):
        if origin and origin not in origins:
            base["origin"] = f"{base['origin']};{origin}"
            origins.append(origin)


def _strip_keys(entry: dict[str, Any]) -> dict[str, Any]:
    return {"primary": entry["primary"], "aliases": entry["aliases"], "origin": entry["origin"]}
