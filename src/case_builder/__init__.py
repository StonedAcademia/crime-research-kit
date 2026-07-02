"""Public API for the CRK case-builder agent app.

The package keeps CRK JSONL records as the canonical ledger. Import from this
module when callers need the stable app surface instead of internal graph,
agent, or tool modules.
"""

from __future__ import annotations

from .app.service import run_case_builder
from .models.state import CaseBuilderState, new_run_id

__all__ = ["CaseBuilderState", "new_run_id", "run_case_builder"]
