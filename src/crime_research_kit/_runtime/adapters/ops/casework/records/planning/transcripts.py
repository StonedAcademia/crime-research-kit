"""Transcript locator indexing command."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

from crime_research_kit._runtime.core.casefile import case_path, ensure_case, log_action, now_utc, resolve_case_path, stable_id, today, write_json

from crime_research_kit._runtime.adapters.ops.evidence.ledger.records import report_out_path

from ..workspace import find_source

TIMESTAMP_RE = re.compile(r"(?<!\d)(?:(?P<hours>\d{1,2}):)?(?P<minutes>\d{1,2}):(?P<seconds>\d{2})(?:[.,]\d{1,3})?(?!\d)")
SPEAKER_LINE_RE = re.compile(r"^\s*(?P<speaker>[A-Z][A-Za-z0-9 .'\-]{1,48}):\s*(?P<text>.+?)\s*$")


def timestamp_to_seconds(match: re.Match[str]) -> int:
    return int(match.group("hours") or 0) * 3600 + int(match.group("minutes") or 0) * 60 + int(match.group("seconds") or 0)


def transcript_segment_from_line(source_id: str, line: str, line_no: int) -> dict[str, Any] | None:
    timestamp_match = TIMESTAMP_RE.search(line)
    speaker_match = SPEAKER_LINE_RE.match(line)
    speaker = speaker_match.group("speaker").strip() if speaker_match else None
    text = speaker_match.group("text").strip() if speaker_match else line.strip()
    if timestamp_match:
        text = (line[: timestamp_match.start()] + line[timestamp_match.end() :]).strip(" -\t")
        speaker_after_timestamp = SPEAKER_LINE_RE.match(text)
        if speaker_after_timestamp:
            speaker = speaker_after_timestamp.group("speaker").strip()
            text = speaker_after_timestamp.group("text").strip()
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
            "locator": {"line": line_no, "timestamp": timestamp_match.group(0) if timestamp_match else None, "speaker": speaker},
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
    text_path = resolve_case_path(args.case_dir, str(text_rel))
    if not text_path or not text_path.exists():
        raise SystemExit(f"Source text_path does not exist: {text_rel}")
    segments = _segments(args.source_id, text_path.read_text(encoding="utf-8", errors="replace").splitlines(), args.max_segments)
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
    log_action(args.case_dir, "index_transcript", {"source_id": args.source_id, "segment_count": len(segments), "speakers": speakers, "report": str(out), "include_private": getattr(args, "include_private", False)})
    print(json.dumps({"segment_count": len(segments), "speakers": speakers, "report": str(out)}, indent=2, ensure_ascii=False))


def _segments(source_id: str, lines: list[str], max_segments: int) -> list[dict[str, Any]]:
    segments = []
    for line_no, line in enumerate(lines, start=1):
        segment = transcript_segment_from_line(source_id, line, line_no)
        if segment:
            segments.append(segment)
        if len(segments) >= max_segments:
            break
    return segments
