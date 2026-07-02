"""Workflow prompts so MCP hosts receive CRK guidance in-band."""

from __future__ import annotations

from typing import Any

from case_builder.adapters.interfaces.mcp.context import ServerContext

START_CASE = """Start a CRK research case. Steps:
1. Confirm the case slug and title with the user, then check list_cases / case_info.
2. Plan source lanes with plan_public_records for the seed subject.
3. Capture public sources with ingest_url or add_source; grade reliability honestly.
Safety: public-interest sources only; no guilt/membership inference from proximity;
private-person details stay private by default; every claim needs a traceable source.
"""

PROCESS_SOURCE = """Process one registered source end to end:
1. parse_source (or ocr_source for scanned PDFs) to get text.
2. draft_extraction to create the packet template; read the source text with get_source_text.
3. Fill the packet: only what the source itself states, with source_ids on every record,
   assertion_type preserved, neutral role labels, status unverified.
4. save_extraction_packet, then ask the user to review it. Do NOT import it yourself.
"""

REVIEW_PACKET = """Help the user review a staged extraction packet before canonical import:
1. list_staged_packets, then read the packet resource and its source text side by side.
2. Check every record: correct source_ids, no invented facts, neutral labels, privacy flags.
3. Only after the user explicitly approves in conversation, call import_extraction with
   confirm=true. Never set confirm=true on your own initiative.
"""

PUBLIC_READINESS = """Assess public-output readiness:
1. run_report and get_records to survey claims, statuses, and confidence.
2. Check contradiction, source-independence, and privacy posture; wire stories that share
   an independence_group are one source, not corroboration.
3. Summarize blockers for the user. Exports default public-safe; include_private is for
   internal review only and its output must not be published.
"""


def register(mcp: Any, ctx: ServerContext) -> None:
    @mcp.prompt()
    def start_case() -> str:
        """Start a new CRK case with safe source planning."""
        return START_CASE

    @mcp.prompt()
    def process_source() -> str:
        """Parse, draft, and fill one source's extraction packet."""
        return PROCESS_SOURCE

    @mcp.prompt()
    def review_packet() -> str:
        """Review a staged packet and gate the canonical import."""
        return REVIEW_PACKET

    @mcp.prompt()
    def public_readiness() -> str:
        """Audit public-output readiness and privacy posture."""
        return PUBLIC_READINESS
