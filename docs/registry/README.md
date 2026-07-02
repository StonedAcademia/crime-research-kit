# Registry

Machine-readable lane, template, and governance registries.

## Analysis Vocabulary Packs

`analysis/vocabulary.json` and `analysis/scoring.json` hold the neutral default
classification vocabulary for analysis reports: ordered term packs for relation
families, relationship classes, and bridge labels, plus layer ordering and
status/grade score tables. Classifiers scan packs top-to-bottom; first match wins;
records matching no pack surface as `unclassified` rather than inheriting an
implied label.

A case may extend the defaults with `analysis_vocabulary.json` in its case
directory (`data/cases/<slug>/`). Override entries with an existing `key` extend
that pack's terms; entries with a new `key` are inserted before the defaults
(more specific wins). `layer_order`/`status_scores`/`grade_scores` merge per key.
Case-specific investigation vocabulary belongs in the case override, never in
these defaults; see `data/examples/synthetic_case/analysis_vocabulary.json` for a
worked example.
