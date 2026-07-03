# crime_research_kit

This package is the public Python namespace for Crime Research Kit.

The supported import root is `crime_research_kit.sdk`. Runtime implementation
modules are intentionally not re-exported here; promote interfaces into the SDK
package as they become stable.

Pre-1.0 policy:

- Public Python callers import from `crime_research_kit.sdk`.
- Packaged top-level modules such as `adapters`, `core`, and `pipeline` are
  current runtime internals for console scripts and the app layer.
- Historical `case_builder.*` import paths are not compatibility targets.
