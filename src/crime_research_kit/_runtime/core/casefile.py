"""Small helpers for reading and updating CRK case folders."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

RECORD_FILES = {
    "sources": "sources.jsonl",
    "entities": "entities.jsonl",
    "places": "places.jsonl",
    "artifacts": "artifacts.jsonl",
    "claims": "claims.jsonl",
    "events": "events.jsonl",
    "event_links": "event_links.jsonl",
    "relationships": "relationships.jsonl",
    "source_spans": "source_spans.jsonl",
    "quotes": "quotes.jsonl",
    "research_actions": "research_actions.jsonl",
    "redactions": "redactions.jsonl",
}


class CasefileError(RuntimeError):
    """Raised when a case folder cannot satisfy a local workflow step."""


def case_path(case_dir: str | Path) -> Path:
    return Path(case_dir).expanduser().resolve()


def records_dir(case_dir: str | Path) -> Path:
    return case_path(case_dir) / "records"


def ensure_case(case_dir: str | Path) -> Path:
    path = case_path(case_dir)
    if not (path / "case.json").exists():
        raise CasefileError(f"Not a CRK case workspace: {path}")
    return path


def case_id(case_dir: str | Path) -> str:
    path = ensure_case(case_dir)
    data = json.loads((path / "case.json").read_text(encoding="utf-8"))
    return str(data.get("case_id") or path.name)


def record_path(case_dir: str | Path, record_name: str) -> Path:
    return ensure_case(case_dir) / "records" / RECORD_FILES[record_name]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise CasefileError(f"Invalid JSON in {path}:{lineno}: {exc}") from exc
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_records(case_dir: str | Path, record_name: str) -> list[dict[str, Any]]:
    return read_jsonl(record_path(case_dir, record_name))


def find_source(case_dir: str | Path, source_id: str) -> dict[str, Any]:
    for source in load_records(case_dir, "sources"):
        if source.get("source_id") == source_id:
            return source
    raise CasefileError(f"Source not found: {source_id}")


def update_source(case_dir: str | Path, source_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    path = record_path(case_dir, "sources")
    sources = read_jsonl(path)
    for source in sources:
        if source.get("source_id") == source_id:
            source.update(updates)
            write_jsonl(path, sources)
            return source
    raise CasefileError(f"Source not found: {source_id}")


def log_action(case_dir: str | Path, action: str, details: dict[str, Any]) -> None:
    append_jsonl(
        record_path(case_dir, "research_actions"),
        {"timestamp": dt.datetime.now(dt.timezone.utc).isoformat(), "action": action, "details": details},
    )


def case_relative(case_dir: str | Path, path: Path) -> str:
    return path.resolve().relative_to(ensure_case(case_dir)).as_posix()


def resolve_case_path(case_dir: str | Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else ensure_case(case_dir) / path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def today() -> str:
    return dt.date.today().isoformat()


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def slugify(value: str, max_len: int = 64) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return (slug[:max_len] or "item").strip("_")


def stable_id(prefix: str, *parts: str, length: int = 10) -> str:
    raw = "|".join(part or "" for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()[:length].upper()
    return f"{prefix}{digest}"
