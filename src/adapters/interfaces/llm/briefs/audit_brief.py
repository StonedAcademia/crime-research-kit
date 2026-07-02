"""Reviewer brief over deterministic audit outputs. Flags, never decides."""

from __future__ import annotations

import datetime as dt
from typing import Any, Sequence

from adapters.ops.safety.policy import ensure_staged_write
from core.casefile import ensure_case, log_action

PROMPT_TEMPLATE = """Summarize these public-readiness audit outputs for a human reviewer.
List concrete blockers and open questions as short bullet points. Do NOT decide
whether the case is ready and do NOT soften findings.

{audits}
"""

HEADER = (
    "# Readiness review brief\n\n"
    "This brief flags issues for a human reviewer. It is not evidence and it\n"
    "does not decide readiness; the deterministic audit outputs remain the\n"
    "source of record.\n\n"
)


def write_readiness_brief(
    model: Any,
    case_dir: str,
    audit_results: Sequence[dict[str, Any]],
) -> str:
    case = ensure_case(case_dir)
    audits = "\n\n".join(
        f"## {item.get('name')}\n{item.get('stdout') or '(no output)'}"
        for item in audit_results
    )
    reply = model.invoke(PROMPT_TEMPLATE.format(audits=audits))
    body = str(getattr(reply, "content", reply)).strip()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    target = case / "staging" / "candidates" / f"readiness_brief_{stamp}.md"
    ensure_staged_write(case, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(HEADER + body + "\n", encoding="utf-8")
    log_action(
        case,
        "readiness_brief",
        {"path": str(target.name), "audits": [str(item.get("name")) for item in audit_results]},
    )
    return str(target)
