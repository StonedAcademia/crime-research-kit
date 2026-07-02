#!/usr/bin/env python3
"""True Crime / Cult-Origin Research CLI.

This tool is intentionally simple and local-first. It helps a Codex agent create
case folders, register public sources, stage source extraction, import structured
JSON records, validate JSONL files, and export Manim-ready CSVs.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import math
import re
import sys
import textwrap
import urllib.parse
import urllib.request
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

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

SCHEMA_BY_RECORD = {
    "sources": "source.schema.json",
    "entities": "entity.schema.json",
    "places": "place.schema.json",
    "artifacts": "artifact.schema.json",
    "claims": "claim.schema.json",
    "events": "event.schema.json",
    "event_links": "event_link.schema.json",
    "relationships": "relationship.schema.json",
    "source_spans": "source_span.schema.json",
    "quotes": "quote.schema.json",
    "research_actions": "research_action.schema.json",
    "redactions": "redaction.schema.json",
}

DEFAULT_EXTRACTION = {
    "source_id": "",
    "extraction_notes": "",
    "entities": [],
    "places": [],
    "artifacts": [],
    "claims": [],
    "events": [],
    "event_links": [],
    "relationships": [],
    "source_spans": [],
    "quotes": [],
    "redactions": [],
}

def lane_registry_path() -> Path:
    script = Path(__file__).resolve()
    candidates = [
        script.parents[4] / "docs" / "lanes.json",
        Path.cwd() / "docs" / "lanes.json",
        Path.cwd() / "tc-c-kit" / "docs" / "lanes.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise SystemExit(f"Missing docs/lanes.json lane registry. Searched: {searched}")


def load_lanes_registry() -> dict[str, Any]:
    return json.loads(lane_registry_path().read_text(encoding="utf-8"))


LANE_REGISTRY = load_lanes_registry()
EXTRACTION_TEMPLATE_FILES = {
    name: row["template_file"] for name, row in LANE_REGISTRY["templates"].items()
}
EXTRACTION_TEMPLATE_NOTES = {
    name: row["notes"] for name, row in LANE_REGISTRY["templates"].items()
}
PUBLIC_RECORD_LANES = {
    lane: {
        "skill": row["skill"],
        "triggers": row["triggers"],
        "source_types": row["source_types"],
        "template": row["template"],
        "notes": row["notes"],
    }
    for lane, row in LANE_REGISTRY["lanes"].items()
    if row.get("public_record_plan")
}
FALLBACK_PUBLIC_RECORD_LANES = list(LANE_REGISTRY["fallback_public_record_lanes"])

ID_FIELDS = {
    "sources": "source_id",
    "entities": "entity_id",
    "places": "place_id",
    "artifacts": "artifact_id",
    "claims": "claim_id",
    "events": "event_id",
    "event_links": "event_link_id",
    "relationships": "rel_id",
    "source_spans": "source_span_id",
    "quotes": "quote_id",
    "research_actions": "timestamp",
    "redactions": "redaction_id",
}

PUBLIC_CONTACT_RE = re.compile(
    r"(?i)(?:\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b|\b\d{3}-\d{2}-\d{4}\b)"
)
ADDRESS_RE = re.compile(
    r"(?i)\b\d{1,6}\s+[A-Z0-9][A-Z0-9'.-]*(?:\s+[A-Z0-9][A-Z0-9'.-]*){0,5}\s+"
    r"(?:street|st\.?|avenue|ave\.?|road|rd\.?|drive|dr\.?|lane|ln\.?|boulevard|blvd\.?|court|ct\.?|place|pl\.?|way)\b"
)
CONTACT_FIELD_RE = re.compile(r"(?:^|_)(?:address|phone|telephone|email|contact|home_address|mailing_address)(?:$|_)", re.I)
ALLEGATION_RE = re.compile(
    r"\b(?:accus(?:e|ed|ation)|alleg(?:e|ed|ation)|abuse|assault|charged|criminal|"
    r"cult member|perpetrator|person of interest|suspect|rumou?r|unverified)\b",
    re.I,
)
WIRE_TERMS = {"associated press", "ap", "reuters", "upi", "united press international", "afp"}
PRESS_RELEASE_TERMS = {
    "press release",
    "news release",
    "pr newswire",
    "business wire",
    "globenewswire",
    "marketwired",
    "official statement",
}

DATE_RE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b", re.I)
CAP_PHRASE_RE = re.compile(r"\b(?:[A-Z][a-zA-Z'\-.]+(?:\s+|$)){2,5}")
TIMESTAMP_RE = re.compile(r"(?<!\d)(?:(?P<hours>\d{1,2}):)?(?P<minutes>\d{1,2}):(?P<seconds>\d{2})(?:[.,]\d{1,3})?(?!\d)")
SPEAKER_LINE_RE = re.compile(r"^\s*(?P<speaker>[A-Z][A-Za-z0-9 .'\-]{1,48}):\s*(?P<text>.+?)\s*$")

def today() -> str:
    return dt.date.today().isoformat()


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def slugify(value: str, max_len: int = 64) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return (value[:max_len] or "item").strip("_")


def stable_id(prefix: str, *parts: str, length: int = 10) -> str:
    raw = "|".join(p or "" for p in parts)
    digest = hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()[:length].upper()
    return f"{prefix}{digest}"


def case_path(case_dir: str | Path) -> Path:
    return Path(case_dir).expanduser().resolve()


def records_dir(case_dir: str | Path) -> Path:
    return case_path(case_dir) / "records"


def record_path(case_dir: str | Path, record_name: str) -> Path:
    return records_dir(case_dir) / RECORD_FILES[record_name]


def ensure_case(case_dir: str | Path) -> None:
    cdir = case_path(case_dir)
    if not (cdir / "case.json").exists():
        raise SystemExit(f"Not a case workspace: {cdir}. Run init-case first.")


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON in {path}:{lineno}: {exc}") from exc
    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def case_relative_path(case_dir: str | Path, value: str | None) -> Path | None:
    if not value:
        return None
    p = Path(value).expanduser()
    if p.is_absolute():
        return p
    return case_path(case_dir) / p


def skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def fresh_default_extraction() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_EXTRACTION))


def load_extraction_template(template_name: str) -> dict[str, Any]:
    filename = EXTRACTION_TEMPLATE_FILES.get(template_name)
    if not filename:
        raise SystemExit(f"Unknown extraction template: {template_name}")
    candidates = [
        skill_dir() / "assets" / "templates" / filename,
        Path.cwd() / ".agents" / "skills" / "truecrime-cult-research" / "assets" / "templates" / filename,
        Path.cwd() / "tc-c-kit" / ".agents" / "skills" / "truecrime-cult-research" / "assets" / "templates" / filename,
    ]
    for path in candidates:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            break
    else:
        data = fresh_default_extraction()

    packet = fresh_default_extraction()
    for key, value in data.items():
        packet[key] = value
    for key, value in DEFAULT_EXTRACTION.items():
        if key not in packet:
            packet[key] = [] if isinstance(value, list) else value
    packet["extraction_template"] = template_name
    packet["template_focus"] = EXTRACTION_TEMPLATE_NOTES[template_name]
    return packet


def load_sources(case_dir: str | Path) -> list[dict[str, Any]]:
    return read_jsonl(record_path(case_dir, "sources"))


def find_source(case_dir: str | Path, source_id: str) -> dict[str, Any] | None:
    for src in load_sources(case_dir):
        if src.get("source_id") == source_id:
            return src
    return None


def log_action(case_dir: str | Path, action: str, details: dict[str, Any]) -> None:
    append_jsonl(record_path(case_dir, "research_actions"), {
        "timestamp": now_utc(),
        "action": action,
        "details": details,
    })


def init_case(args: argparse.Namespace) -> None:
    cdir = case_path(args.case_dir)
    cdir.mkdir(parents=True, exist_ok=True)
    for sub in [
        "raw/downloads",
        "raw/sources",
        "records",
        "staging/extractions",
        "staging/candidates",
        "exports/manim",
        "notes",
    ]:
        (cdir / sub).mkdir(parents=True, exist_ok=True)
    case_meta = {
        "case_id": slugify(args.title or cdir.name),
        "title": args.title or cdir.name,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "research_scope": args.scope or "",
        "public_interest": args.public_interest or "educational/documentary research",
    }
    write_json(cdir / "case.json", case_meta)
    for fname in RECORD_FILES.values():
        p = cdir / "records" / fname
        p.touch(exist_ok=True)
    (cdir / "notes" / "case_brief.md").write_text(f"# Case brief: {case_meta['title']}\n\n", encoding="utf-8")
    print(f"Initialized case workspace: {cdir}")


def add_source_record(
    case_dir: str | Path,
    *,
    title: str,
    source_type: str,
    reliability_grade: str,
    url: str | None = None,
    author: str | None = None,
    publisher: str | None = None,
    date_published: str | None = None,
    archive_url: str | None = None,
    raw_path: str | None = None,
    text_path: str | None = None,
    content_type: str | None = None,
    capture_method: str | None = None,
    capture_timestamp: str | None = None,
    raw_sha256: str | None = None,
    text_sha256: str | None = None,
    preservation_status: str | None = None,
    notes: str = "",
    public_export: bool = True,
) -> dict[str, Any]:
    ensure_case(case_dir)
    source_id = stable_id("S", url or title, date_published or "", publisher or "")
    existing = find_source(case_dir, source_id)
    if existing:
        return existing
    rec = {
        "source_id": source_id,
        "title": title or "Untitled source",
        "source_type": source_type,
        "author": author,
        "publisher": publisher,
        "date_published": date_published,
        "date_accessed": today(),
        "url": url,
        "archive_url": archive_url,
        "raw_path": raw_path,
        "text_path": text_path,
        "content_type": content_type,
        "capture_method": capture_method,
        "capture_timestamp": capture_timestamp,
        "raw_sha256": raw_sha256,
        "text_sha256": text_sha256,
        "preservation_status": preservation_status,
        "reliability_grade": reliability_grade,
        "independence_group": None,
        "notes": notes,
        "public_export": public_export,
    }
    append_jsonl(record_path(case_dir, "sources"), rec)
    log_action(case_dir, "add_source", {"source_id": source_id, "title": title, "url": url})
    return rec


def add_source(args: argparse.Namespace) -> None:
    rec = add_source_record(
        args.case_dir,
        title=args.title,
        source_type=args.source_type,
        reliability_grade=args.reliability_grade,
        url=args.url,
        author=args.author,
        publisher=args.publisher,
        date_published=args.date_published,
        archive_url=args.archive_url,
        notes=args.notes or "",
        public_export=not args.no_public_export,
    )
    print(json.dumps(rec, indent=2, ensure_ascii=False))


def safe_filename_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    domain = slugify(parsed.netloc)
    path = slugify(parsed.path or "index")[:48]
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"{domain}_{path}_{digest}"


def fetch_url(url: str, timeout: int = 25) -> tuple[str, bytes, dict[str, str]]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "truecrime-research-kit/0.1 (+public-interest research; contact: local-user)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - user-requested URL ingestion
        content_type = resp.headers.get("Content-Type", "")
        data = resp.read()
        return content_type, data, dict(resp.headers.items())


def extract_html_text(raw: bytes, content_type: str) -> tuple[str, dict[str, Any]]:
    # Decode
    charset = "utf-8"
    m = re.search(r"charset=([^;]+)", content_type or "", flags=re.I)
    if m:
        charset = m.group(1).strip()
    try:
        html_text = raw.decode(charset, errors="replace")
    except LookupError:
        html_text = raw.decode("utf-8", errors="replace")

    meta: dict[str, Any] = {"title": None, "author": None, "date_published": None}

    # Best extraction if available.
    try:
        import trafilatura  # type: ignore
        extracted = trafilatura.extract(html_text, include_comments=False, include_tables=True)
        meta_obj = trafilatura.extract_metadata(html_text)
        if meta_obj:
            meta["title"] = getattr(meta_obj, "title", None)
            meta["author"] = getattr(meta_obj, "author", None)
            meta["date_published"] = getattr(meta_obj, "date", None)
        if extracted:
            return extracted.strip(), meta
    except Exception:
        pass

    # BeautifulSoup if available.
    try:
        from bs4 import BeautifulSoup  # type: ignore
        soup = BeautifulSoup(html_text, "html.parser")
        if soup.title and soup.title.string:
            meta["title"] = soup.title.string.strip()
        for key in ["article:published_time", "date", "pubdate", "publishdate", "timestamp"]:
            tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
            if tag and tag.get("content"):
                meta["date_published"] = tag.get("content")
                break
        for key in ["author", "article:author"]:
            tag = soup.find("meta", attrs={"name": key}) or soup.find("meta", attrs={"property": key})
            if tag and tag.get("content"):
                meta["author"] = tag.get("content")
                break
        for bad in soup(["script", "style", "noscript", "svg"]):
            bad.decompose()
        text = soup.get_text("\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip(), meta
    except Exception:
        pass

    # Crude fallback.
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.I | re.S)
    if title_match:
        meta["title"] = html.unescape(re.sub(r"\s+", " ", title_match.group(1)).strip())
    text = re.sub(r"<script\b.*?</script>", "", html_text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(), meta


def ingest_url(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    url = args.url
    filename = safe_filename_from_url(url)
    raw_path = cdir / "raw" / "downloads" / f"{filename}.html"
    text_path = cdir / "raw" / "sources" / f"{filename}.txt"
    try:
        content_type, raw, headers = fetch_url(url, timeout=args.timeout)
    except Exception as exc:
        raise SystemExit(f"Failed to fetch {url}: {exc}") from exc

    raw_path.write_bytes(raw)
    text, meta = extract_html_text(raw, content_type)
    text_path.write_text(text, encoding="utf-8")
    raw_sha256 = file_sha256(raw_path)
    text_sha256 = file_sha256(text_path)
    parsed = urllib.parse.urlparse(url)
    publisher = args.publisher or parsed.netloc
    title = args.title or meta.get("title") or url
    rec = add_source_record(
        args.case_dir,
        title=title,
        source_type=args.source_type,
        reliability_grade=args.reliability_grade,
        url=url,
        author=args.author or meta.get("author"),
        publisher=publisher,
        date_published=args.date_published or meta.get("date_published"),
        archive_url=args.archive_url,
        raw_path=str(raw_path.relative_to(cdir)),
        text_path=str(text_path.relative_to(cdir)),
        content_type=content_type,
        capture_method="ingest_url",
        capture_timestamp=now_utc(),
        raw_sha256=raw_sha256,
        text_sha256=text_sha256,
        preservation_status="captured",
        notes=args.notes or f"Fetched content-type={content_type}; bytes={len(raw)}; raw_sha256={raw_sha256}; text_sha256={text_sha256}",
        public_export=not args.no_public_export,
    )
    log_action(
        args.case_dir,
        "ingest_url",
        {
            "source_id": rec["source_id"],
            "url": url,
            "headers": headers,
            "raw_sha256": raw_sha256,
            "text_sha256": text_sha256,
            "content_type": content_type,
        },
    )
    print(f"Ingested {url}")
    print(json.dumps(rec, indent=2, ensure_ascii=False))


def draft_extraction(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    src = find_source(args.case_dir, args.source_id)
    if not src:
        raise SystemExit(f"Source not found: {args.source_id}")
    packet = load_extraction_template(args.template)
    packet["source_id"] = args.source_id
    packet["source_metadata"] = src
    packet["extraction_instructions"] = (
        "Fill arrays using only claims directly supported by this source. "
        "Treat eyewitness statements as claims. Do not infer guilt, motive, membership, or relationships. "
        "Set claim assertion_type to distinguish source-stated facts, allegations, denials, court findings, "
        "self-reports, biography claims, lead-only items, and expert context. "
        "Add source_spans for page, paragraph, timestamp, exhibit, docket item, accession, or quote-offset locators. "
        "Set public_export=false for living private persons, minors, private addresses/contact info, and weak allegations."
    )
    text_rel = src.get("text_path")
    if text_rel:
        text_path = cdir / text_rel
        packet["source_text_path"] = text_rel
        if text_path.exists():
            content = text_path.read_text(encoding="utf-8", errors="replace")
            packet["source_excerpt_for_orientation"] = content[: args.excerpt_chars]
    out = cdir / "staging" / "extractions" / f"{args.source_id}_extraction.json"
    write_json(out, packet)
    print(f"Wrote draft extraction packet: {out}")


def make_candidate_id(prefix: str, name: str, source_id: str) -> str:
    return stable_id(prefix, name, source_id, length=8)


def ner_suggest(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    sources = load_sources(args.case_dir)
    selected = [s for s in sources if not args.source_id or s.get("source_id") == args.source_id]
    candidates: list[dict[str, Any]] = []
    for src in selected:
        text_rel = src.get("text_path")
        if not text_rel:
            continue
        p = cdir / text_rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        names = sorted(set(
            re.sub(r"\s+", " ", m.group(0)).strip()
            for m in CAP_PHRASE_RE.finditer(text)
            if len(m.group(0).strip()) >= 5
        ))
        # Keep this small. It is a lead generator, not a truth engine.
        for name in names[: args.limit]:
            if name.lower() in {"new york", "los angeles", "united states", "associated press"}:
                continue
            candidates.append({
                "candidate_id": make_candidate_id("N", name, src["source_id"]),
                "name": name,
                "candidate_type": "unknown_named_entity",
                "source_id": src["source_id"],
                "status": "needs_human_or_agent_review",
            })
        for date in sorted(set(m.group(0) for m in DATE_RE.finditer(text)))[: args.limit]:
            candidates.append({
                "candidate_id": make_candidate_id("D", date, src["source_id"]),
                "name": date,
                "candidate_type": "date_or_time_expression",
                "source_id": src["source_id"],
                "status": "needs_human_or_agent_review",
            })
    out = cdir / "staging" / "candidates" / f"ner_suggestions_{today()}.json"
    write_json(out, {"candidates": candidates})
    print(f"Wrote {len(candidates)} candidates: {out}")


def normalize_lookup(value: str | None) -> set[str]:
    if not value:
        return set()
    collapsed = re.sub(r"\s+", " ", value.strip().casefold())
    compact = re.sub(r"[^a-z0-9]+", "", collapsed)
    return {key for key in {collapsed, compact} if key}


def parse_name_entries(names: list[str] | None, names_files: list[str] | None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    def add_line(raw: str, origin: str) -> None:
        line = raw.strip()
        if not line or line.startswith("#"):
            return
        parts = [part.strip() for part in line.split("|") if part.strip()]
        if not parts:
            return
        primary = parts[0]
        aliases: list[str] = []
        seen_aliases: set[str] = set()
        for part in parts:
            key = part.casefold()
            if key in seen_aliases:
                continue
            seen_aliases.add(key)
            aliases.append(part)
        entries.append({"primary": primary, "aliases": aliases, "origin": origin})

    for names_file in names_files or []:
        path = Path(names_file).expanduser()
        if not path.exists():
            raise SystemExit(f"Missing names file: {path}")
        for line in path.read_text(encoding="utf-8").splitlines():
            add_line(line, str(path))

    for name in names or []:
        add_line(name, "--name")

    merged: list[dict[str, Any]] = []
    for entry in entries:
        keys: set[str] = set()
        for alias in entry["aliases"]:
            keys.update(normalize_lookup(alias))
        matching_indexes = [
            idx
            for idx, existing in enumerate(merged)
            if keys & existing["keys"]
        ]
        if not matching_indexes:
            merged.append({
                "primary": entry["primary"],
                "aliases": list(entry["aliases"]),
                "origin": entry["origin"],
                "keys": keys,
            })
            continue

        base = merged[matching_indexes[0]]
        for alias in entry["aliases"]:
            if alias.casefold() not in {existing.casefold() for existing in base["aliases"]}:
                base["aliases"].append(alias)
        base["keys"].update(keys)
        if entry["origin"] not in str(base["origin"]).split(";"):
            base["origin"] = f"{base['origin']};{entry['origin']}"

        for idx in reversed(matching_indexes[1:]):
            other = merged.pop(idx)
            for alias in other["aliases"]:
                if alias.casefold() not in {existing.casefold() for existing in base["aliases"]}:
                    base["aliases"].append(alias)
            base["keys"].update(other["keys"])
            for origin in str(other["origin"]).split(";"):
                if origin and origin not in str(base["origin"]).split(";"):
                    base["origin"] = f"{base['origin']};{origin}"

    return [
        {"primary": entry["primary"], "aliases": entry["aliases"], "origin": entry["origin"]}
        for entry in merged
    ]


def entity_lookup_keys(entity: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for field in ("name", "display_name"):
        keys.update(normalize_lookup(entity.get(field)))
    for alias in entity.get("aliases", []) or []:
        keys.update(normalize_lookup(str(alias)))
    return keys


def build_entity_index(entities: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entity in entities:
        for key in entity_lookup_keys(entity):
            index.setdefault(key, entity)
    return index


def find_entity_for_entry(entry: dict[str, Any], index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for alias in entry["aliases"]:
        for key in normalize_lookup(alias):
            if key in index:
                return index[key]
    return None


def contains_name(text: str, name: str) -> bool:
    clean = name.strip()
    if not clean:
        return False
    return re.search(rf"(?<!\w){re.escape(clean)}(?!\w)", text, flags=re.I) is not None


def read_source_texts(case_dir: str | Path, sources: list[dict[str, Any]]) -> dict[str, str]:
    cdir = case_path(case_dir)
    texts: dict[str, str] = {}
    for source in sources:
        source_id = source.get("source_id")
        text_rel = source.get("text_path")
        if not source_id or not text_rel:
            continue
        path = cdir / str(text_rel)
        if not path.exists():
            continue
        texts[str(source_id)] = path.read_text(encoding="utf-8", errors="replace")
    return texts


def source_matches_for_entry(entry: dict[str, Any], source_texts: dict[str, str]) -> set[str]:
    matches: set[str] = set()
    for source_id, text in source_texts.items():
        if any(contains_name(text, alias) for alias in entry["aliases"]):
            matches.add(source_id)
    return matches


def make_candidate_entity(entry: dict[str, Any], source_ids: Iterable[str]) -> dict[str, Any]:
    clean_sources = sorted(set(source_ids))
    return {
        "entity_id": stable_id("E", entry["primary"], "name_list_candidate"),
        "entity_type": "person",
        "name": entry["primary"],
        "display_name": entry["primary"],
        "aliases": entry["aliases"][1:],
        "status": "candidate",
        "role_tags": ["person_mentioned"],
        "privacy_level": "unknown",
        "living_status": "unknown",
        "source_ids": clean_sources,
        "claim_ids": [],
        "public_export": False,
        "notes": (
            "Candidate created from user-provided name list by link-names. "
            "Do not treat as identified or publicly export until source-reviewed."
        ),
    }


def refresh_entity_from_name_entry(entity: dict[str, Any], entry: dict[str, Any], source_ids: Iterable[str]) -> bool:
    changed = False
    existing_sources = clean_id_list(entity.get("source_ids"))
    merged_sources = sorted(set(existing_sources) | set(source_ids))
    if merged_sources != existing_sources:
        entity["source_ids"] = merged_sources
        changed = True

    aliases = list(entity.get("aliases", []) or [])
    alias_keys = {str(alias).casefold() for alias in aliases}
    entity_name_keys = set()
    for field in ("name", "display_name"):
        value = entity.get(field)
        if value:
            entity_name_keys.add(str(value).casefold())
    for alias in entry["aliases"]:
        alias_key = alias.casefold()
        if alias_key in entity_name_keys or alias_key in alias_keys:
            continue
        aliases.append(alias)
        alias_keys.add(alias_key)
        changed = True
    if aliases != (entity.get("aliases", []) or []):
        entity["aliases"] = aliases
    return changed


def append_if_new(case_dir: str | Path, record_name: str, row: dict[str, Any], id_field: str, existing_ids: set[str]) -> bool:
    row_id = str(row.get(id_field, ""))
    if not row_id or row_id in existing_ids:
        return False
    append_jsonl(record_path(case_dir, record_name), row)
    existing_ids.add(row_id)
    return True


def clean_id_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item not in (None, "")]


def pair_ids(left: str, right: str) -> tuple[str, str]:
    return tuple(sorted([left, right]))  # type: ignore[return-value]


def co_mention_note(anchor: str) -> str:
    return (
        f"Name-list co-mention via {anchor}. This does not establish guilt, "
        "membership, motive, direct participation, or a source-stated relationship."
    )


def write_name_link_research_brief(
    case_dir: str | Path,
    *,
    entries: list[dict[str, Any]],
    resolved: list[dict[str, Any]],
    events: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    source_texts: dict[str, str],
    counts: dict[str, int],
) -> Path:
    cdir = case_path(case_dir)
    case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
    case_title = case_meta.get("title", cdir.name)
    names_slug = slugify("_".join(entry["primary"] for entry in entries), max_len=40)
    out = cdir / "notes" / f"name_link_research_{today()}_{names_slug}.md"

    source_titles = {str(source.get("source_id")): source.get("title", "") for source in sources}
    event_titles = [event.get("title", "") for event in events if event.get("title")]
    target_events = event_titles[:8]

    content = [
        f"# Name-link research brief: {case_title}",
        "",
        "## Purpose",
        "",
        "Use this brief to extend the source record for the listed names. The existing `link-names` pass writes only private, unverified co-mention links unless a reviewed extraction supplies stronger source-stated relationship language.",
        "",
        "## Current run",
        "",
        md_table(
            ["Metric", "Count"],
            [[key, str(value)] for key, value in sorted(counts.items())],
        ),
        "",
        "## Names",
        "",
        md_table(
            ["Input", "Entity", "Matched sources", "Origin"],
            [
                [
                    item["entry"]["primary"],
                    item["entity"].get("entity_id", ""),
                    flatten(sorted(item.get("source_ids", []))),
                    item["entry"].get("origin", ""),
                ]
                for item in resolved
            ],
        ),
        "",
        "## Suggested search queries",
        "",
    ]
    for entry in entries:
        primary = entry["primary"]
        queries = [
            f'"{primary}" "{case_title}"',
            f'"{primary}" interview testimony affidavit',
            f'"{primary}" correction retraction disputed misidentified',
        ]
        for event_title in target_events[:3]:
            queries.append(f'"{primary}" "{event_title}"')
        content.extend([f"### {primary}", ""])
        content.extend(f"- `{query}`" for query in queries)
        content.append("")

    content.extend([
        "## Source gaps",
        "",
        md_table(
            ["Name", "Gap"],
            [
                [item["entry"]["primary"], "No ingested source text currently mentions this name."]
                for item in resolved
                if not item.get("source_ids")
            ] or [["None", "All names matched at least one ingested source text or existing entity record."]],
        ),
        "",
        "## Existing source text matches",
        "",
        md_table(
            ["Source", "Title", "Text available"],
            [
                [source_id, source_titles.get(source_id, ""), "yes"]
                for source_id in sorted(source_texts)
            ] or [["None", "", "no"]],
        ),
        "",
        "## Agent-assisted web workflow",
        "",
        "1. Search the query list above using only public-interest, publicly available sources.",
        "2. Prefer official records, local reporting, strong investigative reporting, transcripts, and direct archives.",
        "3. Ingest or register each source before extracting facts:",
        "",
        "```bash",
        "python .agents/skills/truecrime-cult-research/scripts/tcr.py ingest-url tc-c-kit/data/cases/<case_slug> \"<URL>\" --source-type news_article --reliability-grade B",
        "python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID>",
        "```",
        "",
        "4. Fill the extraction packet with source-stated entities, events, claims, relationships, and event links only.",
        "5. Re-run `link-names` after new sources are imported.",
        "",
        "## Safety notes",
        "",
        "- Co-mention is not evidence of guilt, membership, motive, or participation.",
        "- Keep living private people, minors, and weak allegations out of public exports.",
        "- Upgrade relation types only when a cited source explicitly supports the wording.",
    ])

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(content) + "\n", encoding="utf-8")
    return out


def link_names(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    entries = parse_name_entries(args.name, args.names_file)
    if not entries:
        raise SystemExit("Provide at least one --name or --names-file entry")

    sources = load_sources(args.case_dir)
    entities = read_jsonl(record_path(args.case_dir, "entities"))
    events = read_jsonl(record_path(args.case_dir, "events"))
    relationships = read_jsonl(record_path(args.case_dir, "relationships"))
    event_links = read_jsonl(record_path(args.case_dir, "event_links"))
    source_texts = read_source_texts(args.case_dir, sources)

    entity_index = build_entity_index(entities)
    entity_ids = {str(entity.get("entity_id")) for entity in entities if entity.get("entity_id")}
    rel_ids = {str(rel.get("rel_id")) for rel in relationships if rel.get("rel_id")}
    event_link_ids = {str(link.get("event_link_id")) for link in event_links if link.get("event_link_id")}

    counts = {
        "input_names": len(entries),
        "matched_existing_entities": 0,
        "candidate_entities_created": 0,
        "entities_refreshed": 0,
        "event_links_created": 0,
        "relationships_created": 0,
        "duplicate_records_skipped": 0,
    }
    resolved: list[dict[str, Any]] = []
    entity_records_changed = False

    for entry in entries:
        matched_sources = source_matches_for_entry(entry, source_texts)
        entity = find_entity_for_entry(entry, entity_index)
        if entity:
            counts["matched_existing_entities"] += 1
            if refresh_entity_from_name_entry(entity, entry, matched_sources):
                counts["entities_refreshed"] += 1
                entity_records_changed = True
                entity_index = build_entity_index(entities)
        else:
            entity = make_candidate_entity(entry, matched_sources)
            if append_if_new(args.case_dir, "entities", entity, "entity_id", entity_ids):
                counts["candidate_entities_created"] += 1
                entities.append(entity)
                for key in entity_lookup_keys(entity):
                    entity_index.setdefault(key, entity)
            else:
                existing = next(
                    (
                        row
                        for row in entities
                        if row.get("entity_id") == entity.get("entity_id")
                    ),
                    None,
                )
                if existing and refresh_entity_from_name_entry(existing, entry, matched_sources):
                    counts["entities_refreshed"] += 1
                    entity_records_changed = True
                    entity = existing
                    entity_index = build_entity_index(entities)
                else:
                    counts["duplicate_records_skipped"] += 1
        resolved.append({"entry": entry, "entity": entity, "source_ids": matched_sources})

    if entity_records_changed:
        write_jsonl(record_path(args.case_dir, "entities"), entities)

    resolved_by_entity_id = {
        str(item["entity"].get("entity_id")): item
        for item in resolved
        if item["entity"].get("entity_id")
    }

    source_to_entities: dict[str, set[str]] = {}
    event_to_entities: dict[str, set[str]] = {}
    for item in resolved:
        entity_id = str(item["entity"].get("entity_id", ""))
        if not entity_id:
            continue
        for source_id in item.get("source_ids", set()):
            source_to_entities.setdefault(source_id, set()).add(entity_id)

    for event in events:
        event_id = str(event.get("event_id", ""))
        if not event_id:
            continue
        event_sources = clean_id_list(event.get("source_ids"))
        if not event_sources:
            continue
        event_entity_ids = set(clean_id_list(event.get("entity_ids")))
        matched_for_event: dict[str, set[str]] = {}
        event_text = " ".join(str(event.get(field, "")) for field in ("title", "notes"))
        for item in resolved:
            entity_id = str(item["entity"].get("entity_id", ""))
            if not entity_id:
                continue
            basis: set[str] = set()
            if entity_id in event_entity_ids:
                basis.add("existing_event_entity_id")
            if set(event_sources) & set(item.get("source_ids", set())):
                basis.add("source_text_cooccurrence")
            if event_text and any(contains_name(event_text, alias) for alias in item["entry"]["aliases"]):
                basis.add("event_text_name_match")
            if basis:
                matched_for_event[entity_id] = basis
        if not matched_for_event:
            continue
        event_to_entities[event_id] = set(matched_for_event)
        for entity_id, basis in matched_for_event.items():
            link = {
                "event_link_id": stable_id("EL", entity_id, event_id, "co_mentioned_in_event"),
                "entity_id": entity_id,
                "event_id": event_id,
                "relation_type": "co_mentioned_in_event",
                "basis": ";".join(sorted(basis)),
                "claim_ids": clean_id_list(event.get("claim_ids")),
                "source_ids": event_sources,
                "confidence": 0.45 if "existing_event_entity_id" in basis else 0.3,
                "status": "unverified",
                "public_export": False,
                "notes": co_mention_note(f"event {event_id}"),
            }
            if append_if_new(args.case_dir, "event_links", link, "event_link_id", event_link_ids):
                counts["event_links_created"] += 1
            else:
                counts["duplicate_records_skipped"] += 1

        for left, right in combinations(sorted(matched_for_event), 2):
            src_entity_id, dst_entity_id = pair_ids(left, right)
            rel = {
                "rel_id": stable_id("R", src_entity_id, dst_entity_id, "co_mentioned_with", event_id),
                "src_entity_id": src_entity_id,
                "dst_entity_id": dst_entity_id,
                "relation_type": "co_mentioned_with",
                "start_date": event.get("start_date"),
                "end_date": event.get("end_date"),
                "claim_ids": clean_id_list(event.get("claim_ids")),
                "source_ids": event_sources,
                "confidence": 0.3,
                "status": "unverified",
                "public_export": False,
                "notes": co_mention_note(f"event {event_id}"),
            }
            if append_if_new(args.case_dir, "relationships", rel, "rel_id", rel_ids):
                counts["relationships_created"] += 1
            else:
                counts["duplicate_records_skipped"] += 1

    for source_id, entity_set in sorted(source_to_entities.items()):
        for left, right in combinations(sorted(entity_set), 2):
            src_entity_id, dst_entity_id = pair_ids(left, right)
            rel = {
                "rel_id": stable_id("R", src_entity_id, dst_entity_id, "co_mentioned_with", source_id),
                "src_entity_id": src_entity_id,
                "dst_entity_id": dst_entity_id,
                "relation_type": "co_mentioned_with",
                "start_date": None,
                "end_date": None,
                "claim_ids": [],
                "source_ids": [source_id],
                "confidence": 0.25,
                "status": "unverified",
                "public_export": False,
                "notes": co_mention_note(f"source {source_id}"),
            }
            if append_if_new(args.case_dir, "relationships", rel, "rel_id", rel_ids):
                counts["relationships_created"] += 1
            else:
                counts["duplicate_records_skipped"] += 1

    brief_path = write_name_link_research_brief(
        args.case_dir,
        entries=entries,
        resolved=resolved,
        events=events,
        sources=sources,
        source_texts=source_texts,
        counts=counts,
    )
    log_action(
        args.case_dir,
        "link_names",
        {
            "names": [entry["primary"] for entry in entries],
            "counts": counts,
            "research_brief": str(brief_path.relative_to(case_path(args.case_dir))),
            "event_to_entities": {key: sorted(value) for key, value in event_to_entities.items()},
            "resolved_entity_ids": sorted(resolved_by_entity_id),
        },
    )
    print(json.dumps({"counts": counts, "research_brief": str(brief_path)}, indent=2, ensure_ascii=False))


def import_extraction(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    path = Path(args.extraction_json).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Missing extraction JSON: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    source_id = data.get("source_id")
    if not source_id:
        raise SystemExit("Extraction JSON must include source_id")
    if not find_source(args.case_dir, source_id):
        raise SystemExit(f"Unknown source_id in extraction: {source_id}")

    mapping = {
        "entities": "entities",
        "places": "places",
        "artifacts": "artifacts",
        "claims": "claims",
        "events": "events",
        "event_links": "event_links",
        "relationships": "relationships",
        "source_spans": "source_spans",
        "quotes": "quotes",
        "redactions": "redactions",
    }
    counts: dict[str, int] = {}
    for key, record_name in mapping.items():
        rows = data.get(key, []) or []
        if not isinstance(rows, list):
            raise SystemExit(f"Expected {key} to be a list")
        for row in rows:
            if not isinstance(row, dict):
                raise SystemExit(f"Expected each item in {key} to be an object")
            row.setdefault("source_ids", [source_id])
            if key in {"quotes", "source_spans"}:
                row.setdefault("source_id", source_id)
            if key == "source_spans" and not row.get("source_span_id") and row.get("span_id"):
                row["source_span_id"] = row["span_id"]
            append_jsonl(record_path(args.case_dir, record_name), row)
        counts[key] = len(rows)
    log_action(args.case_dir, "import_extraction", {"source_id": source_id, "path": str(path), "counts": counts})
    print(json.dumps({"imported": counts}, indent=2))


def load_schema(schema_name: str) -> dict[str, Any] | None:
    # Search upward from script path for the canonical docs/schemas directory,
    # while keeping the legacy schemas/ path as a compatibility fallback.
    here = Path(__file__).resolve()
    schema_dirs: list[Path] = []
    for i in range(min(len(here.parents), 6)):
        schema_dirs.append(here.parents[i] / "docs" / "schemas")
        schema_dirs.append(here.parents[i] / "schemas")
    cwd = Path.cwd()
    schema_dirs.extend([
        cwd / "tc-c-kit" / "docs" / "schemas",
        cwd / "docs" / "schemas",
        cwd / "tc-c-kit" / "schemas",
        cwd / "schemas",
    ])
    seen: set[Path] = set()
    for schema_dir in schema_dirs:
        p = schema_dir / schema_name
        if p in seen:
            continue
        seen.add(p)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


def basic_required_validation(record_name: str, row: dict[str, Any], idx: int) -> list[str]:
    required = {
        "sources": ["source_id", "title", "source_type", "reliability_grade", "date_accessed"],
        "entities": ["entity_id", "entity_type", "name", "status", "source_ids"],
        "places": ["place_id", "name", "source_ids"],
        "artifacts": ["artifact_id", "artifact_type", "name", "source_ids"],
        "claims": ["claim_id", "claim", "status", "confidence", "source_ids"],
        "events": ["event_id", "title", "event_type", "source_ids"],
        "event_links": ["event_link_id", "entity_id", "event_id", "relation_type", "source_ids"],
        "relationships": ["rel_id", "src_entity_id", "dst_entity_id", "relation_type", "source_ids"],
        "source_spans": ["source_span_id", "source_id", "locator_type", "locator"],
        "quotes": ["quote_id", "source_id", "exact_quote"],
        "research_actions": ["timestamp", "action", "details"],
        "redactions": ["redaction_id", "record_id", "reason"],
    }.get(record_name, [])
    errors = []
    for field in required:
        if field not in row or row.get(field) in (None, ""):
            errors.append(f"{record_name}[{idx}] missing required field: {field}")
    return errors


def validate(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    errors: list[str] = []
    jsonschema_validator = None
    try:
        import jsonschema  # type: ignore
        jsonschema_validator = jsonschema
    except Exception:
        jsonschema_validator = None

    for record_name, fname in RECORD_FILES.items():
        rows = read_jsonl(record_path(args.case_dir, record_name))
        schema = load_schema(SCHEMA_BY_RECORD.get(record_name, "")) if record_name in SCHEMA_BY_RECORD else None
        for idx, row in enumerate(rows, start=1):
            errors.extend(basic_required_validation(record_name, row, idx))
            if jsonschema_validator and schema:
                try:
                    jsonschema_validator.validate(instance=row, schema=schema)
                except Exception as exc:
                    errors.append(f"{record_name}[{idx}] schema error: {exc}")
    if errors:
        print("Validation failed:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Validation passed for {case_path(args.case_dir)}")


def flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ";".join(str(v) for v in value)
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: flatten(row.get(col)) for col in columns})


def public_rows(rows: Iterable[dict[str, Any]], include_private: bool = False) -> list[dict[str, Any]]:
    if include_private:
        return list(rows)
    return [r for r in rows if r.get("public_export", True) is not False]


def discover_cases(cases_root: str | Path) -> list[Path]:
    root = Path(cases_root).expanduser().resolve()
    if (root / "case.json").exists():
        return [root]
    if not root.exists():
        raise SystemExit(f"Missing cases root: {root}")
    cases = sorted(path.parent for path in root.glob("*/case.json"))
    if not cases:
        raise SystemExit(f"No case workspaces found under: {root}")
    return cases


def source_independence_key(source: dict[str, Any]) -> str:
    if source.get("independence_group"):
        return str(source["independence_group"])
    if source.get("publisher"):
        return str(source["publisher"])
    if source.get("url"):
        parsed = urllib.parse.urlparse(str(source["url"]))
        if parsed.netloc:
            return parsed.netloc.lower()
    return str(source.get("source_id", "unknown"))


def record_id(record_name: str, row: dict[str, Any], idx: int = 0) -> str:
    field = ID_FIELDS.get(record_name)
    if field and row.get(field) not in (None, ""):
        return str(row[field])
    return f"{record_name}:{idx}"


def normalize_match_text(value: Any) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urllib.parse.urlparse(raw)
    if not parsed.netloc:
        return normalize_match_text(raw)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = re.sub(r"/+$", "", parsed.path or "/")
    query = urllib.parse.urlencode(sorted(
        (key, val)
        for key, val in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    ))
    return urllib.parse.urlunparse((parsed.scheme.lower() or "https", netloc, path, "", query, ""))


def report_out_path(case_dir: str | Path, requested: str | None, default_rel: str) -> Path:
    if requested:
        return Path(requested).expanduser().resolve()
    return case_path(case_dir) / default_rel


def compact_record(record_name: str, row: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    fields = [
        "source_id",
        "entity_id",
        "claim_id",
        "event_id",
        "event_link_id",
        "rel_id",
        "source_span_id",
        "span_id",
        "title",
        "name",
        "display_name",
        "claim",
        "publisher",
        "url",
        "status",
        "source_ids",
        "public_export",
    ]
    item = {"record_type": record_name, "record_id": record_id(record_name, row, idx)}
    for field in fields:
        if row.get(field) not in (None, "", []):
            item[field] = row.get(field)
    return item


def preservation_artifact(case_dir: str | Path, source: dict[str, Any], path_field: str) -> dict[str, Any]:
    rel_value = source.get(path_field)
    artifact = {
        "field": path_field,
        "path": rel_value,
        "exists": False,
        "size_bytes": None,
        "sha256": None,
        "issue": None,
    }
    path = case_relative_path(case_dir, str(rel_value)) if rel_value else None
    if not path:
        artifact["issue"] = f"{path_field} is not set"
        return artifact
    if not path.exists():
        artifact["issue"] = f"{path_field} does not exist on disk"
        return artifact
    if not path.is_file():
        artifact["issue"] = f"{path_field} is not a file"
        return artifact
    artifact.update({
        "exists": True,
        "size_bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    })
    return artifact


def source_preservation_report(case_dir: str | Path, source: dict[str, Any]) -> dict[str, Any]:
    artifacts = [
        preservation_artifact(case_dir, source, "raw_path"),
        preservation_artifact(case_dir, source, "text_path"),
    ]
    existing_artifacts = [item for item in artifacts if item["exists"]]
    configured_missing = [
        item for item in artifacts
        if item.get("path") and not item["exists"]
    ]
    if configured_missing:
        status = "missing_artifacts"
    elif existing_artifacts:
        status = "captured"
    elif source.get("archive_url"):
        status = "registered_with_archive"
    else:
        status = "metadata_only"

    return {
        "generated_at": now_utc(),
        "source_id": source.get("source_id"),
        "title": source.get("title"),
        "url": source.get("url"),
        "archive_url": source.get("archive_url"),
        "content_type": source.get("content_type"),
        "capture_method": source.get("capture_method"),
        "capture_timestamp": source.get("capture_timestamp"),
        "preservation_status": status,
        "artifacts": artifacts,
        "warnings": [str(item["issue"]) for item in artifacts if item.get("issue")],
    }


def preserve_source(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    source = None
    for row in sources:
        if row.get("source_id") == args.source_id:
            source = row
            break
    if not source:
        raise SystemExit(f"Source not found: {args.source_id}")

    if args.archive_url:
        source["archive_url"] = args.archive_url
    if args.content_type:
        source["content_type"] = args.content_type
    source.setdefault("capture_method", "registered_source")
    source["preservation_checked_at"] = now_utc()

    report = source_preservation_report(args.case_dir, source)
    source["preservation_status"] = report["preservation_status"]
    for artifact in report["artifacts"]:
        if artifact["field"] == "raw_path" and artifact.get("sha256"):
            source["raw_sha256"] = artifact["sha256"]
            source["raw_size_bytes"] = artifact["size_bytes"]
        if artifact["field"] == "text_path" and artifact.get("sha256"):
            source["text_sha256"] = artifact["sha256"]
            source["text_size_bytes"] = artifact["size_bytes"]
    source["preservation_warnings"] = report["warnings"]

    write_jsonl(record_path(args.case_dir, "sources"), sources)
    out = report_out_path(args.case_dir, getattr(args, "out", None), f"exports/source_preservation/{args.source_id}.json")
    write_json(out, report)
    log_action(
        args.case_dir,
        "preserve_source",
        {
            "source_id": args.source_id,
            "report": str(out),
            "preservation_status": report["preservation_status"],
            "warnings": report["warnings"],
        },
    )
    print(json.dumps({"source_id": args.source_id, "preservation_status": report["preservation_status"], "report": str(out)}, indent=2, ensure_ascii=False))


def entity_resolution_context(
    entity: dict[str, Any],
    *,
    claims: list[dict[str, Any]],
    events: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    event_links: list[dict[str, Any]],
) -> dict[str, Any]:
    entity_id = str(entity.get("entity_id", ""))
    claim_ids = set(clean_id_list(entity.get("claim_ids")))
    claim_ids.update(
        str(claim.get("claim_id"))
        for claim in claims
        if entity_id and entity_id in " ".join(str(claim.get(field, "")) for field in ("claim", "notes"))
    )
    event_ids = {
        str(event.get("event_id"))
        for event in events
        if entity_id in clean_id_list(event.get("entity_ids"))
    }
    event_ids.update(
        str(link.get("event_id"))
        for link in event_links
        if str(link.get("entity_id")) == entity_id
    )
    rel_ids = {
        str(rel.get("rel_id"))
        for rel in relationships
        if entity_id in {str(rel.get("src_entity_id")), str(rel.get("dst_entity_id"))}
    }
    source_ids = set(clean_id_list(entity.get("source_ids")))
    for claim in claims:
        if str(claim.get("claim_id")) in claim_ids:
            source_ids.update(clean_id_list(claim.get("source_ids")))
    return {
        "entity_id": entity_id,
        "source_ids": sorted(source_ids),
        "claim_ids": sorted(item for item in claim_ids if item),
        "event_ids": sorted(item for item in event_ids if item),
        "relationship_ids": sorted(item for item in rel_ids if item),
        "privacy_level": entity.get("privacy_level"),
        "living_status": entity.get("living_status"),
        "public_export": entity.get("public_export", True),
    }


def append_identity_candidate(
    candidates: list[dict[str, Any]],
    *,
    reason: str,
    key: str,
    rows: list[tuple[int, dict[str, Any]]],
    context_by_id: dict[str, dict[str, Any]],
) -> None:
    if len(rows) < 2:
        return
    entity_ids = [str(row.get("entity_id")) for _idx, row in rows if row.get("entity_id")]
    contexts = [context_by_id.get(entity_id, {}) for entity_id in entity_ids]
    source_sets = [set(clean_id_list(ctx.get("source_ids"))) for ctx in contexts]
    shared_sources = sorted(set.intersection(*source_sets)) if source_sets else []
    private_flags = sorted({
        str(ctx.get("privacy_level"))
        for ctx in contexts
        if ctx.get("privacy_level") in {"private_person", "minor", "unknown"}
    })
    candidates.append({
        "candidate_id": stable_id("IR", reason, key, "|".join(sorted(entity_ids))),
        "reason": reason,
        "match_key": key,
        "recommendation": "human_review_required_before_merge",
        "confidence": 0.65 if shared_sources else 0.5,
        "shared_source_ids": shared_sources,
        "privacy_flags": private_flags,
        "records": [compact_record("entities", row, idx) for idx, row in rows],
        "contexts": contexts,
    })


def resolve_identities(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    entities = read_jsonl(record_path(args.case_dir, "entities"))
    claims = read_jsonl(record_path(args.case_dir, "claims"))
    events = read_jsonl(record_path(args.case_dir, "events"))
    relationships = read_jsonl(record_path(args.case_dir, "relationships"))
    event_links = read_jsonl(record_path(args.case_dir, "event_links"))

    context_by_id = {
        str(entity.get("entity_id")): entity_resolution_context(
            entity,
            claims=claims,
            events=events,
            relationships=relationships,
            event_links=event_links,
        )
        for entity in entities
        if entity.get("entity_id")
    }
    groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for idx, entity in enumerate(entities, start=1):
        if entity.get("status") == "merged" and not getattr(args, "include_merged", False):
            continue
        values = [entity.get("name"), entity.get("display_name")]
        values.extend(entity.get("aliases", []) or [])
        for value in values:
            key = normalize_match_text(value)
            if len(key) >= args.min_key_chars:
                groups.setdefault(key, []).append((idx, entity))

    candidates: list[dict[str, Any]] = []
    seen_entity_sets: set[tuple[str, ...]] = set()
    for key, rows in sorted(groups.items()):
        ids = tuple(sorted(str(row.get("entity_id")) for _idx, row in rows if row.get("entity_id")))
        if len(ids) < 2 or ids in seen_entity_sets:
            continue
        seen_entity_sets.add(ids)
        append_identity_candidate(
            candidates,
            reason="same_normalized_name_or_alias",
            key=key,
            rows=rows,
            context_by_id=context_by_id,
        )

    summary = {
        "candidate_count": len(candidates),
        "entity_count": len(entities),
        "policy": "This report does not merge, delete, or publicly identify entities.",
    }
    report = {
        "generated_at": now_utc(),
        "case_dir": str(case_path(args.case_dir)),
        "summary": summary,
        "candidates": candidates,
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), f"staging/candidates/identity_resolution_{today()}.json")
    write_json(out, report)
    log_action(
        args.case_dir,
        "resolve_identities",
        {
            "candidate_count": len(candidates),
            "report": str(out),
            "include_merged": getattr(args, "include_merged", False),
        },
    )
    print(json.dumps({"candidate_count": len(candidates), "report": str(out)}, indent=2, ensure_ascii=False))


def claim_tokens(claim: dict[str, Any]) -> set[str]:
    text = normalize_match_text(claim.get("claim"))
    return {token for token in text.split() if len(token) > 3}


def claim_overlap(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_tokens = claim_tokens(left)
    right_tokens = claim_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def contradiction_severity(flag_type: str, left: dict[str, Any], right: dict[str, Any]) -> str:
    assertion_types = {str(left.get("assertion_type", "")), str(right.get("assertion_type", ""))}
    statuses = {str(left.get("status", "")), str(right.get("status", ""))}
    if "court_finding" in assertion_types or "false_or_retracted" in statuses:
        return "high"
    if flag_type in {"explicit_contradiction", "opposing_assertion_types"}:
        return "medium"
    return "low"


def make_contradiction_flag(
    *,
    flag_type: str,
    left: dict[str, Any],
    right: dict[str, Any],
    reason: str,
    overlap: float | None = None,
) -> dict[str, Any]:
    left_id = str(left.get("claim_id", ""))
    right_id = str(right.get("claim_id", ""))
    return {
        "flag_id": stable_id("CF", flag_type, left_id, right_id),
        "flag_type": flag_type,
        "severity": contradiction_severity(flag_type, left, right),
        "claim_ids": sorted([left_id, right_id]),
        "source_ids": sorted(set(clean_id_list(left.get("source_ids"))) | set(clean_id_list(right.get("source_ids")))),
        "assertion_types": sorted({str(left.get("assertion_type", "")), str(right.get("assertion_type", ""))}),
        "statuses": sorted({str(left.get("status", "")), str(right.get("status", ""))}),
        "text_overlap": overlap,
        "reason": reason,
        "records": [
            compact_record("claims", left),
            compact_record("claims", right),
        ],
    }


def audit_contradictions(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    claims = read_jsonl(record_path(args.case_dir, "claims"))
    if not getattr(args, "include_private", False):
        claims = public_rows(claims)
    claim_by_id = {str(claim.get("claim_id")): claim for claim in claims if claim.get("claim_id")}
    flags: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str, str]] = set()

    def add_flag(flag: dict[str, Any]) -> None:
        ids = tuple(sorted(flag["claim_ids"]))
        key = (flag["flag_type"], ids[0], ids[1])
        if key in seen_pairs:
            return
        seen_pairs.add(key)
        flags.append(flag)

    for claim in claims:
        for other_id in clean_id_list(claim.get("contradicts")):
            other = claim_by_id.get(other_id)
            if not other:
                continue
            add_flag(make_contradiction_flag(
                flag_type="explicit_contradiction",
                left=claim,
                right=other,
                reason="A claim explicitly lists the other claim in its contradicts array.",
            ))

    for left, right in combinations(claims, 2):
        left_id = str(left.get("claim_id", ""))
        right_id = str(right.get("claim_id", ""))
        if not left_id or not right_id:
            continue
        overlap = claim_overlap(left, right)
        if overlap < args.min_overlap:
            continue
        assertion_types = {str(left.get("assertion_type", "")), str(right.get("assertion_type", ""))}
        statuses = {str(left.get("status", "")), str(right.get("status", ""))}
        if {"allegation", "denial"} <= assertion_types:
            add_flag(make_contradiction_flag(
                flag_type="opposing_assertion_types",
                left=left,
                right=right,
                overlap=overlap,
                reason="Similar claim text has allegation and denial assertion types.",
            ))
        if "court_finding" in assertion_types and ("allegation" in assertion_types or "denial" in assertion_types):
            add_flag(make_contradiction_flag(
                flag_type="court_finding_conflict_review",
                left=left,
                right=right,
                overlap=overlap,
                reason="Similar claim text includes a court finding and a claim framed differently by another source.",
            ))
        if "false_or_retracted" in statuses and statuses & {"verified", "corroborated", "single_source"}:
            add_flag(make_contradiction_flag(
                flag_type="status_conflict",
                left=left,
                right=right,
                overlap=overlap,
                reason="Similar claim text has false/retracted status alongside an active support status.",
            ))

    summary: dict[str, int] = {}
    for flag in flags:
        summary[str(flag["flag_type"])] = summary.get(str(flag["flag_type"]), 0) + 1
    report = {
        "generated_at": now_utc(),
        "case_dir": str(case_path(args.case_dir)),
        "include_private": getattr(args, "include_private", False),
        "flag_count": len(flags),
        "summary": summary,
        "flags": flags,
        "policy": "This report identifies review targets; it does not change claim status or confidence.",
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), "exports/claim_contradiction_audit.json")
    write_json(out, report)
    log_action(
        args.case_dir,
        "audit_contradictions",
        {
            "flag_count": len(flags),
            "summary": summary,
            "report": str(out),
            "include_private": getattr(args, "include_private", False),
        },
    )
    print(json.dumps({"flag_count": len(flags), "summary": summary, "report": str(out)}, indent=2, ensure_ascii=False))
    if getattr(args, "fail_on_flags", False) and flags:
        raise SystemExit(1)


def infer_public_record_lanes(subject: str, requested_lanes: list[str]) -> list[str]:
    if requested_lanes:
        return sorted(dict.fromkeys(requested_lanes))
    text = subject.casefold()
    matches = [
        lane
        for lane, config in PUBLIC_RECORD_LANES.items()
        if any(trigger in text for trigger in config["triggers"])
    ]
    if matches:
        return sorted(dict.fromkeys(matches))
    return list(FALLBACK_PUBLIC_RECORD_LANES)


def public_record_lane_plan(lane: str, subject: str) -> dict[str, Any]:
    config = PUBLIC_RECORD_LANES[lane]
    source_queries = [
        f'"{subject}" {term}'
        for term in config["triggers"][:5]
    ]
    return {
        "lane": lane,
        "skill": config["skill"],
        "template": config["template"],
        "source_types": config["source_types"],
        "notes": config["notes"],
        "suggested_queries": source_queries,
        "recommended_next_commands": [
            "add-source or ingest-url each public source before extraction",
            f"draft-extraction --template {config['template']} for lane-specific packets",
            "validate after imports",
        ],
    }


def plan_public_records(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    subject = args.subject.strip()
    if not subject:
        raise SystemExit("--subject is required")
    lanes = infer_public_record_lanes(subject, args.lane or [])
    plans = [public_record_lane_plan(lane, subject) for lane in lanes]
    report = {
        "generated_at": now_utc(),
        "case_dir": str(case_path(args.case_dir)),
        "subject": subject,
        "research_question": args.question or "",
        "lanes": plans,
        "policy": (
            "This source plan is a lead map. It does not create evidence, infer misconduct, "
            "or make identity/relationship claims."
        ),
    }
    default_name = f"staging/candidates/public_records_plan_{slugify(subject, max_len=32)}_{today()}.json"
    out = report_out_path(args.case_dir, getattr(args, "out", None), default_name)
    write_json(out, report)
    log_action(
        args.case_dir,
        "plan_public_records",
        {
            "subject": subject,
            "lanes": lanes,
            "report": str(out),
        },
    )
    print(json.dumps({"lane_count": len(lanes), "lanes": lanes, "report": str(out)}, indent=2, ensure_ascii=False))


def timestamp_to_seconds(match: re.Match[str]) -> int:
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return hours * 3600 + minutes * 60 + seconds


def transcript_segment_from_line(source_id: str, line: str, line_no: int) -> dict[str, Any] | None:
    timestamp_match = TIMESTAMP_RE.search(line)
    speaker_match = SPEAKER_LINE_RE.match(line)
    speaker = speaker_match.group("speaker").strip() if speaker_match else None
    text = speaker_match.group("text").strip() if speaker_match else line.strip()
    if timestamp_match:
        text = (line[:timestamp_match.start()] + line[timestamp_match.end():]).strip(" -\t")
        speaker_match_after_timestamp = SPEAKER_LINE_RE.match(text)
        if speaker_match_after_timestamp:
            speaker = speaker_match_after_timestamp.group("speaker").strip()
            text = speaker_match_after_timestamp.group("text").strip()
    if not timestamp_match and not speaker_match:
        return None
    return {
        "segment_id": stable_id("TS", source_id, str(line_no), line, length=10),
        "source_id": source_id,
        "line": line_no,
        "timestamp": timestamp_match.group(0) if timestamp_match else None,
        "timestamp_seconds": timestamp_to_seconds(timestamp_match) if timestamp_match else None,
        "speaker": speaker,
        "text": text,
        "quote_candidate": text[:280],
        "source_span_placeholder": {
            "locator_type": "timestamp" if timestamp_match else "line",
            "locator": {
                "line": line_no,
                "timestamp": timestamp_match.group(0) if timestamp_match else None,
                "speaker": speaker,
            },
        },
    }


def index_transcript(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    source = find_source(args.case_dir, args.source_id)
    if not source:
        raise SystemExit(f"Source not found: {args.source_id}")
    if source.get("public_export") is False and not args.include_private:
        raise SystemExit("Source is public_export=false. Use --include-private for internal transcript indexing.")
    text_rel = source.get("text_path")
    if not text_rel:
        raise SystemExit(f"Source has no text_path: {args.source_id}")
    text_path = case_relative_path(args.case_dir, str(text_rel))
    if not text_path or not text_path.exists():
        raise SystemExit(f"Source text_path does not exist: {text_rel}")

    segments: list[dict[str, Any]] = []
    for line_no, line in enumerate(text_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        segment = transcript_segment_from_line(args.source_id, line, line_no)
        if not segment:
            continue
        segments.append(segment)
        if len(segments) >= args.max_segments:
            break

    speakers = sorted({str(segment["speaker"]) for segment in segments if segment.get("speaker")})
    report = {
        "generated_at": now_utc(),
        "case_dir": str(case_path(args.case_dir)),
        "source_id": args.source_id,
        "source_title": source.get("title"),
        "segment_count": len(segments),
        "speakers": speakers,
        "segments": segments,
        "policy": (
            "Transcript segments are candidate locators. Import claims or quotes only after "
            "reviewing the source text and preserving source_spans."
        ),
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), f"staging/candidates/transcript_index_{args.source_id}_{today()}.json")
    write_json(out, report)
    log_action(
        args.case_dir,
        "index_transcript",
        {
            "source_id": args.source_id,
            "segment_count": len(segments),
            "speakers": speakers,
            "report": str(out),
            "include_private": getattr(args, "include_private", False),
        },
    )
    print(json.dumps({"segment_count": len(segments), "speakers": speakers, "report": str(out)}, indent=2, ensure_ascii=False))


def plan_open_records(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    subject = args.subject.strip()
    agency = args.agency.strip()
    if not subject or not agency:
        raise SystemExit("--subject and --agency are required")
    requested_records = [item.strip() for item in (args.record or []) if item.strip()]
    if not requested_records:
        requested_records = [
            f"public records concerning {subject}",
            "record indexes, logs, correspondence metadata, reports, policies, and responsive attachments where public",
        ]
    date_range = args.date_range or "date range to be narrowed before submission"
    jurisdiction = args.jurisdiction or "jurisdiction to confirm"
    law = args.law or "applicable FOIA/open-records law to confirm"
    exclusions = [
        "home addresses, personal phone/email, financial identifiers, medical details, and private-person contact details",
        "records about minors unless already central to a public-interest record and legally releasable",
        "non-responsive private material and privileged/exempt content",
    ]
    request_text = "\n".join([
        f"To: {agency}",
        "",
        f"Under {law}, I request public records concerning {subject}.",
        f"Jurisdiction/scope: {jurisdiction}.",
        f"Date range: {date_range}.",
        "",
        "Requested record categories:",
        *[f"- {record}" for record in requested_records],
        "",
        "Please provide records electronically where available. Please segregate and release non-exempt portions of responsive records.",
        "Please exclude or redact private-person contact details, medical details, financial identifiers, and information about minors unless legally required and clearly responsive.",
        "If fees are expected, please provide an estimate before processing.",
    ])
    report = {
        "generated_at": now_utc(),
        "case_dir": str(case_path(args.case_dir)),
        "subject": subject,
        "agency": agency,
        "jurisdiction": jurisdiction,
        "law": law,
        "date_range": date_range,
        "requested_records": requested_records,
        "privacy_exclusions": exclusions,
        "request_text": request_text,
        "appeal_tracker": {
            "submitted_at": None,
            "tracking_number": None,
            "statutory_due_date": None,
            "response_status": "not_submitted",
            "appeal_due_date": None,
            "notes": "",
        },
        "policy": "This is a planning artifact. It does not create evidence claims or establish that records exist.",
    }
    default_name = f"staging/candidates/open_records_plan_{slugify(subject, max_len=32)}_{today()}.json"
    out = report_out_path(args.case_dir, getattr(args, "out", None), default_name)
    write_json(out, report)
    log_action(
        args.case_dir,
        "plan_open_records",
        {
            "subject": subject,
            "agency": agency,
            "jurisdiction": jurisdiction,
            "record_count": len(requested_records),
            "report": str(out),
        },
    )
    print(json.dumps({"subject": subject, "agency": agency, "record_count": len(requested_records), "report": str(out)}, indent=2, ensure_ascii=False))


def add_review_issue(
    issues: list[dict[str, Any]],
    *,
    record_type: str,
    record_id_value: str,
    issue_type: str,
    severity: str,
    message: str,
    field: str = "",
    value: Any = "",
) -> None:
    issues.append({
        "record_type": record_type,
        "record_id": record_id_value,
        "issue_type": issue_type,
        "severity": severity,
        "field": field,
        "message": message,
        "value": str(value)[:280],
    })


def review_narrative_readiness(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    claims = read_jsonl(record_path(args.case_dir, "claims"))
    events = read_jsonl(record_path(args.case_dir, "events"))
    relationships = read_jsonl(record_path(args.case_dir, "relationships"))
    source_by_id = {str(source.get("source_id")): source for source in sources if source.get("source_id")}
    if not getattr(args, "include_private", False):
        claims = public_rows(claims)
        events = public_rows(events)
        relationships = public_rows(relationships)

    issues: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = str(claim.get("claim_id", ""))
        source_ids = clean_id_list(claim.get("source_ids"))
        source_rows, missing_sources = source_rows_for_ids(source_by_id, source_ids)
        status = str(claim.get("status", "")).casefold()
        assertion_type = str(claim.get("assertion_type", "")).casefold()
        privacy_review = str(claim.get("privacy_review", "clear") or "clear").casefold()
        independent_count = len({source_independence_key(source) for source in source_rows})

        if not source_ids:
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="missing_sources", severity="blocker", message="Narrative claim has no source_ids.")
        if missing_sources:
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="missing_source_records", severity="blocker", message="Narrative claim references missing source rows.", field="source_ids", value=";".join(missing_sources))
        if privacy_review != "clear":
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="privacy_not_clear", severity="blocker", message="Claim privacy review is not clear.", field="privacy_review", value=privacy_review)
        if status in {"unverified", "disputed", "false_or_retracted", "excluded_from_public_script"}:
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="needs_caveat_or_exclusion", severity="warning", message="Claim status requires caveat or exclusion from narrative.", field="status", value=status)
        if assertion_type == "lead_only":
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="lead_only_claim", severity="blocker", message="Lead-only claims are not narrative-ready.", field="assertion_type", value=assertion_type)
        if assertion_type == "allegation" and independent_count < args.min_independent_sources:
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="weak_allegation_support", severity="blocker", message="Allegation lacks the configured independent source count.", field="source_ids", value=";".join(source_ids))
        if status == "corroborated" and independent_count < args.min_independent_sources:
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="corroboration_independence_gap", severity="warning", message="Claim is marked corroborated but does not meet the configured independent source count.", field="source_ids", value=";".join(source_ids))
        if args.require_spans and not clean_id_list(claim.get("source_span_ids")):
            add_review_issue(issues, record_type="claims", record_id_value=claim_id, issue_type="missing_source_spans", severity="warning", message="Claim has no precise source_span_ids.")

    for event in events:
        event_id = str(event.get("event_id", ""))
        if not clean_id_list(event.get("source_ids")):
            add_review_issue(issues, record_type="events", record_id_value=event_id, issue_type="missing_sources", severity="warning", message="Narrative event has no source_ids.")
        if args.require_spans and not clean_id_list(event.get("source_span_ids")):
            add_review_issue(issues, record_type="events", record_id_value=event_id, issue_type="missing_source_spans", severity="info", message="Event has no precise source_span_ids.")

    for rel in relationships:
        rel_id = str(rel.get("rel_id", ""))
        relation_type = str(rel.get("relation_type", ""))
        if relation_type in {"co_mentioned_with", "possibly_same_as"} and rel.get("public_export", True) is not False:
            add_review_issue(issues, record_type="relationships", record_id_value=rel_id, issue_type="lead_relationship_public", severity="blocker", message="Lead-only relationship is public-exportable.", field="relation_type", value=relation_type)
        if not clean_id_list(rel.get("source_ids")):
            add_review_issue(issues, record_type="relationships", record_id_value=rel_id, issue_type="missing_sources", severity="warning", message="Narrative relationship has no source_ids.")

    summary: dict[str, int] = {}
    severity_summary: dict[str, int] = {}
    for issue in issues:
        issue_type = str(issue.get("issue_type", "unknown_issue"))
        severity = str(issue.get("severity", "blocker"))
        summary[issue_type] = summary.get(issue_type, 0) + 1
        severity_summary[severity] = severity_summary.get(severity, 0) + 1
    report = {
        "generated_at": now_utc(),
        "case_dir": str(cdir),
        "include_private": getattr(args, "include_private", False),
        "min_independent_sources": args.min_independent_sources,
        "require_spans": args.require_spans,
        "issue_count": len(issues),
        "summary": summary,
        "severity_summary": severity_summary,
        "issues": issues,
        "policy": "Narrative readiness is advisory. Resolve blocker issues before public script, video, or report use.",
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), "exports/narrative_readiness_review.json")
    write_json(out, report)
    log_action(
        args.case_dir,
        "review_narrative_readiness",
        {
            "issue_count": len(issues),
            "summary": summary,
            "severity_summary": severity_summary,
            "report": str(out),
            "include_private": getattr(args, "include_private", False),
        },
    )
    print(json.dumps({"issue_count": len(issues), "summary": summary, "severity_summary": severity_summary, "report": str(out)}, indent=2, ensure_ascii=False))
    if getattr(args, "fail_on_blockers", False) and severity_summary.get("blocker", 0):
        raise SystemExit(1)


def audit_privacy_redactions(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    source_by_id = {str(source.get("source_id")): source for source in sources if source.get("source_id")}
    issues: list[dict[str, Any]] = []

    for record_name in RECORD_FILES:
        if record_name == "research_actions":
            continue
        rows = read_jsonl(record_path(args.case_dir, record_name))
        for idx, row in enumerate(rows, start=1):
            if row.get("public_export", True) is False and not getattr(args, "include_private", False):
                continue
            rid = record_id(record_name, row, idx)
            privacy_review = str(row.get("privacy_review", "")).casefold()
            if row.get("public_export", True) is not False and privacy_review in {"needs_review", "redact", "exclude"}:
                add_review_issue(issues, record_type=record_name, record_id_value=rid, issue_type="public_record_privacy_review_open", severity="blocker", message="Public record has privacy_review that requires review, redaction, or exclusion.", field="privacy_review", value=privacy_review)

            for field, text in text_fields_for_public_scan(row):
                if CONTACT_FIELD_RE.search(field):
                    add_review_issue(issues, record_type=record_name, record_id_value=rid, issue_type="contact_field_present", severity="blocker", message="Record has an address/contact-style field.", field=field, value=text)
                elif PUBLIC_CONTACT_RE.search(text) or ADDRESS_RE.search(text):
                    add_review_issue(issues, record_type=record_name, record_id_value=rid, issue_type="contact_or_address_pattern", severity="blocker", message="Record text appears to contain contact or address information.", field=field, value=text)

            if record_name == "entities":
                privacy_text = " ".join(str(row.get(field, "")) for field in ("privacy_level", "status", "notes")).casefold()
                roles_text = " ".join(str(item) for item in (row.get("role_tags") or [])).casefold()
                if row.get("public_export", True) is not False and ("private_person" in privacy_text or "private_person" in roles_text):
                    add_review_issue(issues, record_type=record_name, record_id_value=rid, issue_type="private_person_public", severity="blocker", message="Private-person entity is public-exportable.", field="privacy_level", value=row.get("privacy_level", ""))
                if row.get("public_export", True) is not False and re.search(r"\b(?:minor|juvenile|child|underage)\b", privacy_text + " " + roles_text):
                    add_review_issue(issues, record_type=record_name, record_id_value=rid, issue_type="minor_public", severity="blocker", message="Minor-related entity is public-exportable.", field="privacy_level", value=row.get("privacy_level", ""))

            if record_name == "claims":
                audit_claim_public_support(issues, row, rid, source_by_id)

    redactions = read_jsonl(record_path(args.case_dir, "redactions"))
    if not redactions and args.require_redaction_log:
        add_review_issue(issues, record_type="redactions", record_id_value="redactions", issue_type="missing_redaction_log", severity="warning", message="No redaction rows exist for this case.")
    for idx, row in enumerate(redactions, start=1):
        rid = record_id("redactions", row, idx)
        status = str(row.get("status", row.get("review_status", ""))).casefold()
        if status in {"open", "pending", "needs_review", "unresolved"}:
            add_review_issue(issues, record_type="redactions", record_id_value=rid, issue_type="open_redaction", severity="warning", message="Redaction row appears unresolved.", field="status", value=status)

    summary: dict[str, int] = {}
    severity_summary: dict[str, int] = {}
    for issue in issues:
        issue_type = str(issue.get("issue_type", "unknown_issue"))
        severity = str(issue.get("severity", "blocker"))
        summary[issue_type] = summary.get(issue_type, 0) + 1
        severity_summary[severity] = severity_summary.get(severity, 0) + 1
    report = {
        "generated_at": now_utc(),
        "case_dir": str(cdir),
        "include_private": getattr(args, "include_private", False),
        "issue_count": len(issues),
        "summary": summary,
        "severity_summary": severity_summary,
        "issues": issues,
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), "exports/privacy_redaction_audit.json")
    write_json(out, report)
    log_action(
        args.case_dir,
        "audit_privacy_redactions",
        {
            "issue_count": len(issues),
            "summary": summary,
            "severity_summary": severity_summary,
            "report": str(out),
            "include_private": getattr(args, "include_private", False),
        },
    )
    print(json.dumps({"issue_count": len(issues), "summary": summary, "severity_summary": severity_summary, "report": str(out)}, indent=2, ensure_ascii=False))
    if issues and not getattr(args, "warn_only", False):
        raise SystemExit(1)


def append_duplicate_candidate(
    candidates: list[dict[str, Any]],
    *,
    record_type: str,
    reason: str,
    key: str,
    rows: list[tuple[int, dict[str, Any]]],
) -> None:
    if len(rows) < 2:
        return
    candidates.append({
        "record_type": record_type,
        "reason": reason,
        "match_key": key,
        "records": [compact_record(record_type, row, idx) for idx, row in rows],
    })


def dedupe(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    candidates: list[dict[str, Any]] = []
    record_types = ["entities", "sources", "claims"] if getattr(args, "record_type", "all") == "all" else [args.record_type]

    if "entities" in record_types:
        entities = read_jsonl(record_path(args.case_dir, "entities"))
        entity_groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for idx, entity in enumerate(entities, start=1):
            values = [entity.get("name"), entity.get("display_name")]
            values.extend(entity.get("aliases", []) or [])
            for value in values:
                key = normalize_match_text(value)
                if len(key) >= args.min_key_chars:
                    entity_groups.setdefault(key, []).append((idx, entity))
        for key, rows in sorted(entity_groups.items()):
            append_duplicate_candidate(candidates, record_type="entities", reason="same_normalized_name_or_alias", key=key, rows=rows)

    if "sources" in record_types:
        sources = read_jsonl(record_path(args.case_dir, "sources"))
        source_groups: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = {}
        for idx, source in enumerate(sources, start=1):
            for field in ("url", "archive_url"):
                key = normalize_url(source.get(field))
                if key:
                    source_groups.setdefault((f"same_{field}", key), []).append((idx, source))
            title_key = normalize_match_text(source.get("title"))
            publisher_key = normalize_match_text(source.get("publisher"))
            date_key = normalize_match_text(source.get("date_published"))
            if len(title_key) >= args.min_key_chars:
                source_groups.setdefault(("same_title_publisher_date", "|".join([title_key, publisher_key, date_key])), []).append((idx, source))
            for field in ("raw_path", "text_path"):
                key = str(source.get(field) or "").strip()
                if key:
                    source_groups.setdefault((f"same_{field}", key), []).append((idx, source))
        for (reason, key), rows in sorted(source_groups.items()):
            append_duplicate_candidate(candidates, record_type="sources", reason=reason, key=key, rows=rows)

    if "claims" in record_types:
        claims = read_jsonl(record_path(args.case_dir, "claims"))
        claim_groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for idx, claim in enumerate(claims, start=1):
            key = normalize_match_text(claim.get("claim"))
            if len(key) >= args.min_key_chars:
                claim_groups.setdefault(key, []).append((idx, claim))
        for key, rows in sorted(claim_groups.items()):
            append_duplicate_candidate(candidates, record_type="claims", reason="same_normalized_claim_text", key=key, rows=rows)

    summary: dict[str, int] = {}
    for candidate in candidates:
        kind = str(candidate["record_type"])
        summary[kind] = summary.get(kind, 0) + 1
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "case_dir": str(cdir),
        "policy": "This report does not merge or delete evidence rows.",
        "candidate_count": len(candidates),
        "summary": summary,
        "candidates": candidates,
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), f"staging/candidates/dedupe_report_{today()}.json")
    write_json(out, report)
    log_action(
        args.case_dir,
        "dedupe",
        {
            "record_types": record_types,
            "candidate_count": len(candidates),
            "summary": summary,
            "report": str(out),
        },
    )
    print(json.dumps({"candidate_count": len(candidates), "summary": summary, "report": str(out)}, indent=2, ensure_ascii=False))


def public_export_enabled(row: dict[str, Any]) -> bool:
    return row.get("public_export", True) is not False


def text_fields_for_public_scan(row: Any, prefix: str = "") -> list[tuple[str, str]]:
    skip = {"url", "archive_url", "raw_path", "text_path", "source_text_path", "source_metadata"}
    if isinstance(row, dict):
        values: list[tuple[str, str]] = []
        for key, value in row.items():
            if key in skip:
                continue
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            values.extend(text_fields_for_public_scan(value, next_prefix))
        return values
    if isinstance(row, list):
        values = []
        for idx, value in enumerate(row):
            values.extend(text_fields_for_public_scan(value, f"{prefix}[{idx}]"))
        return values
    if row in (None, ""):
        return []
    return [(prefix, str(row))]


def add_audit_issue(
    issues: list[dict[str, Any]],
    *,
    record_type: str,
    record_id_value: str,
    issue_type: str,
    message: str,
    field: str = "",
    value: str = "",
) -> None:
    issues.append({
        "record_type": record_type,
        "record_id": record_id_value,
        "issue_type": issue_type,
        "field": field,
        "message": message,
        "value": value[:240],
    })


def source_rows_for_ids(source_by_id: dict[str, dict[str, Any]], source_ids: Iterable[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for source_id in source_ids:
        source = source_by_id.get(str(source_id))
        if source:
            rows.append(source)
        else:
            missing.append(str(source_id))
    return rows, missing


def audit_claim_public_support(
    issues: list[dict[str, Any]],
    claim: dict[str, Any],
    claim_id: str,
    source_by_id: dict[str, dict[str, Any]],
) -> None:
    source_ids = clean_id_list(claim.get("source_ids"))
    if not source_ids:
        add_audit_issue(
            issues,
            record_type="claims",
            record_id_value=claim_id,
            issue_type="unsupported_claim",
            message="Public claim has no source_ids.",
        )
        return

    source_rows, missing = source_rows_for_ids(source_by_id, source_ids)
    if missing:
        add_audit_issue(
            issues,
            record_type="claims",
            record_id_value=claim_id,
            issue_type="unsupported_claim",
            message="Public claim references source_ids that are not in records/sources.jsonl.",
            field="source_ids",
            value=";".join(missing),
        )
    if not source_rows:
        return

    grades = {str(source.get("reliability_grade", "")).upper() for source in source_rows}
    text = " ".join(str(claim.get(field, "")) for field in ("claim", "claim_type", "status", "notes"))
    status = str(claim.get("status", "")).casefold()
    assertion_type = str(claim.get("assertion_type", "")).casefold()
    privacy_review = str(claim.get("privacy_review", "clear") or "clear").casefold()
    confidence_raw = claim.get("confidence")
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = None
    independent_count = len({source_independence_key(source) for source in source_rows})

    if privacy_review != "clear":
        add_audit_issue(
            issues,
            record_type="claims",
            record_id_value=claim_id,
            issue_type="privacy_review_not_clear",
            message="Public claim has not cleared privacy review.",
            field="privacy_review",
            value=privacy_review,
        )
    if assertion_type == "lead_only":
        add_audit_issue(
            issues,
            record_type="claims",
            record_id_value=claim_id,
            issue_type="lead_only_or_weak_allegation",
            message="Public claim is marked assertion_type=lead_only.",
            field="assertion_type",
            value=assertion_type,
        )
    if status == "unverified" and (confidence is None or confidence < 0.5):
        add_audit_issue(
            issues,
            record_type="claims",
            record_id_value=claim_id,
            issue_type="unsupported_claim",
            message="Public claim is unverified and low-confidence.",
            field="status",
            value=status,
        )
    if grades and all(grade in {"", "D", "X"} for grade in grades):
        add_audit_issue(
            issues,
            record_type="claims",
            record_id_value=claim_id,
            issue_type="weak_claim_sources",
            message="Public claim is supported only by lead-only or excluded source grades.",
            field="source_ids",
            value=";".join(source_ids),
        )
    if (assertion_type == "allegation" or ALLEGATION_RE.search(text)) and (
        "lead" in status
        or status in {"unverified", "rumor", "unsupported", "single_source"}
        or (confidence is not None and confidence < 0.5)
        or independent_count < 2
    ):
        add_audit_issue(
            issues,
            record_type="claims",
            record_id_value=claim_id,
            issue_type="lead_only_or_weak_allegation",
            message="Public allegation is lead-only, weakly supported, low-confidence, or lacks independent corroboration.",
            field="claim",
            value=str(claim.get("claim", "")),
        )


def audit_public_export(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    source_by_id = {str(source.get("source_id")): source for source in sources if source.get("source_id")}
    issues: list[dict[str, Any]] = []

    for record_name in RECORD_FILES:
        if record_name == "research_actions":
            continue
        rows = read_jsonl(record_path(args.case_dir, record_name))
        for idx, row in enumerate(rows, start=1):
            if not public_export_enabled(row):
                continue
            rid = record_id(record_name, row, idx)

            privacy_review = str(row.get("privacy_review", "")).casefold()
            if privacy_review in {"needs_review", "redact", "exclude"}:
                add_audit_issue(
                    issues,
                    record_type=record_name,
                    record_id_value=rid,
                    issue_type="privacy_review_blocks_public_export",
                    message="Public record has privacy_review that blocks or requires review before export.",
                    field="privacy_review",
                    value=str(row.get("privacy_review", "")),
                )

            for field, text in text_fields_for_public_scan(row):
                if CONTACT_FIELD_RE.search(field):
                    add_audit_issue(
                        issues,
                        record_type=record_name,
                        record_id_value=rid,
                        issue_type="address_or_contact_info",
                        message="Public record contains an address/contact field.",
                        field=field,
                        value=text,
                    )
                elif PUBLIC_CONTACT_RE.search(text) or ADDRESS_RE.search(text):
                    add_audit_issue(
                        issues,
                        record_type=record_name,
                        record_id_value=rid,
                        issue_type="address_or_contact_info",
                        message="Public record text appears to contain address/contact information.",
                        field=field,
                        value=text,
                    )

            if record_name == "entities":
                privacy = " ".join(str(row.get(field, "")) for field in ("privacy_level", "status", "notes")).casefold()
                roles = " ".join(str(item) for item in (row.get("role_tags") or [])).casefold()
                if "private_person" in privacy or privacy in {"private", "private person"} or "private_person" in roles:
                    add_audit_issue(
                        issues,
                        record_type=record_name,
                        record_id_value=rid,
                        issue_type="private_person_public",
                        message="Public export includes an entity marked as a private person.",
                        field="privacy_level",
                        value=str(row.get("privacy_level", "")),
                    )
                if re.search(r"\b(?:minor|juvenile|child|underage)\b", privacy + " " + roles):
                    add_audit_issue(
                        issues,
                        record_type=record_name,
                        record_id_value=rid,
                        issue_type="minor_public",
                        message="Public export includes an entity marked as or describing a minor.",
                        field="privacy_level",
                        value=str(row.get("privacy_level", "")),
                    )

            if record_name == "sources":
                grade = str(row.get("reliability_grade", "")).upper()
                if grade in {"D", "X"}:
                    add_audit_issue(
                        issues,
                        record_type=record_name,
                        record_id_value=rid,
                        issue_type="lead_only_or_excluded_source_public",
                        message="Public export includes a lead-only or excluded source grade.",
                        field="reliability_grade",
                        value=grade,
                    )

            if record_name == "claims":
                audit_claim_public_support(issues, row, rid, source_by_id)

            if record_name in {"events", "event_links", "relationships"} and not clean_id_list(row.get("source_ids")):
                add_audit_issue(
                    issues,
                    record_type=record_name,
                    record_id_value=rid,
                    issue_type="unsupported_public_record",
                    message="Public record has no source_ids.",
                    field="source_ids",
                )

    summary: dict[str, int] = {}
    for issue in issues:
        key = str(issue["issue_type"])
        summary[key] = summary.get(key, 0) + 1
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "case_dir": str(cdir),
        "issue_count": len(issues),
        "summary": summary,
        "issues": issues,
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), "exports/public_export_audit.json")
    write_json(out, report)
    log_action(
        args.case_dir,
        "audit_public_export",
        {
            "issue_count": len(issues),
            "summary": summary,
            "report": str(out),
            "warn_only": getattr(args, "warn_only", False),
        },
    )
    print(json.dumps({"issue_count": len(issues), "summary": summary, "report": str(out)}, indent=2, ensure_ascii=False))
    if issues and not getattr(args, "warn_only", False):
        raise SystemExit(1)


def source_text_blob(source: dict[str, Any]) -> str:
    return " ".join(str(source.get(field, "")) for field in ("title", "source_type", "author", "publisher", "notes")).casefold()


def is_wire_source(source: dict[str, Any]) -> bool:
    text = source_text_blob(source)
    if "associated press" in text or "reuters" in text or "united press international" in text or "afp" in text:
        return True
    return any(str(source.get(field, "")).strip().casefold() == "ap" for field in ("author", "publisher"))


def is_press_release_source(source: dict[str, Any]) -> bool:
    text = source_text_blob(source)
    return any(term in text for term in PRESS_RELEASE_TERMS)


def add_source_independence_flag(
    flags: list[dict[str, Any]],
    *,
    flag_type: str,
    message: str,
    source_ids: Iterable[str],
    record_type: str = "",
    record_id_value: str = "",
    independence_groups: Iterable[str] = (),
) -> None:
    normalized_source_ids = sorted(set(str(source_id) for source_id in source_ids if source_id))
    flags.append({
        "flag_type": flag_type,
        "record_type": record_type,
        "record_id": record_id_value,
        "source_ids": normalized_source_ids,
        "source_ids_joined": ";".join(normalized_source_ids),
        "independence_groups": sorted(set(str(group) for group in independence_groups if group)),
        "message": message,
    })


def source_independence(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    source_by_id = {str(source.get("source_id")): source for source in sources if source.get("source_id")}
    flags: list[dict[str, Any]] = []

    title_groups: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        key = normalize_match_text(source.get("title"))
        if len(key) >= getattr(args, "min_title_chars", 16):
            title_groups.setdefault(key, []).append(source)
    for group_sources in title_groups.values():
        if len(group_sources) < 2:
            continue
        source_ids = [str(source.get("source_id", "")) for source in group_sources]
        groups = [source_independence_key(source) for source in group_sources]
        if any(is_wire_source(source) for source in group_sources):
            add_source_independence_flag(
                flags,
                flag_type="repeated_wire_copy",
                message="Multiple sources share a title and at least one appears to be wire copy.",
                source_ids=source_ids,
                independence_groups=groups,
            )
        if any(is_press_release_source(source) for source in group_sources):
            add_source_independence_flag(
                flags,
                flag_type="press_release_repetition",
                message="Multiple sources share a title and at least one appears to be a press release or release repost.",
                source_ids=source_ids,
                independence_groups=groups,
            )

    record_names = [name for name in ("claims", "events", "event_links", "relationships") if name in RECORD_FILES]
    for record_name in record_names:
        rows = read_jsonl(record_path(args.case_dir, record_name))
        if not getattr(args, "include_private", False):
            rows = public_rows(rows)
        for idx, row in enumerate(rows, start=1):
            source_ids = clean_id_list(row.get("source_ids"))
            if not source_ids:
                continue
            source_rows, _missing = source_rows_for_ids(source_by_id, source_ids)
            if not source_rows:
                continue
            groups = [source_independence_key(source) for source in source_rows]
            rid = record_id(record_name, row, idx)
            if len(source_rows) > 1 and len(set(groups)) <= 1:
                add_source_independence_flag(
                    flags,
                    flag_type="same_source_chain",
                    message="Record cites multiple sources that collapse to the same independence group.",
                    source_ids=source_ids,
                    record_type=record_name,
                    record_id_value=rid,
                    independence_groups=groups,
                )
            if source_rows and all(is_wire_source(source) for source in source_rows):
                add_source_independence_flag(
                    flags,
                    flag_type="wire_copy_support_only",
                    message="Record support appears to come only from wire-copy sources.",
                    source_ids=source_ids,
                    record_type=record_name,
                    record_id_value=rid,
                    independence_groups=groups,
                )
            if source_rows and all(is_press_release_source(source) for source in source_rows):
                add_source_independence_flag(
                    flags,
                    flag_type="press_release_support_only",
                    message="Record support appears to come only from press-release or release-repost sources.",
                    source_ids=source_ids,
                    record_type=record_name,
                    record_id_value=rid,
                    independence_groups=groups,
                )

    summary: dict[str, int] = {}
    for flag in flags:
        key = str(flag["flag_type"])
        summary[key] = summary.get(key, 0) + 1
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "case_dir": str(cdir),
        "include_private": getattr(args, "include_private", False),
        "flag_count": len(flags),
        "summary": summary,
        "flags": flags,
    }
    out = report_out_path(args.case_dir, getattr(args, "out", None), "exports/source_independence_report.json")
    write_json(out, report)
    log_action(
        args.case_dir,
        "audit_source_independence",
        {
            "flag_count": len(flags),
            "summary": summary,
            "report": str(out),
            "include_private": getattr(args, "include_private", False),
        },
    )
    print(json.dumps({"flag_count": len(flags), "summary": summary, "report": str(out)}, indent=2, ensure_ascii=False))
    if getattr(args, "fail_on_flags", False) and flags:
        raise SystemExit(1)


def evidence_level(claim: dict[str, Any], source_rows: list[dict[str, Any]]) -> str:
    status = str(claim.get("status", "unknown"))
    public = claim.get("public_export", True) is not False
    source_count = len(source_rows)
    independent_count = len({source_independence_key(src) for src in source_rows})
    grades = {str(src.get("reliability_grade", "")) for src in source_rows}

    if status == "false_or_retracted":
        return "false_or_retracted"
    if status == "disputed":
        return "disputed"
    if status == "excluded_from_public_script" or not public:
        return "excluded_from_public"
    if status == "unverified":
        return "unverified"
    if status == "verified":
        return "verified"
    if status == "corroborated":
        return "corroborated"
    if independent_count >= 2:
        return "multi_source"
    if source_count == 1 and "A" in grades:
        return "single_source_grade_a"
    if source_count == 1:
        return "single_source"
    return "no_source"


def grade_summary(source_rows: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for source in source_rows:
        grade = str(source.get("reliability_grade", "") or "unknown")
        counts[grade] = counts.get(grade, 0) + 1
    return ";".join(f"{grade}:{counts[grade]}" for grade in sorted(counts))


def date_sort_key(value: Any) -> tuple[int, int, int, str]:
    raw = str(value or "")
    match = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", raw)
    if match:
        year = int(match.group(1))
        month = int(match.group(2) or "1")
        day = int(match.group(3) or "1")
        return (year, month, day, raw)
    decade = re.match(r"^(\d{3})0s$", raw)
    if decade:
        return (int(decade.group(1) + "0"), 1, 1, raw)
    return (9999, 12, 31, raw)


def export_timeline(args: argparse.Namespace) -> None:
    case_dirs = discover_cases(args.cases_root)
    include_private = args.include_private
    out = Path(args.out_dir).expanduser().resolve() if args.out_dir else case_dirs[0].parent.parent / "exports" / "timeline"
    out.mkdir(parents=True, exist_ok=True)

    case_rows: list[dict[str, Any]] = []
    timeline_rows: list[dict[str, Any]] = []
    claim_rows: list[dict[str, Any]] = []

    for cdir in case_dirs:
        case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
        case_slug = cdir.name
        case_id = case_meta.get("case_id", case_slug)
        case_title = case_meta.get("title", case_slug)
        sources = public_rows(read_jsonl(record_path(cdir, "sources")), include_private)
        claims = public_rows(read_jsonl(record_path(cdir, "claims")), include_private)
        events = public_rows(read_jsonl(record_path(cdir, "events")), include_private)
        relationships = public_rows(read_jsonl(record_path(cdir, "relationships")), include_private)

        source_by_id = {src.get("source_id"): src for src in sources}
        claim_by_id = {claim.get("claim_id"): claim for claim in claims}
        case_rows.append({
            "case_slug": case_slug,
            "case_id": case_id,
            "case_title": case_title,
            "event_count": len(events),
            "claim_count": len(claims),
            "relationship_count": len(relationships),
            "source_count": len(sources),
            "include_private": include_private,
        })

        for claim in claims:
            source_ids = [sid for sid in claim.get("source_ids", []) if sid in source_by_id]
            source_rows = [source_by_id[sid] for sid in source_ids]
            independent_count = len({source_independence_key(src) for src in source_rows})
            related_events = [
                event.get("event_id", "")
                for event in events
                if claim.get("claim_id") in (event.get("claim_ids") or [])
            ]
            claim_rows.append({
                "case_slug": case_slug,
                "case_id": case_id,
                "case_title": case_title,
                "claim_id": claim.get("claim_id", ""),
                "claim": claim.get("claim", ""),
                "claim_type": claim.get("claim_type", ""),
                "status": claim.get("status", ""),
                "confidence": claim.get("confidence", ""),
                "privacy_review": claim.get("privacy_review", ""),
                "public_export": claim.get("public_export", True),
                "evidence_level": evidence_level(claim, source_rows),
                "source_count": len(source_rows),
                "independent_source_count": independent_count,
                "source_grades": grade_summary(source_rows),
                "source_ids": source_ids,
                "source_titles": [src.get("title", "") for src in source_rows],
                "event_ids": related_events,
            })

        for event in events:
            event_claims = [
                claim_by_id[claim_id]
                for claim_id in event.get("claim_ids", [])
                if claim_id in claim_by_id
            ]
            source_ids = set(event.get("source_ids", []))
            for claim in event_claims:
                source_ids.update(claim.get("source_ids", []))
            source_rows = [source_by_id[sid] for sid in sorted(source_ids) if sid in source_by_id]
            claim_levels = [evidence_level(claim, [source_by_id[sid] for sid in claim.get("source_ids", []) if sid in source_by_id]) for claim in event_claims]
            timeline_rows.append({
                "case_slug": case_slug,
                "case_id": case_id,
                "case_title": case_title,
                "event_id": event.get("event_id", ""),
                "start_date": event.get("start_date", ""),
                "end_date": event.get("end_date", ""),
                "date_precision": event.get("date_precision", ""),
                "event_type": event.get("event_type", ""),
                "title": event.get("title", ""),
                "status": event.get("status", ""),
                "confidence": event.get("confidence", ""),
                "public_export": event.get("public_export", True),
                "claim_count": len(event_claims),
                "claim_ids": [claim.get("claim_id", "") for claim in event_claims],
                "claim_statuses": sorted({str(claim.get("status", "")) for claim in event_claims}),
                "evidence_levels": sorted(set(claim_levels)),
                "source_count": len(source_rows),
                "source_grades": grade_summary(source_rows),
                "source_ids": [src.get("source_id", "") for src in source_rows],
                "notes": event.get("notes", ""),
            })

    timeline_rows.sort(key=lambda row: (date_sort_key(row.get("start_date")), row.get("case_slug", ""), row.get("event_id", "")))
    claim_rows.sort(key=lambda row: (row.get("case_slug", ""), row.get("status", ""), row.get("claim_id", "")))

    write_csv(out / "cases.csv", case_rows, [
        "case_slug", "case_id", "case_title", "event_count", "claim_count", "relationship_count", "source_count", "include_private"
    ])
    write_csv(out / "timeline.csv", timeline_rows, [
        "case_slug", "case_id", "case_title", "event_id", "start_date", "end_date", "date_precision", "event_type", "title", "status",
        "confidence", "public_export", "claim_count", "claim_ids", "claim_statuses", "evidence_levels", "source_count", "source_grades",
        "source_ids", "notes"
    ])
    write_csv(out / "corroborations.csv", claim_rows, [
        "case_slug", "case_id", "case_title", "claim_id", "claim", "claim_type", "status", "confidence", "privacy_review",
        "public_export", "evidence_level", "source_count", "independent_source_count", "source_grades", "source_ids",
        "source_titles", "event_ids"
    ])

    level_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for row in claim_rows:
        level = str(row.get("evidence_level", "unknown"))
        status = str(row.get("status", "unknown"))
        level_counts[level] = level_counts.get(level, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1

    content = [
        "# Cross-case timeline and corroboration index",
        "",
        f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        f"Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}",
        "",
        "## Cases",
        "",
        md_table(
            ["Case", "Events", "Claims", "Relationships", "Sources"],
            [[row["case_title"], row["event_count"], row["claim_count"], row["relationship_count"], row["source_count"]] for row in case_rows],
        ),
        "",
        "## Corroboration Summary",
        "",
        md_table(
            ["Evidence level", "Claims"],
            [[level, count] for level, count in sorted(level_counts.items())],
        ),
        "",
        md_table(
            ["Claim status", "Claims"],
            [[status, count] for status, count in sorted(status_counts.items())],
        ),
        "",
        "## Timeline",
        "",
        md_table(
            ["Date", "Case", "Event", "Status", "Evidence", "Sources", "Claims"],
            [
                [
                    row.get("start_date", ""),
                    row.get("case_title", ""),
                    row.get("title", ""),
                    row.get("status", ""),
                    flatten(row.get("evidence_levels")),
                    row.get("source_grades", ""),
                    flatten(row.get("claim_ids")),
                ]
                for row in timeline_rows
            ],
        ),
        "",
        "## Claim Corroborations",
        "",
        md_table(
            ["Case", "Claim", "Status", "Evidence", "Sources", "Events", "Public"],
            [
                [
                    row.get("case_title", ""),
                    row.get("claim_id", ""),
                    row.get("status", ""),
                    row.get("evidence_level", ""),
                    row.get("source_grades", ""),
                    flatten(row.get("event_ids")),
                    row.get("public_export", ""),
                ]
                for row in claim_rows
            ],
        ),
    ]
    (out / "timeline.md").write_text("\n".join(str(line) for line in content) + "\n", encoding="utf-8")
    print(f"Exported cross-case timeline to {out}")


SUBCASE_TITLES = {
    "aa_synanon_daytop": "Recovery movement / therapeutic community lineage",
    "parsons_hubbard_crowley": "Parsons / Hubbard / Crowley / O.T.O.",
    "elan_tti": "Troubled Teen Industry / Elan School",
    "mkultra_cia": "MKULTRA industry / intelligence behavioral research",
    "psi_remote_viewing_gateway": "Psi / remote-viewing / Gateway intelligence lane",
    "pandora_bizarre_ti": "PANDORA / BIZARRE / targeted-individual allegation lane",
    "monarch_montauk_narratives": "Monarch / Montauk / Phoenix narrative lane",
    "milab_military_abductions": "Military abduction / super-soldier narrative lane",
    "finders_jonestown_abuse_allegations": "Finders / Jonestown abuse-interference allegation lane",
    "promis_corporate_intelligence": "PROMIS / corporate-intelligence vector lane",
    "maxwell_barr_epstein": "Epstein industry / Maxwell / Barr / Dalton lane",
    "scientology": "Scientology / Hubbard institutional lane",
    "general": "General / unassigned",
}

RELATIONSHIP_CLASS_TITLES = {
    "documented_successor": "Documented succession / component lineage",
    "method_diffusion": "Method diffusion / institutional borrowing",
    "personnel_bridge": "Personnel / role / affiliation bridge",
    "narrative_inheritance": "Narrative inheritance / story-world growth",
    "contested_overlap": "Contested overlap / disputed institutional tie",
    "hypothesis_requires_more_sources": "Hypothesis requiring more sources",
}


def entity_display(entity: dict[str, Any] | None, fallback: str = "") -> str:
    if not entity:
        return fallback
    return str(entity.get("display_name") or entity.get("name") or fallback)


def infer_subcase(event: dict[str, Any], claims: list[dict[str, Any]]) -> str:
    text = " ".join(
        [
            str(event.get("event_id", "")),
            str(event.get("title", "")),
            str(event.get("event_type", "")),
            str(event.get("notes", "")),
            " ".join(str(claim.get("claim", "")) for claim in claims),
        ]
    ).lower()

    def has(pattern: str) -> bool:
        return re.search(pattern, text) is not None

    if any(has(pattern) for pattern in [r"\bbabalon\b", r"\bparsons\b", r"\bcrowley\b", r"\bo\.t\.o\b", r"\boto\b", r"\bagape lodge\b"]):
        return "parsons_hubbard_crowley"
    if any(has(pattern) for pattern in [r"\belan\b", r"\btroubled teen\b", r"\bresidential treatment\b", r"\binstitutional child abuse\b", r"\bgao\b", r"\bsica\b"]):
        return "elan_tti"
    if any(has(pattern) for pattern in [r"\bpromis\b", r"\binslaw\b", r"\bcasolaro\b", r"\bpergamon\b", r"\bmaxwell.*promis\b"]):
        return "promis_corporate_intelligence"
    if any(has(pattern) for pattern in [r"\bscanate\b", r"\bgondola wish\b", r"\bgrill flame\b", r"\bcenter lane\b", r"\bsun streak\b", r"\bstar gate\b", r"\bstargate\b", r"\bgateway process\b", r"\bmonroe institute\b", r"\bremote viewing\b"]):
        return "psi_remote_viewing_gateway"
    if any(has(pattern) for pattern in [r"\bpandora\b", r"\bbizarre\b", r"\bmoscow signal\b", r"\bsynthetic telepathy\b", r"\bvoice[- ]?to[- ]?skull\b", r"\btargeted individual\b", r"\bgangstalking\b", r"\bdirected energy\b"]):
        return "pandora_bizarre_ti"
    if any(has(pattern) for pattern in [r"\bproject monarch\b", r"\bmonarch programming\b", r"\bmontauk\b", r"\bphoenix project\b", r"\bcamp hero\b", r"\btrauma[- ]based mind control\b"]):
        return "monarch_montauk_narratives"
    if any(has(pattern) for pattern in [r"\bmilab\b", r"\bmilitary abduction\b", r"\bsuper[- ]?soldier\b", r"\bsecret space\b"]):
        return "milab_military_abductions"
    if any(has(pattern) for pattern in [r"\bthe finders\b", r"\bfinders\b", r"\bjonestown\b", r"\bpeoples temple\b"]):
        return "finders_jonestown_abuse_allegations"
    if any(has(pattern) for pattern in [r"\bmkultra\b", r"\bmk-ultra\b", r"\bmksearch\b", r"\bmkoften\b", r"\bmkchickwit\b", r"\bmknaomi\b", r"\bmkdelta\b", r"\bqkhilltop\b", r"\bhuman ecology\b", r"\ballan memorial\b", r"\bewen cameron\b", r"\bpsychic driving\b", r"\bdepatterning\b", r"\bsubproject 68\b", r"\bcia\b", r"\bdulles\b"]):
        return "mkultra_cia"
    if any(has(pattern) for pattern in [r"\bepstein\b", r"\bghislaine\b", r"\brobert maxwell\b", r"\bdonald barr\b", r"\bdalton\b", r"\bpergamon\b"]):
        return "maxwell_barr_epstein"
    if any(has(pattern) for pattern in [r"\bscientology\b", r"\bdianetics\b"]):
        return "scientology"
    if any(has(pattern) for pattern in [r"\balcoholics anonymous\b", r"\ba\.a\.", r"\baa\b", r"\bsynanon\b", r"\bdaytop\b", r"\bday top\b", r"\btherapeutic communit"]):
        return "aa_synanon_daytop"
    return "general"


def best_pair_relation(left_roles: list[str], right_roles: list[str]) -> str:
    role_set = set(left_roles + right_roles)
    if left_roles and right_roles and set(left_roles) == {"participant"} and set(right_roles) == {"participant"}:
        return "shared_event_participants"
    if "opened_school" in role_set:
        return "co_opened_school"
    if "founder_mentioned" in role_set:
        return "same_source_founder_context"
    if "contextual_reference" in role_set:
        return "contextual_reference_same_event"
    return "shared_event"


def merge_people_edge(
    edge_map: dict[tuple[str, str], dict[str, Any]],
    src_id: str,
    dst_id: str,
    *,
    people_by_id: dict[str, dict[str, Any]],
    connection_type: str,
    event_ids: list[str] | None = None,
    rel_ids: list[str] | None = None,
    claim_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    statuses: list[str] | None = None,
    confidence: float | int | str | None = None,
    public_export: bool = True,
    notes: list[str] | None = None,
) -> None:
    if src_id == dst_id:
        return
    left, right = sorted([src_id, dst_id])
    key = (left, right)
    if key not in edge_map:
        edge_map[key] = {
            "src_entity_id": left,
            "dst_entity_id": right,
            "src_name": entity_display(people_by_id.get(left), left),
            "dst_name": entity_display(people_by_id.get(right), right),
            "connection_types": [],
            "event_ids": [],
            "rel_ids": [],
            "claim_ids": [],
            "source_ids": [],
            "statuses": [],
            "confidence": 0.0,
            "public_export": True,
            "notes": [],
        }
    edge = edge_map[key]
    for field, values in [
        ("connection_types", [connection_type]),
        ("event_ids", event_ids or []),
        ("rel_ids", rel_ids or []),
        ("claim_ids", claim_ids or []),
        ("source_ids", source_ids or []),
        ("statuses", statuses or []),
        ("notes", notes or []),
    ]:
        for value in values:
            if value not in edge[field]:
                edge[field].append(value)
    try:
        edge["confidence"] = max(float(edge.get("confidence", 0.0)), float(confidence or 0.0))
    except (TypeError, ValueError):
        pass
    edge["public_export"] = bool(edge.get("public_export", True) and public_export)


def truncate_label(value: str, limit: int = 42) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def people_graph_groups(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> tuple[dict[str, str], list[list[dict[str, Any]]]]:
    node_ids = [str(node.get("entity_id", "")) for node in nodes]
    parent = {node_id: node_id for node_id in node_ids}

    def find(node_id: str) -> str:
        while parent[node_id] != node_id:
            parent[node_id] = parent[parent[node_id]]
            node_id = parent[node_id]
        return node_id

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for edge in edges:
        src = str(edge.get("src_entity_id", ""))
        dst = str(edge.get("dst_entity_id", ""))
        if src in parent and dst in parent:
            union(src, dst)

    node_by_id = {str(node.get("entity_id", "")): node for node in nodes}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for node_id, node in node_by_id.items():
        grouped.setdefault(find(node_id), []).append(node)

    groups = sorted(
        (sorted(group, key=entity_display) for group in grouped.values()),
        key=lambda group: (-len(group), entity_display(group[0]) if group else ""),
    )
    group_by_id: dict[str, str] = {}
    for idx, group in enumerate(groups, start=1):
        group_id = f"G{idx}"
        for node in group:
            group_by_id[str(node.get("entity_id", ""))] = group_id
    return group_by_id, groups


def edge_is_lead_only(edge: dict[str, Any]) -> bool:
    connection_types = parse_cell_list(edge.get("connection_types"))
    statuses = parse_cell_list(edge.get("statuses"))
    substantive_types = {
        "associated_with",
        "co_opened_school",
        "co_participant_in_event",
        "father_of",
        "founded",
        "founder_of",
        "headmaster_of",
        "official_source_describes_abuse_scheme_with",
        "opened",
        "shared_event",
        "shared_event_participants",
        "taught_at",
    }
    evidence_statuses = {"verified", "corroborated", "single_source"}
    if any(kind in substantive_types for kind in connection_types) and any(status in evidence_statuses for status in statuses):
        return False
    if "unverified" in statuses:
        return True
    return any(kind in connection_types for kind in ["co_mentioned_with", "contextual_reference_same_event"])


def edge_evidence_label(edge: dict[str, Any]) -> str:
    statuses = parse_cell_list(edge.get("statuses"))
    connection_types = parse_cell_list(edge.get("connection_types"))
    if "corroborated" in statuses:
        return "corroborated"
    if "single_source" in statuses:
        return "single-source"
    if "unverified" in statuses:
        return "lead-only"
    if any(kind in connection_types for kind in ["co_mentioned_with", "contextual_reference_same_event"]):
        return "context"
    return statuses[0].replace("_", " ") if statuses else "recorded"


def render_people_graph_html(
    case_title: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    include_private: bool,
) -> str:
    width = 1320
    height = max(820, 650 + (len(nodes) * 7))
    cx = width / 2
    cy = height / 2
    colors = ["#2563eb", "#0f766e", "#7c3aed", "#b45309", "#be123c", "#475569", "#15803d", "#0369a1"]
    weighted_edges = []
    for edge in edges:
        row = dict(edge)
        row["edge_weight"] = evidence_edge_weight(row)
        weighted_edges.append(row)

    group_by_id, groups = people_graph_groups(nodes, weighted_edges)
    degree = {str(node.get("entity_id", "")): 0 for node in nodes}
    weighted_degree = {str(node.get("entity_id", "")): 0.0 for node in nodes}
    for edge in weighted_edges:
        weight = parse_float(edge.get("edge_weight"), 0.0)
        for node_id in [str(edge.get("src_entity_id", "")), str(edge.get("dst_entity_id", ""))]:
            if node_id in degree:
                degree[node_id] += 1
                weighted_degree[node_id] += weight

    positions: dict[str, tuple[float, float]] = {}
    cluster_rx = 440
    cluster_ry = 255
    for group_idx, group in enumerate(groups):
        if len(groups) == 1:
            group_x, group_y = cx, cy
        else:
            angle = (2 * math.pi * group_idx / max(1, len(groups))) - (math.pi / 2)
            group_x = cx + cluster_rx * math.cos(angle)
            group_y = cy + cluster_ry * math.sin(angle)
        member_radius = 0 if len(group) == 1 else min(96, 46 + (len(group) * 10))
        for member_idx, node in enumerate(group):
            if len(group) == 1:
                x, y = group_x, group_y
            else:
                member_angle = (2 * math.pi * member_idx / len(group)) - (math.pi / 2)
                x = group_x + member_radius * math.cos(member_angle)
                y = group_y + member_radius * math.sin(member_angle)
            positions[str(node["entity_id"])] = (x, y)

    edge_lines = []
    for edge in weighted_edges:
        src = str(edge["src_entity_id"])
        dst = str(edge["dst_entity_id"])
        if src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        weight = parse_float(edge.get("edge_weight"), 0.0)
        dashed = "stroke-dasharray:7 7;" if edge_is_lead_only(edge) else ""
        stroke = "#1d4ed8" if weight >= 0.7 else "#64748b" if weight >= 0.35 else "#94a3b8"
        title = (
            f"{edge.get('src_name', src)} - {edge.get('dst_name', dst)} | "
            f"{flatten(edge.get('connection_types'))} | "
            f"status={flatten(edge.get('statuses')) or 'unknown'} | "
            f"weight={weight:.2f}"
        )
        edge_lines.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="edge" '
            f'style="stroke:{stroke};stroke-width:{1.2 + (weight * 4):.2f};{dashed}">'
            f"<title>{html.escape(title)}</title></line>"
        )

    node_shapes = []
    for node in nodes:
        entity_id = str(node["entity_id"])
        x, y = positions[entity_id]
        group_id = group_by_id.get(entity_id, "G?")
        group_num = int(group_id[1:]) if group_id[1:].isdigit() else 1
        color = colors[(group_num - 1) % len(colors)]
        weight = weighted_degree.get(entity_id, 0.0)
        node_radius = 29 + min(12, weight * 5)
        label = truncate_label(entity_display(node), 24)
        sub = truncate_label(f"{group_id} | {node.get('status', 'unknown')} | deg {degree.get(entity_id, 0)}", 34)
        fill = "#fff7ed" if node.get("public_export", True) is False else "#ffffff"
        title = (
            f"{entity_display(node)} | group={group_id} | "
            f"roles={flatten(node.get('role_tags'))} | "
            f"claims={flatten(node.get('claim_ids'))} | "
            f"sources={flatten(node.get('source_ids'))}"
        )
        node_shapes.append(
            "<g>"
            f"<title>{html.escape(title)}</title>"
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{node_radius:.1f}" class="node" '
            f'style="stroke:{color};fill:{fill};" />'
            f'<text x="{x:.1f}" y="{y + node_radius + 18:.1f}" class="node-label">{html.escape(label)}</text>'
            f'<text x="{x:.1f}" y="{y + node_radius + 34:.1f}" class="node-sub">{html.escape(sub)}</text>'
            "</g>"
        )

    group_rows = "\n".join(
        "<tr>"
        f"<td>G{idx}</td>"
        f"<td>{len(group)}</td>"
        f"<td>{html.escape('; '.join(entity_display(node) for node in group))}</td>"
        "</tr>"
        for idx, group in enumerate(groups, start=1)
    )
    node_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(group_by_id.get(str(node.get('entity_id')), ''))}</td>"
        f"<td>{html.escape(entity_display(node))}</td>"
        f"<td>{html.escape(str(node.get('status', '')))}</td>"
        f"<td>{degree.get(str(node.get('entity_id')), 0)}</td>"
        f"<td>{weighted_degree.get(str(node.get('entity_id')), 0.0):.2f}</td>"
        f"<td>{html.escape(flatten(node.get('role_tags')))}</td>"
        f"<td>{html.escape(flatten(node.get('source_ids')))}</td>"
        "</tr>"
        for node in sorted(nodes, key=lambda row: (group_by_id.get(str(row.get("entity_id")), ""), entity_display(row)))
    )
    edge_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(edge['src_name'])}</td>"
        f"<td>{html.escape(edge['dst_name'])}</td>"
        f"<td>{html.escape(edge_evidence_label(edge))}</td>"
        f"<td>{edge.get('edge_weight', 0):.2f}</td>"
        f"<td>{html.escape(flatten(edge.get('statuses')))}</td>"
        f"<td>{html.escape(str(edge.get('confidence', '')))}</td>"
        f"<td>{html.escape(flatten(edge.get('connection_types')))}</td>"
        f"<td>{html.escape(flatten(edge.get('event_ids')))}</td>"
        f"<td>{html.escape(flatten(edge.get('claim_ids')))}</td>"
        f"<td>{html.escape(flatten(edge.get('source_ids')))}</td>"
        "</tr>"
        for edge in sorted(weighted_edges, key=lambda row: (-parse_float(row.get("edge_weight"), 0.0), row["src_name"], row["dst_name"]))
    )
    strong_edges = sum(1 for edge in weighted_edges if parse_float(edge.get("edge_weight"), 0.0) >= 0.7)
    lead_edges = sum(1 for edge in weighted_edges if edge_is_lead_only(edge))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Evidence-weighted people graph - {html.escape(case_title)}</title>
<style>
body {{ margin: 0; font-family: Arial, sans-serif; color: #1f2933; background: #f7f8fa; }}
main {{ max-width: 1420px; margin: 0 auto; padding: 28px; }}
h1 {{ font-size: 26px; margin: 0 0 6px; }}
h2 {{ font-size: 18px; margin: 0 0 14px; }}
p {{ max-width: 1080px; line-height: 1.45; }}
.summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }}
.metric {{ background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 14px; }}
.metric strong {{ display: block; font-size: 22px; margin-bottom: 4px; }}
.metric span {{ color: #475569; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
.panel {{ background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 18px; margin-top: 18px; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 14px 0 0; color: #475569; font-size: 13px; }}
.legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
.swatch {{ width: 22px; height: 0; border-top: 4px solid #1d4ed8; display: inline-block; }}
.swatch.medium {{ border-color: #64748b; }}
.swatch.weak {{ border-color: #94a3b8; border-top-style: dashed; }}
svg {{ width: 100%; height: auto; background: #fbfcfe; border: 1px solid #d8dee6; border-radius: 8px; }}
.edge {{ opacity: 0.82; }}
.node {{ stroke-width: 4; }}
.node-label {{ fill: #111827; font-size: 13px; font-weight: 700; text-anchor: middle; }}
.node-sub {{ fill: #475569; font-size: 11px; text-anchor: middle; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ border-bottom: 1px solid #e2e8f0; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #eef2f7; }}
@media (max-width: 860px) {{
  main {{ padding: 16px; }}
  .summary {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  table {{ font-size: 12px; }}
}}
</style>
</head>
<body>
<main>
<h1>Evidence-weighted people graph</h1>
<p>{html.escape(case_title)}. Scope: {"public and internal rows" if include_private else "public-export rows only"}. Edges are source-bound direct person-person relationships or shared event/context links; contextual links do not imply direct participation.</p>
<div class="summary">
<div class="metric"><strong>{len(nodes)}</strong><span>People</span></div>
<div class="metric"><strong>{len(weighted_edges)}</strong><span>Edges</span></div>
<div class="metric"><strong>{len(groups)}</strong><span>Connected groups</span></div>
<div class="metric"><strong>{strong_edges}/{lead_edges}</strong><span>Strong / lead edges</span></div>
</div>
<section class="panel">
<svg viewBox="0 0 {width} {height}" role="img" aria-label="People-only connection graph">
{''.join(edge_lines)}
{''.join(node_shapes)}
</svg>
<div class="legend">
<span><i class="swatch"></i> higher-weight evidence edge</span>
<span><i class="swatch medium"></i> medium evidence edge</span>
<span><i class="swatch weak"></i> lead/context edge</span>
<span>Node outline color marks graph group; node size follows weighted degree.</span>
</div>
</section>
<section class="panel">
<h2>Graph Groups</h2>
<table>
<thead><tr><th>Group</th><th>People</th><th>Members</th></tr></thead>
<tbody>{group_rows}</tbody>
</table>
</section>
<section class="panel">
<h2>People</h2>
<table>
<thead><tr><th>Group</th><th>Person</th><th>Status</th><th>Degree</th><th>Weighted Degree</th><th>Roles</th><th>Sources</th></tr></thead>
<tbody>{node_rows}</tbody>
</table>
</section>
<section class="panel">
<h2>Edges</h2>
<table>
<thead><tr><th>Person</th><th>Person</th><th>Evidence</th><th>Weight</th><th>Status</th><th>Confidence</th><th>Connection</th><th>Events</th><th>Claims</th><th>Sources</th></tr></thead>
<tbody>
{edge_rows}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def render_subcase_timeline_html(
    case_title: str,
    subcase_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    include_private: bool,
) -> str:
    width = 1320
    left = 260
    right = 40
    top = 70
    lane_h = 95
    height = max(360, top + lane_h * max(1, len(subcase_rows)) + 80)
    dated = [row for row in event_rows if date_sort_key(row.get("start_date"))[0] != 9999]
    years = [date_sort_key(row.get("start_date"))[0] for row in dated] or [2000]
    min_year = min(years)
    max_year = max(years) + 1
    span = max_year - min_year

    def x_for(date_value: Any) -> float:
        year, month, day, _ = date_sort_key(date_value)
        frac = (year - min_year) + ((month - 1) / 12) + ((day - 1) / 365)
        return left + (frac / span) * (width - left - right)

    lane_y = {row["subcase_id"]: top + idx * lane_h for idx, row in enumerate(subcase_rows)}
    axis = [
        f'<line x1="{left}" y1="{top - 30}" x2="{width - right}" y2="{top - 30}" class="axis" />'
    ]
    for year in range(min_year, max_year + 1, max(1, (max_year - min_year) // 6 or 1)):
        x = left + ((year - min_year) / span) * (width - left - right)
        axis.append(f'<line x1="{x:.1f}" y1="{top - 38}" x2="{x:.1f}" y2="{height - 45}" class="grid" />')
        axis.append(f'<text x="{x:.1f}" y="{top - 45}" class="axis-label">{year}</text>')

    lanes = []
    for row in subcase_rows:
        y = lane_y[row["subcase_id"]]
        lanes.append(f'<text x="24" y="{y + 6}" class="lane-label">{html.escape(row["subcase_title"])}</text>')
        lanes.append(f'<line x1="{left}" y1="{y}" x2="{width - right}" y2="{y}" class="lane" />')

    points = []
    for row in event_rows:
        subcase_id = row["subcase_id"]
        if subcase_id not in lane_y:
            continue
        x = x_for(row.get("start_date"))
        y = lane_y[subcase_id]
        color_class = "verified" if row.get("status") == "verified" else "single"
        label = truncate_label(str(row.get("title", "")), 38)
        points.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" class="point {color_class}" />')
        points.append(f'<text x="{x + 10:.1f}" y="{y - 10:.1f}" class="event-label">{html.escape(label)}</text>')
        points.append(f'<text x="{x + 10:.1f}" y="{y + 8:.1f}" class="event-date">{html.escape(str(row.get("start_date", "")))}</text>')

    table_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('start_date', '')))}</td>"
        f"<td>{html.escape(str(row.get('subcase_title', '')))}</td>"
        f"<td>{html.escape(str(row.get('title', '')))}</td>"
        f"<td>{html.escape(str(row.get('status', '')))}</td>"
        f"<td>{html.escape(flatten(row.get('evidence_levels')))}</td>"
        f"<td>{html.escape(str(row.get('source_grades', '')))}</td>"
        f"<td>{html.escape(flatten(row.get('claim_ids')))}</td>"
        "</tr>"
        for row in event_rows
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Subcase timeline chart - {html.escape(case_title)}</title>
<style>
body {{ margin: 0; font-family: Arial, sans-serif; color: #1f2933; background: #f7f8fa; }}
main {{ max-width: 1440px; margin: 0 auto; padding: 28px; }}
h1 {{ font-size: 26px; margin: 0 0 6px; }}
p {{ max-width: 980px; line-height: 1.45; }}
.panel {{ background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 18px; margin-top: 18px; }}
svg {{ width: 100%; height: auto; background: #fbfcfe; border: 1px solid #d8dee6; border-radius: 8px; }}
.axis {{ stroke: #334155; stroke-width: 1.5; }}
.grid {{ stroke: #d8dee6; stroke-width: 1; }}
.lane {{ stroke: #cbd5e1; stroke-width: 1.5; }}
.lane-label {{ fill: #111827; font-size: 13px; font-weight: 700; }}
.axis-label {{ fill: #475569; font-size: 12px; text-anchor: middle; }}
.point {{ stroke: #ffffff; stroke-width: 2; }}
.verified {{ fill: #2563eb; }}
.single {{ fill: #0f766e; }}
.event-label {{ fill: #111827; font-size: 12px; font-weight: 700; paint-order: stroke; stroke: #fbfcfe; stroke-width: 4px; }}
.event-date {{ fill: #475569; font-size: 11px; paint-order: stroke; stroke: #fbfcfe; stroke-width: 4px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ border-bottom: 1px solid #e2e8f0; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #eef2f7; }}
</style>
</head>
<body>
<main>
<h1>Subcase timeline chart</h1>
<p>{html.escape(case_title)}. Scope: {"public and internal rows" if include_private else "public-export rows only"}. Subcase lanes are inferred from source-bound event and claim text.</p>
<section class="panel">
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Subcase timeline chart">
{''.join(axis)}
{''.join(lanes)}
{''.join(points)}
</svg>
</section>
<section class="panel">
<h2>Timeline rows</h2>
<table>
<thead><tr><th>Date</th><th>Subcase</th><th>Event</th><th>Status</th><th>Evidence</th><th>Sources</th><th>Claims</th></tr></thead>
<tbody>
{table_rows}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def export_case_charts(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    include_private = args.include_private
    out = Path(args.out_dir).expanduser().resolve() if args.out_dir else cdir / "exports" / "charts"
    out.mkdir(parents=True, exist_ok=True)

    case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
    case_title = str(case_meta.get("title", cdir.name))
    sources = public_rows(read_jsonl(record_path(cdir, "sources")), include_private)
    entities = public_rows(read_jsonl(record_path(cdir, "entities")), include_private)
    claims = public_rows(read_jsonl(record_path(cdir, "claims")), include_private)
    events = public_rows(read_jsonl(record_path(cdir, "events")), include_private)
    event_links = public_rows(read_jsonl(record_path(cdir, "event_links")), include_private)
    relationships = public_rows(read_jsonl(record_path(cdir, "relationships")), include_private)

    source_by_id = {source.get("source_id"): source for source in sources}
    claim_by_id = {claim.get("claim_id"): claim for claim in claims}
    people = [
        entity for entity in entities
        if entity.get("entity_type") == "person"
    ]
    people_by_id = {str(person.get("entity_id")): person for person in people}

    edge_map: dict[tuple[str, str], dict[str, Any]] = {}
    for rel in relationships:
        src_id = str(rel.get("src_entity_id", ""))
        dst_id = str(rel.get("dst_entity_id", ""))
        if src_id in people_by_id and dst_id in people_by_id:
            merge_people_edge(
                edge_map,
                src_id,
                dst_id,
                people_by_id=people_by_id,
                connection_type=str(rel.get("relation_type", "")),
                rel_ids=[str(rel.get("rel_id", ""))],
                claim_ids=[str(claim_id) for claim_id in rel.get("claim_ids", [])],
                source_ids=[str(source_id) for source_id in rel.get("source_ids", [])],
                statuses=[str(rel.get("status", ""))],
                confidence=rel.get("confidence", 0),
                public_export=rel.get("public_export", True) is not False,
                notes=[str(rel.get("notes", ""))] if rel.get("notes") else [],
            )

    links_by_event: dict[str, list[dict[str, Any]]] = {}
    for link in event_links:
        links_by_event.setdefault(str(link.get("event_id", "")), []).append(link)

    for event in events:
        event_id = str(event.get("event_id", ""))
        person_roles: dict[str, list[str]] = {}
        person_claims: dict[str, list[str]] = {}
        person_sources: dict[str, list[str]] = {}
        for entity_id in event.get("entity_ids", []) or []:
            entity_id = str(entity_id)
            if entity_id in people_by_id:
                person_roles.setdefault(entity_id, []).append("event_entity")
                person_claims.setdefault(entity_id, []).extend(str(cid) for cid in event.get("claim_ids", []) or [])
                person_sources.setdefault(entity_id, []).extend(str(sid) for sid in event.get("source_ids", []) or [])
        for link in links_by_event.get(event_id, []):
            entity_id = str(link.get("entity_id", ""))
            if entity_id in people_by_id:
                person_roles.setdefault(entity_id, []).append(str(link.get("relation_type", "")))
                person_claims.setdefault(entity_id, []).extend(str(cid) for cid in link.get("claim_ids", []) or [])
                person_sources.setdefault(entity_id, []).extend(str(sid) for sid in link.get("source_ids", []) or [])
        person_ids = sorted(person_roles)
        for src_id, dst_id in combinations(person_ids, 2):
            relation_type = best_pair_relation(person_roles[src_id], person_roles[dst_id])
            merge_people_edge(
                edge_map,
                src_id,
                dst_id,
                people_by_id=people_by_id,
                connection_type=relation_type,
                event_ids=[event_id],
                claim_ids=sorted(set(person_claims.get(src_id, []) + person_claims.get(dst_id, []))),
                source_ids=sorted(set(person_sources.get(src_id, []) + person_sources.get(dst_id, []))),
                statuses=[str(event.get("status", ""))],
                confidence=event.get("confidence", 0),
                public_export=event.get("public_export", True) is not False,
                notes=[f"Shared event: {event.get('title', event_id)}"],
            )

    people_edges = sorted(edge_map.values(), key=lambda row: (row["src_name"], row["dst_name"]))
    people_nodes = []
    for person in people:
        node = dict(person)
        if not include_private:
            node["claim_ids"] = [claim_id for claim_id in node.get("claim_ids", []) if claim_id in claim_by_id]
        people_nodes.append(node)
    people_nodes = sorted(people_nodes, key=lambda person: entity_display(person))

    write_csv(out / "people_nodes.csv", people_nodes, [
        "entity_id", "name", "display_name", "aliases", "status", "role_tags", "privacy_level", "living_status", "source_ids", "claim_ids", "public_export"
    ])
    write_csv(out / "people_edges.csv", people_edges, [
        "src_entity_id", "dst_entity_id", "src_name", "dst_name", "connection_types", "event_ids", "rel_ids", "claim_ids", "source_ids",
        "statuses", "confidence", "public_export", "notes"
    ])
    (out / "people_graph.html").write_text(
        render_people_graph_html(case_title, people_nodes, people_edges, include_private),
        encoding="utf-8",
    )

    timeline_rows: list[dict[str, Any]] = []
    subcase_counts: dict[str, dict[str, Any]] = {}
    for event in events:
        event_claims = [
            claim_by_id[claim_id]
            for claim_id in event.get("claim_ids", [])
            if claim_id in claim_by_id
        ]
        subcase_id = infer_subcase(event, event_claims)
        subcase_title = SUBCASE_TITLES.get(subcase_id, subcase_id)
        source_ids = set(str(source_id) for source_id in event.get("source_ids", []) or [])
        for claim in event_claims:
            source_ids.update(str(source_id) for source_id in claim.get("source_ids", []) or [])
        source_rows = [source_by_id[source_id] for source_id in sorted(source_ids) if source_id in source_by_id]
        evidence_levels = sorted({
            evidence_level(claim, [source_by_id[sid] for sid in claim.get("source_ids", []) if sid in source_by_id])
            for claim in event_claims
        })
        row = {
            "subcase_id": subcase_id,
            "subcase_title": subcase_title,
            "event_id": event.get("event_id", ""),
            "start_date": event.get("start_date", ""),
            "end_date": event.get("end_date", ""),
            "date_precision": event.get("date_precision", ""),
            "event_type": event.get("event_type", ""),
            "title": event.get("title", ""),
            "status": event.get("status", ""),
            "confidence": event.get("confidence", ""),
            "claim_ids": [claim.get("claim_id", "") for claim in event_claims],
            "evidence_levels": evidence_levels,
            "source_grades": grade_summary(source_rows),
            "source_ids": [source.get("source_id", "") for source in source_rows],
            "public_export": event.get("public_export", True),
        }
        timeline_rows.append(row)
        summary = subcase_counts.setdefault(subcase_id, {
            "subcase_id": subcase_id,
            "subcase_title": subcase_title,
            "event_count": 0,
            "claim_count": 0,
            "first_date": "",
            "last_date": "",
        })
        summary["event_count"] += 1
        summary["claim_count"] += len(event_claims)
        if not summary["first_date"] or date_sort_key(event.get("start_date")) < date_sort_key(summary["first_date"]):
            summary["first_date"] = event.get("start_date", "")
        if not summary["last_date"] or date_sort_key(event.get("start_date")) > date_sort_key(summary["last_date"]):
            summary["last_date"] = event.get("start_date", "")

    timeline_rows.sort(key=lambda row: (row["subcase_id"], date_sort_key(row.get("start_date")), row.get("event_id", "")))
    subcase_rows = sorted(subcase_counts.values(), key=lambda row: (date_sort_key(row.get("first_date")), row["subcase_id"]))
    write_csv(out / "subcase_summary.csv", subcase_rows, [
        "subcase_id", "subcase_title", "event_count", "claim_count", "first_date", "last_date"
    ])
    write_csv(out / "subcase_timelines.csv", timeline_rows, [
        "subcase_id", "subcase_title", "event_id", "start_date", "end_date", "date_precision", "event_type", "title", "status",
        "confidence", "claim_ids", "evidence_levels", "source_grades", "source_ids", "public_export"
    ])
    (out / "subcase_timelines.html").write_text(
        render_subcase_timeline_html(case_title, subcase_rows, timeline_rows, include_private),
        encoding="utf-8",
    )

    index = [
        f"# Case charts: {case_title}",
        "",
        f"Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}",
        "",
        "## Files",
        "",
        "- `people_graph.html`",
        "- `people_nodes.csv`",
        "- `people_edges.csv`",
        "- `subcase_timelines.html`",
        "- `subcase_timelines.csv`",
        "- `subcase_summary.csv`",
        "",
        "## People Graph",
        "",
        f"People: {len(people_nodes)}",
        f"Edges: {len(people_edges)}",
        "",
        "## Subcase Timelines",
        "",
        md_table(
            ["Subcase", "Events", "Claims", "First", "Last"],
            [[row["subcase_title"], row["event_count"], row["claim_count"], row["first_date"], row["last_date"]] for row in subcase_rows],
        ),
    ]
    (out / "charts.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"Exported case charts to {out}")


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"Missing CSV: {path}")
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def parse_cell_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [part for part in str(value).split(";") if part]


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
    finite = [
        distance
        for (left, right), distance in dist.items()
        if left != right and not math.isinf(distance) and distance > 0
    ]
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
            "python ../.agents/skills/truecrime-cult-research/scripts/tcr.py export-people-clusters ..."
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
        partition = leidenalg.find_partition(
            graph,
            leidenalg.RBConfigurationVertexPartition,
            weights=weights,
            resolution_parameter=resolution,
            seed=seed,
        )
        communities = [[node_ids[idx] for idx in community] for community in partition]
    else:
        communities = [[node_id] for node_id in node_ids]
    return [sorted(community) for community in communities]


def render_people_clusters_html(
    case_title: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    cluster_by_id: dict[str, str],
    density_by_id: dict[str, float],
    include_private: bool,
) -> str:
    width = 1280
    height = 820
    colors = ["#2563eb", "#0f766e", "#7c3aed", "#b45309", "#be123c", "#475569", "#15803d", "#0369a1"]
    clusters: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        clusters.setdefault(cluster_by_id[str(node["entity_id"])], []).append(node)
    cluster_ids = sorted(clusters)
    cx = width / 2
    cy = height / 2
    cluster_radius = 250
    positions: dict[str, tuple[float, float]] = {}
    for cluster_idx, cluster_id in enumerate(cluster_ids):
        angle = (2 * math.pi * cluster_idx / max(1, len(cluster_ids))) - (math.pi / 2)
        cluster_x = cx + cluster_radius * math.cos(angle)
        cluster_y = cy + cluster_radius * math.sin(angle)
        members = sorted(clusters[cluster_id], key=entity_display)
        member_radius = 48 if len(members) > 1 else 0
        for member_idx, node in enumerate(members):
            if len(members) == 1:
                x, y = cluster_x, cluster_y
            else:
                member_angle = (2 * math.pi * member_idx / len(members)) - (math.pi / 2)
                x = cluster_x + member_radius * math.cos(member_angle)
                y = cluster_y + member_radius * math.sin(member_angle)
            positions[str(node["entity_id"])] = (x, y)

    edge_lines = []
    for edge in edges:
        src = str(edge["src_entity_id"])
        dst = str(edge["dst_entity_id"])
        if src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        weight = parse_float(edge.get("edge_weight"), 0.0)
        dashed = "stroke-dasharray:6 6;" if "co_mentioned_with" in parse_cell_list(edge.get("connection_types")) else ""
        edge_lines.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'class="edge" style="stroke-width:{0.75 + (weight * 4):.2f};{dashed}" />'
        )

    node_shapes = []
    for node in nodes:
        entity_id = str(node["entity_id"])
        x, y = positions[entity_id]
        cluster_id = cluster_by_id[entity_id]
        color = colors[(int(cluster_id[1:]) - 1) % len(colors)] if cluster_id[1:].isdigit() else colors[0]
        density = density_by_id.get(entity_id, 0.0)
        radius = 24 + min(16, density * 18)
        label = truncate_label(entity_display(node), 24)
        node_shapes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" class="node" style="stroke:{color};" />'
            f'<text x="{x:.1f}" y="{y + radius + 18:.1f}" class="node-label">{html.escape(label)}</text>'
            f'<text x="{x:.1f}" y="{y + radius + 34:.1f}" class="node-sub">{html.escape(cluster_id)} kde={density:.2f}</text>'
        )

    node_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(cluster_by_id[str(node['entity_id'])])}</td>"
        f"<td>{html.escape(entity_display(node))}</td>"
        f"<td>{density_by_id.get(str(node['entity_id']), 0.0):.6f}</td>"
        f"<td>{html.escape(str(node.get('status', '')))}</td>"
        f"<td>{html.escape(str(node.get('public_export', '')))}</td>"
        "</tr>"
        for node in sorted(nodes, key=lambda row: (cluster_by_id[str(row["entity_id"])], entity_display(row)))
    )
    edge_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(edge.get('src_name', '')))}</td>"
        f"<td>{html.escape(str(edge.get('dst_name', '')))}</td>"
        f"<td>{html.escape(str(edge.get('edge_weight', '')))}</td>"
        f"<td>{html.escape(str(edge.get('connection_types', '')))}</td>"
        f"<td>{html.escape(str(edge.get('statuses', '')))}</td>"
        "</tr>"
        for edge in sorted(edges, key=lambda row: (str(row.get("src_name", "")), str(row.get("dst_name", ""))))
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Leiden people clusters - {html.escape(case_title)}</title>
<style>
body {{ margin: 0; font-family: Arial, sans-serif; color: #1f2933; background: #f7f8fa; }}
main {{ max-width: 1420px; margin: 0 auto; padding: 28px; }}
h1 {{ font-size: 26px; margin: 0 0 6px; }}
p {{ max-width: 980px; line-height: 1.45; }}
.panel {{ background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 18px; margin-top: 18px; }}
svg {{ width: 100%; height: auto; background: #fbfcfe; border: 1px solid #d8dee6; border-radius: 8px; }}
.edge {{ stroke: #64748b; opacity: 0.78; }}
.node {{ fill: #ffffff; stroke-width: 4; }}
.node-label {{ fill: #111827; font-size: 13px; font-weight: 700; text-anchor: middle; }}
.node-sub {{ fill: #475569; font-size: 11px; text-anchor: middle; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ border-bottom: 1px solid #e2e8f0; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #eef2f7; }}
</style>
</head>
<body>
<main>
<h1>Leiden people clusters</h1>
<p>{html.escape(case_title)}. Scope: {"public and internal rows" if include_private else "public-export rows only"}. Edge weights are evidence-weighted; node size is graph-kernel density. Dashed edges include weak co-mentions and should be treated as leads only.</p>
<section class="panel">
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Leiden people clusters">
{''.join(edge_lines)}
{''.join(node_shapes)}
</svg>
</section>
<section class="panel">
<h2>Clustered People</h2>
<table>
<thead><tr><th>Cluster</th><th>Person</th><th>KDE</th><th>Status</th><th>Public Export</th></tr></thead>
<tbody>{node_rows}</tbody>
</table>
</section>
<section class="panel">
<h2>Weighted Edges</h2>
<table>
<thead><tr><th>Person</th><th>Person</th><th>Weight</th><th>Connection</th><th>Status</th></tr></thead>
<tbody>{edge_rows}</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def export_people_clusters(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    out = Path(args.out_dir).expanduser().resolve() if args.out_dir else cdir / "exports" / "clusters"
    charts_dir = Path(args.charts_dir).expanduser().resolve() if args.charts_dir else cdir / "exports" / "charts"
    out.mkdir(parents=True, exist_ok=True)

    export_case_charts(argparse.Namespace(case_dir=args.case_dir, out_dir=str(charts_dir), include_private=args.include_private))

    case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
    case_title = str(case_meta.get("title", cdir.name))
    nodes = read_csv_dicts(charts_dir / "people_nodes.csv")
    raw_edges = read_csv_dicts(charts_dir / "people_edges.csv")
    node_ids = [str(node["entity_id"]) for node in nodes]
    node_by_id = {str(node["entity_id"]): node for node in nodes}

    weighted_edges: list[dict[str, Any]] = []
    for edge in raw_edges:
        row: dict[str, Any] = dict(edge)
        row["edge_weight"] = evidence_edge_weight(row)
        weighted_edges.append(row)

    communities = leiden_partition(
        node_ids,
        weighted_edges,
        resolution=args.resolution,
        seed=args.seed,
    )
    communities = sorted(
        communities,
        key=lambda community: (-len(community), min(entity_display(node_by_id[node_id]) for node_id in community)),
    )
    cluster_by_id: dict[str, str] = {}
    for idx, community in enumerate(communities, start=1):
        cluster_id = f"C{idx}"
        for node_id in community:
            cluster_by_id[node_id] = cluster_id

    dist = weighted_distances(node_ids, weighted_edges)
    kernel, sigma = kernel_affinity_matrix(node_ids, dist, args.sigma)
    kde_by_id = {
        node_id: round(sum(kernel[(node_id, other)] for other in node_ids) / max(1, len(node_ids)), 6)
        for node_id in node_ids
    }
    degree: dict[str, int] = {node_id: 0 for node_id in node_ids}
    weighted_degree: dict[str, float] = {node_id: 0.0 for node_id in node_ids}
    for edge in weighted_edges:
        src = str(edge["src_entity_id"])
        dst = str(edge["dst_entity_id"])
        weight = parse_float(edge.get("edge_weight"), 0.0)
        for node_id in (src, dst):
            if node_id in degree:
                degree[node_id] += 1
                weighted_degree[node_id] += weight

    cluster_rows: list[dict[str, Any]] = []
    for node in nodes:
        node_id = str(node["entity_id"])
        cluster_rows.append({
            "cluster_id": cluster_by_id.get(node_id, ""),
            "entity_id": node_id,
            "name": entity_display(node),
            "status": node.get("status", ""),
            "public_export": node.get("public_export", ""),
            "kde_density": kde_by_id.get(node_id, 0.0),
            "degree": degree.get(node_id, 0),
            "weighted_degree": round(weighted_degree.get(node_id, 0.0), 6),
            "claim_ids": node.get("claim_ids", ""),
            "source_ids": node.get("source_ids", ""),
        })
    cluster_rows.sort(key=lambda row: (row["cluster_id"], -float(row["kde_density"]), row["name"]))

    summary_rows: list[dict[str, Any]] = []
    for cluster_id in sorted(set(cluster_by_id.values())):
        members = [node_id for node_id, cid in cluster_by_id.items() if cid == cluster_id]
        internal_weight = 0.0
        boundary_weight = 0.0
        for edge in weighted_edges:
            src = str(edge["src_entity_id"])
            dst = str(edge["dst_entity_id"])
            weight = parse_float(edge.get("edge_weight"), 0.0)
            if src in members and dst in members:
                internal_weight += weight
            elif src in members or dst in members:
                boundary_weight += weight
        summary_rows.append({
            "cluster_id": cluster_id,
            "size": len(members),
            "members": ";".join(entity_display(node_by_id[node_id]) for node_id in sorted(members, key=lambda nid: entity_display(node_by_id[nid]))),
            "mean_kde_density": round(sum(kde_by_id[node_id] for node_id in members) / max(1, len(members)), 6),
            "internal_edge_weight": round(internal_weight, 6),
            "boundary_edge_weight": round(boundary_weight, 6),
        })

    kernel_rows = []
    for node_id in node_ids:
        row = {"entity_id": node_id, "name": entity_display(node_by_id[node_id])}
        for other in node_ids:
            row[other] = kernel[(node_id, other)]
        kernel_rows.append(row)

    edge_rows = []
    for edge in weighted_edges:
        src = str(edge["src_entity_id"])
        dst = str(edge["dst_entity_id"])
        edge_rows.append({
            **edge,
            "src_cluster_id": cluster_by_id.get(src, ""),
            "dst_cluster_id": cluster_by_id.get(dst, ""),
            "same_cluster": cluster_by_id.get(src) == cluster_by_id.get(dst),
            "edge_weight": edge["edge_weight"],
        })

    write_csv(out / "people_clusters.csv", cluster_rows, [
        "cluster_id", "entity_id", "name", "status", "public_export", "kde_density", "degree", "weighted_degree", "claim_ids", "source_ids",
    ])
    write_csv(out / "cluster_summary.csv", summary_rows, [
        "cluster_id", "size", "members", "mean_kde_density", "internal_edge_weight", "boundary_edge_weight",
    ])
    write_csv(out / "people_cluster_edges.csv", edge_rows, [
        "src_entity_id", "dst_entity_id", "src_name", "dst_name", "src_cluster_id", "dst_cluster_id", "same_cluster", "connection_types",
        "statuses", "confidence", "edge_weight", "event_ids", "rel_ids", "claim_ids", "source_ids", "public_export", "notes",
    ])
    write_csv(out / "people_kernel_matrix.csv", kernel_rows, ["entity_id", "name", *node_ids])
    (out / "people_clusters.html").write_text(
        render_people_clusters_html(case_title, nodes, edge_rows, cluster_by_id, kde_by_id, args.include_private),
        encoding="utf-8",
    )

    report_lines = [
        f"# Leiden people clustering: {case_title}",
        "",
        f"Scope: {'public and private/internal rows' if args.include_private else 'public-export rows only'}",
        f"Leiden resolution: {args.resolution}",
        f"Leiden seed: {args.seed}",
        f"Kernel sigma: {sigma:.6f}",
        "",
        "## Files",
        "",
        "- `people_clusters.html`",
        "- `people_clusters.csv`",
        "- `cluster_summary.csv`",
        "- `people_cluster_edges.csv`",
        "- `people_kernel_matrix.csv`",
        "- `clusters.md`",
        "",
        "## Clusters",
        "",
        md_table(
            ["Cluster", "Size", "Mean KDE", "Internal Weight", "Boundary Weight", "Members"],
            [
                [
                    row["cluster_id"],
                    row["size"],
                    row["mean_kde_density"],
                    row["internal_edge_weight"],
                    row["boundary_edge_weight"],
                    row["members"],
                ]
                for row in summary_rows
            ],
        ),
        "",
        "## Interpretation Guardrails",
        "",
        "- Leiden clusters organize current graph structure; they are not evidence of a unified conspiracy.",
        "- Kernel density is graph-neighborhood density over evidence-weighted edges, not geographic density.",
        "- Weak `co_mentioned_with` edges are downweighted and remain lead-only.",
        "- Non-public rows remain for internal review unless separately privacy-reviewed.",
    ]
    (out / "clusters.md").write_text("\n".join(str(line) for line in report_lines) + "\n", encoding="utf-8")
    print(f"Exported Leiden people clusters to {out}")


STATUS_SCORE = {
    "verified": 1.0,
    "corroborated": 0.9,
    "single_source": 0.65,
    "disputed": 0.35,
    "unverified": 0.2,
    "excluded_from_public_script": 0.1,
    "false_or_retracted": 0.05,
}

GRADE_SCORE = {"A": 1.0, "B": 0.82, "C": 0.55, "D": 0.25, "X": 0.0}


def source_grade_score(source_rows: list[dict[str, Any]]) -> float:
    if not source_rows:
        return 0.0
    return round(max(GRADE_SCORE.get(str(source.get("reliability_grade", "")), 0.35) for source in source_rows), 3)


def readiness_label(row: dict[str, Any], source_rows: list[dict[str, Any]] | None = None) -> str:
    status = str(row.get("status", ""))
    privacy = str(row.get("privacy_review", "clear"))
    public_export = row.get("public_export", True) is not False
    grades = {str(source.get("reliability_grade", "")) for source in (source_rows or [])}
    if not public_export:
        return "internal_only"
    if privacy and privacy != "clear":
        return "needs_privacy_review"
    if status in {"excluded_from_public_script", "false_or_retracted"}:
        return "excluded_or_retracted"
    if status in {"disputed", "unverified"}:
        return "lead_or_disputed"
    if status == "single_source":
        return "source_note_required"
    if status in {"verified", "corroborated"} and grades and grades <= {"A", "B"}:
        return "public_ready"
    if status in {"verified", "corroborated"}:
        return "usable_with_context"
    return "review_needed"


def chart_row_table(rows: list[dict[str, Any]], columns: list[str], limit: int = 25) -> str:
    display_rows = rows[:limit]
    if not display_rows:
        return "<p class=\"muted\">No rows.</p>"
    head = "".join(f"<th>{html.escape(col.replace('_', ' ').title())}</th>" for col in columns)
    body = []
    for row in display_rows:
        cells = "".join(f"<td>{html.escape(flatten(row.get(col)))}</td>" for col in columns)
        body.append(f"<tr>{cells}</tr>")
    extra = f"<p class=\"muted\">Showing {len(display_rows)} of {len(rows)} rows.</p>" if len(rows) > limit else ""
    return f"<div class=\"table-wrap\"><table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>{extra}"


def simple_bar_rows(rows: list[dict[str, Any]], label_key: str, value_key: str, color_key: str | None = None, limit: int = 20) -> str:
    if not rows:
        return "<p class=\"muted\">No rows.</p>"
    max_value = max((parse_float(row.get(value_key), 0.0) for row in rows), default=1.0) or 1.0
    parts = []
    for row in rows[:limit]:
        value = parse_float(row.get(value_key), 0.0)
        width = max(2.0, 100.0 * value / max_value)
        color_class = slugify(str(row.get(color_key or label_key, "bar")), 24)
        parts.append(
            "<div class=\"bar-row\">"
            f"<span class=\"bar-label\">{html.escape(str(row.get(label_key, '')))}</span>"
            f"<span class=\"bar-track\"><span class=\"bar-fill c-{color_class}\" style=\"width:{width:.1f}%\"></span></span>"
            f"<span class=\"bar-value\">{html.escape(str(row.get(value_key, '')))}</span>"
            "</div>"
        )
    return "".join(parts)


def record_id_for(row: dict[str, Any]) -> str:
    for key in ["claim_id", "event_id", "event_link_id", "rel_id", "entity_id", "source_id"]:
        if row.get(key):
            return str(row[key])
    return ""


def public_ready_record(row: dict[str, Any]) -> bool:
    privacy = str(row.get("privacy_review", "clear") or "clear")
    return row.get("public_export", True) is not False and privacy == "clear"


def best_grade(source_rows: list[dict[str, Any]]) -> str:
    return max(
        (str(source.get("reliability_grade", "")) for source in source_rows),
        key=lambda grade: GRADE_SCORE.get(grade, 0.0),
        default="",
    )


def source_grade_counts(source_rows: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for source in source_rows:
        grade = str(source.get("reliability_grade", "") or "unknown")
        counts[grade] = counts.get(grade, 0) + 1
    return ";".join(f"{grade}:{counts[grade]}" for grade in sorted(counts))


def weakest_status(statuses: list[str]) -> str:
    return min(statuses, key=lambda status: STATUS_SCORE.get(status, 0.0), default="")


def boundary_signal(row: dict[str, Any]) -> bool:
    text = " ".join(
        str(row.get(key, ""))
        for key in ["claim", "claim_type", "relation_type", "event_type", "title", "notes", "status"]
    ).lower()
    return bool(parse_cell_list(row.get("contradicts"))) or any(
        term in text
        for term in [
            "boundary",
            "contradict",
            "disputed",
            "unverified",
            "lead-only",
            "lead only",
            "not verified",
            "not proof",
            "unclear",
            "category bridge",
            "context only",
        ]
    )


def relation_family(relation_type: str, record_kind: str = "relationship") -> str:
    rel = relation_type.lower()
    if "co_mentioned" in rel:
        return "lead_only_co_mentions"
    if record_kind == "event_link":
        return "event_context"
    if any(term in rel for term in ["found", "co_found", "member", "participant", "opened", "completed_treatment", "program"]):
        return "treatment_lineage"
    if any(term in rel for term in ["father", "family", "sentenced", "criminal", "teacher", "headmaster", "hired"]):
        return "legal_criminal_or_family"
    if any(term in rel for term in ["promis", "inslaw", "cia", "institution", "contract", "inquiry"]):
        return "software_inquiry_context"
    if any(term in rel for term in ["behavior", "authority", "category", "context"]):
        return "category_bridges"
    return "institutional_or_career_roles"


def relationship_class(record: dict[str, Any], record_kind: str = "relationship") -> str:
    explicit = str(record.get("relationship_class") or "").strip()
    if explicit in RELATIONSHIP_CLASS_TITLES:
        return explicit
    relation_type = str(record.get("relation_type", "")).lower()
    status = str(record.get("status", "")).lower()
    notes = str(record.get("notes", "")).lower()
    basis = str(record.get("basis", "")).lower()
    summary = str(record.get("summary", "")).lower()
    record_id = str(record.get("rel_id") or record.get("event_link_id") or record.get("claim_id") or "").lower()
    text = " ".join([record_id, relation_type, status, notes, basis, summary])
    if "co_mentioned" in relation_type:
        return "hypothesis_requires_more_sources"
    if any(term in text for term in [
        "successor",
        "part_of_program",
        "component_of",
        "absorbed_into",
        "outgrowth",
        "redesignated",
        "program_lineage",
    ]):
        return "documented_successor"
    if any(term in text for term in [
        "therapeutic_community_model",
        "therapeutic_community",
        "therapeutic-community",
        "source_model_context",
        "model_context",
        "reformulated_program_context",
        "reported_method",
        "treatment_context",
        "treatment-model",
        "treatment model",
        "treatment-method",
        "treatment method",
        "prior_treatment_context",
        "method",
        "behavior_modification",
        "behavior modification",
        "authority_conformity",
        "authority/conformity",
        "obedience research",
        "classic studies in the conformity debate",
        "drug_rehabilitation",
        "drug rehabilitation",
        "rehabilitation program",
        "category_member_context",
        "category bridge",
        "category_bridge",
        "behavioral context",
        "drug rehab category",
        "peer pressure",
        "self-help",
        "residential program",
        "source_describes_as",
        "writings_described_as_basis",
        "based on hubbard",
        "drug residues",
        "narconon",
        "origin_context_for",
    ]):
        return "method_diffusion"
    if any(term in text for term in [
        "narrative",
        "legend",
        "monarch",
        "montauk",
        "milab",
        "super_soldier",
        "targeted_individual",
        "synthetic_telepathy",
        "appears_in_narrative",
        "alleged_spin_off",
    ]):
        return "narrative_inheritance"
    if status == "disputed" or any(term in text for term in [
        "contested",
        "reported_allegation",
        "allegation",
        "unclear",
        "boundary",
        "house_inquiry",
        "house question",
        "question/inquiry",
        "inquiry lane",
        "further investigation",
        "promis",
        "inslaw",
        "finders",
        "jonestown",
    ]):
        return "contested_overlap"
    if status == "unverified" or "lead" in text:
        return "hypothesis_requires_more_sources"
    if record_kind == "event_link":
        return "personnel_bridge"
    if any(term in text for term in [
        "co_founder",
        "founder",
        "member",
        "participant",
        "researcher",
        "affiliated",
        "classmate",
        "father",
        "teacher",
        "headmaster",
        "sentenced",
        "worked",
        "guided",
        "approved_project",
    ]):
        return "personnel_bridge"
    return "personnel_bridge"


def audit_bridge_class(capacity: str) -> str:
    lowered = capacity.lower()
    if "lead" in lowered:
        return "lead_context_bridge"
    if "drug-rehabilitation" in lowered or "drug rehabilitation" in lowered:
        return "category_only_drug_rehab_bridge"
    if "behavior" in lowered or "authority" in lowered or "category" in lowered:
        return "category_bridge"
    if "software" in lowered or "promis" in lowered or "institutional" in lowered:
        return "institutional_software_bridge"
    if "direct" in lowered:
        return "direct_org_person_context"
    return slugify(capacity or "audit_bridge", 32)


def read_cluster_metadata(clusters_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    cluster_rows: dict[str, dict[str, Any]] = {}
    cluster_labels: dict[str, str] = {}
    summary_path = clusters_dir / "cluster_summary.csv"
    if summary_path.exists():
        for row in read_csv_dicts(summary_path):
            cluster_id = str(row.get("cluster_id") or "")
            if cluster_id:
                cluster_rows[cluster_id] = row
    return cluster_rows, cluster_labels


def parse_cluster_bridge_audit(cdir: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    notes = sorted((cdir / "notes").glob("cluster_bridge_audit*.md"))
    if not notes:
        return {}, []
    text = notes[-1].read_text(encoding="utf-8")
    cluster_labels: dict[str, str] = {}
    bridge_rows: list[dict[str, Any]] = []
    section = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            section = line
            continue
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if section == "## Cluster labels" and len(cells) >= 3 and re.match(r"^C\d+$", cells[0]):
            cluster_labels[cells[0]] = cells[1]
        if section == "## Bridge backbone" and len(cells) >= 6 and "->" in cells[0]:
            src, dst = [part.strip() for part in cells[0].split("->", 1)]
            source_ids = re.findall(r"`([^`]+)`", cells[4])
            bridge_rows.append({
                "bridge_id": f"B_{src}_{dst}_{slugify(cells[1], 32).upper()}",
                "src_cluster": src,
                "dst_cluster": dst,
                "capacity": cells[1],
                "audit_path": cells[2],
                "audit_status": cells[3],
                "audit_source_ids": source_ids,
                "boundary_text": cells[5],
            })
    return cluster_labels, bridge_rows


def analysis_graph(
    entities: list[dict[str, Any]],
    events: list[dict[str, Any]],
    event_links: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    allowed_statuses: set[str] | None = None,
) -> tuple[dict[str, list[tuple[str, dict[str, Any]]]], dict[str, dict[str, Any]]]:
    allowed = allowed_statuses or {"verified", "corroborated", "single_source"}
    graph: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    meta: dict[str, dict[str, Any]] = {}
    entity_by_id = {str(entity.get("entity_id")): entity for entity in entities}
    event_by_id = {str(event.get("event_id")): event for event in events}

    def add_node(node_id: str, label: str, layer: str) -> None:
        meta.setdefault(node_id, {"id": node_id, "label": label, "layer": layer})

    def add_edge(left: str, right: str, record: dict[str, Any], record_id: str, edge_type: str) -> None:
        status = str(record.get("status", ""))
        if status not in allowed:
            return
        source_ids = parse_cell_list(record.get("source_ids"))
        claim_ids = parse_cell_list(record.get("claim_ids"))
        edge = {
            "record_id": record_id,
            "edge_type": edge_type,
            "relation_type": record.get("relation_type", edge_type),
            "relationship_class": relationship_class(record, edge_type),
            "status": status,
            "source_ids": source_ids,
            "claim_ids": claim_ids,
            "confidence": record.get("confidence", ""),
            "notes": record.get("notes", ""),
            "public_export": record.get("public_export", True),
        }
        graph.setdefault(left, []).append((right, edge))
        graph.setdefault(right, []).append((left, edge))

    for entity in entities:
        add_node(
            str(entity.get("entity_id")),
            entity_display(entity),
            str(entity.get("entity_type", "entity")),
        )
    for event in events:
        event_id = "EVENT:" + str(event.get("event_id"))
        add_node(event_id, str(event.get("title") or event.get("event_id")), "event")
    for rel in relationships:
        src = str(rel.get("src_entity_id", ""))
        dst = str(rel.get("dst_entity_id", ""))
        if src in entity_by_id and dst in entity_by_id:
            add_edge(src, dst, rel, str(rel.get("rel_id", "")), "relationship")
    for link in event_links:
        entity_id = str(link.get("entity_id", ""))
        event_id = "EVENT:" + str(link.get("event_id", ""))
        if entity_id in entity_by_id and event_id in meta:
            add_edge(entity_id, event_id, link, str(link.get("event_link_id", "")), "event_link")
    return graph, meta


def shortest_analysis_path(
    graph: dict[str, list[tuple[str, dict[str, Any]]]],
    starts: list[str],
    goals: list[str],
) -> list[tuple[str, str, dict[str, Any]]] | None:
    goal_set = set(goals)
    queue = list(starts)
    previous: dict[str, tuple[str | None, dict[str, Any] | None]] = {node: (None, None) for node in starts}
    for node in queue:
        if node in goal_set:
            return []
    idx = 0
    while idx < len(queue):
        node = queue[idx]
        idx += 1
        for nxt, edge in graph.get(node, []):
            if nxt in previous:
                continue
            previous[nxt] = (node, edge)
            if nxt in goal_set:
                steps: list[tuple[str, str, dict[str, Any]]] = []
                cur = nxt
                while previous[cur][0] is not None:
                    prev, prev_edge = previous[cur]
                    assert prev is not None and prev_edge is not None
                    steps.append((prev, cur, prev_edge))
                    cur = prev
                return list(reversed(steps))
            queue.append(nxt)
    return None


def classify_bridge_path(steps: list[tuple[str, str, dict[str, Any]]], meta: dict[str, dict[str, Any]]) -> str:
    labels = " ".join(meta.get(node, {}).get("label", node) for step in steps for node in step[:2]).lower()
    notes = " ".join(str(step[2].get("notes", "")) for step in steps).lower()
    classes = {relationship_class(step[2], str(step[2].get("edge_type", "relationship"))) for step in steps}
    if "hypothesis_requires_more_sources" in classes:
        return "hypothesis_requires_more_sources_bridge"
    if "contested_overlap" in classes:
        return "contested_overlap_bridge"
    if "narrative_inheritance" in classes:
        return "narrative_inheritance_bridge"
    if "method_diffusion" in classes:
        return "method_diffusion_bridge"
    if "documented_successor" in classes:
        return "documented_successor_bridge"
    if any(term in labels for term in ["drug rehabilitation program context", "behavioral-control and authority context"]):
        return "category_bridge"
    if any(term in labels for term in ["promis", "inslaw", "central intelligence agency", "cia"]):
        return "institutional_software_bridge"
    if "lead" in notes or "alleged" in notes:
        return "lead_context_bridge"
    if len(steps) <= 2:
        return "direct_or_near_direct"
    return "indirect_context_bridge"


PALETTE = {
    "verified": "#1f7a4f",
    "corroborated": "#2b6cb0",
    "single_source": "#b7791f",
    "unverified": "#a63a3a",
    "disputed": "#7f1d1d",
    "internal_only": "#6b7280",
    "lead_or_disputed": "#a63a3a",
    "source_note_required": "#b7791f",
    "public_ready": "#1f7a4f",
    "usable_with_context": "#2b6cb0",
    "needs_privacy_review": "#7c3aed",
    "A": "#1f7a4f",
    "B": "#2b6cb0",
    "C": "#b7791f",
    "D": "#a63a3a",
    "X": "#2f3742",
}

CHART_COLORS = ["#2b6cb0", "#1f7a4f", "#b7791f", "#7c3aed", "#a63a3a", "#0f766e", "#4b5563", "#c2410c"]


def color_for(value: Any, fallback_index: int = 0) -> str:
    key = str(value or "")
    return PALETTE.get(key, CHART_COLORS[fallback_index % len(CHART_COLORS)])


def short_label(value: Any, max_len: int = 26) -> str:
    text = str(value or "")
    return text if len(text) <= max_len else text[: max_len - 1] + "..."


def svg_no_data() -> str:
    return (
        '<div class="chart-shell">'
        '<svg class="chart-svg" viewBox="0 0 900 220" role="img" aria-label="No chart data">'
        '<rect x="0" y="0" width="900" height="220" rx="8" class="chart-bg"/>'
        '<text x="450" y="112" class="axis-label" text-anchor="middle">No chart data</text>'
        "</svg></div>"
    )


def html_title(value: Any) -> str:
    return f"<title>{html.escape(flatten(value))}</title>"


def chart_with_preview(chart_html: str, preview_html: str) -> str:
    return (
        f"{chart_html}"
        '<details class="data-preview"><summary>Data preview</summary>'
        f"{preview_html}"
        "</details>"
    )


def parse_year(value: Any) -> int | None:
    match = re.match(r"^(\d{4})", str(value or ""))
    if match:
        return int(match.group(1))
    return None


def render_sankey_svg(nodes: list[dict[str, Any]], links: list[dict[str, Any]]) -> str:
    if not nodes or not links:
        return svg_no_data()
    node_by_id = {str(row.get("cluster_id")): row for row in nodes}
    stage: dict[str, int] = {cluster_id: 0 for cluster_id in node_by_id}
    for _ in range(max(1, len(links))):
        changed = False
        for link in links:
            src = str(link.get("src_cluster", ""))
            dst = str(link.get("dst_cluster", ""))
            if src in stage and dst in stage and stage[dst] < stage[src] + 1:
                stage[dst] = stage[src] + 1
                changed = True
        if not changed:
            break
    stages: dict[int, list[str]] = {}
    for cluster_id, idx in stage.items():
        stages.setdefault(idx, []).append(cluster_id)
    width, height = 1120, 420
    max_stage = max(stages) if stages else 1
    positions: dict[str, tuple[float, float]] = {}
    for idx, cluster_ids in stages.items():
        ordered = sorted(cluster_ids)
        x = 80 + (width - 200) * (idx / max(1, max_stage))
        step = (height - 120) / max(1, len(ordered))
        for pos, cluster_id in enumerate(ordered):
            y = 70 + step * pos + step / 2
            positions[cluster_id] = (x, y)
    paths = []
    for link in links:
        src = str(link.get("src_cluster", ""))
        dst = str(link.get("dst_cluster", ""))
        if src not in positions or dst not in positions:
            continue
        sx, sy = positions[src]
        dx, dy = positions[dst]
        color = color_for(link.get("public_readiness") or link.get("bridge_class"))
        stroke_width = 10 if link.get("public_readiness") != "lead_or_disputed" else 6
        dash = " stroke-dasharray=\"7 5\"" if "category" in str(link.get("bridge_class", "")) or "lead" in str(link.get("bridge_class", "")) else ""
        paths.append(
            f'<path d="M {sx + 128:.1f} {sy:.1f} C {(sx + dx) / 2:.1f} {sy:.1f}, {(sx + dx) / 2:.1f} {dy:.1f}, {dx:.1f} {dy:.1f}" '
            f'fill="none" stroke="{color}" stroke-opacity="0.42" stroke-width="{stroke_width}"{dash}>{html_title(link.get("path"))}</path>'
        )
    rects = []
    for cluster_id, (x, y) in positions.items():
        node = node_by_id.get(cluster_id, {})
        label = f"{cluster_id}: {short_label(node.get('cluster_label'), 22)}"
        members = short_label(node.get("member_names"), 38)
        rects.append(
            f'<g><rect x="{x:.1f}" y="{y - 24:.1f}" width="142" height="48" rx="7" class="node-box"/>'
            f'<text x="{x + 10:.1f}" y="{y - 5:.1f}" class="node-label">{html.escape(label)}</text>'
            f'<text x="{x + 10:.1f}" y="{y + 13:.1f}" class="mini-label">{html.escape(members)}</text></g>'
        )
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Cluster bridge Sankey">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'{"".join(paths)}{"".join(rects)}'
        '<text x="20" y="30" class="axis-label">Audited inter-cluster bridge flow; dashed links are category/lead/context bridges.</text>'
        "</svg></div>"
    )


def render_layered_graph_svg(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    if not nodes:
        return svg_no_data()
    degree: dict[str, int] = {}
    for edge in edges:
        degree[str(edge.get("src_id", ""))] = degree.get(str(edge.get("src_id", "")), 0) + 1
        degree[str(edge.get("dst_id", ""))] = degree.get(str(edge.get("dst_id", "")), 0) + 1
    selected = sorted(nodes, key=lambda row: (-degree.get(str(row.get("node_id")), 0), str(row.get("label", ""))))[:64]
    selected_ids = {str(row.get("node_id")) for row in selected}
    layers = sorted({str(row.get("layer") or "entity") for row in selected})
    width, height = 1120, 620
    positions: dict[str, tuple[float, float]] = {}
    for layer_idx, layer in enumerate(layers):
        layer_nodes = [row for row in selected if str(row.get("layer") or "entity") == layer]
        x = 80 + layer_idx * ((width - 160) / max(1, len(layers) - 1))
        step = (height - 140) / max(1, len(layer_nodes))
        for idx, row in enumerate(layer_nodes):
            y = 88 + idx * step + step / 2
            positions[str(row.get("node_id"))] = (x, y)
    edge_lines = []
    for edge in edges:
        src = str(edge.get("src_id", ""))
        dst = str(edge.get("dst_id", ""))
        if src not in selected_ids or dst not in selected_ids or src not in positions or dst not in positions:
            continue
        sx, sy = positions[src]
        dx, dy = positions[dst]
        edge_lines.append(
            f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{dx:.1f}" y2="{dy:.1f}" '
            f'stroke="{color_for(edge.get("status"))}" stroke-width="{max(1.0, parse_float(edge.get("source_count"), 1.0)):.1f}" stroke-opacity="0.22">'
            f'{html_title(edge.get("relation_type"))}</line>'
        )
    node_marks = []
    for row in selected:
        node_id = str(row.get("node_id"))
        x, y = positions[node_id]
        radius = 5 + min(11, degree.get(node_id, 0))
        node_marks.append(
            f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{color_for(row.get("status"), len(node_marks))}" stroke="#fff" stroke-width="1.5"/>'
            f'<text x="{x + 14:.1f}" y="{y + 4:.1f}" class="mini-label">{html.escape(short_label(row.get("label"), 24))}</text></g>'
        )
    layer_labels = "".join(
        f'<text x="{80 + idx * ((width - 160) / max(1, len(layers) - 1)):.1f}" y="46" class="axis-label" text-anchor="middle">{html.escape(layer)}</text>'
        for idx, layer in enumerate(layers)
    )
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Layered knowledge graph">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'{layer_labels}{"".join(edge_lines)}{"".join(node_marks)}'
        "</svg></div>"
    )


def render_layered_graph_v2_svg(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    if not nodes:
        return svg_no_data()
    degree = {str(row.get("node_id", "")): int(parse_float(row.get("degree"), 0.0)) for row in nodes}
    selected = sorted(
        nodes,
        key=lambda row: (
            int(parse_float(row.get("layer_order"), 99)),
            -degree.get(str(row.get("node_id", "")), 0),
            -parse_float(row.get("source_count"), 0.0),
            str(row.get("label", "")),
        ),
    )[:120]
    selected_ids = {str(row.get("node_id")) for row in selected}
    layers = sorted(
        {str(row.get("layer") or "entity") for row in selected},
        key=lambda layer: min(int(parse_float(row.get("layer_order"), 99)) for row in selected if str(row.get("layer") or "entity") == layer),
    )
    width, height = 1440, 860
    left, right, top, bottom = 74, 72, 92, 82
    lane_width = width - left - right
    lane_height = height - top - bottom
    positions: dict[str, tuple[float, float]] = {}
    for layer_idx, layer in enumerate(layers):
        layer_nodes = [row for row in selected if str(row.get("layer") or "entity") == layer]
        x = left + layer_idx * (lane_width / max(1, len(layers) - 1))
        step = lane_height / max(1, len(layer_nodes))
        for idx, row in enumerate(layer_nodes):
            y = top + idx * step + step / 2
            positions[str(row.get("node_id"))] = (x, y)

    layer_guides = []
    for idx, layer in enumerate(layers):
        x = left + idx * (lane_width / max(1, len(layers) - 1))
        layer_guides.append(
            f'<line x1="{x:.1f}" y1="{top - 26}" x2="{x:.1f}" y2="{height - bottom + 22}" stroke="#e3ebf2" stroke-width="1"/>'
            f'<text x="{x:.1f}" y="50" class="axis-label" text-anchor="middle">{html.escape(layer)}</text>'
        )

    edge_marks = []
    for edge in sorted(edges, key=lambda row: parse_float(row.get("evidence_weight"), 0.0)):
        src = str(edge.get("src_id", ""))
        dst = str(edge.get("dst_id", ""))
        if src not in selected_ids or dst not in selected_ids or src not in positions or dst not in positions:
            continue
        sx, sy = positions[src]
        dx, dy = positions[dst]
        mid = abs(dx - sx) * 0.42
        c1 = sx + mid
        c2 = dx - mid
        weight = max(1.0, min(5.5, 1.0 + parse_float(edge.get("evidence_weight"), 0.0) * 3.4))
        readiness = str(edge.get("readiness", ""))
        dash = ' stroke-dasharray="7 7"' if str(edge.get("caveat", "")) else ""
        title = (
            f"{edge.get('src_label')} -> {edge.get('dst_label')} | {edge.get('relation_type')} | "
            f"{edge.get('relationship_class')} | {edge.get('status')} | readiness={readiness} | "
            f"sources={edge.get('source_count')} | caveat={edge.get('caveat')}"
        )
        edge_marks.append(
            f'<path d="M {sx:.1f} {sy:.1f} C {c1:.1f} {sy:.1f}, {c2:.1f} {dy:.1f}, {dx:.1f} {dy:.1f}" '
            f'fill="none" stroke="{color_for(readiness or edge.get("status"))}" stroke-width="{weight:.2f}" '
            f'stroke-opacity="0.22"{dash}>{html_title(title)}</path>'
        )

    node_marks = []
    for row in selected:
        node_id = str(row.get("node_id"))
        x, y = positions[node_id]
        radius = 5.5 + min(13.0, math.sqrt(max(0, degree.get(node_id, 0))) * 3.1)
        readiness = str(row.get("readiness") or row.get("evidence_state") or row.get("status"))
        title = (
            f"{row.get('label')} | layer={row.get('layer')} | cluster={row.get('cluster_id')} | "
            f"status={row.get('status')} | readiness={row.get('readiness')} | evidence={row.get('evidence_state')} | "
            f"sources={row.get('source_count')} | degree={row.get('degree')} | caveat={row.get('caveat')}"
        )
        label = html.escape(short_label(row.get("label"), 22))
        node_marks.append(
            f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color_for(readiness)}" '
            f'fill-opacity="0.9" stroke="#fff" stroke-width="1.6">{html_title(title)}</circle>'
            f'<text x="{x + radius + 7:.1f}" y="{y + 4:.1f}" class="mini-label">{label}</text></g>'
        )

    legend = [
        ("public_ready", "public ready"),
        ("usable_with_context", "context"),
        ("source_note_required", "single source"),
        ("lead_or_disputed", "lead/disputed"),
        ("internal_only", "internal"),
    ]
    legend_marks = []
    for idx, (key, label) in enumerate(legend):
        x = left + idx * 150
        y = height - 34
        legend_marks.append(
            f'<g><circle cx="{x}" cy="{y}" r="7" fill="{color_for(key)}"/>'
            f'<text x="{x + 14}" y="{y + 4}" class="mini-label">{html.escape(label)}</text></g>'
        )

    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Layered knowledge graph v2">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'<text x="{left}" y="24" class="axis-label">Layered evidence navigation graph: node color reflects readiness/evidence state; dashed edges require caveats.</text>'
        f'{"".join(layer_guides)}{"".join(edge_marks)}{"".join(node_marks)}{"".join(legend_marks)}'
        "</svg></div>"
    )


def render_heatmap_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    row_keys = sorted({str(row.get("claim_type") or "unknown") for row in rows})
    col_keys = sorted({str(row.get("status") or "unknown") for row in rows}, key=lambda status: -STATUS_SCORE.get(status, 0))
    cell = 48
    left, top = 210, 58
    width = left + cell * len(col_keys) + 40
    height = top + cell * len(row_keys) + 50
    by_key = {(str(row.get("claim_type") or "unknown"), str(row.get("status") or "unknown")): row for row in rows}
    cells = []
    for r_idx, row_key in enumerate(row_keys):
        y = top + r_idx * cell
        cells.append(f'<text x="{left - 12}" y="{y + 29}" class="mini-label" text-anchor="end">{html.escape(short_label(row_key, 28))}</text>')
        for c_idx, col_key in enumerate(col_keys):
            x = left + c_idx * cell
            row = by_key.get((row_key, col_key), {})
            count = int(row.get("claim_count") or 0)
            confidence = parse_float(row.get("avg_confidence"), 0.0)
            opacity = 0.18 + 0.72 * confidence
            fill = color_for(col_key, c_idx)
            cells.append(
                f'<g><rect x="{x}" y="{y}" width="{cell - 4}" height="{cell - 4}" rx="5" fill="{fill}" fill-opacity="{opacity:.2f}" stroke="#fff"/>'
                f'<text x="{x + cell / 2 - 2:.1f}" y="{y + 28}" class="heat-label" text-anchor="middle">{count if count else ""}</text>'
                f'{html_title(f"{row_key} / {col_key}: {count} claims, avg confidence {confidence}")}</g>'
            )
    headers = "".join(
        f'<text x="{left + idx * cell + cell / 2 - 2:.1f}" y="42" class="mini-label" text-anchor="middle" transform="rotate(-35 {left + idx * cell + cell / 2 - 2:.1f} 42)">{html.escape(short_label(col, 16))}</text>'
        for idx, col in enumerate(col_keys)
    )
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Evidence confidence heatmap">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>{headers}{"".join(cells)}'
        "</svg></div>"
    )


def render_fragility_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    width, height = 900, 360
    left, right, top, bottom = 68, 28, 40, 54
    max_load = max((parse_float(row.get("load_bearing_score"), 0.0) for row in rows), default=1.0) or 1.0
    points = []
    for idx, row in enumerate(rows[:42]):
        load = parse_float(row.get("load_bearing_score"), 0.0)
        frag = parse_float(row.get("fragility_score"), 0.0)
        x = left + (width - left - right) * load / max_load
        y = top + (height - top - bottom) * (1 - frag)
        points.append(
            f'<g><line x1="{x:.1f}" y1="{height - bottom}" x2="{x:.1f}" y2="{y:.1f}" stroke="#c8d4df" stroke-width="1"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{color_for(row.get("fragility_tier"), idx)}" fill-opacity="0.86">'
            f'{html_title(row.get("record_id"))}</circle></g>'
        )
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Bridge fragility scatterplot">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" class="axis"/>'
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" class="axis"/>'
        f'<text x="{width / 2}" y="{height - 14}" class="axis-label" text-anchor="middle">load-bearing bridge count</text>'
        f'<text x="18" y="{height / 2}" class="axis-label" text-anchor="middle" transform="rotate(-90 18 {height / 2})">fragility score</text>'
        f'{"".join(points)}</svg></div>'
    )


def render_claim_matrix_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    claim_order = sorted({str(row.get("claim_id")) for row in rows})[:28]
    source_counts: dict[str, int] = {}
    for row in rows:
        sid = str(row.get("source_id"))
        source_counts[sid] = source_counts.get(sid, 0) + 1
    source_order = [sid for sid, _ in sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))[:28]]
    cell = 20
    left, top = 190, 118
    width = left + cell * len(source_order) + 38
    height = top + cell * len(claim_order) + 45
    cells = []
    grade_by_cell = {(str(row.get("claim_id")), str(row.get("source_id"))): str(row.get("source_grade") or "") for row in rows}
    for r_idx, claim_id in enumerate(claim_order):
        y = top + r_idx * cell
        cells.append(f'<text x="{left - 10}" y="{y + 14}" class="mini-label" text-anchor="end">{html.escape(short_label(claim_id, 26))}</text>')
        for c_idx, source_id in enumerate(source_order):
            x = left + c_idx * cell
            grade = grade_by_cell.get((claim_id, source_id))
            fill = color_for(grade, c_idx) if grade else "#edf2f7"
            opacity = "0.9" if grade else "0.55"
            title = f"{claim_id} / {source_id} / {grade or 'no link'}"
            cells.append(f'<rect x="{x}" y="{y}" width="{cell - 3}" height="{cell - 3}" rx="2" fill="{fill}" fill-opacity="{opacity}">{html_title(title)}</rect>')
    headers = "".join(
        f'<text x="{left + idx * cell + 8}" y="{top - 8}" class="mini-label" text-anchor="start" transform="rotate(-55 {left + idx * cell + 8} {top - 8})">{html.escape(short_label(source_id, 12))}</text>'
        for idx, source_id in enumerate(source_order)
    )
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Claim source matrix">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>{headers}{"".join(cells)}'
        "</svg></div>"
    )


def pie_path(cx: float, cy: float, radius: float, start: float, end: float) -> str:
    start_x = cx + radius * math.cos(start)
    start_y = cy + radius * math.sin(start)
    end_x = cx + radius * math.cos(end)
    end_y = cy + radius * math.sin(end)
    large = 1 if end - start > math.pi else 0
    return f"M {cx} {cy} L {start_x:.2f} {start_y:.2f} A {radius} {radius} 0 {large} 1 {end_x:.2f} {end_y:.2f} Z"


def render_source_quality_svg(grade_rows: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> str:
    if not grade_rows:
        return svg_no_data()
    width, height = 900, 360
    total = sum(int(row.get("count") or 0) for row in grade_rows) or 1
    start = -math.pi / 2
    slices = []
    legend = []
    for idx, row in enumerate(grade_rows):
        count = int(row.get("count") or 0)
        end = start + 2 * math.pi * count / total
        grade = str(row.get("grade") or "unknown")
        color = color_for(grade, idx)
        slices.append(f'<path d="{pie_path(190, 178, 116, start, end)}" fill="{color}" fill-opacity="0.82">{html_title(f"{grade}: {count}")}</path>')
        legend.append(f'<g><rect x="352" y="{84 + idx * 28}" width="16" height="16" rx="3" fill="{color}"/><text x="376" y="{97 + idx * 28}" class="node-label">Grade {html.escape(grade)}: {count}</text></g>')
        start = end
    footprints = []
    metric_keys = ["claim_count", "event_count", "event_link_count", "relationship_count", "person_count"]
    totals = {key: sum(int(row.get(key) or 0) for row in source_rows) for key in metric_keys}
    max_total = max(totals.values(), default=1) or 1
    for idx, key in enumerate(metric_keys):
        value = totals[key]
        x = 540 + idx * 62
        bar_height = 170 * value / max_total
        footprints.append(
            f'<g><rect x="{x}" y="{260 - bar_height:.1f}" width="34" height="{bar_height:.1f}" rx="4" fill="{CHART_COLORS[idx]}" fill-opacity="0.8"/>'
            f'<text x="{x + 17}" y="282" class="mini-label" text-anchor="middle" transform="rotate(-35 {x + 17} 282)">{html.escape(key.replace("_count", ""))}</text>'
            f'<text x="{x + 17}" y="{252 - bar_height:.1f}" class="heat-label" text-anchor="middle">{value}</text></g>'
        )
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Source quality dashboard">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'{"".join(slices)}<circle cx="190" cy="178" r="62" fill="#fff"/>'
        f'<text x="190" y="174" class="metric" text-anchor="middle">{total}</text><text x="190" y="196" class="mini-label" text-anchor="middle">sources</text>'
        f'{"".join(legend)}{"".join(footprints)}'
        '<text x="540" y="58" class="axis-label">Source coverage footprint</text>'
        "</svg></div>"
    )


def render_path_atlas_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    display = rows[:22]
    max_hops = max((int(row.get("hops") or 0) for row in display), default=1)
    width, height = 1080, 80 + 30 * len(display)
    left, right = 180, 42
    lane_width = width - left - right
    parts = []
    for hop in range(max_hops + 1):
        x = left + lane_width * hop / max(1, max_hops)
        parts.append(f'<line x1="{x:.1f}" y1="42" x2="{x:.1f}" y2="{height - 28}" stroke="#e1e8ef" stroke-width="1"/>')
        parts.append(f'<text x="{x:.1f}" y="30" class="mini-label" text-anchor="middle">{hop}</text>')
    for idx, row in enumerate(display):
        y = 62 + idx * 30
        hops = int(row.get("hops") or 0)
        end_x = left + lane_width * hops / max(1, max_hops)
        color = color_for("lead_or_disputed" if str(row.get("over_six_hops")) == "True" else row.get("weakest_status"), idx)
        parts.append(f'<text x="{left - 12}" y="{y + 4}" class="mini-label" text-anchor="end">{html.escape(short_label(row.get("target_person"), 24))}</text>')
        parts.append(f'<line x1="{left}" y1="{y}" x2="{end_x:.1f}" y2="{y}" stroke="{color}" stroke-width="4" stroke-opacity="0.65">{html_title(row.get("path"))}</line>')
        for hop in range(hops + 1):
            x = left + lane_width * hop / max(1, max_hops)
            parts.append(f'<circle cx="{x:.1f}" cy="{y}" r="4" fill="{color}"/>')
        if str(row.get("over_six_hops")) == "True":
            parts.append(f'<text x="{end_x + 9:.1f}" y="{y + 4}" class="warn-label">&gt;6</text>')
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="6DOF path atlas">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'<text x="{left + lane_width / 2:.1f}" y="{height - 8}" class="axis-label" text-anchor="middle">hops from anchor</text>'
        f'{"".join(parts)}</svg></div>'
    )


def render_boundary_overlay_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    record_types = sorted({str(row.get("record_type") or "record") for row in rows})
    statuses = sorted({str(row.get("status") or "unknown") for row in rows})
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row.get("record_type") or "record"), str(row.get("status") or "unknown"))
        counts[key] = counts.get(key, 0) + 1
    width, height = 920, 120 + 70 * len(record_types)
    left, top = 150, 62
    x_step = (width - left - 54) / max(1, len(statuses) - 1)
    y_step = 70
    max_count = max(counts.values(), default=1)
    bubbles = []
    for r_idx, record_type in enumerate(record_types):
        y = top + r_idx * y_step
        bubbles.append(f'<text x="{left - 14}" y="{y + 5}" class="node-label" text-anchor="end">{html.escape(record_type)}</text>')
        for s_idx, status in enumerate(statuses):
            count = counts.get((record_type, status), 0)
            if not count:
                continue
            x = left + s_idx * x_step
            radius = 7 + 22 * math.sqrt(count / max_count)
            bubbles.append(f'<circle cx="{x:.1f}" cy="{y}" r="{radius:.1f}" fill="{color_for(status, s_idx)}" fill-opacity="0.72">{html_title(f"{record_type} / {status}: {count}")}</circle><text x="{x:.1f}" y="{y + 4}" class="heat-label" text-anchor="middle">{count}</text>')
    headers = "".join(f'<text x="{left + idx * x_step:.1f}" y="36" class="mini-label" text-anchor="middle">{html.escape(short_label(status, 16))}</text>' for idx, status in enumerate(statuses))
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Contradiction and boundary overlay">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>{headers}{"".join(bubbles)}</svg></div>'
    )


def render_swimlanes_svg(rows: list[dict[str, Any]]) -> str:
    dated = [row for row in rows if parse_year(row.get("start_date")) is not None]
    if not dated:
        return svg_no_data()
    years = [parse_year(row.get("start_date")) for row in dated]
    min_year = min(year for year in years if year is not None)
    max_year = max(year for year in years if year is not None)
    lanes = sorted({str(row.get("cluster_id") or "unclustered") for row in dated})[:12]
    width, height = 1120, 96 + 54 * len(lanes)
    left, right, top = 156, 44, 68
    lane_width = width - left - right
    parts = []
    for idx, lane in enumerate(lanes):
        y = top + idx * 54
        parts.append(f'<line x1="{left}" y1="{y}" x2="{width - right}" y2="{y}" stroke="#d9e1e8" stroke-width="1"/>')
        parts.append(f'<text x="{left - 14}" y="{y + 4}" class="node-label" text-anchor="end">{html.escape(lane)}</text>')
    ticks = 6
    for tick in range(ticks + 1):
        year = min_year + (max_year - min_year) * tick / max(1, ticks)
        x = left + lane_width * tick / max(1, ticks)
        parts.append(f'<line x1="{x:.1f}" y1="46" x2="{x:.1f}" y2="{height - 30}" stroke="#edf2f7" stroke-width="1"/>')
        parts.append(f'<text x="{x:.1f}" y="34" class="mini-label" text-anchor="middle">{int(year)}</text>')
    for row in dated:
        lane = str(row.get("cluster_id") or "unclustered")
        if lane not in lanes:
            continue
        year = parse_year(row.get("start_date"))
        assert year is not None
        x = left + lane_width * (year - min_year) / max(1, max_year - min_year)
        y = top + lanes.index(lane) * 54
        color = color_for(row.get("event_link_status") or row.get("status"))
        parts.append(f'<circle cx="{x:.1f}" cy="{y}" r="5.5" fill="{color}" fill-opacity="0.82">{html_title(row.get("event_title"))}</circle>')
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Temporal cluster swimlanes">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>{"".join(parts)}</svg></div>'
    )


def render_treemap_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    display = rows[:36]
    family_totals: dict[str, float] = {}
    for row in display:
        family = str(row.get("relation_family") or "other")
        family_totals[family] = family_totals.get(family, 0.0) + parse_float(row.get("weighted_count"), 0.0)
    width, height = 1040, 430
    x, y, chart_w, chart_h = 24, 38, width - 48, height - 62
    total = sum(family_totals.values()) or 1.0
    rects = []
    x_cursor = x
    for f_idx, (family, family_value) in enumerate(sorted(family_totals.items(), key=lambda item: -item[1])):
        family_w = chart_w * family_value / total
        family_rows = [row for row in display if str(row.get("relation_family") or "other") == family]
        child_total = sum(parse_float(row.get("weighted_count"), 0.0) for row in family_rows) or 1.0
        y_cursor = y
        rects.append(f'<text x="{x_cursor + 5:.1f}" y="{y_cursor - 8:.1f}" class="mini-label">{html.escape(short_label(family, 24))}</text>')
        for row in family_rows:
            value = parse_float(row.get("weighted_count"), 0.0)
            child_h = chart_h * value / child_total
            color = color_for(row.get("status"), f_idx)
            title = f"{row.get('relation_type')} / weight {value}"
            rects.append(
                f'<g><rect x="{x_cursor:.1f}" y="{y_cursor:.1f}" width="{max(1, family_w - 4):.1f}" height="{max(1, child_h - 3):.1f}" rx="4" fill="{color}" fill-opacity="0.74" stroke="#fff"/>'
                f'<text x="{x_cursor + 6:.1f}" y="{y_cursor + 16:.1f}" class="treemap-label">{html.escape(short_label(row.get("relation_type"), int(max(8, family_w / 8))))}</text>'
                f'{html_title(title)}</g>'
            )
            y_cursor += child_h
        x_cursor += family_w
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Relationship type treemap">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>{"".join(rects)}</svg></div>'
    )


def render_bipartite_svg(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    if not nodes or not edges:
        return svg_no_data()
    people = [row for row in nodes if row.get("node_type") == "person"]
    sources = [row for row in nodes if row.get("node_type") == "source"]
    people = sorted(people, key=lambda row: -parse_float(row.get("degree"), 0.0))[:16]
    sources = sorted(sources, key=lambda row: -parse_float(row.get("degree"), 0.0))[:20]
    people_ids = {str(row.get("entity_id")) for row in people}
    source_ids = {str(row.get("source_id")) for row in sources}
    width, height = 1080, max(520, 74 + 24 * max(len(people), len(sources)))
    left_x, right_x = 250, 820
    people_pos = {str(row.get("entity_id")): (left_x, 58 + idx * 28) for idx, row in enumerate(people)}
    source_pos = {str(row.get("source_id")): (right_x, 58 + idx * 24) for idx, row in enumerate(sources)}
    paths = []
    for edge in edges:
        pid = str(edge.get("person_id"))
        sid = str(edge.get("source_id"))
        if pid not in people_ids or sid not in source_ids:
            continue
        sx, sy = people_pos[pid]
        dx, dy = source_pos[sid]
        paths.append(f'<path d="M {sx + 8} {sy} C 455 {sy}, 610 {dy}, {dx - 8} {dy}" fill="none" stroke="{color_for(edge.get("source_grade"))}" stroke-width="1.2" stroke-opacity="0.18">{html_title(edge.get("contexts"))}</path>')
    labels = []
    for row in people:
        x0, y0 = people_pos[str(row.get("entity_id"))]
        labels.append(f'<circle cx="{x0}" cy="{y0}" r="6" fill="#2b6cb0"/><text x="{x0 - 12}" y="{y0 + 4}" class="mini-label" text-anchor="end">{html.escape(short_label(row.get("label"), 28))}</text>')
    for row in sources:
        x0, y0 = source_pos[str(row.get("source_id"))]
        labels.append(f'<circle cx="{x0}" cy="{y0}" r="5" fill="{color_for(row.get("reliability_grade"))}"/><text x="{x0 + 12}" y="{y0 + 4}" class="mini-label">{html.escape(short_label(row.get("label"), 36))}</text>')
    return (
        '<div class="chart-shell scroll-x">'
        f'<svg class="chart-svg" style="min-width:{width}px" viewBox="0 0 {width} {height}" role="img" aria-label="Person source bipartite graph">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        '<text x="250" y="30" class="axis-label" text-anchor="middle">people</text><text x="820" y="30" class="axis-label" text-anchor="middle">sources</text>'
        f'{"".join(paths)}{"".join(labels)}</svg></div>'
    )


def render_readiness_svg(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return svg_no_data()
    width, height = 760, 320
    total = sum(int(row.get("count") or 0) for row in rows) or 1
    start = -math.pi / 2
    slices = []
    legend = []
    for idx, row in enumerate(rows):
        count = int(row.get("count") or 0)
        readiness = str(row.get("readiness") or "unknown")
        end = start + 2 * math.pi * count / total
        color = color_for(readiness, idx)
        slices.append(f'<path d="{pie_path(170, 160, 108, start, end)}" fill="{color}" fill-opacity="0.84">{html_title(f"{readiness}: {count}")}</path>')
        legend.append(f'<g><rect x="330" y="{58 + idx * 29}" width="17" height="17" rx="3" fill="{color}"/><text x="356" y="{72 + idx * 29}" class="node-label">{html.escape(readiness)} ({count})</text></g>')
        start = end
    return (
        '<div class="chart-shell">'
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Public narrative readiness donut">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="8" class="chart-bg"/>'
        f'{"".join(slices)}<circle cx="170" cy="160" r="58" fill="#fff"/>'
        f'<text x="170" y="158" class="metric" text-anchor="middle">{total}</text><text x="170" y="180" class="mini-label" text-anchor="middle">records</text>'
        f'{"".join(legend)}</svg></div>'
    )


def analysis_chart_files() -> list[tuple[str, str]]:
    return [
        ("Cluster Bridge Sankey", "cluster_bridge_sankey_nodes.csv / cluster_bridge_sankey_links.csv"),
        ("Layered Knowledge Graph", "layered_knowledge_graph_nodes.csv / layered_knowledge_graph_edges.csv"),
        ("Layered Knowledge Graph v2", "layered_knowledge_graph_v2_nodes.csv / layered_knowledge_graph_v2_edges.csv / layered_knowledge_graph_v2_layers.csv"),
        ("Evidence Confidence Heatmap", "evidence_confidence_heatmap.csv / evidence_confidence_heatmap_aggregate.csv"),
        ("Bridge Fragility", "bridge_fragility.csv / bridge_fragility_segments.csv"),
        ("Claim Corroboration Matrix", "claim_corroboration_matrix.csv / claim_corroboration_edges.csv"),
        ("Source Quality Dashboard", "source_quality_dashboard.csv"),
        ("6DOF Path Atlas", "sixdof_path_atlas.csv / sixdof_path_segments.csv"),
        ("Contradiction / Boundary Overlay", "contradiction_boundary_overlay.csv"),
        ("Temporal Cluster Swimlanes", "temporal_cluster_swimlanes.csv"),
        ("Relationship-Class Treemap", "relationship_type_treemap.csv"),
        ("Person-Source Bipartite Graph", "person_source_bipartite_nodes.csv / person_source_bipartite_edges.csv"),
        ("Public Narrative Readiness", "public_narrative_readiness.csv"),
    ]


def analysis_chart_css() -> str:
    return """
