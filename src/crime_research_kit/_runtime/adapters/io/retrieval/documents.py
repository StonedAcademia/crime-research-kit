"""Convert canonical CRK records and source text into retrieval documents."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from crime_research_kit._runtime.core.casefile import case_id, case_path, load_records, resolve_case_path
from .policy import compact_metadata, public_allowed


@dataclass(frozen=True)
class EvidenceDocument:
    doc_id: str
    text: str
    metadata: dict[str, str | int | float | bool | None]

    def to_llama_document(self):
        try:
            from llama_index.core import Document  # type: ignore
        except ImportError as exc:
            raise RuntimeError("LlamaIndex is not installed. Install the local retrieval extra.") from exc
        return Document(id_=self.doc_id, text=self.text, metadata=self.metadata)


def build_evidence_documents(case_dir: str | Path, *, include_private: bool = False) -> list[EvidenceDocument]:
    cid = case_id(case_dir)
    sources = {row.get("source_id"): row for row in load_records(case_dir, "sources")}
    documents: list[EvidenceDocument] = []
    for source in sources.values():
        if source and public_allowed(source, include_private=include_private):
            documents.extend(_source_text_documents(case_dir, cid, source))
            documents.append(_source_record_document(cid, source))
    for record_name in ["claims", "events", "relationships", "event_links", "quotes", "source_spans"]:
        for row in load_records(case_dir, record_name):
            if public_allowed(row, include_private=include_private):
                documents.append(_record_document(cid, record_name, row, sources))
    return [doc for doc in documents if doc.text.strip()]


def to_llama_documents(documents: list[EvidenceDocument]) -> list[Any]:
    return [document.to_llama_document() for document in documents]


def _source_record_document(case_id_value: str, source: dict[str, Any]) -> EvidenceDocument:
    text = "\n".join(
        part
        for part in [
            f"Source title: {source.get('title')}",
            f"Publisher: {source.get('publisher')}",
            f"Date published: {source.get('date_published')}",
            f"Notes: {source.get('notes')}",
        ]
        if part and not part.endswith("None")
    )
    doc_id = f"{case_id_value}:source:{source.get('source_id')}"
    return EvidenceDocument(doc_id=doc_id, text=text, metadata=_base_metadata(case_id_value, "source", source.get("source_id"), source))


def _record_document(
    case_id_value: str,
    record_name: str,
    row: dict[str, Any],
    sources: dict[str, dict[str, Any]],
) -> EvidenceDocument:
    record_id = _record_id(record_name, row)
    source_ids = row.get("source_ids") or ([row.get("source_id")] if row.get("source_id") else [])
    source = sources.get(source_ids[0]) if source_ids else None
    text = _record_text(record_name, row)
    metadata = _base_metadata(case_id_value, record_name, record_id, row)
    metadata.update(
        {
            "source_ids": source_ids,
            "source_id": source_ids[0] if source_ids else None,
            "reliability_grade": source.get("reliability_grade") if source else None,
            "independence_group": source.get("independence_group") if source else None,
        }
    )
    doc_id = f"{case_id_value}:{record_name}:{record_id}"
    return EvidenceDocument(doc_id=doc_id, text=text, metadata=compact_metadata(metadata))


def _source_text_documents(case_dir: str | Path, case_id_value: str, source: dict[str, Any]) -> list[EvidenceDocument]:
    path = resolve_case_path(case_dir, source.get("text_path"))
    if not path or not path.exists():
        return []
    paragraphs = [part.strip() for part in path.read_text(encoding="utf-8", errors="replace").split("\n\n") if part.strip()]
    documents: list[EvidenceDocument] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        doc_id = f"{source.get('source_id')}:p{index}"
        metadata = _base_metadata(case_id_value, "source_text", doc_id, source)
        metadata.update({"source_id": source.get("source_id"), "paragraph": index, "text_sha256": _sha256(paragraph)})
        doc_id = f"{case_id_value}:source_text:{source.get('source_id')}:p{index}"
        documents.append(EvidenceDocument(doc_id=doc_id, text=paragraph, metadata=compact_metadata(metadata)))
    return documents


def _record_text(record_name: str, row: dict[str, Any]) -> str:
    if record_name == "claims":
        return str(row.get("claim") or "")
    if record_name == "events":
        return f"{row.get('title', '')}\n{row.get('notes', '')}".strip()
    if record_name == "relationships":
        return f"{row.get('src_entity_id')} {row.get('relation_type')} {row.get('dst_entity_id')}\n{row.get('notes', '')}".strip()
    if record_name == "event_links":
        return f"{row.get('entity_id')} {row.get('relation_type')} {row.get('event_id')}\n{row.get('notes', '')}".strip()
    if record_name == "quotes":
        return str(row.get("exact_quote") or "")
    if record_name == "source_spans":
        return str(row.get("exact_text") or row.get("summary") or row.get("notes") or "")
    return str(row)


def _record_id(record_name: str, row: dict[str, Any]) -> str | None:
    return row.get(
        {
            "claims": "claim_id",
            "events": "event_id",
            "relationships": "rel_id",
            "event_links": "event_link_id",
            "quotes": "quote_id",
            "source_spans": "source_span_id",
        }[record_name]
    )


def _base_metadata(case_id_value: str, record_type: str, record_id: str | None, row: dict[str, Any]) -> dict[str, Any]:
    return compact_metadata(
        {
            "case_id": case_id_value,
            "record_type": record_type,
            "record_id": record_id,
            "public_export": row.get("public_export", True),
            "status": row.get("status"),
            "confidence": row.get("confidence"),
            "privacy_review": row.get("privacy_review"),
            "privacy_level": row.get("privacy_level"),
            "source_span_ids": row.get("source_span_ids"),
        }
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
