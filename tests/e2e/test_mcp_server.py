import asyncio
import json
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from case_builder.mcp.context import ServerContext
from case_builder.mcp.server import create_server
from case_builder.ops.runner import TrcrRunner
from tests.helpers import KIT_ROOT


def make_server(cases_root: Path):
    ctx = ServerContext(
        repo_root=KIT_ROOT,
        cases_root=cases_root,
        runner=TrcrRunner(repo_root=KIT_ROOT, dry_run=True),
    )
    return create_server(ctx)


def low_level_server(server):
    return getattr(server, "_mcp_server", None) or server.mcp_server


def tool_payload(result) -> dict:
    return json.loads(result.content[0].text)


def test_server_exposes_tools_and_enforces_gate(synthetic_case_copy):
    from mcp.shared.memory import create_connected_server_and_client_session as client_session

    server = make_server(synthetic_case_copy.parent)

    async def scenario():
        async with client_session(low_level_server(server)) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {"case_info", "get_records", "save_extraction_packet", "import_extraction", "export_manim"} <= names

            info = tool_payload(await client.call_tool("case_info", {"case": "synthetic_case"}))
            assert info["ok"] is True

            refusal = tool_payload(
                await client.call_tool("import_extraction", {"case": "synthetic_case", "packet": "p.json"})
            )
            assert refusal["ok"] is False

            prompts = await client.list_prompts()
            assert {"start_case", "process_source", "review_packet", "public_readiness"} <= {
                prompt.name for prompt in prompts.prompts
            }

    asyncio.run(scenario())
