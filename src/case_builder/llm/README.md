# case_builder.llm

Provider resolution and bounded, single-purpose LLM agents. Agents accept any
object with `.invoke(prompt)` returning an object with `.content`, so tests
inject fakes and never require langchain or a running model.

| Module | Responsibility |
| --- | --- |
| `provider.py` | `TRCR_MODEL` spec parsing (`provider:model`), local-provider check, `get_chat_model()` via langchain `init_chat_model`. |
| `packet_agent.py` | Fill a CLI-drafted extraction packet from source text: JSON-only output, one retry with error feedback, guilt-label lint, automation defaults, no invented source IDs. |
| `audit_brief.py` | Summarize deterministic audit outputs into a reviewer brief under `staging/candidates/`. Flags, never decides. |
| `lane_suggest.py` | Suggest additional source lanes with rationale; suggestions are recorded, never silently applied. |

Configuration: `TRCR_MODEL=ollama:model` (default `ollama:llama3.1`).
Managed model-provider specs are rejected before model initialization.
LLM output is never evidence: agent-written records stay `status: unverified`,
low confidence, `public_export: false`, and go through the packet review gate.
