"""Server context: rooted case resolution so tools never touch arbitrary paths."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adapters.ops.runner import CrkRunner, default_repo_root
from core.config import CrkSettings
from crime_research_kit.sdk import CrkClient, CrkContext
from crime_research_kit.sdk.results import OperationResult

CASE_SLUG_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,80}")


@dataclass
class ServerContext:
    repo_root: Path
    cases_root: Path
    runner: CrkRunner
    settings: CrkSettings
    skill_root: Path | None = None


def default_context() -> ServerContext:
    repo_root = default_repo_root()
    cases_root = Path(os.environ.get("CRK_CASES_ROOT") or repo_root / "data" / "cases")
    return ServerContext(
        repo_root=repo_root,
        cases_root=cases_root,
        runner=CrkRunner(repo_root=repo_root, dry_run=False),
        settings=CrkSettings(),
        skill_root=default_skill_root(repo_root),
    )


def default_skill_root(repo_root: Path) -> Path:
    configured = os.environ.get("CRK_SKILL_ROOT")
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


def sdk_client(ctx: ServerContext) -> CrkClient:
    return CrkClient(
        CrkContext(
            repo_root=ctx.repo_root,
            cases_root=ctx.cases_root,
            dry_run=ctx.runner.dry_run,
            settings=_settings_dict(ctx.settings),
        )
    )


def sdk_case(ctx: ServerContext, case: str):
    return sdk_client(ctx).case(resolve_case(ctx, case))


def mcp_result(result: OperationResult) -> dict[str, Any]:
    payload = result.to_dict()
    diagnostics = payload.get("diagnostics") or {}
    for key in ("command", "dry_run", "skipped", "returncode", "stdout", "stderr"):
        if key in diagnostics:
            payload[key] = diagnostics[key]
    if payload.get("errors"):
        payload["errors"] = [_error_message(error) for error in payload["errors"]]
    if payload.get("warnings"):
        payload["warnings"] = [_warning_message(warning) for warning in payload["warnings"]]
    return payload


def _settings_dict(settings: CrkSettings) -> dict[str, Any]:
    return {
        "model_spec": settings.model_spec,
        "searxng_url": settings.searxng_url,
        "qdrant_url": settings.qdrant_url,
        "qdrant_host": settings.qdrant_host,
        "qdrant_port": settings.qdrant_port,
        "embed_model": settings.embed_model,
        "mem0_llm_provider": settings.mem0_llm_provider,
        "mem0_llm_model": settings.mem0_llm_model,
        "embedder_provider": settings.embedder_provider,
    }


def _error_message(error: Any) -> str:
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(error)


def _warning_message(warning: Any) -> str:
    if isinstance(warning, dict):
        return str(warning.get("message") or warning)
    return str(warning)
