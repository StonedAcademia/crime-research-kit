# Report Frontend Assets

This source tree builds the static CSS and JavaScript that report templates
inline or package with rendered analysis pages. The generated outputs are
committed under `src/adapters/ops/evidence/reports/analysis/pages/templates_data/static/`.

Regenerate the committed assets from the repository root with:

```bash
moon run crk:frontend-build
```

The CSS build scans `templates_data/**/*.j2`. The templates are added in later
report-template-layer tasks, so `styles.css` also declares an inline Tailwind
source for the `crk-` component classes that must survive the first build.
