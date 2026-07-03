# Analysis Chart Reports

Helpers and command modules for the generated analysis chart bundle.

Classification for relationship classes, relation families, bridge labels,
status/grade scoring, and layer order is pack-driven through `vocabulary.py` and
the `docs/registry/analysis/` shards. Case directories may add
`analysis_vocabulary.json` overrides; `unclassified` is a report-only bucket for
records that match no pack or structural rule.
