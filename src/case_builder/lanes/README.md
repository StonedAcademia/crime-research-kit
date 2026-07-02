# lanes

The lanes package loads `docs/registry/lanes.json`, the canonical registry for public
record lanes, extraction templates, trigger terms, adjacent skill routing, and
source-type hints.

Runtime code should use `registry.py` instead of hard-coded lane maps. The
registry is data only: it can route planning and extraction workflows, but it
does not create claims, sources, or public-ready assertions.
