from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from tests.helpers import KIT_ROOT

pytest.importorskip("mcp")


def _payload(result) -> dict:
    return json.loads(result.content[0].text)


def test_mcp_stdio_tools_operate_temp_mkultra_case(populated_mkultra_case: Path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def scenario():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "crime_research_kit._runtime.adapters.interfaces.mcp.server"],
            env={
                **os.environ,
                "CRK_CASES_ROOT": str(populated_mkultra_case.parent),
                "PYTHONPATH": str(KIT_ROOT / "src"),
            },
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert {"case_info", "get_source_text", "draft_extraction", "save_extraction_packet", "import_extraction"} <= names

                info = _payload(await session.call_tool("case_info", {"case": populated_mkultra_case.name}))
                assert info["ok"] is True
                assert info["data"]["case_id"] == "mkultra_live_e2e_case"

                text = _payload(
                    await session.call_tool(
                        "get_source_text",
                        {
                            "case": populated_mkultra_case.name,
                            "source_id": "S_NSARCHIVE_MKULTRA_CONTEXT_2024",
                            "max_chars": 800,
                        },
                    )
                )
                assert text["ok"] is True
                assert "National Security Archive" in text["data"]["text"]

                drafted = _payload(
                    await session.call_tool(
                        "draft_extraction",
                        {
                            "case": populated_mkultra_case.name,
                            "source_id": "S_NSARCHIVE_MKULTRA_CONTEXT_2024",
                            "template": "generic",
                        },
                    )
                )
                assert drafted["ok"] is True

                saved = _payload(
                    await session.call_tool(
                        "save_extraction_packet",
                        {
                            "case": populated_mkultra_case.name,
                            "packet_name": "mcp_candidate.json",
                            "packet": {"source_id": "S_NSARCHIVE_MKULTRA_CONTEXT_2024", "claims": []},
                        },
                    )
                )
                assert saved["ok"] is True

                refused = _payload(
                    await session.call_tool(
                        "import_extraction",
                        {"case": populated_mkultra_case.name, "packet": "mcp_candidate.json"},
                    )
                )
                assert refused["ok"] is False
                assert any("confirm" in error for error in refused["errors"])

    asyncio.run(scenario())
