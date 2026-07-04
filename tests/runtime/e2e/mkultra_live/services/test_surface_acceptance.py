from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import KIT_ROOT
from tests.runtime.e2e.mkultra_live.source_seed import PRIMARY_SOURCE_ID

pytest.importorskip("mcp")


def test_cli_mcp_and_agent_skill_surfaces_share_the_same_case_contract(
    populated_mkultra_case: Path,
    tmp_path: Path,
    ledger_runner,
    ledger_command,
    crkit_runner,
):
    cli = _cli_surface(populated_mkultra_case, ledger_runner, ledger_command, crkit_runner)
    mcp = asyncio.run(_mcp_surface(populated_mkultra_case))
    agent = _agent_skill_surface(populated_mkultra_case, tmp_path, cli, mcp)

    transcript = {"case": populated_mkultra_case.name, "cli": cli, "mcp": mcp, "agent_skill": agent}
    out = populated_mkultra_case / "staging" / "candidates" / "surface_acceptance_transcript.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(transcript, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert out.exists()
    assert cli["case_id"] == "mkultra_live_e2e_case"
    assert mcp["case_id"] == cli["case_id"]
    assert mcp["import_without_confirm_refused"] is True
    assert agent["candidate_only"] is True
    assert agent["evidence_claim"] is False
    assert agent["requires_human_import_approval"] is True
    assert agent["uses_source_ids"] is True


def _cli_surface(case_dir: Path, ledger_runner, ledger_command, crkit_runner) -> dict[str, Any]:
    validate = ledger_command(ledger_runner, "validate", ["validate", str(case_dir)]).to_dict()
    readiness = ledger_command(
        ledger_runner,
        "review_narrative_readiness",
        ["review-narrative-readiness", str(case_dir)],
    ).to_dict()
    plan = crkit_runner(
        "plan",
        str(case_dir),
        "--title",
        "MKULTRA Surface Acceptance",
        "--subject",
        "Operate a source-backed MKULTRA case through CLI, MCP, and an agent skill.",
        "--source-id",
        PRIMARY_SOURCE_ID,
        "--runner",
        "sequential",
    )
    assert validate["ok"] is True
    assert readiness["ok"] is True
    planned = " ".join(" ".join(command) for command in plan["planned_commands"])
    assert "draft-extraction" in planned
    return {
        "case_id": "mkultra_live_e2e_case",
        "validate": validate["ok"],
        "readiness_report": readiness["data"].get("path"),
        "plan_status": plan["status"],
        "planned_commands": plan["planned_commands"],
        "review_required": plan.get("review_required", True),
    }


async def _mcp_surface(case_dir: Path) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "crime_research_kit._runtime.adapters.interfaces.mcp.server"],
        env={
            **os.environ,
            "CRK_CASES_ROOT": str(case_dir.parent),
            "PYTHONPATH": str(KIT_ROOT / "src"),
        },
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = {tool.name for tool in (await session.list_tools()).tools}
            prompts = {prompt.name for prompt in (await session.list_prompts()).prompts}
            prompt = await session.get_prompt("process_source", {})
            reference = await session.read_resource("crk://references/controlled_vocabularies")
            case_info = _payload(await session.call_tool("case_info", {"case": case_dir.name}))
            text = _payload(await session.call_tool("get_source_text", {"case": case_dir.name, "source_id": PRIMARY_SOURCE_ID, "max_chars": 800}))
            drafted = _payload(await session.call_tool("draft_extraction", {"case": case_dir.name, "source_id": PRIMARY_SOURCE_ID, "template": "generic"}))
            saved = _payload(
                await session.call_tool(
                    "save_extraction_packet",
                    {
                        "case": case_dir.name,
                        "packet_name": "surface_mcp_candidate.json",
                        "packet": {"source_id": PRIMARY_SOURCE_ID, "claims": []},
                    },
                )
            )
            refused = _payload(await session.call_tool("import_extraction", {"case": case_dir.name, "packet": "surface_mcp_candidate.json"}))

    assert {"case_info", "get_source_text", "draft_extraction", "save_extraction_packet", "import_extraction"} <= tools
    assert {"process_source", "review_packet", "public_readiness"} <= prompts
    assert "Do NOT import" in prompt.messages[0].content.text
    assert "Controlled vocabularies" in reference.contents[0].text
    assert text["ok"] is True and "National Security Archive" in text["data"]["text"]
    assert drafted["ok"] is True
    assert saved["ok"] is True
    assert refused["ok"] is False
    return {
        "case_id": case_info["data"]["case_id"],
        "tools_checked": sorted(tools),
        "prompts_checked": sorted(prompts),
        "reference_checked": "controlled_vocabularies",
        "import_without_confirm_refused": any("confirm" in error for error in refused["errors"]),
    }


def _agent_skill_surface(case_dir: Path, tmp_path: Path, cli: dict[str, Any], mcp: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get("CRK_LIVE_CODEX") != "1":
        pytest.skip("set CRK_LIVE_CODEX=1 to run the agent/skill acceptance leg")
    codex_bin = os.environ.get("CRK_CODEX_BIN", "codex")
    if shutil.which(codex_bin) is None:
        pytest.skip(f"Codex executable not found: {codex_bin}")

    schema = tmp_path / "surface_agent.schema.json"
    schema.write_text(json.dumps(_agent_schema(), indent=2), encoding="utf-8")
    output = tmp_path / "surface_agent.json"
    prompt = _agent_prompt(case_dir.name, cli, mcp)
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
    return json.loads(output.read_text(encoding="utf-8"))


def _agent_prompt(case_name: str, cli: dict[str, Any], mcp: dict[str, Any]) -> str:
    summary = json.dumps({"cli": cli, "mcp": {k: mcp[k] for k in ("case_id", "import_without_confirm_refused")}}, sort_keys=True)
    return (
        "Use the truecrime-cult-research skill. Do not run commands and do not edit files. "
        "You are reviewing a CRK surface-acceptance transcript for case "
        f"{case_name}. Return only the requested JSON. Treat this as candidate review material, not evidence. "
        "Set candidate_only=true, evidence_claim=false, uses_source_ids=true, and "
        "requires_human_import_approval=true if the CLI/MCP transcript preserves those boundaries. "
        f"Transcript summary: {summary}"
    )


def _agent_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["surface", "skill", "candidate_only", "evidence_claim", "uses_source_ids", "requires_human_import_approval", "summary"],
        "properties": {
            "surface": {"type": "string", "enum": ["agent_skill"]},
            "skill": {"type": "string"},
            "candidate_only": {"type": "boolean"},
            "evidence_claim": {"type": "boolean"},
            "uses_source_ids": {"type": "boolean"},
            "requires_human_import_approval": {"type": "boolean"},
            "summary": {"type": "string"},
        },
        "additionalProperties": False,
    }


def _payload(result) -> dict[str, Any]:
    return json.loads(result.content[0].text)
