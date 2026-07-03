# Analysis Pages

Typed report page assembly and Jinja2 rendering for analysis exports.

`specs.py` converts analysis CSV products into `ReportPage` models with
structured filters, table previews, and `SvgDoc` figures. `render.py` owns the
runtime renderer for pages, dashboards, SVG documents, and atomic HTML writes.
Template markup and committed static assets live under `templates_data/`; the old
Python string-rendered page, CSS, and interaction-script helpers have been
removed.