<style>
:root { color-scheme: light; --ink:#182026; --muted:#5d6975; --line:#d9e1e8; --panel:#f8fafc; --accent:#2b6cb0; --good:#237a57; --warn:#b7791f; --bad:#a63a3a; --soft:#eef4fa; }
body { margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--ink); background:#fff; }
header { padding:28px 36px 18px; border-bottom:1px solid var(--line); background:var(--panel); }
main { padding:24px 36px 56px; max-width:1440px; margin:0 auto; }
h1 { margin:0 0 8px; font-size:26px; letter-spacing:0; }
h2 { margin:0 0 10px; font-size:19px; letter-spacing:0; }
h3 { margin:18px 0 8px; font-size:14px; letter-spacing:0; }
p, li { color:var(--muted); line-height:1.45; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }
.grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap:18px; align-items:stretch; }
section, .card { border:1px solid var(--line); border-radius:8px; padding:16px; background:#fff; overflow:hidden; }
.card { display:flex; flex-direction:column; min-height:160px; }
.card-link { margin-top:auto; font-weight:700; }
.wide { grid-column:1 / -1; }
.muted { color:var(--muted); font-size:13px; }
.toolbar { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:16px 0; }
.toolbar input { min-width:260px; flex:1; border:1px solid var(--line); border-radius:6px; padding:9px 10px; font:inherit; }
.toolbar button, .back-link { border:1px solid var(--line); border-radius:6px; background:#fff; color:#283542; padding:8px 10px; font:inherit; font-size:12px; cursor:pointer; }
.toolbar button:hover, .toolbar button[aria-pressed="true"] { background:var(--soft); border-color:#a9bdcf; }
.chart-layout { display:grid; grid-template-columns:minmax(0, 1fr) 320px; gap:16px; align-items:start; }
.inspector { border:1px solid var(--line); border-radius:8px; padding:14px; background:#fbfdff; position:sticky; top:16px; min-height:160px; }
.inspector-title { margin:0 0 8px; font-size:13px; font-weight:800; }
.inspector-body { color:var(--muted); font-size:13px; line-height:1.45; overflow-wrap:anywhere; }
.table-wrap { overflow:auto; border:1px solid var(--line); border-radius:6px; }
table { border-collapse:collapse; width:100%; min-width:720px; font-size:12px; }
th, td { padding:7px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { background:var(--soft); color:#24313d; position:sticky; top:0; }
code { background:#edf2f7; padding:1px 4px; border-radius:4px; }
.chart-shell { width:100%; overflow:hidden; border:1px solid var(--line); border-radius:8px; background:#fff; margin:8px 0 12px; }
.chart-shell.scroll-x { overflow-x:auto; }
.chart-svg { display:block; width:100%; height:auto; min-height:240px; }
.chart-bg { fill:#fbfdff; }
.axis { stroke:#93a4b4; stroke-width:1.2; }
.axis-label { fill:#465461; font-size:12px; font-weight:650; }
.node-label { fill:#1f2933; font-size:12px; font-weight:650; }
.mini-label { fill:#53616f; font-size:10.5px; }
.heat-label { fill:#111827; font-size:11px; font-weight:700; }
.warn-label { fill:var(--bad); font-size:11px; font-weight:800; }
.metric { fill:#16202a; font-size:27px; font-weight:800; }
.node-box { fill:#fff; stroke:#bac8d6; stroke-width:1.2; }
.treemap-label { fill:#111827; font-size:10px; font-weight:700; pointer-events:none; }
.data-preview { margin-top:14px; }
.data-preview summary { cursor:pointer; color:var(--muted); font-size:12px; font-weight:700; }
.interactive-mark { cursor:pointer; outline:none; transform-box:fill-box; transform-origin:center; transition:opacity .16s ease, filter .16s ease, stroke-width .16s ease, transform .16s ease; }
.interactive-mark:hover, .interactive-mark:focus { filter:drop-shadow(0 0 5px rgba(43,108,176,.62)); transform:scale(1.035); }
.interactive-mark.is-selected { filter:drop-shadow(0 0 9px rgba(35,122,87,.78)); opacity:1 !important; stroke:#111827 !important; stroke-width:2.4 !important; transform:scale(1.07); animation:selectedPulse 1.25s ease-in-out infinite; }
.interactive-mark.is-related { filter:drop-shadow(0 0 5px rgba(183,121,31,.45)); opacity:.82 !important; }
.interactive-mark.is-dim { opacity:.1 !important; filter:grayscale(.85); }
.inspector.is-live { border-color:#9fb8ce; box-shadow:0 8px 24px rgba(35,52,68,.08); }
.inspector.is-selected { border-color:#88b4a1; box-shadow:0 10px 28px rgba(35,122,87,.12); }
.chart-tooltip { position:fixed; z-index:20; max-width:360px; pointer-events:none; background:#17212b; color:#fff; border-radius:7px; padding:8px 10px; font-size:12px; line-height:1.35; box-shadow:0 10px 26px rgba(10,22,34,.24); opacity:0; transform:translate(10px, 12px); transition:opacity .12s ease, transform .12s ease; overflow-wrap:anywhere; }
.chart-tooltip.is-visible { opacity:.96; transform:translate(12px, 14px); }
.click-flash { position:fixed; z-index:19; width:10px; height:10px; border-radius:999px; pointer-events:none; border:2px solid rgba(43,108,176,.55); transform:translate(-50%, -50%) scale(1); animation:clickFlash .48s ease-out forwards; }
@keyframes selectedPulse { 0%, 100% { filter:drop-shadow(0 0 7px rgba(35,122,87,.55)); } 50% { filter:drop-shadow(0 0 13px rgba(35,122,87,.9)); } }
@keyframes clickFlash { to { opacity:0; transform:translate(-50%, -50%) scale(9); } }
@media (prefers-reduced-motion: reduce) { .interactive-mark, .chart-tooltip, .click-flash { transition:none; animation:none; } .interactive-mark:hover, .interactive-mark:focus, .interactive-mark.is-selected { transform:none; } }
@media (max-width: 900px) { header, main { padding-left:18px; padding-right:18px; } .chart-layout { grid-template-columns:1fr; } .inspector { position:static; } }
</style>
"""


def analysis_chart_script() -> str:
    return """
<script>
(() => {
  const inspector = document.querySelector('[data-inspector]');
  const inspectorBody = document.querySelector('[data-inspector-body]');
  const search = document.querySelector('[data-search]');
  const reset = document.querySelector('[data-reset]');
  const tooltip = document.createElement('div');
  tooltip.className = 'chart-tooltip';
  tooltip.setAttribute('role', 'status');
  document.body.appendChild(tooltip);
  const marks = Array.from(document.querySelectorAll('svg title'))
    .map((title) => title.parentElement)
    .filter(Boolean);
  const stopWords = new Set(['with', 'from', 'this', 'that', 'source', 'status', 'claim', 'event', 'path', 'record', 'count', 'context', 'bridge']);
  function detailFor(el) {
    const title = el.querySelector('title');
    return title ? title.textContent.trim() : '';
  }
  function compactDetail(text, limit = 360) {
    if (!text) return '';
    return text.length > limit ? `${text.slice(0, limit - 1)}...` : text;
  }
  function tokensFor(text) {
    return new Set(
      (text || '')
        .toLowerCase()
        .split(/[^a-z0-9_:-]+/)
        .filter((token) => token.length > 3 && !stopWords.has(token))
        .slice(0, 36)
    );
  }
  function setInspector(text, mode = 'live') {
    if (!inspectorBody) return;
    inspectorBody.textContent = text || 'Hover or click a chart mark to inspect the row, path, source, or status behind it.';
    if (inspector) {
      inspector.classList.toggle('is-live', Boolean(text) && mode === 'live');
      inspector.classList.toggle('is-selected', Boolean(text) && mode === 'selected');
    }
  }
  function eventPoint(event) {
    const target = event && event.target && event.target.getBoundingClientRect ? event.target.getBoundingClientRect() : null;
    const x = event && Number.isFinite(event.clientX) && event.clientX ? event.clientX : (target ? target.right : 24);
    const y = event && Number.isFinite(event.clientY) && event.clientY ? event.clientY : (target ? target.top : 24);
    return { x, y };
  }
  function showTooltip(text, event) {
    if (!text || !event) return;
    const point = eventPoint(event);
    tooltip.textContent = compactDetail(text, 220);
    tooltip.style.left = `${Math.max(8, Math.min(window.innerWidth - 390, point.x + 12))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(window.innerHeight - 140, point.y + 12))}px`;
    tooltip.classList.add('is-visible');
  }
  function hideTooltip() {
    tooltip.classList.remove('is-visible');
  }
  function clickFlash(event) {
    if (!event) return;
    const point = eventPoint(event);
    const flash = document.createElement('span');
    flash.className = 'click-flash';
    flash.style.left = `${point.x}px`;
    flash.style.top = `${point.y}px`;
    document.body.appendChild(flash);
    window.setTimeout(() => flash.remove(), 520);
  }
  function selectMark(el, event) {
    const selectedText = detailFor(el);
    const selectedTokens = tokensFor(selectedText);
    let relatedCount = 0;
    marks.forEach((mark) => {
      mark.classList.remove('is-selected', 'is-related', 'is-dim');
      if (mark === el) return;
      const otherTokens = tokensFor(detailFor(mark));
      const related = [...selectedTokens].some((token) => otherTokens.has(token));
      if (related) {
        mark.classList.add('is-related');
        relatedCount += 1;
      } else {
        mark.classList.add('is-dim');
      }
    });
    el.classList.add('is-selected');
    setInspector(`${selectedText}${relatedCount ? `\n\nRelated marks highlighted: ${relatedCount}` : ''}`, 'selected');
    clickFlash(event);
    showTooltip(selectedText, event);
  }
  function applyQuery(query) {
    const q = (query || '').trim().toLowerCase();
    marks.forEach((el) => {
      const text = detailFor(el).toLowerCase();
      const visible = !q || text.includes(q);
      if (!el.classList.contains('is-selected')) {
        el.classList.toggle('is-dim', !visible);
      }
    });
  }
  marks.forEach((el) => {
    el.classList.add('interactive-mark');
    el.setAttribute('tabindex', '0');
    el.setAttribute('role', 'button');
    el.setAttribute('aria-label', compactDetail(detailFor(el), 120));
    el.addEventListener('mouseenter', (event) => {
      setInspector(detailFor(el), 'live');
      showTooltip(detailFor(el), event);
    });
    el.addEventListener('mousemove', (event) => showTooltip(detailFor(el), event));
    el.addEventListener('mouseleave', hideTooltip);
    el.addEventListener('focus', (event) => {
      setInspector(detailFor(el), 'live');
      showTooltip(detailFor(el), event);
    });
    el.addEventListener('blur', hideTooltip);
    el.addEventListener('click', (event) => {
      event.stopPropagation();
      selectMark(el, event);
    });
    el.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectMark(el, event);
      }
    });
  });
  if (search) {
    search.addEventListener('input', () => applyQuery(search.value));
  }
  document.querySelectorAll('[data-query]').forEach((button) => {
    button.addEventListener('click', () => {
      const value = button.getAttribute('data-query') || '';
      if (search) search.value = value;
      document.querySelectorAll('[data-query]').forEach((btn) => btn.setAttribute('aria-pressed', 'false'));
      button.setAttribute('aria-pressed', 'true');
      applyQuery(value);
      setInspector(value ? `Filtered marks containing: ${value}` : '');
    });
  });
  if (reset) {
    reset.addEventListener('click', () => {
      if (search) search.value = '';
      hideTooltip();
      marks.forEach((mark) => mark.classList.remove('is-dim', 'is-selected', 'is-related'));
      document.querySelectorAll('[data-query]').forEach((btn) => btn.setAttribute('aria-pressed', 'false'));
      setInspector('');
    });
  }
  setInspector('');
})();
</script>
"""


def filter_terms(rows: list[dict[str, Any]], keys: list[str], limit: int = 10) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in keys:
            values = parse_cell_list(row.get(key)) or [str(row.get(key, ""))]
            for value in values:
                text = str(value).strip()
                if not text or text in seen or len(text) > 48:
                    continue
                seen.add(text)
                terms.append(text)
                if len(terms) >= limit:
                    return terms
    return terms


def build_analysis_chart_specs(chart_data: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted([
        {
            "number": 1,
            "title": "Cluster Bridge Sankey",
            "filename": "01_cluster_bridge_sankey.html",
            "description": "Audited inter-cluster bridge flow with category and lead-context links visually separated.",
            "csvs": "cluster_bridge_sankey_nodes.csv / cluster_bridge_sankey_links.csv",
            "chart_html": render_sankey_svg(chart_data["sankey_nodes"], chart_data["cluster_bridge_links"]),
            "preview_html": chart_row_table(chart_data["cluster_bridges"], ["src_cluster", "dst_cluster", "bridge_class", "hops", "path", "statuses"], 12),
            "filters": filter_terms(chart_data["cluster_bridge_links"], ["public_readiness", "bridge_class"]),
        },
        {
            "number": 2,
            "title": "Layered Knowledge Graph",
            "filename": "02_layered_knowledge_graph.html",
            "description": "Layered graph separating people, events, organizations, institutions, and context nodes.",
            "csvs": "layered_knowledge_graph_nodes.csv / layered_knowledge_graph_edges.csv",
            "chart_html": render_layered_graph_svg(chart_data["layered_nodes"], chart_data["layered_edges"]),
            "preview_html": chart_row_table(chart_data["layered_edges"], ["src_label", "dst_label", "edge_type", "relation_type", "relationship_class", "status", "source_count"], 18),
            "filters": filter_terms(chart_data["layered_edges"], ["status", "edge_type", "relation_type", "relationship_class"]),
        },
        {
            "number": 13,
            "title": "Layered Knowledge Graph v2",
            "filename": "13_layered_knowledge_graph_v2.html",
            "description": "Evidence-navigation graph with explicit layers, source grades, public-readiness state, caveats, and cluster context.",
            "csvs": "layered_knowledge_graph_v2_nodes.csv / layered_knowledge_graph_v2_edges.csv / layered_knowledge_graph_v2_layers.csv",
            "chart_html": render_layered_graph_v2_svg(chart_data["layered_v2_nodes"], chart_data["layered_v2_edges"]),
            "preview_html": chart_row_table(chart_data["layered_v2_edges"], ["src_label", "dst_label", "relationship_class", "bridge_class", "readiness", "source_count", "caveat"], 18),
            "filters": filter_terms(chart_data["layered_v2_edges"], ["readiness", "bridge_class", "relationship_class", "best_source_grade", "caveat"]),
        },
        {
            "number": 3,
            "title": "Evidence Confidence Heatmap",
            "filename": "03_evidence_confidence_heatmap.html",
            "description": "Claim-type by status heatmap, with cell intensity tied to average confidence.",
            "csvs": "evidence_confidence_heatmap.csv / evidence_confidence_heatmap_aggregate.csv",
            "chart_html": render_heatmap_svg(chart_data["heatmap_aggregate"]),
            "preview_html": chart_row_table(chart_data["claim_heatmap"], ["claim_id", "status", "confidence", "source_count", "best_source_grade", "readiness"], 18),
            "filters": filter_terms(chart_data["claim_heatmap"], ["status", "claim_type", "readiness"]),
        },
        {
            "number": 4,
            "title": "Bridge Fragility Chart",
            "filename": "04_bridge_fragility.html",
            "description": "Load-bearing bridge records plotted against fragility score.",
            "csvs": "bridge_fragility.csv / bridge_fragility_segments.csv",
            "chart_html": render_fragility_svg(chart_data["fragility"]),
            "preview_html": chart_row_table(chart_data["fragility"], ["record_id", "relationship_class", "load_bearing_score", "fragility_score", "fragility_tier", "bridge_class"], 18),
            "filters": filter_terms(chart_data["fragility"], ["fragility_tier", "bridge_class", "relationship_class", "status"]),
        },
        {
            "number": 5,
            "title": "Claim Corroboration Matrix",
            "filename": "05_claim_corroboration_matrix.html",
            "description": "Claim-source matrix colored by source grade and preserving boundary/contradiction markers.",
            "csvs": "claim_corroboration_matrix.csv / claim_corroboration_edges.csv",
            "chart_html": render_claim_matrix_svg(chart_data["claim_matrix"]),
            "preview_html": chart_row_table(chart_data["claim_matrix"], ["claim_id", "source_id", "source_grade", "source_type", "claim_status"], 20),
            "filters": filter_terms(chart_data["claim_matrix"], ["source_grade", "claim_status", "source_role"]),
        },
        {
            "number": 6,
            "title": "Source Quality Dashboard",
            "filename": "06_source_quality_dashboard.html",
            "description": "Source-grade distribution with coverage footprint across claims, events, relationships, and people.",
            "csvs": "source_quality_dashboard.csv",
            "chart_html": render_source_quality_svg(chart_data["source_grade_counts"], chart_data["source_dashboard"]),
            "preview_html": chart_row_table(chart_data["source_dashboard"], ["source_id", "reliability_grade", "claim_count", "event_count", "relationship_count", "nonpublic_record_count"], 18),
            "filters": filter_terms(chart_data["source_dashboard"], ["reliability_grade", "source_type", "publisher"]),
        },
        {
            "number": 7,
            "title": "6DOF Path Atlas",
            "filename": "07_sixdof_path_atlas.html",
            "description": "Hop-distance atlas from the anchor person, with paths over six hops explicitly marked.",
            "csvs": "sixdof_path_atlas.csv / sixdof_path_segments.csv",
            "chart_html": render_path_atlas_svg(chart_data["path_atlas"]),
            "preview_html": chart_row_table(chart_data["path_atlas"], ["target_person", "hops", "over_six_hops", "weakest_status", "relationship_classes"], 18),
            "filters": filter_terms(chart_data["path_atlas"], ["weakest_status", "bridge_classes", "relationship_classes", "over_six_hops"]),
        },
        {
            "number": 8,
            "title": "Contradiction / Boundary Overlay",
            "filename": "08_contradiction_boundary_overlay.html",
            "description": "Boundary and contradiction markers grouped by record type and status.",
            "csvs": "contradiction_boundary_overlay.csv",
            "chart_html": render_boundary_overlay_svg(chart_data["boundary_rows"]),
            "preview_html": chart_row_table(chart_data["boundary_rows"], ["record_id", "record_type", "status", "claim_type", "boundary_kind", "relationship_class", "summary"], 18),
            "filters": filter_terms(chart_data["boundary_rows"], ["record_type", "status", "boundary_kind", "relationship_class"]),
        },
        {
            "number": 9,
            "title": "Temporal Cluster Swimlanes",
            "filename": "09_temporal_cluster_swimlanes.html",
            "description": "Dated event-link markers placed on one swimlane per cluster.",
            "csvs": "temporal_cluster_swimlanes.csv",
            "chart_html": render_swimlanes_svg(chart_data["swimlanes"]),
            "preview_html": chart_row_table(chart_data["swimlanes"], ["cluster_id", "start_date", "event_id", "event_title", "relationship_class", "status", "source_count"], 18),
            "filters": filter_terms(chart_data["swimlanes"], ["cluster_id", "status", "event_link_status", "relation_type", "relationship_class"]),
        },
        {
            "number": 10,
            "title": "Relationship-Class Treemap",
            "filename": "10_relationship_type_treemap.html",
            "description": "Weighted relationship/event-link buckets grouped by lineage, diffusion, personnel, narrative, contested, and hypothesis classes.",
            "csvs": "relationship_type_treemap.csv",
            "chart_html": render_treemap_svg(chart_data["relation_type_counts"]),
            "preview_html": chart_row_table(chart_data["relation_type_counts"], ["relationship_class", "relation_family", "relation_type", "status", "weighted_count", "row_count"], 18),
            "filters": filter_terms(chart_data["relation_type_counts"], ["relationship_class", "relation_family", "status", "public_scope"]),
        },
        {
            "number": 11,
            "title": "Person-Source Bipartite Graph",
            "filename": "11_person_source_bipartite.html",
            "description": "Top person-source evidence links derived from direct, claim, relationship, event, and event-link paths.",
            "csvs": "person_source_bipartite_nodes.csv / person_source_bipartite_edges.csv",
            "chart_html": render_bipartite_svg(chart_data["person_source_nodes"], chart_data["person_source"]),
            "preview_html": chart_row_table(chart_data["person_source"], ["person_name", "source_id", "source_grade", "contexts"], 18),
            "filters": filter_terms(chart_data["person_source"], ["source_grade", "contexts", "public_evidence_state"]),
        },
        {
            "number": 12,
            "title": "Public Narrative Readiness",
            "filename": "12_public_narrative_readiness.html",
            "description": "Readiness tiers for public narration, with privacy and boundary gates preserved.",
            "csvs": "public_narrative_readiness.csv",
            "chart_html": render_readiness_svg(chart_data["readiness_counts"]),
            "preview_html": chart_row_table(chart_data["readiness_counts"], ["readiness", "count"], 12),
            "filters": filter_terms(chart_data["readiness_counts"], ["readiness"]),
        },
    ], key=lambda spec: int(spec["number"]))


def render_analysis_chart_page(case_title: str, include_private: bool, spec: dict[str, Any]) -> str:
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    filter_buttons = "".join(
        f'<button type="button" data-query="{html.escape(term)}" aria-pressed="false">{html.escape(short_label(term, 22))}</button>'
        for term in spec.get("filters", [])
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(spec["title"])} - {html.escape(case_title)}</title>
{analysis_chart_css()}
</head>
<body>
<header>
<p><a class="back-link" href="analysis_charts.html">Back to chart index</a></p>
<h1>{int(spec["number"])}. {html.escape(spec["title"])}</h1>
<p>{html.escape(spec["description"])}</p>
<p>Generated {html.escape(generated)}. Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}.</p>
<p>CSV source: <code>{html.escape(spec["csvs"])}</code></p>
</header>
<main>
<section>
<div class="toolbar">
<input type="search" data-search placeholder="Filter visible marks by label, status, source, claim, or path">
{filter_buttons}
<button type="button" data-query="" aria-pressed="false">All</button>
<button type="button" data-reset>Reset selection</button>
</div>
<div class="chart-layout">
<div>
{spec["chart_html"]}
<details class="data-preview"><summary>Data preview</summary>{spec["preview_html"]}</details>
</div>
<aside class="inspector" data-inspector>
<p class="inspector-title">Inspector</p>
<div class="inspector-body" data-inspector-body></div>
</aside>
</div>
</section>
</main>
{analysis_chart_script()}
</body>
</html>
"""


def render_analysis_dashboard(case_title: str, include_private: bool, chart_specs: list[dict[str, Any]]) -> str:
    generated = dt.datetime.now(dt.timezone.utc).isoformat()
    file_rows = "".join(
        f"<li><code>{html.escape(name)}</code> - {html.escape(path)}</li>"
        for name, path in analysis_chart_files()
    )
    cards = "".join(
        '<article class="card">'
        f'<h2>{int(spec["number"])}. {html.escape(spec["title"])}</h2>'
        f'<p>{html.escape(spec["description"])}</p>'
        f'<p class="muted"><code>{html.escape(spec["csvs"])}</code></p>'
        f'<a class="card-link" href="{html.escape(spec["filename"])}">Open interactive chart</a>'
        "</article>"
        for spec in chart_specs
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Analysis chart index - {html.escape(case_title)}</title>
{analysis_chart_css()}
</head>
<body>
<header>
<h1>Analysis charts: {html.escape(case_title)}</h1>
<p>Generated {html.escape(generated)}. Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}.</p>
<p>Open each chart in its own page for data-derived filters, hover/click inspection, keyboard focus, and collapsible table previews.</p>
</header>
<main>
<section class="wide"><h2>Files</h2><ul>{file_rows}</ul></section>
<div class="grid">{cards}</div>
</main>
</body>
</html>
"""


def export_analysis_charts(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    include_private = args.include_private
    out = Path(args.out_dir).expanduser().resolve() if args.out_dir else cdir / "exports" / "analysis_charts"
    out.mkdir(parents=True, exist_ok=True)

    case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
    case_title = str(case_meta.get("title", cdir.name))
    sources = public_rows(read_jsonl(record_path(cdir, "sources")), include_private)
    entities = public_rows(read_jsonl(record_path(cdir, "entities")), include_private)
    claims = public_rows(read_jsonl(record_path(cdir, "claims")), include_private)
    events = public_rows(read_jsonl(record_path(cdir, "events")), include_private)
    event_links = public_rows(read_jsonl(record_path(cdir, "event_links")), include_private)
    relationships = public_rows(read_jsonl(record_path(cdir, "relationships")), include_private)

    source_by_id = {str(source.get("source_id")): source for source in sources}
    claim_by_id = {str(claim.get("claim_id")): claim for claim in claims}
    entity_by_id = {str(entity.get("entity_id")): entity for entity in entities}
    people = [entity for entity in entities if entity.get("entity_type") == "person"]
    people_by_id = {str(person.get("entity_id")): person for person in people}

    clusters_dir = Path(args.clusters_dir).expanduser().resolve() if args.clusters_dir else cdir / "exports" / "clusters"
    cluster_by_person: dict[str, str] = {}
    if (clusters_dir / "people_clusters.csv").exists():
        for row in read_csv_dicts(clusters_dir / "people_clusters.csv"):
            cluster_by_person[str(row.get("entity_id"))] = str(row.get("cluster_id") or "")
    if not cluster_by_person:
        for idx, person in enumerate(sorted(people, key=entity_display), start=1):
            cluster_by_person[str(person.get("entity_id"))] = f"P{idx}"

    cluster_summary, cluster_labels = read_cluster_metadata(clusters_dir)
    audit_cluster_labels, audit_bridges = parse_cluster_bridge_audit(cdir)
    cluster_labels.update(audit_cluster_labels)

    graph, graph_meta = analysis_graph(entities, events, event_links, relationships)
    for person_id, cluster_id in cluster_by_person.items():
        if person_id in graph_meta:
            graph_meta[person_id]["cluster_id"] = cluster_id

    cluster_members: dict[str, list[str]] = {}
    for person_id, cluster_id in cluster_by_person.items():
        if person_id in people_by_id:
            cluster_members.setdefault(cluster_id, []).append(person_id)

    cluster_ids = sorted(cluster_members)
    sankey_nodes: list[dict[str, Any]] = []
    for cluster_id in cluster_ids:
        members = sorted(cluster_members[cluster_id], key=lambda person_id: entity_display(people_by_id.get(person_id)))
        summary = cluster_summary.get(cluster_id, {})
        sankey_nodes.append({
            "cluster_id": cluster_id,
            "cluster_label": cluster_labels.get(cluster_id, summary.get("label") or summary.get("members") or cluster_id),
            "member_entity_ids": members,
            "member_names": [entity_display(people_by_id.get(person_id)) for person_id in members],
            "size": len(members),
            "mean_kde_density": summary.get("mean_kde_density", ""),
            "internal_edge_weight": summary.get("internal_edge_weight", ""),
            "boundary_edge_weight": summary.get("boundary_edge_weight", ""),
            "notes": "cluster from people_clusters.csv" if cluster_summary else "fallback one-person cluster",
        })

    cluster_bridge_rows: list[dict[str, Any]] = []
    cluster_bridge_links: list[dict[str, Any]] = []
    bridge_segment_rows: list[dict[str, Any]] = []
    edge_load: dict[str, dict[str, Any]] = {}
    path_atlas: list[dict[str, Any]] = []
    path_segments: list[dict[str, Any]] = []

    def node_label(node_id: str) -> str:
        return str(graph_meta.get(node_id, {}).get("label", node_id))

    def path_label(steps: list[tuple[str, str, dict[str, Any]]]) -> str:
        if not steps:
            return ""
        return " -> ".join([node_label(steps[0][0]), *[node_label(step[1]) for step in steps]])

    audit_by_pair = {(row["src_cluster"], row["dst_cluster"]): row for row in audit_bridges}
    bridge_pairs = list(audit_by_pair) if audit_by_pair else list(combinations(cluster_ids, 2))
    for left, right in bridge_pairs:
        steps = shortest_analysis_path(graph, cluster_members[left], cluster_members[right])
        audit_row = audit_by_pair.get((left, right), {})
        if steps is None and not audit_row:
            continue
        steps = steps or []
        statuses = sorted({str(step[2].get("status", "")) for step in steps})
        relationship_classes = sorted({
            relationship_class(step[2], str(step[2].get("edge_type", "relationship")))
            for step in steps
        })
        source_ids = sorted({sid for step in steps for sid in parse_cell_list(step[2].get("source_ids"))})
        if audit_row.get("audit_source_ids"):
            source_ids = sorted(set(source_ids) | set(parse_cell_list(audit_row.get("audit_source_ids"))))
        claim_ids = sorted({cid for step in steps for cid in parse_cell_list(step[2].get("claim_ids"))})
        source_rows = [source_by_id[sid] for sid in source_ids if sid in source_by_id]
        boundary_claim_ids = sorted(
            claim_id for claim_id in claim_ids
            if claim_id in claim_by_id and boundary_signal(claim_by_id[claim_id])
        )
        bridge_class = audit_bridge_class(str(audit_row.get("capacity", ""))) if audit_row else classify_bridge_path(steps, graph_meta)
        path_text = path_label(steps) or str(audit_row.get("audit_path", ""))
        public_export = all(step[2].get("public_export", True) is not False for step in steps) if steps else bool(audit_row)
        is_lead_bridge = "lead" in " ".join([str(audit_row.get("capacity", "")), str(audit_row.get("boundary_text", "")), bridge_class]).lower()
        row = {
            "bridge_id": audit_row.get("bridge_id") or f"B_{left}_{right}_{slugify(bridge_class, 32).upper()}",
            "src_cluster": left,
            "dst_cluster": right,
            "src_cluster_label": cluster_labels.get(left, left),
            "dst_cluster_label": cluster_labels.get(right, right),
            "bridge_class": bridge_class,
            "relationship_classes": relationship_classes,
            "hops": len(steps),
            "path": path_text,
            "statuses": statuses,
            "source_ids": source_ids,
            "claim_ids": claim_ids,
            "boundary_claim_ids": boundary_claim_ids,
            "boundary_text": audit_row.get("boundary_text", ""),
            "source_grade_counts": source_grade_counts(source_rows),
            "public_readiness": "lead_or_disputed" if is_lead_bridge else readiness_label({"status": weakest_status(statuses) or "single_source", "public_export": public_export}, source_rows),
            "public_export": public_export,
            "notes": audit_row.get("capacity", ""),
        }
        cluster_bridge_rows.append(row)
        cluster_bridge_links.append(row)
        for src, dst, edge in steps:
            record_id = str(edge.get("record_id", ""))
            if not record_id:
                continue
            bridge_segment_rows.append({
                "bridge_id": row["bridge_id"],
                "segment_index": len([segment for segment in bridge_segment_rows if segment.get("bridge_id") == row["bridge_id"]]) + 1,
                "src_id": src,
                "src_label": node_label(src),
                "dst_id": dst,
                "dst_label": node_label(dst),
                "record_type": edge.get("edge_type", ""),
                "record_id": record_id,
                "relation_type": edge.get("relation_type", ""),
                "relationship_class": edge.get("relationship_class") or relationship_class(edge, str(edge.get("edge_type", "relationship"))),
                "status": edge.get("status", ""),
                "confidence": edge.get("confidence", ""),
                "source_ids": parse_cell_list(edge.get("source_ids")),
                "claim_ids": parse_cell_list(edge.get("claim_ids")),
                "public_export": edge.get("public_export", True),
                "guardrail_note": "lead/category/context edge; do not read as direct personal tie" if classify_bridge_path([(src, dst, edge)], graph_meta) != "direct_or_near_direct" else "",
            })
            load = edge_load.setdefault(record_id, {
                "record_id": record_id,
                "edge_type": edge.get("edge_type", ""),
                "relation_type": edge.get("relation_type", ""),
                "relationship_class": edge.get("relationship_class") or relationship_class(edge, str(edge.get("edge_type", "relationship"))),
                "status": edge.get("status", ""),
                "source_ids": set(),
                "claim_ids": set(),
                "load_bearing_score": 0,
                "bridge_classes": set(),
                "example_path": path_label(steps),
            })
            load["load_bearing_score"] += 1
            load["bridge_classes"].add(bridge_class)
            load.setdefault("relationship_classes", set()).add(edge.get("relationship_class") or relationship_class(edge, str(edge.get("edge_type", "relationship"))))
            load["source_ids"].update(parse_cell_list(edge.get("source_ids")))
            load["claim_ids"].update(parse_cell_list(edge.get("claim_ids")))

    anchor_id = "E_BILL_W" if "E_BILL_W" in people_by_id else (sorted(people_by_id, key=lambda eid: entity_display(people_by_id[eid]))[0] if people_by_id else "")
    if anchor_id:
        for person_id, person in sorted(people_by_id.items(), key=lambda item: entity_display(item[1])):
            if person_id == anchor_id:
                continue
            steps = shortest_analysis_path(graph, [anchor_id], [person_id])
            if steps is None:
                continue
            statuses = [str(step[2].get("status", "")) for step in steps]
            path_id = f"P_{slugify(entity_display(people_by_id[anchor_id]), 24).upper()}_{slugify(entity_display(person), 24).upper()}"
            path_atlas.append({
                "path_id": path_id,
                "anchor_person": entity_display(people_by_id[anchor_id]),
                "target_person": entity_display(person),
                "target_entity_id": person_id,
                "target_cluster": cluster_by_person.get(person_id, ""),
                "hops": len(steps),
                "over_six_hops": len(steps) > 6,
                "path": path_label(steps),
                "weakest_status": min(statuses, key=lambda status: STATUS_SCORE.get(status, 0.0)) if statuses else "",
                "bridge_classes": sorted({classify_bridge_path([step], graph_meta) for step in steps}),
                "relationship_classes": sorted({
                    relationship_class(step[2], str(step[2].get("edge_type", "relationship")))
                    for step in steps
                }),
                "source_ids": sorted({sid for step in steps for sid in parse_cell_list(step[2].get("source_ids"))}),
                "claim_ids": sorted({cid for step in steps for cid in parse_cell_list(step[2].get("claim_ids"))}),
                "caveat": "Contains category/context bridges; path length is not evidence of influence, guilt, membership, or control.",
            })
            for idx, (src, dst, edge) in enumerate(steps, start=1):
                step_class = classify_bridge_path([(src, dst, edge)], graph_meta)
                path_segments.append({
                    "path_id": path_id,
                    "segment_index": idx,
                    "src_id": src,
                    "src_label": node_label(src),
                    "dst_id": dst,
                    "dst_label": node_label(dst),
                    "src_cluster": graph_meta.get(src, {}).get("cluster_id", ""),
                    "dst_cluster": graph_meta.get(dst, {}).get("cluster_id", ""),
                    "record_type": edge.get("edge_type", ""),
                    "record_id": edge.get("record_id", ""),
                    "relation_type": edge.get("relation_type", ""),
                    "relationship_class": edge.get("relationship_class") or relationship_class(edge, str(edge.get("edge_type", "relationship"))),
                    "segment_status": edge.get("status", ""),
                    "segment_confidence": edge.get("confidence", ""),
                    "segment_public_export": edge.get("public_export", True),
                    "source_ids": parse_cell_list(edge.get("source_ids")),
                    "claim_ids": parse_cell_list(edge.get("claim_ids")),
                    "is_category_bridge": step_class == "category_bridge",
                    "is_context_only": step_class in {"category_bridge", "institutional_software_bridge", "lead_context_bridge", "indirect_context_bridge"},
                    "caveat": "context/category/lead edge" if step_class != "direct_or_near_direct" else "",
                })

    layered_nodes: list[dict[str, Any]] = []
    for node_id, meta in sorted(graph_meta.items(), key=lambda item: (item[1].get("layer", ""), item[1].get("label", ""))):
        source_ids = parse_cell_list(entity_by_id.get(node_id, {}).get("source_ids")) if node_id in entity_by_id else []
        layered_nodes.append({
            "node_id": node_id,
            "label": meta.get("label", ""),
            "layer": meta.get("layer", ""),
            "cluster_id": meta.get("cluster_id", ""),
            "status": entity_by_id.get(node_id, {}).get("status", ""),
            "source_count": len(source_ids),
            "public_export": entity_by_id.get(node_id, {}).get("public_export", True),
        })
    seen_edges: set[tuple[str, str, str]] = set()
    layered_edges: list[dict[str, Any]] = []
    for src, edges in graph.items():
        for dst, edge in edges:
            key = tuple(sorted([src, dst]) + [str(edge.get("record_id", ""))])
            if key in seen_edges:
                continue
            seen_edges.add(key)
            layered_edges.append({
                "src_id": src,
                "dst_id": dst,
                "src_label": node_label(src),
                "dst_label": node_label(dst),
                "edge_type": edge.get("edge_type", ""),
                "relation_type": edge.get("relation_type", ""),
                "relationship_class": edge.get("relationship_class") or relationship_class(edge, str(edge.get("edge_type", "relationship"))),
                "status": edge.get("status", ""),
                "confidence": edge.get("confidence", ""),
                "source_count": len(parse_cell_list(edge.get("source_ids"))),
                "source_ids": parse_cell_list(edge.get("source_ids")),
                "claim_ids": parse_cell_list(edge.get("claim_ids")),
                "public_export": edge.get("public_export", True),
            })

    layer_order_map = {
        "person": 1,
        "institution": 2,
        "organization": 3,
        "group": 4,
        "event_series": 5,
        "event": 6,
        "object": 7,
        "publication": 8,
        "document": 9,
        "place_alias": 10,
        "entity": 11,
    }
    event_record_by_node = {"EVENT:" + str(event.get("event_id")): event for event in events}
    degree_by_node: dict[str, int] = {}
    for edge in layered_edges:
        degree_by_node[str(edge.get("src_id", ""))] = degree_by_node.get(str(edge.get("src_id", "")), 0) + 1
        degree_by_node[str(edge.get("dst_id", ""))] = degree_by_node.get(str(edge.get("dst_id", "")), 0) + 1

    def source_rows_for_ids(source_ids: Iterable[str]) -> list[dict[str, Any]]:
        return [source_by_id[sid] for sid in source_ids if sid in source_by_id]

    def independent_count(source_rows: list[dict[str, Any]]) -> int:
        return len({source_independence_key(source) for source in source_rows})

    def node_evidence_state(record: dict[str, Any], source_rows: list[dict[str, Any]]) -> str:
        if record.get("public_export", True) is False:
            return "internal_only"
        status = str(record.get("status", ""))
        if status == "candidate":
            return "candidate_or_identity_review"
        if not source_rows:
            return "unsourced_context"
        grade = best_grade(source_rows)
        if grade in {"A", "B"}:
            return "documented_source"
        return "source_note_required"

    def caveat_for_edge(edge: dict[str, Any], source_rows: list[dict[str, Any]], boundary_claim_ids: list[str], bridge_class: str) -> str:
        status = str(edge.get("status", ""))
        edge_class = str(edge.get("relationship_class", ""))
        if edge.get("public_export", True) is False:
            return "Internal-only edge; do not use in public narrative without review."
        if edge_class == "hypothesis_requires_more_sources" or status == "unverified":
            return "Hypothesis/lead; needs more independent sources."
        if edge_class == "contested_overlap" or status == "disputed" or boundary_claim_ids:
            return "Contested or boundary-marked edge; narrate with the dispute."
        if bridge_class not in {"direct_or_near_direct", "documented_successor_bridge"}:
            return "Context/category/method bridge; not a direct personal tie."
        if len(source_rows) <= 1 or status == "single_source":
            return "Single-source edge; verify before public narrative use."
        return ""

    layered_v2_nodes: list[dict[str, Any]] = []
    for row in layered_nodes:
        node_id = str(row.get("node_id", ""))
        record = entity_by_id.get(node_id) or event_record_by_node.get(node_id) or {}
        source_ids = parse_cell_list(record.get("source_ids"))
        claim_ids = parse_cell_list(record.get("claim_ids"))
        node_sources = source_rows_for_ids(source_ids)
        readiness = readiness_label(record, node_sources) if record else "review_needed"
        layer = str(row.get("layer") or "entity")
        evidence_state = node_evidence_state(record, node_sources)
        boundary = boundary_signal(record) if record else False
        layered_v2_nodes.append({
            "node_id": node_id,
            "label": row.get("label", ""),
            "layer": layer,
            "layer_order": layer_order_map.get(layer, 99),
            "cluster_id": row.get("cluster_id", ""),
            "status": record.get("status", row.get("status", "")),
            "degree": degree_by_node.get(node_id, 0),
            "source_count": len(source_ids),
            "independent_source_count": independent_count(node_sources),
            "best_source_grade": best_grade(node_sources),
            "source_grade_counts": source_grade_counts(node_sources),
            "claim_count": len(claim_ids),
            "evidence_state": evidence_state,
            "readiness": readiness,
            "boundary_flag": boundary,
            "public_export": record.get("public_export", row.get("public_export", True)),
            "caveat": "Boundary/context node; inspect source chain before narration." if boundary or evidence_state in {"candidate_or_identity_review", "unsourced_context"} else "",
        })

    layered_v2_edges: list[dict[str, Any]] = []
    for idx, edge in enumerate(layered_edges, start=1):
        source_ids = set(parse_cell_list(edge.get("source_ids")))
        claim_ids = parse_cell_list(edge.get("claim_ids"))
        boundary_claim_ids: list[str] = []
        for claim_id in claim_ids:
            claim = claim_by_id.get(claim_id)
            if not claim:
                continue
            source_ids.update(parse_cell_list(claim.get("source_ids")))
            if boundary_signal(claim):
                boundary_claim_ids.append(claim_id)
        edge_sources = source_rows_for_ids(sorted(source_ids))
        src_id = str(edge.get("src_id", ""))
        dst_id = str(edge.get("dst_id", ""))
        graph_edge = {
            "record_id": edge.get("edge_id") or edge.get("record_id") or f"LKG2_{idx}",
            "edge_type": edge.get("edge_type", ""),
            "relation_type": edge.get("relation_type", ""),
            "relationship_class": edge.get("relationship_class", ""),
            "status": edge.get("status", ""),
            "source_ids": sorted(source_ids),
            "claim_ids": claim_ids,
            "confidence": edge.get("confidence", ""),
            "notes": "",
            "public_export": edge.get("public_export", True),
        }
        bridge_class = classify_bridge_path([(src_id, dst_id, graph_edge)], graph_meta)
        readiness = readiness_label(graph_edge, edge_sources)
        evidence_weight = round(
            STATUS_SCORE.get(str(edge.get("status", "")), 0.35)
            * max(0.35, source_grade_score(edge_sources))
            * (1.0 + min(4, len(edge_sources)) * 0.12),
            3,
        )
        caveat = caveat_for_edge(graph_edge, edge_sources, boundary_claim_ids, bridge_class)
        layered_v2_edges.append({
            "edge_id": graph_edge["record_id"],
            "src_id": src_id,
            "dst_id": dst_id,
            "src_label": edge.get("src_label", ""),
            "dst_label": edge.get("dst_label", ""),
            "src_layer": graph_meta.get(src_id, {}).get("layer", ""),
            "dst_layer": graph_meta.get(dst_id, {}).get("layer", ""),
            "edge_type": edge.get("edge_type", ""),
            "relation_type": edge.get("relation_type", ""),
            "relationship_class": edge.get("relationship_class", ""),
            "relation_family": relation_family(str(edge.get("relation_type", "")), str(edge.get("edge_type", ""))),
            "bridge_class": bridge_class,
            "status": edge.get("status", ""),
            "confidence": edge.get("confidence", ""),
            "evidence_weight": evidence_weight,
            "source_count": len(edge_sources),
            "independent_source_count": independent_count(edge_sources),
            "best_source_grade": best_grade(edge_sources),
            "source_grade_counts": source_grade_counts(edge_sources),
            "claim_ids": claim_ids,
            "source_ids": sorted(source_ids),
            "boundary_claim_ids": sorted(boundary_claim_ids),
            "readiness": readiness,
            "boundary_flag": bool(boundary_claim_ids) or boundary_signal(graph_edge),
            "public_export": edge.get("public_export", True),
            "caveat": caveat,
        })

    layer_summary_map: dict[str, dict[str, Any]] = {}
    for node in layered_v2_nodes:
        layer = str(node.get("layer", "entity"))
        bucket = layer_summary_map.setdefault(layer, {
            "layer": layer,
            "layer_order": node.get("layer_order", 99),
            "node_count": 0,
            "public_node_count": 0,
            "internal_node_count": 0,
            "candidate_node_count": 0,
            "source_count": 0,
            "edge_count": 0,
            "public_edge_count": 0,
            "lead_or_disputed_edge_count": 0,
            "public_ready_edge_count": 0,
            "_statuses": {},
            "_classes": {},
        })
        bucket["node_count"] += 1
        bucket["public_node_count"] += 1 if node.get("public_export", True) is not False else 0
        bucket["internal_node_count"] += 1 if node.get("public_export", True) is False else 0
        bucket["candidate_node_count"] += 1 if str(node.get("status", "")) == "candidate" else 0
        bucket["source_count"] += int(node.get("source_count", 0) or 0)
    for edge in layered_v2_edges:
        for layer_key in ["src_layer", "dst_layer"]:
            layer = str(edge.get(layer_key) or "entity")
            bucket = layer_summary_map.setdefault(layer, {
                "layer": layer,
                "layer_order": layer_order_map.get(layer, 99),
                "node_count": 0,
                "public_node_count": 0,
                "internal_node_count": 0,
                "candidate_node_count": 0,
                "source_count": 0,
                "edge_count": 0,
                "public_edge_count": 0,
                "lead_or_disputed_edge_count": 0,
                "public_ready_edge_count": 0,
                "_statuses": {},
                "_classes": {},
            })
            bucket["edge_count"] += 1
            bucket["public_edge_count"] += 1 if edge.get("public_export", True) is not False else 0
            bucket["lead_or_disputed_edge_count"] += 1 if str(edge.get("readiness", "")) == "lead_or_disputed" else 0
            bucket["public_ready_edge_count"] += 1 if str(edge.get("readiness", "")) == "public_ready" else 0
            status = str(edge.get("status", "") or "unknown")
            rel_class = str(edge.get("relationship_class", "") or "unknown")
            bucket["_statuses"][status] = bucket["_statuses"].get(status, 0) + 1
            bucket["_classes"][rel_class] = bucket["_classes"].get(rel_class, 0) + 1
    layered_v2_layers = []
    for row in sorted(layer_summary_map.values(), key=lambda item: (int(parse_float(item.get("layer_order"), 99)), str(item.get("layer", "")))):
        statuses = sorted(row.pop("_statuses").items(), key=lambda item: (-item[1], item[0]))
        classes = sorted(row.pop("_classes").items(), key=lambda item: (-item[1], item[0]))
        row["dominant_statuses"] = ";".join(f"{key}:{value}" for key, value in statuses[:5])
        row["dominant_relationship_classes"] = ";".join(f"{key}:{value}" for key, value in classes[:5])
        layered_v2_layers.append(row)

    claim_heatmap: list[dict[str, Any]] = []
    claim_matrix: list[dict[str, Any]] = []
    claim_edge_rows: list[dict[str, Any]] = []
    for claim in sorted(claims, key=lambda row: str(row.get("claim_id", ""))):
        source_ids = [sid for sid in parse_cell_list(claim.get("source_ids")) if sid in source_by_id]
        source_rows = [source_by_id[sid] for sid in source_ids]
        independent_count = len({source_independence_key(src) for src in source_rows})
        claim_heatmap.append({
            "claim_id": claim.get("claim_id", ""),
            "claim": claim.get("claim", ""),
            "claim_type": claim.get("claim_type", ""),
            "status": claim.get("status", ""),
            "confidence": claim.get("confidence", ""),
            "status_score": STATUS_SCORE.get(str(claim.get("status", "")), 0.0),
            "source_count": len(source_rows),
            "independent_source_count": independent_count,
            "best_source_grade": best_grade(source_rows),
            "source_grade_counts": source_grade_counts(source_rows),
            "source_grade_score": source_grade_score(source_rows),
            "privacy_review": claim.get("privacy_review", ""),
            "public_export": claim.get("public_export", True),
            "boundary_flag": boundary_signal(claim),
            "readiness": readiness_label(claim, source_rows),
        })
        for source in source_rows:
            claim_matrix.append({
                "claim_id": claim.get("claim_id", ""),
                "claim_label": str(claim.get("claim", ""))[:160],
                "source_id": source.get("source_id", ""),
                "source_title": source.get("title", ""),
                "source_grade": source.get("reliability_grade", ""),
                "source_type": source.get("source_type", ""),
                "source_publisher": source.get("publisher", ""),
                "claim_status": claim.get("status", ""),
                "claim_confidence": claim.get("confidence", ""),
                "claim_type": claim.get("claim_type", ""),
                "source_role": "boundary_source" if boundary_signal(claim) else "direct_support",
                "safe_public_cell": public_ready_record(claim) and source.get("public_export", True) is not False,
                "boundary_flag": boundary_signal(claim),
                "contradiction_flag": bool(parse_cell_list(claim.get("contradicts"))),
                "contradicts": claim.get("contradicts", []),
                "supports": claim.get("supports", []),
            })
        for edge_type, linked_ids in [("supports", parse_cell_list(claim.get("supports"))), ("contradicts", parse_cell_list(claim.get("contradicts")))]:
            for linked_id in linked_ids:
                linked = claim_by_id.get(linked_id, {})
                claim_edge_rows.append({
                    "from_claim_id": claim.get("claim_id", ""),
                    "to_claim_id": linked_id,
                    "edge_type": edge_type,
                    "from_claim_status": claim.get("status", ""),
                    "to_claim_status": linked.get("status", ""),
                    "from_confidence": claim.get("confidence", ""),
                    "to_confidence": linked.get("confidence", ""),
                    "shared_source_count": len(set(source_ids) & set(parse_cell_list(linked.get("source_ids")))),
                    "from_source_ids": source_ids,
                    "to_source_ids": parse_cell_list(linked.get("source_ids")),
                    "boundary_flag": edge_type == "contradicts" or boundary_signal(claim) or boundary_signal(linked),
                    "safe_public_pair": public_ready_record(claim) and (not linked or public_ready_record(linked)),
                })

    heatmap_groups: dict[tuple[str, str], dict[str, Any]] = {}
    for row in claim_heatmap:
        key = (str(row.get("claim_type") or "unknown"), str(row.get("status") or "unknown"))
        group = heatmap_groups.setdefault(key, {
            "claim_type": key[0],
            "status": key[1],
            "claim_count": 0,
            "public_claim_count": 0,
            "internal_only_count": 0,
            "needs_review_count": 0,
            "confidence_total": 0.0,
            "source_count_total": 0,
            "a_sources": 0,
            "b_sources": 0,
            "c_sources": 0,
            "d_sources": 0,
            "boundary_claim_count": 0,
            "claim_ids": [],
        })
        group["claim_count"] += 1
        group["public_claim_count"] += 1 if row.get("public_export") is not False else 0
        group["internal_only_count"] += 1 if row.get("public_export") is False else 0
        group["needs_review_count"] += 1 if row.get("privacy_review") and row.get("privacy_review") != "clear" else 0
        group["confidence_total"] += parse_float(row.get("confidence"), 0.0)
        group["source_count_total"] += int(row.get("source_count") or 0)
        group["boundary_claim_count"] += 1 if row.get("boundary_flag") else 0
        group["claim_ids"].append(row.get("claim_id", ""))
        grade_map = dict(part.split(":", 1) for part in str(row.get("source_grade_counts", "")).split(";") if ":" in part)
        group["a_sources"] += int(grade_map.get("A", "0"))
        group["b_sources"] += int(grade_map.get("B", "0"))
        group["c_sources"] += int(grade_map.get("C", "0"))
        group["d_sources"] += int(grade_map.get("D", "0"))
    heatmap_aggregate = []
    for group in heatmap_groups.values():
        count = max(1, int(group["claim_count"]))
        group["avg_confidence"] = round(float(group.pop("confidence_total")) / count, 3)
        group["avg_source_count"] = round(float(group["source_count_total"]) / count, 3)
        heatmap_aggregate.append(group)
    heatmap_aggregate.sort(key=lambda row: (str(row["claim_type"]), str(row["status"])))

    source_counter: dict[str, dict[str, Any]] = {
        sid: {
            "source_id": sid,
            "title": source.get("title", ""),
            "reliability_grade": source.get("reliability_grade", ""),
            "source_type": source.get("source_type", ""),
            "publisher": source.get("publisher", ""),
            "date_published": source.get("date_published", ""),
            "date_accessed": source.get("date_accessed", ""),
            "url": source.get("url", ""),
            "independence_group": source.get("independence_group", ""),
            "claim_count": 0,
            "event_count": 0,
            "event_link_count": 0,
            "relationship_count": 0,
            "entity_count": 0,
            "person_count": 0,
            "verified_claim_count": 0,
            "corroborated_claim_count": 0,
            "single_source_claim_count": 0,
            "disputed_claim_count": 0,
            "unverified_claim_count": 0,
            "needs_privacy_review_count": 0,
            "nonpublic_record_count": 0,
            "source_quality_notes": source.get("notes", ""),
            "public_export": source.get("public_export", True),
        }
        for sid, source in source_by_id.items()
    }
    for claim in claims:
        for sid in parse_cell_list(claim.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["claim_count"] += 1
                status_key = f"{claim.get('status', 'unknown')}_claim_count"
                if status_key in source_counter[sid]:
                    source_counter[sid][status_key] += 1
                if claim.get("privacy_review") and claim.get("privacy_review") != "clear":
                    source_counter[sid]["needs_privacy_review_count"] += 1
                if claim.get("public_export", True) is False:
                    source_counter[sid]["nonpublic_record_count"] += 1
    for event in events:
        for sid in parse_cell_list(event.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["event_count"] += 1
                if event.get("public_export", True) is False:
                    source_counter[sid]["nonpublic_record_count"] += 1
    for link in event_links:
        for sid in parse_cell_list(link.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["event_link_count"] += 1
                if link.get("public_export", True) is False:
                    source_counter[sid]["nonpublic_record_count"] += 1
    for rel in relationships:
        for sid in parse_cell_list(rel.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["relationship_count"] += 1
                if rel.get("public_export", True) is False:
                    source_counter[sid]["nonpublic_record_count"] += 1
    for entity in entities:
        for sid in parse_cell_list(entity.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["entity_count"] += 1
                if entity.get("public_export", True) is False:
                    source_counter[sid]["nonpublic_record_count"] += 1
    for person in people:
        for sid in parse_cell_list(person.get("source_ids")):
            if sid in source_counter:
                source_counter[sid]["person_count"] += 1
    source_dashboard = sorted(source_counter.values(), key=lambda row: (str(row["reliability_grade"]), str(row["source_id"])))
    grade_counts: dict[str, int] = {}
    for source in source_dashboard:
        grade = str(source.get("reliability_grade", ""))
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    source_grade_count_rows = [{"grade": grade, "count": count} for grade, count in sorted(grade_counts.items())]

    boundary_rows: list[dict[str, Any]] = []
    for claim in claims:
        claim_type = str(claim.get("claim_type", ""))
        status = str(claim.get("status", ""))
        contradicts = parse_cell_list(claim.get("contradicts"))
        if claim_type == "contradiction_or_boundary" or contradicts or status in {"disputed", "unverified", "excluded_from_public_script"}:
            boundary_rows.append({
                "record_id": claim.get("claim_id", ""),
                "record_type": "claim",
                "status": status,
                "claim_type": claim_type,
                "boundary_kind": "contradicts" if contradicts else claim_type or status,
                "summary": claim.get("claim", ""),
                "source_ids": claim.get("source_ids", []),
                "contradicts": contradicts,
            })
    for rel in relationships:
        notes = str(rel.get("notes", "")).lower()
        if boundary_signal(rel) or any(term in notes for term in ["boundary", "lead", "alleged", "not verified", "do not treat"]):
            boundary_rows.append({
                "record_id": rel.get("rel_id", ""),
                "record_type": "relationship",
                "status": rel.get("status", ""),
                "claim_type": "",
                "boundary_kind": "relationship_note",
                "relationship_class": relationship_class(rel),
                "summary": rel.get("notes", ""),
                "source_ids": rel.get("source_ids", []),
                "contradicts": "",
            })
    for link in event_links:
        if boundary_signal(link):
            boundary_rows.append({
                "record_id": link.get("event_link_id", ""),
                "record_type": "event_link",
                "status": link.get("status", ""),
                "claim_type": "",
                "boundary_kind": "event_link_context",
                "relationship_class": relationship_class(link, "event_link"),
                "summary": link.get("notes", "") or link.get("basis", ""),
                "source_ids": link.get("source_ids", []),
                "contradicts": "",
            })

    swimlanes: list[dict[str, Any]] = []
    event_by_id = {str(event.get("event_id")): event for event in events}
    seen_swimlane_keys: set[tuple[str, str, str]] = set()
    for link in event_links:
        event_id = str(link.get("event_id", ""))
        event = event_by_id.get(event_id, {})
        entity_id = str(link.get("entity_id", ""))
        cluster_id = cluster_by_person.get(entity_id, "unclustered")
        key = (cluster_id, event_id, str(link.get("event_link_id", "")))
        seen_swimlane_keys.add(key)
        swimlanes.append({
            "cluster_id": cluster_id,
            "cluster_label": cluster_labels.get(cluster_id, cluster_id),
            "entity_id": entity_id,
            "name": entity_display(entity_by_id.get(entity_id)),
            "start_date": event.get("start_date", ""),
            "end_date": event.get("end_date", ""),
            "date_precision": event.get("date_precision", ""),
            "event_id": event_id,
            "event_title": event.get("title", ""),
            "event_type": event.get("event_type", ""),
            "status": event.get("status", ""),
            "confidence": event.get("confidence", ""),
            "event_link_id": link.get("event_link_id", ""),
            "relation_type": link.get("relation_type", ""),
            "relationship_class": relationship_class(link, "event_link"),
            "event_link_status": link.get("status", ""),
            "event_link_confidence": link.get("confidence", ""),
            "source_count": len(set(parse_cell_list(event.get("source_ids"))) | set(parse_cell_list(link.get("source_ids")))),
            "claim_ids": sorted(set(parse_cell_list(event.get("claim_ids"))) | set(parse_cell_list(link.get("claim_ids")))),
            "source_ids": sorted(set(parse_cell_list(event.get("source_ids"))) | set(parse_cell_list(link.get("source_ids")))),
            "is_public_safe": public_ready_record(event) and public_ready_record(link),
            "caveat": "co-mention/context link" if "co_mentioned" in str(link.get("relation_type", "")) else "",
        })
    for event in events:
        event_id = str(event.get("event_id", ""))
        for entity_id in parse_cell_list(event.get("entity_ids")) or [""]:
            cluster_id = cluster_by_person.get(entity_id, "unclustered")
            key = (cluster_id, event_id, "")
            if key in seen_swimlane_keys:
                continue
            swimlanes.append({
                "cluster_id": cluster_id,
                "cluster_label": cluster_labels.get(cluster_id, cluster_id),
                "entity_id": entity_id,
                "name": entity_display(entity_by_id.get(entity_id)),
                "start_date": event.get("start_date", ""),
                "end_date": event.get("end_date", ""),
                "date_precision": event.get("date_precision", ""),
                "event_id": event_id,
                "event_title": event.get("title", ""),
                "event_type": event.get("event_type", ""),
                "status": event.get("status", ""),
                "confidence": event.get("confidence", ""),
                "event_link_id": "",
                "relation_type": "event_entity",
                "relationship_class": "personnel_bridge",
                "event_link_status": "",
                "event_link_confidence": "",
                "source_count": len(parse_cell_list(event.get("source_ids"))),
                "claim_ids": event.get("claim_ids", []),
                "source_ids": event.get("source_ids", []),
                "is_public_safe": public_ready_record(event),
                "caveat": "",
            })
    swimlanes.sort(key=lambda row: (str(row["cluster_id"]), date_sort_key(row.get("start_date")), str(row["event_id"])))

    relation_counts: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for rel in relationships:
        relation_type = str(rel.get("relation_type", ""))
        rel_class = relationship_class(rel)
        status = str(rel.get("status", ""))
        family = relation_family(relation_type)
        public_scope = "public" if rel.get("public_export", True) is not False else "internal"
        key = ("relationship", rel_class, family, relation_type, status + "/" + public_scope)
        bucket = relation_counts.setdefault(key, {
            "record_kind": "relationship",
            "relationship_class": rel_class,
            "relationship_class_label": RELATIONSHIP_CLASS_TITLES.get(rel_class, rel_class),
            "relation_family": family,
            "relation_type": relation_type,
            "status": status,
            "public_scope": public_scope,
            "row_count": 0,
            "weighted_count": 0.0,
            "source_count": 0,
            "claim_count": 0,
            "boundary_count": 0,
            "lead_only_count": 0,
            "sample_record_ids": [],
        })
        bucket["row_count"] += 1
        weight = STATUS_SCORE.get(status, 0.3)
        if "co_mentioned" in relation_type:
            weight *= 0.1
            bucket["lead_only_count"] += 1
        bucket["weighted_count"] = round(float(bucket["weighted_count"]) + weight, 3)
        bucket["source_count"] += len(parse_cell_list(rel.get("source_ids")))
        bucket["claim_count"] += len(parse_cell_list(rel.get("claim_ids")))
        bucket["boundary_count"] += 1 if boundary_signal(rel) else 0
        if len(bucket["sample_record_ids"]) < 8:
            bucket["sample_record_ids"].append(rel.get("rel_id", ""))
    for link in event_links:
        relation_type = str(link.get("relation_type", ""))
        rel_class = relationship_class(link, "event_link")
        status = str(link.get("status", ""))
        family = relation_family(relation_type, "event_link")
        public_scope = "public" if link.get("public_export", True) is not False else "internal"
        key = ("event_link", rel_class, family, relation_type, status + "/" + public_scope)
        bucket = relation_counts.setdefault(key, {
            "record_kind": "event_link",
            "relationship_class": rel_class,
            "relationship_class_label": RELATIONSHIP_CLASS_TITLES.get(rel_class, rel_class),
            "relation_family": family,
            "relation_type": relation_type,
            "status": status,
            "public_scope": public_scope,
            "row_count": 0,
            "weighted_count": 0.0,
            "source_count": 0,
            "claim_count": 0,
            "boundary_count": 0,
            "lead_only_count": 0,
            "sample_record_ids": [],
        })
        bucket["row_count"] += 1
        weight = STATUS_SCORE.get(status, 0.3)
        if "co_mentioned" in relation_type:
            weight *= 0.1
            bucket["lead_only_count"] += 1
        bucket["weighted_count"] = round(float(bucket["weighted_count"]) + weight, 3)
        bucket["source_count"] += len(parse_cell_list(link.get("source_ids")))
        bucket["claim_count"] += len(parse_cell_list(link.get("claim_ids")))
        bucket["boundary_count"] += 1 if boundary_signal(link) else 0
        if len(bucket["sample_record_ids"]) < 8:
            bucket["sample_record_ids"].append(link.get("event_link_id", ""))
    relation_type_counts = [
        row
        for row in sorted(relation_counts.values(), key=lambda item: (-float(item["weighted_count"]), str(item["relation_type"])))
    ]

    person_source_map: dict[tuple[str, str], set[str]] = {}
    for person in people:
        person_id = str(person.get("entity_id", ""))
        for sid in parse_cell_list(person.get("source_ids")):
            person_source_map.setdefault((person_id, sid), set()).add("entity_source")
        for claim_id in parse_cell_list(person.get("claim_ids")):
            claim = claim_by_id.get(claim_id)
            if claim:
                for sid in parse_cell_list(claim.get("source_ids")):
                    person_source_map.setdefault((person_id, sid), set()).add("entity_claim")
    for rel in relationships:
        for person_id in [str(rel.get("src_entity_id", "")), str(rel.get("dst_entity_id", ""))]:
            if person_id in people_by_id:
                for sid in parse_cell_list(rel.get("source_ids")):
                    person_source_map.setdefault((person_id, sid), set()).add("relationship")
                for claim_id in parse_cell_list(rel.get("claim_ids")):
                    claim = claim_by_id.get(claim_id)
                    if claim:
                        for sid in parse_cell_list(claim.get("source_ids")):
                            person_source_map.setdefault((person_id, sid), set()).add("relationship_claim")
    for event in events:
        for person_id in parse_cell_list(event.get("entity_ids")):
            if person_id in people_by_id:
                for sid in parse_cell_list(event.get("source_ids")):
                    person_source_map.setdefault((person_id, sid), set()).add("event_entity")
                for claim_id in parse_cell_list(event.get("claim_ids")):
                    claim = claim_by_id.get(claim_id)
                    if claim:
                        for sid in parse_cell_list(claim.get("source_ids")):
                            person_source_map.setdefault((person_id, sid), set()).add("event_claim")
    for link in event_links:
        person_id = str(link.get("entity_id", ""))
        if person_id in people_by_id:
            for sid in parse_cell_list(link.get("source_ids")):
                person_source_map.setdefault((person_id, sid), set()).add("event_link")
            for claim_id in parse_cell_list(link.get("claim_ids")):
                claim = claim_by_id.get(claim_id)
                if claim:
                    for sid in parse_cell_list(claim.get("source_ids")):
                        person_source_map.setdefault((person_id, sid), set()).add("event_link_claim")
    person_source = []
    for (person_id, sid), contexts in sorted(person_source_map.items(), key=lambda item: (entity_display(people_by_id.get(item[0][0])), item[0][1])):
        source = source_by_id.get(sid, {})
        person_source.append({
            "edge_id": f"SP_{slugify(sid, 24).upper()}_{slugify(person_id, 24).upper()}",
            "person_id": person_id,
            "person_name": entity_display(people_by_id.get(person_id)),
            "cluster_id": cluster_by_person.get(person_id, ""),
            "source_id": sid,
            "source_title": source.get("title", ""),
            "source_grade": source.get("reliability_grade", ""),
            "source_type": source.get("source_type", ""),
            "publisher": source.get("publisher", ""),
            "contexts": sorted(contexts),
            "public_evidence_state": "public" if people_by_id.get(person_id, {}).get("public_export", True) is not False and source.get("public_export", True) is not False else "mixed",
            "privacy_flag": people_by_id.get(person_id, {}).get("public_export", True) is False or source.get("public_export", True) is False,
            "notes": "co-mention/context only" if contexts <= {"event_link", "event_link_claim"} else "",
        })
    person_source_nodes: list[dict[str, Any]] = []
    source_node_ids = {row["source_id"] for row in person_source}
    person_node_ids = {row["person_id"] for row in person_source}
    for person_id in sorted(person_node_ids, key=lambda pid: entity_display(people_by_id.get(pid))):
        person = people_by_id.get(person_id, {})
        person_source_nodes.append({
            "node_id": f"person:{person_id}",
            "node_type": "person",
            "label": entity_display(person),
            "source_id": "",
            "entity_id": person_id,
            "reliability_grade": "",
            "source_type": "",
            "publisher": "",
            "privacy_level": person.get("privacy_level", ""),
            "living_status": person.get("living_status", ""),
            "role_tags": person.get("role_tags", []),
            "status": person.get("status", ""),
            "public_export": person.get("public_export", True),
            "degree": sum(1 for row in person_source if row["person_id"] == person_id),
        })
    for sid in sorted(source_node_ids):
        source = source_by_id.get(sid, {})
        person_source_nodes.append({
            "node_id": f"source:{sid}",
            "node_type": "source",
            "label": source.get("title", sid),
            "source_id": sid,
            "entity_id": "",
            "reliability_grade": source.get("reliability_grade", ""),
            "source_type": source.get("source_type", ""),
            "publisher": source.get("publisher", ""),
            "privacy_level": "",
            "living_status": "",
            "role_tags": "",
            "status": "",
            "public_export": source.get("public_export", True),
            "degree": sum(1 for row in person_source if row["source_id"] == sid),
        })

    readiness_rows: list[dict[str, Any]] = []
    for record_type, rows, id_key in [
        ("claim", claims, "claim_id"),
        ("event", events, "event_id"),
        ("event_link", event_links, "event_link_id"),
        ("relationship", relationships, "rel_id"),
    ]:
        for row in rows:
            source_rows = [source_by_id[sid] for sid in parse_cell_list(row.get("source_ids")) if sid in source_by_id]
            boundary = boundary_signal(row)
            readiness_rows.append({
                "record_type": record_type,
                "record_id": row.get(id_key, ""),
                "status": row.get("status", ""),
                "confidence": row.get("confidence", ""),
                "source_count": len(source_rows),
                "best_source_grade": best_grade(source_rows),
                "source_grade_counts": source_grade_counts(source_rows),
                "public_export": row.get("public_export", True),
            "privacy_review": row.get("privacy_review", "clear"),
            "readiness": readiness_label(row, source_rows),
            "boundary_flag": boundary,
            "required_caveat": "Boundary/lead/context wording required." if boundary else "",
            "relationship_class": relationship_class(row, record_type) if record_type in {"event_link", "relationship"} else "",
            "summary": row.get("claim") or row.get("title") or row.get("notes", ""),
        })
    readiness_count_map: dict[str, int] = {}
    for row in readiness_rows:
        readiness = str(row.get("readiness", ""))
        readiness_count_map[readiness] = readiness_count_map.get(readiness, 0) + 1
    readiness_counts = [{"readiness": key, "count": value} for key, value in sorted(readiness_count_map.items())]

    fragility = []
    for row in edge_load.values():
        status = str(row["status"])
        load_score = int(row["load_bearing_score"])
        support_score = STATUS_SCORE.get(status, 0.25)
        if any(cls in {"category_bridge", "lead_context_bridge", "institutional_software_bridge"} for cls in row["bridge_classes"]):
            support_score *= 0.7
        fragility_score = round(max(0.0, min(1.0, 1.0 - support_score + min(0.25, load_score * 0.025))), 3)
        if fragility_score <= 0.25:
            tier = "stable"
        elif fragility_score <= 0.5:
            tier = "qualified"
        elif fragility_score <= 0.75:
            tier = "fragile"
        else:
            tier = "lead_only"
        fragility.append({
            "record_id": row["record_id"],
            "edge_type": row["edge_type"],
            "relation_type": row["relation_type"],
            "relationship_class": ";".join(sorted(row.get("relationship_classes", []))),
            "status": status,
            "load_bearing_score": row["load_bearing_score"],
            "bridge_class": ";".join(sorted(row["bridge_classes"])),
            "source_ids": sorted(row["source_ids"]),
            "claim_ids": sorted(row["claim_ids"]),
            "support_score": round(support_score, 3),
            "fragility_score": fragility_score,
            "fragility_tier": tier,
            "required_caveat": "Do not narrate as direct influence/contact." if tier in {"fragile", "lead_only"} else "",
            "example_path": row["example_path"],
        })
    fragility.sort(key=lambda row: (-int(row["load_bearing_score"]), str(row["record_id"])))

    write_csv(out / "cluster_bridge_sankey_nodes.csv", sankey_nodes, [
        "cluster_id", "cluster_label", "member_entity_ids", "member_names", "size", "mean_kde_density",
        "internal_edge_weight", "boundary_edge_weight", "notes",
    ])
    write_csv(out / "cluster_bridge_sankey_links.csv", cluster_bridge_links, [
        "bridge_id", "src_cluster", "dst_cluster", "src_cluster_label", "dst_cluster_label", "bridge_class", "relationship_classes", "hops",
        "path", "statuses", "source_ids", "claim_ids", "boundary_claim_ids", "boundary_text", "source_grade_counts",
        "public_readiness", "public_export", "notes",
    ])
    write_csv(out / "cluster_bridge_sankey.csv", cluster_bridge_rows, [
        "bridge_id", "src_cluster", "dst_cluster", "bridge_class", "relationship_classes", "hops", "path", "statuses", "source_ids",
        "claim_ids", "boundary_claim_ids", "boundary_text", "public_readiness", "public_export",
    ])
    write_csv(out / "layered_knowledge_graph_nodes.csv", layered_nodes, [
        "node_id", "label", "layer", "cluster_id", "status", "source_count", "public_export",
    ])
    write_csv(out / "layered_knowledge_graph_edges.csv", layered_edges, [
        "src_id", "dst_id", "src_label", "dst_label", "edge_type", "relation_type", "relationship_class", "status", "confidence", "source_count", "source_ids", "claim_ids", "public_export",
    ])
    write_csv(out / "layered_knowledge_graph_v2_nodes.csv", layered_v2_nodes, [
        "node_id", "label", "layer", "layer_order", "cluster_id", "status", "degree", "source_count",
        "independent_source_count", "best_source_grade", "source_grade_counts", "claim_count", "evidence_state",
        "readiness", "boundary_flag", "public_export", "caveat",
    ])
    write_csv(out / "layered_knowledge_graph_v2_edges.csv", layered_v2_edges, [
        "edge_id", "src_id", "dst_id", "src_label", "dst_label", "src_layer", "dst_layer", "edge_type",
        "relation_type", "relationship_class", "relation_family", "bridge_class", "status", "confidence",
        "evidence_weight", "source_count", "independent_source_count", "best_source_grade", "source_grade_counts",
        "claim_ids", "source_ids", "boundary_claim_ids", "readiness", "boundary_flag", "public_export", "caveat",
    ])
    write_csv(out / "layered_knowledge_graph_v2_layers.csv", layered_v2_layers, [
        "layer", "layer_order", "node_count", "public_node_count", "internal_node_count", "candidate_node_count",
        "source_count", "edge_count", "public_edge_count", "lead_or_disputed_edge_count", "public_ready_edge_count",
        "dominant_statuses", "dominant_relationship_classes",
    ])
    write_csv(out / "evidence_confidence_heatmap.csv", claim_heatmap, [
        "claim_id", "claim", "claim_type", "status", "confidence", "status_score", "source_count", "independent_source_count",
        "best_source_grade", "source_grade_counts", "source_grade_score", "privacy_review", "public_export", "boundary_flag", "readiness",
    ])
    write_csv(out / "evidence_confidence_heatmap_aggregate.csv", heatmap_aggregate, [
        "claim_type", "status", "claim_count", "public_claim_count", "internal_only_count", "needs_review_count",
        "avg_confidence", "avg_source_count", "source_count_total", "a_sources", "b_sources", "c_sources", "d_sources",
        "boundary_claim_count", "claim_ids",
    ])
    write_csv(out / "bridge_fragility.csv", fragility, [
        "record_id", "edge_type", "relation_type", "relationship_class", "status", "load_bearing_score", "bridge_class", "source_ids",
        "claim_ids", "support_score", "fragility_score", "fragility_tier", "required_caveat", "example_path",
    ])
    write_csv(out / "bridge_fragility_segments.csv", bridge_segment_rows, [
        "bridge_id", "segment_index", "src_id", "src_label", "dst_id", "dst_label", "record_type", "record_id",
        "relation_type", "relationship_class", "status", "confidence", "source_ids", "claim_ids", "public_export", "guardrail_note",
    ])
    write_csv(out / "claim_corroboration_matrix.csv", claim_matrix, [
        "claim_id", "claim_label", "source_id", "source_title", "source_grade", "source_type", "source_publisher",
        "claim_status", "claim_confidence", "claim_type", "source_role", "safe_public_cell", "boundary_flag",
        "contradiction_flag", "contradicts", "supports",
    ])
    write_csv(out / "claim_corroboration_edges.csv", claim_edge_rows, [
        "from_claim_id", "to_claim_id", "edge_type", "from_claim_status", "to_claim_status", "from_confidence",
        "to_confidence", "shared_source_count", "from_source_ids", "to_source_ids", "boundary_flag", "safe_public_pair",
    ])
    write_csv(out / "source_quality_dashboard.csv", source_dashboard, [
        "source_id", "title", "reliability_grade", "source_type", "publisher", "date_published", "date_accessed", "url",
        "independence_group", "claim_count", "event_count", "event_link_count", "relationship_count", "entity_count",
        "person_count", "verified_claim_count", "corroborated_claim_count", "single_source_claim_count",
        "disputed_claim_count", "unverified_claim_count", "needs_privacy_review_count", "nonpublic_record_count",
        "source_quality_notes", "public_export",
    ])
    write_csv(out / "sixdof_path_atlas.csv", path_atlas, [
        "path_id", "anchor_person", "target_person", "target_entity_id", "target_cluster", "hops", "over_six_hops",
        "path", "weakest_status", "bridge_classes", "relationship_classes", "source_ids", "claim_ids", "caveat",
    ])
    write_csv(out / "sixdof_path_segments.csv", path_segments, [
        "path_id", "segment_index", "src_id", "src_label", "dst_id", "dst_label", "src_cluster", "dst_cluster",
        "record_type", "record_id", "relation_type", "relationship_class", "segment_status", "segment_confidence", "segment_public_export",
        "source_ids", "claim_ids", "is_category_bridge", "is_context_only", "caveat",
    ])
    write_csv(out / "contradiction_boundary_overlay.csv", boundary_rows, [
        "record_id", "record_type", "status", "claim_type", "boundary_kind", "relationship_class", "summary", "source_ids", "contradicts",
    ])
    write_csv(out / "temporal_cluster_swimlanes.csv", swimlanes, [
        "cluster_id", "cluster_label", "entity_id", "name", "start_date", "end_date", "date_precision", "event_id",
        "event_title", "event_type", "status", "confidence", "event_link_id", "relation_type", "relationship_class", "event_link_status",
        "event_link_confidence", "source_count", "claim_ids", "source_ids", "is_public_safe", "caveat",
    ])
    write_csv(out / "relationship_type_treemap.csv", relation_type_counts, [
        "record_kind", "relationship_class", "relationship_class_label", "relation_family", "relation_type", "status", "public_scope", "row_count", "weighted_count",
        "source_count", "claim_count", "boundary_count", "lead_only_count", "sample_record_ids",
    ])
    write_csv(out / "person_source_bipartite.csv", person_source, [
        "edge_id", "person_id", "person_name", "cluster_id", "source_id", "source_title", "source_grade", "source_type",
        "publisher", "contexts", "public_evidence_state", "privacy_flag", "notes",
    ])
    write_csv(out / "person_source_bipartite_nodes.csv", person_source_nodes, [
        "node_id", "node_type", "label", "source_id", "entity_id", "reliability_grade", "source_type", "publisher",
        "privacy_level", "living_status", "role_tags", "status", "public_export", "degree",
    ])
    write_csv(out / "person_source_bipartite_edges.csv", person_source, [
        "edge_id", "source_id", "person_id", "source_grade", "source_type", "contexts", "public_evidence_state",
        "privacy_flag", "notes",
    ])
    write_csv(out / "public_narrative_readiness.csv", readiness_rows, [
        "record_type", "record_id", "status", "confidence", "source_count", "best_source_grade", "source_grade_counts",
        "public_export", "privacy_review", "readiness", "boundary_flag", "required_caveat", "relationship_class", "summary",
    ])

    chart_data = {
        "sankey_nodes": sankey_nodes,
        "cluster_bridge_links": cluster_bridge_links,
        "cluster_bridges": cluster_bridge_rows,
        "layered_nodes": layered_nodes,
        "layered_edges": layered_edges,
        "layered_v2_nodes": layered_v2_nodes,
        "layered_v2_edges": layered_v2_edges,
        "layered_v2_layers": layered_v2_layers,
        "claim_heatmap": claim_heatmap,
        "heatmap_aggregate": heatmap_aggregate,
        "fragility": fragility,
        "claim_matrix": claim_matrix,
        "source_grade_counts": source_grade_count_rows,
        "source_dashboard": source_dashboard,
        "path_atlas": path_atlas,
        "boundary_rows": boundary_rows,
        "swimlanes": swimlanes,
        "relation_type_counts": relation_type_counts,
        "person_source": person_source,
        "person_source_nodes": person_source_nodes,
        "readiness_counts": readiness_counts,
    }
    chart_specs = build_analysis_chart_specs(chart_data)
    for spec in chart_specs:
        (out / str(spec["filename"])).write_text(
            render_analysis_chart_page(case_title, include_private, spec),
            encoding="utf-8",
        )
    (out / "analysis_charts.html").write_text(
        render_analysis_dashboard(case_title, include_private, chart_specs),
        encoding="utf-8",
    )
    chart_page_lines = [f"- `{spec['filename']}` - {spec['title']}" for spec in chart_specs]
    index = [
        f"# Analysis charts: {case_title}",
        "",
        f"Scope: {'public and private/internal rows' if include_private else 'public-export rows only'}",
        "",
        "## Interactive HTML pages",
        "",
        "- `analysis_charts.html` - chart index",
        *chart_page_lines,
        "",
        "## Files",
        "",
        "- `analysis_charts.html`",
        "- `cluster_bridge_sankey.csv`",
        "- `cluster_bridge_sankey_nodes.csv`",
        "- `cluster_bridge_sankey_links.csv`",
        "- `layered_knowledge_graph_nodes.csv`",
        "- `layered_knowledge_graph_edges.csv`",
        "- `layered_knowledge_graph_v2_nodes.csv`",
        "- `layered_knowledge_graph_v2_edges.csv`",
        "- `layered_knowledge_graph_v2_layers.csv`",
        "- `evidence_confidence_heatmap.csv`",
        "- `evidence_confidence_heatmap_aggregate.csv`",
        "- `bridge_fragility.csv`",
        "- `bridge_fragility_segments.csv`",
        "- `claim_corroboration_matrix.csv`",
        "- `claim_corroboration_edges.csv`",
        "- `source_quality_dashboard.csv`",
        "- `sixdof_path_atlas.csv`",
        "- `sixdof_path_segments.csv`",
        "- `contradiction_boundary_overlay.csv`",
        "- `temporal_cluster_swimlanes.csv`",
        "- `relationship_type_treemap.csv`",
        "- `person_source_bipartite.csv`",
        "- `person_source_bipartite_nodes.csv`",
        "- `person_source_bipartite_edges.csv`",
        "- `public_narrative_readiness.csv`",
        "",
        "## Guardrails",
        "",
        "- These charts are evidence-navigation tools, not proof of a unified conspiracy.",
        "- Category bridges remain distinct from direct personal or institutional relationships.",
        "- Relationship classes separate documented succession, method diffusion, personnel bridges, narrative inheritance, contested overlap, and hypotheses requiring more sources.",
        "- Lead-only and boundary rows must remain visible when interpreting PROMIS/Maxwell, Barr/Epstein, and methodology-influence lanes.",
    ]
    (out / "analysis_charts.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"Exported analysis charts to {out}")


def export_manim(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    out = cdir / "exports" / "manim"
    include_private = args.include_private

    sources = public_rows(read_jsonl(record_path(args.case_dir, "sources")), include_private)
    entities = public_rows(read_jsonl(record_path(args.case_dir, "entities")), include_private)
    people = entities
    places = public_rows(read_jsonl(record_path(args.case_dir, "places")), include_private)
    claims = public_rows(read_jsonl(record_path(args.case_dir, "claims")), include_private)
    events = public_rows(read_jsonl(record_path(args.case_dir, "events")), include_private)
    event_links = public_rows(read_jsonl(record_path(args.case_dir, "event_links")), include_private)
    relationships = public_rows(read_jsonl(record_path(args.case_dir, "relationships")), include_private)

    write_csv(out / "sources.csv", sources, ["source_id", "title", "source_type", "publisher", "author", "date_published", "url", "archive_url", "reliability_grade"])
    write_csv(out / "people.csv", people, ["entity_id", "entity_type", "name", "display_name", "role_tags", "privacy_level", "public_export", "source_ids"])
    write_csv(out / "places.csv", places, ["place_id", "name", "place_type", "admin_area", "country", "lat", "lon", "precision", "privacy_sensitive", "public_export", "source_ids"])
    write_csv(out / "claims.csv", claims, ["claim_id", "claim", "claim_type", "status", "confidence", "source_ids", "contradicts", "public_export"])
    write_csv(out / "events.csv", events, ["event_id", "title", "event_type", "start_date", "end_date", "date_precision", "place_ids", "entity_ids", "claim_ids", "source_ids", "confidence", "status", "public_export"])
    write_csv(out / "event_links.csv", event_links, ["event_link_id", "entity_id", "event_id", "relation_type", "relationship_class", "basis", "claim_ids", "source_ids", "confidence", "status", "public_export"])
    write_csv(out / "relationships.csv", relationships, ["rel_id", "src_entity_id", "dst_entity_id", "relation_type", "relationship_class", "start_date", "end_date", "claim_ids", "source_ids", "confidence", "status", "public_export"])

    print(f"Exported Manim CSVs to {out}")


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        clean = [str(cell).replace("|", "\\|").replace("\n", " ") for cell in row]
        lines.append("| " + " | ".join(clean) + " |")
    return "\n".join(lines)


def report(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    sources = read_jsonl(record_path(args.case_dir, "sources"))
    claims = read_jsonl(record_path(args.case_dir, "claims"))
    events = read_jsonl(record_path(args.case_dir, "events"))
    event_links = read_jsonl(record_path(args.case_dir, "event_links"))
    entities = read_jsonl(record_path(args.case_dir, "entities"))
    rels = read_jsonl(record_path(args.case_dir, "relationships"))
    redactions = read_jsonl(record_path(args.case_dir, "redactions"))

    case_meta = json.loads((cdir / "case.json").read_text(encoding="utf-8"))
    by_status: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        by_status.setdefault(claim.get("status", "unknown"), []).append(claim)

    content = [f"# Evidence board: {case_meta.get('title', cdir.name)}", ""]
    content += ["## Source ledger", ""]
    content.append(md_table(
        ["ID", "Grade", "Type", "Title", "Publisher", "Date"],
        [[s.get("source_id", ""), s.get("reliability_grade", ""), s.get("source_type", ""), s.get("title", ""), s.get("publisher", ""), s.get("date_published", "")] for s in sources]
    ))
    content += ["", "## Entities", ""]
    content.append(md_table(
        ["ID", "Type", "Name", "Roles", "Privacy", "Public"],
        [[e.get("entity_id", ""), e.get("entity_type", ""), e.get("display_name") or e.get("name", ""), flatten(e.get("role_tags")), e.get("privacy_level", ""), str(e.get("public_export", True))] for e in entities]
    ))
    content += ["", "## Events", ""]
    content.append(md_table(
        ["ID", "Date", "Type", "Title", "Status", "Sources"],
        [[ev.get("event_id", ""), ev.get("start_date", ""), ev.get("event_type", ""), ev.get("title", ""), ev.get("status", ""), flatten(ev.get("source_ids"))] for ev in events]
    ))
    content += ["", "## Event links", ""]
    content.append(md_table(
        ["ID", "Entity", "Relation", "Event", "Basis", "Status", "Public"],
        [[link.get("event_link_id", ""), link.get("entity_id", ""), link.get("relation_type", ""), link.get("event_id", ""), link.get("basis", ""), link.get("status", ""), str(link.get("public_export", True))] for link in event_links]
    ))
    content += ["", "## Relationships", ""]
    content.append(md_table(
        ["ID", "Source", "Relation", "Target", "Status", "Sources"],
        [[r.get("rel_id", ""), r.get("src_entity_id", ""), r.get("relation_type", ""), r.get("dst_entity_id", ""), r.get("status", ""), flatten(r.get("source_ids"))] for r in rels]
    ))
    content += ["", "## Claims by status", ""]
    for status, rows in sorted(by_status.items()):
        content += [f"### {status}", ""]
        content.append(md_table(
            ["ID", "Confidence", "Claim", "Sources", "Public"],
            [[c.get("claim_id", ""), str(c.get("confidence", "")), c.get("claim", ""), flatten(c.get("source_ids")), str(c.get("public_export", True))] for c in rows]
        ))
        content.append("")
    content += ["## Redactions / public-output exclusions", ""]
    content.append(md_table(
        ["Record", "Field", "Reason", "Replacement"],
        [[r.get("record_id", ""), r.get("field", ""), r.get("reason", ""), r.get("public_replacement", "")] for r in redactions]
    ))

    out = cdir / "exports" / "evidence_board.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(content) + "\n", encoding="utf-8")
    print(f"Wrote evidence board: {out}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="True Crime / Cult-Origin Research CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init-case", help="Create a case workspace")
    p.add_argument("case_dir")
    p.add_argument("--title", default=None)
    p.add_argument("--scope", default=None)
    p.add_argument("--public-interest", default=None)
    p.set_defaults(func=init_case)

    p = sub.add_parser("add-source", help="Register a source manually")
    p.add_argument("case_dir")
    p.add_argument("--title", required=True)
    p.add_argument("--url", default=None)
    p.add_argument("--source-type", default="news_article")
    p.add_argument("--reliability-grade", default="C", choices=["A", "B", "C", "D", "X"])
    p.add_argument("--author", default=None)
    p.add_argument("--publisher", default=None)
    p.add_argument("--date-published", default=None)
    p.add_argument("--archive-url", default=None)
    p.add_argument("--notes", default="")
    p.add_argument("--no-public-export", action="store_true")
    p.set_defaults(func=add_source)

    p = sub.add_parser("ingest-url", help="Fetch URL, extract text, and register as a source")
    p.add_argument("case_dir")
    p.add_argument("url")
    p.add_argument("--title", default=None)
    p.add_argument("--source-type", default="news_article")
    p.add_argument("--reliability-grade", default="C", choices=["A", "B", "C", "D", "X"])
    p.add_argument("--author", default=None)
    p.add_argument("--publisher", default=None)
    p.add_argument("--date-published", default=None)
    p.add_argument("--archive-url", default=None)
    p.add_argument("--notes", default="")
    p.add_argument("--timeout", type=int, default=25)
    p.add_argument("--no-public-export", action="store_true")
    p.set_defaults(func=ingest_url)

    p = sub.add_parser("draft-extraction", help="Create a structured extraction JSON packet for a source")
    p.add_argument("case_dir")
    p.add_argument("source_id")
    p.add_argument("--excerpt-chars", type=int, default=6000)
    p.add_argument("--template", choices=sorted(EXTRACTION_TEMPLATE_FILES), default="generic", help="Extraction packet template.")
    p.set_defaults(func=draft_extraction)

    p = sub.add_parser("ner-suggest", help="Generate crude named-entity/date suggestions from source text")
    p.add_argument("case_dir")
    p.add_argument("--source-id", default=None)
    p.add_argument("--limit", type=int, default=80)
    p.set_defaults(func=ner_suggest)

    p = sub.add_parser("link-names", help="Link a list of names to existing events and co-mentions")
    p.add_argument("case_dir")
    p.add_argument("--name", action="append", default=[], help="Name to link. Use 'Primary|Alias|Alias' for aliases.")
    p.add_argument("--names-file", action="append", default=[], help="File with one name per line. Aliases use '|'.")
    p.set_defaults(func=link_names)

    p = sub.add_parser("import-extraction", help="Import a filled extraction JSON packet into JSONL records")
    p.add_argument("case_dir")
    p.add_argument("extraction_json")
    p.set_defaults(func=import_extraction)

    p = sub.add_parser("validate", help="Validate case records")
    p.add_argument("case_dir")
    p.set_defaults(func=validate)

    p = sub.add_parser("dedupe", help="Report duplicate candidate entities, sources, or claims")
    p.add_argument("case_dir")
    p.add_argument("--record-type", choices=["all", "entities", "sources", "claims"], default="all")
    p.add_argument("--min-key-chars", type=int, default=12, help="Minimum normalized key length for candidate matching.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/dedupe_report_<date>.json.")
    p.set_defaults(func=dedupe)

    p = sub.add_parser("preserve-source", help="Hash and report preservation metadata for an existing source")
    p.add_argument("case_dir")
    p.add_argument("source_id")
    p.add_argument("--archive-url", default=None, help="Archive URL to store on the source before preservation reporting.")
    p.add_argument("--content-type", default=None, help="Content type to store on the source before preservation reporting.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/source_preservation/<source_id>.json.")
    p.set_defaults(func=preserve_source)

    p = sub.add_parser("resolve-identities", help="Report candidate duplicate or ambiguous identity records without merging")
    p.add_argument("case_dir")
    p.add_argument("--min-key-chars", type=int, default=8, help="Minimum normalized name/alias length for identity candidate matching.")
    p.add_argument("--include-merged", action="store_true", help="Include entity rows already marked status=merged.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/identity_resolution_<date>.json.")
    p.set_defaults(func=resolve_identities)

    p = sub.add_parser("audit-contradictions", help="Report explicit and likely claim contradictions without mutating claims")
    p.add_argument("case_dir")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/claim_contradiction_audit.json.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in contradiction checks.")
    p.add_argument("--min-overlap", type=float, default=0.45, help="Minimum token overlap for likely contradiction pair checks.")
    p.add_argument("--fail-on-flags", action="store_true", help="Exit nonzero when any contradiction flag is found.")
    p.set_defaults(func=audit_contradictions)

    p = sub.add_parser("plan-public-records", help="Write a public-record source-lane plan for a subject")
    p.add_argument("case_dir")
    p.add_argument("--subject", required=True, help="Person, organization, place, event, or question subject to route.")
    p.add_argument("--question", default="", help="Optional research question or scope note.")
    p.add_argument("--lane", action="append", choices=sorted(PUBLIC_RECORD_LANES), default=[], help="Force one or more source lanes instead of keyword inference.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/public_records_plan_<subject>_<date>.json.")
    p.set_defaults(func=plan_public_records)

    p = sub.add_parser("index-transcript", help="Index timestamp and speaker-line candidates from a source text transcript")
    p.add_argument("case_dir")
    p.add_argument("source_id")
    p.add_argument("--max-segments", type=int, default=200, help="Maximum transcript segments to include in the candidate report.")
    p.add_argument("--include-private", action="store_true", help="Include a source marked public_export=false for internal review.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/transcript_index_<source_id>_<date>.json.")
    p.set_defaults(func=index_transcript)

    p = sub.add_parser("plan-open-records", help="Write a FOIA/open-records request plan for an agency and subject")
    p.add_argument("case_dir")
    p.add_argument("--subject", required=True, help="Subject of the request.")
    p.add_argument("--agency", required=True, help="Agency or public body receiving the request.")
    p.add_argument("--jurisdiction", default=None, help="Jurisdiction or office scope to include in the plan.")
    p.add_argument("--law", default=None, help="FOIA, sunshine, or open-records law to cite once confirmed.")
    p.add_argument("--date-range", default=None, help="Date range or temporal scope for responsive records.")
    p.add_argument("--record", action="append", default=[], help="Requested record category. Repeat for multiple categories.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to staging/candidates/open_records_plan_<subject>_<date>.json.")
    p.set_defaults(func=plan_open_records)

    p = sub.add_parser("review-narrative-readiness", help="Report public narrative readiness gaps across claims, events, and relationships")
    p.add_argument("case_dir")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in readiness checks.")
    p.add_argument("--require-spans", action="store_true", help="Flag claims/events without source_span_ids.")
    p.add_argument("--min-independent-sources", type=int, default=2, help="Independent source count expected for corroborated claims and allegations.")
    p.add_argument("--fail-on-blockers", action="store_true", help="Exit nonzero when blocker issues are found.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/narrative_readiness_review.json.")
    p.set_defaults(func=review_narrative_readiness)

    p = sub.add_parser("audit-privacy-redactions", help="Report privacy and redaction issues before public output")
    p.add_argument("case_dir")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in the scan.")
    p.add_argument("--require-redaction-log", action="store_true", help="Warn when no redaction records exist.")
    p.add_argument("--warn-only", action="store_true", help="Write the report but do not exit nonzero on issues.")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/privacy_redaction_audit.json.")
    p.set_defaults(func=audit_privacy_redactions)

    p = sub.add_parser("audit-public-export", help="Fail if public exports include unsafe or unsupported records")
    p.add_argument("case_dir")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/public_export_audit.json.")
    p.add_argument("--warn-only", action="store_true", help="Write the report but do not exit nonzero on issues.")
    p.set_defaults(func=audit_public_export)

    p = sub.add_parser("audit-source-independence", aliases=["source-independence"], help="Report source-chain, wire-copy, and press-release independence risks")
    p.add_argument("case_dir")
    p.add_argument("--out", "--output", dest="out", default=None, help="JSON report path. Defaults to exports/source_independence_report.json.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false in record support checks.")
    p.add_argument("--min-title-chars", type=int, default=16, help="Minimum normalized title length for repeated-copy checks.")
    p.add_argument("--fail-on-flags", action="store_true", help="Exit nonzero when any source-independence flag is found.")
    p.set_defaults(func=source_independence)

    p = sub.add_parser("export-manim", help="Export public-safe Manim-ready CSVs")
    p.add_argument("case_dir")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private analysis only.")
    p.set_defaults(func=export_manim)

    p = sub.add_parser("export-timeline", help="Export cross-case timeline and claim corroboration CSVs")
    p.add_argument("cases_root", help="A cases directory or a single case workspace")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to <kit>/data/exports/timeline for a cases root.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.set_defaults(func=export_timeline)

    p = sub.add_parser("export-case-charts", help="Export people-only graph and subcase timeline chart artifacts")
    p.add_argument("case_dir")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to data/cases/<case>/exports/charts.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.set_defaults(func=export_case_charts)

    p = sub.add_parser("export-analysis-charts", help="Export extended analysis chart CSVs and dashboard")
    p.add_argument("case_dir")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to data/cases/<case>/exports/analysis_charts.")
    p.add_argument("--clusters-dir", default=None, help="Cluster CSV directory. Defaults to data/cases/<case>/exports/clusters.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.set_defaults(func=export_analysis_charts)

    p = sub.add_parser("export-people-clusters", help="Run evidence-weighted Leiden clustering and graph-kernel/KDE analysis on people graph")
    p.add_argument("case_dir")
    p.add_argument("--out-dir", default=None, help="Output directory. Defaults to data/cases/<case>/exports/clusters.")
    p.add_argument("--charts-dir", default=None, help="People chart input/output directory. Defaults to data/cases/<case>/exports/charts.")
    p.add_argument("--include-private", action="store_true", help="Include records with public_export=false. Use for private review only.")
    p.add_argument("--resolution", type=float, default=1.0, help="Leiden resolution parameter.")
    p.add_argument("--seed", type=int, default=7, help="Leiden random seed.")
    p.add_argument("--sigma", type=float, default=None, help="Kernel bandwidth. Defaults to median finite graph distance.")
    p.set_defaults(func=export_people_clusters)

    p = sub.add_parser("report", help="Write Markdown evidence board")
    p.add_argument("case_dir")
    p.set_defaults(func=report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
