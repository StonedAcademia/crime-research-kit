# MCP Tools

MCP tool handlers translate tool calls into SDK-backed case operations while
keeping read, staged-write, and gated-write behavior separated.

Register SDK-backed tools from catalog metadata where safe. `registry.py`
derives SDK-backed tool registrations from operation specs with `mcp_tool`
metadata, checks drift against local handlers, and records explicit direct
exceptions. Local handlers preserve FastMCP-friendly typed signatures, legacy
payload shape, and direct unit-test entrypoints.

This directory does not generate prompts or resources from the SDK catalog.
Those remain explicit MCP content under `content/`. `run_report` also remains
direct/runtime-owned until evidence-board public/private filtering semantics
are explicit, so it is documented as an exception instead of a catalog-driven
SDK tool.
