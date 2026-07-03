# Analysis Chart Reports

Helpers and command modules for the generated analysis chart bundle.

Report exports use the shared template pipeline:

- `pages/specs.py` assembles `core.models.reports.ReportPage` records from CSV
  products and typed `SvgDoc` figures.
- `svg/` modules keep chart geometry in `build_*_figure` functions. They do not
  emit markup directly.
- `pages/render.py` renders pages, dashboards, and SVG documents through the
  Jinja2 templates in `pages/templates_data/`, inlining the committed CSS and JS
  assets so exported HTML remains offline-viewable from an installed package.

Classification for relationship classes, relation families, bridge labels,
status/grade scoring, and layer order is pack-driven through `vocabulary.py` and
the `docs/registry/analysis/` shards. Case directories may add
`analysis_vocabulary.json` overrides; `unclassified` is a report-only bucket for
records that match no pack or structural rule.
