# crime_research_kit

This package is the public Python namespace for Crime Research Kit.

The supported import root is `crime_research_kit.sdk`. Runtime implementation
modules are intentionally not re-exported here; promote interfaces into the SDK
package as they become stable.

Pre-1.0 policy:

- Public Python callers import from `crime_research_kit.sdk`.
- Private runtime modules under `crime_research_kit._runtime` support console
  scripts and the app layer, but are not public SDK imports.
- Top-level `adapters`, `core`, and `pipeline` imports are not packaged
  compatibility targets.
- Historical `case_builder.*` import paths are not compatibility targets.
