"""Server context: rooted case resolution so tools never touch arbitrary paths."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..ops.runner import TrcrRunner, default_repo_root

CASE_SLUG_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,80}")


@dataclass
class ServerContext:
    repo_root: Path
    cases_root: Path
    runner: TrcrRunner
    skill_root: Path | None = None


def default_context() -> ServerContext:
    repo_root = default_repo_root()
    cases_root = Path(os.environ.get("TRCR_CASES_ROOT") or repo_root / "data" / "cases")
    return ServerContext(
        repo_root=repo_root,
        cases_root=cases_root,
        runner=TrcrRunner(repo_root=repo_root, dry_run=False),
        skill_root=default_skill_root(repo_root),
    )


def default_skill_root(repo_root: Path) -> Path:
    configured = os.environ.get("TRCR_SKILL_ROOT")
    if configured:
        return Path(configured)
    candidates = [
        repo_root / ".agents" / "skills" / "truecrime-cult-research",
        repo_root.parent / ".agents" / "skills" / "truecrime-cult-research",
    ]
    for candidate in candidates:
        if (candidate / "SKILL.md").exists():
            return candidate
    return candidates[0]


def resolve_case(ctx: ServerContext, case: str) -> str:
    if not case or not CASE_SLUG_RE.fullmatch(case):
        raise ValueError(f"Invalid case slug: {case!r}. Use letters, digits, '-' and '_' only.")
    root = ctx.cases_root.resolve()
    path = (root / case).resolve()
    if path.parent != root:
        raise ValueError(f"Case path escapes cases root: {case!r}")
    if not (path / "case.json").exists():
        raise ValueError(f"Unknown case: {case}. Known cases: {', '.join(list_case_slugs(ctx)) or 'none'}")
    return str(path)


def list_case_slugs(ctx: ServerContext) -> list[str]:
    if not ctx.cases_root.exists():
        return []
    root = ctx.cases_root.resolve()
    names = []
    for entry in ctx.cases_root.iterdir():
        resolved = entry.resolve()
        if resolved.parent == root and (resolved / "case.json").exists():
            names.append(entry.name)
    return sorted(names)


def error_dict(message: str) -> dict[str, Any]:
    return {"ok": False, "errors": [message]}
