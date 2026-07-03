from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.helpers import KIT_ROOT


def test_ollama_writes_candidate_readiness_brief(populated_mkultra_case: Path):
    from tests.helpers import live_service, requires_extra

    requires_extra("langchain")
    live_service(os.environ.get("OLLAMA_HOST"), "/api/tags")

    from crime_research_kit._runtime.adapters.interfaces.llm.briefs.audit_brief import write_readiness_brief
    from crime_research_kit._runtime.adapters.interfaces.llm.provider import get_chat_model

    model = get_chat_model(os.environ.get("CRK_MODEL", "ollama:llama3.1"))
    path = Path(
        write_readiness_brief(
            model,
            str(populated_mkultra_case),
            [
                {"name": "audit_public_export", "stdout": "0 blockers for the deterministic E2E packet."},
                {"name": "review_narrative_readiness", "stdout": "Span review remains open before public narration."},
            ],
        )
    )

    text = path.read_text(encoding="utf-8")
    assert path.exists()
    assert "not evidence" in text
    assert "does not decide readiness" in text


def test_codex_exec_live_host_smoke_returns_candidate_brief(populated_mkultra_case: Path, tmp_path: Path):
    if os.environ.get("CRK_LIVE_CODEX") != "1":
        pytest.skip("set CRK_LIVE_CODEX=1 to run the direct Codex-service smoke")

    codex_bin = os.environ.get("CRK_CODEX_BIN", "codex")
    if shutil.which(codex_bin) is None:
        pytest.skip(f"Codex executable not found: {codex_bin}")

    schema = tmp_path / "codex_brief.schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["candidate_only", "evidence_claim", "safety_notes", "next_step"],
                "properties": {
                    "candidate_only": {"type": "boolean"},
                    "evidence_claim": {"type": "boolean"},
                    "safety_notes": {"type": "array", "items": {"type": "string"}},
                    "next_step": {"type": "string"},
                },
                "additionalProperties": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "codex_brief.json"
    prompt = (
        "You are a CRK E2E smoke reviewer. Do not run commands and do not edit files. "
        "Based only on this source-backed test summary, return the requested JSON object. "
        "Summary: a temporary MKULTRA course case contains a reviewed staged packet from "
        "S_NSARCHIVE_MKULTRA_CONTEXT_2024. AI output is candidate review material only, "
        "not evidence. State that canonical claims still require source-span review."
    )
    completed = subprocess.run(
        [
            codex_bin,
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--cd",
            str(KIT_ROOT),
            "--output-schema",
            str(schema),
            "-o",
            str(output),
            prompt,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=240,
    )
    combined = f"{completed.stdout}\n{completed.stderr}".casefold()
    if completed.returncode != 0 and any(token in combined for token in ("login", "auth", "authenticated")):
        pytest.skip("Codex service is not authenticated for this host")
    assert completed.returncode == 0, completed.stderr or completed.stdout

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["candidate_only"] is True
    assert payload["evidence_claim"] is False
    assert payload["safety_notes"]
