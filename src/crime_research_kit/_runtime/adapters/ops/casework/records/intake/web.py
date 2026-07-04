"""URL ingestion and HTML text extraction."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import urllib.parse
from typing import Any

from crime_research_kit._runtime.adapters.io.acquisition.http import fetch_url_or_archive
from crime_research_kit._runtime.core.casefile import case_path, ensure_case, file_sha256, log_action, now_utc, slugify

from ..workspace import add_source_record


def safe_filename_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    domain = slugify(parsed.netloc)
    path = slugify(parsed.path or "index")[:48]
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"{domain}_{path}_{digest}"


def extract_html_text(raw: bytes, content_type: str) -> tuple[str, dict[str, Any]]:
    charset = "utf-8"
    match = re.search(r"charset=([^;]+)", content_type or "", flags=re.I)
    if match:
        charset = match.group(1).strip()
    try:
        html_text = raw.decode(charset, errors="replace")
    except LookupError:
        html_text = raw.decode("utf-8", errors="replace")

    meta: dict[str, Any] = {"title": None, "author": None, "date_published": None}
    extracted = _extract_with_trafilatura(html_text, meta)
    if extracted:
        return extracted, meta
    extracted = _extract_with_bs4(html_text, meta)
    if extracted:
        return extracted, meta
    return _fallback_extract(html_text, meta)


def ingest_url(args: argparse.Namespace) -> None:
    ensure_case(args.case_dir)
    cdir = case_path(args.case_dir)
    raw_path = cdir / "raw" / "downloads" / f"{safe_filename_from_url(args.url)}.html"
    text_path = cdir / "raw" / "sources" / f"{safe_filename_from_url(args.url)}.txt"
    try:
        content_type, raw, headers, served_url = fetch_url_or_archive(args.url, timeout=args.timeout)
    except Exception as exc:
        raise SystemExit(f"Failed to fetch {args.url}: {exc}") from exc
    archive_url = args.archive_url or (served_url if served_url != args.url else None)

    raw_path.write_bytes(raw)
    text, meta = extract_html_text(raw, content_type)
    text_path.write_text(text, encoding="utf-8")
    raw_sha256 = file_sha256(raw_path)
    text_sha256 = file_sha256(text_path)
    publisher = args.publisher or urllib.parse.urlparse(args.url).netloc
    record = add_source_record(
        args.case_dir,
        title=args.title or meta.get("title") or args.url,
        source_type=args.source_type,
        reliability_grade=args.reliability_grade,
        url=args.url,
        author=args.author or meta.get("author"),
        publisher=publisher,
        date_published=args.date_published or meta.get("date_published"),
        archive_url=archive_url,
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
            "source_id": record["source_id"],
            "url": args.url,
            "headers": headers,
            "raw_sha256": raw_sha256,
            "text_sha256": text_sha256,
            "content_type": content_type,
        },
    )
    print(f"Ingested {args.url}")
    print(json.dumps(record, indent=2, ensure_ascii=False))


def _extract_with_trafilatura(html_text: str, meta: dict[str, Any]) -> str | None:
    try:
        import trafilatura  # type: ignore

        extracted = trafilatura.extract(html_text, include_comments=False, include_tables=True)
        meta_obj = trafilatura.extract_metadata(html_text)
        if meta_obj:
            meta["title"] = getattr(meta_obj, "title", None)
            meta["author"] = getattr(meta_obj, "author", None)
            meta["date_published"] = getattr(meta_obj, "date", None)
        return extracted.strip() if extracted else None
    except Exception:
        return None


def _extract_with_bs4(html_text: str, meta: dict[str, Any]) -> str | None:
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
        text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n"))
        return re.sub(r"[ \t]{2,}", " ", text).strip()
    except Exception:
        return None


def _fallback_extract(html_text: str, meta: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.I | re.S)
    if title_match:
        meta["title"] = html.unescape(re.sub(r"\s+", " ", title_match.group(1)).strip())
    text = re.sub(r"<script\b.*?</script>", "", html_text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.I | re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip(), meta
