"""Public API for the CRK case-builder agent app.

The package keeps CRK JSONL records as the canonical ledger. Import from this
module when callers need the stable app surface instead of internal graph,
agent, or tool modules.
"""

from __future__ import annotations

from .core import config
from .core.models.state import CaseBuilderState, new_run_id
from .pipeline.app.service import run_case_builder

__all__ = ["CaseBuilderState", "config", "new_run_id", "run_case_builder"]
