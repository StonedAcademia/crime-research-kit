"""Workflow-memory builders for case management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..casefile import case_path, load_records, log_action
from .base import MemoryEntry, MemoryProvider
from .providers.local import LocalMemoryProvider
from .providers.mem0_provider import Mem0LocalProvider


def remember_research_actions(
    case_dir: str | Path,
    *,
    provider: str = "local",
    limit: int = 50,
    **provider_options: Any,
) -> dict[str, Any]:
    memory = _provider(case_dir, provider=provider, provider_options=provider_options)
    actions = load_records(case_dir, "research_actions")[-limit:]
    results = []
    for action in actions:
        entry = MemoryEntry(
            text=_action_text(action),
            metadata={"action": action.get("action"), "timestamp": action.get("timestamp")},
        )
        results.append(memory.add(entry))
    report = {
        "provider": provider,
        "remembered_count": len(results),
        "notes": "Workflow memory is operational context only, not evidence.",
        "results": results,
    }
    out = case_path(case_dir) / "staging" / "memory" / "remember_research_actions_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log_action(case_dir, "remember_research_actions", {"provider": provider, "count": len(results), "report": str(out)})
    return {"provider": provider, "remembered_count": len(results), "report": str(out)}


def _provider(case_dir: str | Path, *, provider: str, provider_options: dict[str, Any]) -> MemoryProvider:
    if provider == "local":
        return LocalMemoryProvider(case_dir)
    if provider == "mem0":
        return Mem0LocalProvider(str(case_dir), **provider_options)
    raise ValueError(f"Unknown memory provider: {provider}")


def _action_text(action: dict[str, Any]) -> str:
    details = action.get("details") or {}
    compact = json.dumps(details, ensure_ascii=False, sort_keys=True)
    return f"CRK workflow action {action.get('action')} at {action.get('timestamp')}: {compact}"
