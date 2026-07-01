# graph

The graph layer contains LangGraph wiring and the sequential fallback runner.
Nodes should be small adapters between state, agent policy, and ops. The
review gates remain explicit so generated plans are not treated as evidence.

| Module | Responsibility |
| --- | --- |
| `state.py` | Typed graph state shared by LangGraph and the sequential runner. |
| `nodes.py` | Bootstrap nodes (lanes, init, source plan) and merge helpers. |
| `gates.py` | Packet and export review gates; interrupt-based under LangGraph, terminal otherwise. |
| `pipeline_nodes.py` | Deterministic capture/parse/draft/import/index/audit/export nodes over the ops core. |
| `checkpoint.py` | SQLite checkpointer under `<case>/.runs/checkpoints.db` for resumable runs. |
| `runner.py` | Pipeline ordering, conditional gate edges, graph build, sequential fallback. |
