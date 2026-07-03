# Report Models

Typed report models separate chart export data from presentation.

- `figures.py` defines generic SVG geometry primitives consumed by templates.
- `page.py` defines report pages, tables, and dashboard indexes.
- Renderers should build these models first, then hand them to the template layer.
