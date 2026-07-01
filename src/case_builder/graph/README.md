# graph

The graph layer contains LangGraph wiring and the sequential fallback runner.
Nodes should be small adapters between state, agent policy, and tools. The
review gate remains explicit so generated plans are not treated as evidence.
