---
name: geographical-location-intelligence
description: "TRCR workflow for identifying, reconciling, and mapping locations tied to evidence items, events, sightings, routes, facilities, media timestamps, exhibits, and locations of interest, then adding source-traceable places, events, event links, artifacts, source spans, map packets, and privacy flags to a case file. Use when Codex needs geospatial case analysis, event maps, evidence-item location pairing, route/location-of-interest clustering, or map-ready exports distinct from parcel/deed/property-record research."
---

# Geographical Location Intelligence

## Operation vocabulary

Lane/template metadata is generated from `docs/registry/`; do not invent new lane IDs in this skill doc. Use operation `draft_extraction` with template `geographical-location` for this lane; CLI fallback: `tcr.py draft-extraction ... --template geographical-location`.


## Purpose

Use this skill to turn source-supported location references into a defensible case map. The focus is evidence geography: where events happened, where evidence items were found or referenced, how locations of interest relate to each other, and which map layers or place aliases are supported by sources.

This skill extends the TRCR case workflow; follow the active truecrime-cult-research safety rules for privacy, source grading, source spans, claims, and public export boundaries. Route parcel ownership, deeds, permits, zoning, and address records to `property-location-records`.

## Required Inputs

Establish these before extraction when possible:

- Target case path, normally `tc-c-kit/data/cases/<case_slug>` in this wrapper repo.
- Source IDs, event IDs, artifact IDs, known places, map/exhibit references, or media timestamps.
- Research question: evidence-item location, event map, route reconstruction, place alias reconciliation, location-of-interest cluster, or public-safe map export.
- Precision needs: exact coordinate, address, facility, street/intersection, neighborhood, jurisdiction, route segment, or vague area.

If a location is a current private residence, minor-related place, shelter/safe house, private workplace, medical/treatment facility, or weak lead, use vague geography and `public_export: false`.

## Workflow

1. **Inventory location-bearing evidence.** List sources, events, artifacts, transcripts, exhibits, images, maps, and claims that mention places or movement.
2. **Collect source-supported locators.** Use [source_lanes.md](references/source_lanes.md). Capture page, paragraph, timestamp, map sheet, exhibit number, coordinate, address, or caption locators with `source_spans`.
3. **Normalize places.** Use [case_mapping.md](references/case_mapping.md) to create or reuse place IDs, aliases, broad/vague locations, and privacy flags.
4. **Assign precision and confidence.** Use [map_packet.md](references/map_packet.md). Do not geocode beyond what the source supports.
5. **Tie places to evidence and events.** Add events, event links, artifacts, and relationships only where a source directly supports the location tie.
6. **Draft a geographical packet.** Use `draft-extraction --template geographical-location`.
7. **Prepare map outputs.** Group points, routes, and areas by source support, date precision, privacy status, and public-export eligibility.
8. **Audit before public output.** Run validation, contradiction/source-independence checks where relevant, and public-export/privacy audits before sharing maps.

## Commands

Use the wrapper-local TRCR tool path and prefix case paths with `tc-c-kit/`:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py plan-public-records tc-c-kit/data/cases/<case_slug> \
  --subject "<event, source, route, evidence item, place, or map question>" \
  --lane geographical-location

python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source tc-c-kit/data/cases/<case_slug> \
  --title "<Map, exhibit, article, transcript, photo, report, or location source>" \
  --url "<public URL or local path>" \
  --source-type other \
  --reliability-grade B \
  --notes "geographical-location; event/evidence locator; precision/privacy review needed"

python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction tc-c-kit/data/cases/<case_slug> <SOURCE_ID> --template geographical-location
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction tc-c-kit/data/cases/<case_slug> tc-c-kit/data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json
python .agents/skills/truecrime-cult-research/scripts/tcr.py audit-public-export tc-c-kit/data/cases/<case_slug> --warn-only
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate tc-c-kit/data/cases/<case_slug>
```

## Extraction Rules

- Record what the source says: at, near, between, route through, found at, photographed at, mapped at, last seen near, or jurisdiction only.
- Preserve location precision separately from confidence. A source can confidently support a vague area without supporting exact coordinates.
- Prefer public buildings, jurisdictions, intersections, route segments, and vague areas over private addresses.
- Do not infer presence, possession, travel, disposal, surveillance, residence, or meeting location from proximity alone.
- Do not publish exact sensitive locations or map layers that reveal private-person addresses, minor-related places, shelters, medical facilities, or weak leads.
- Use `source_spans` for every map-ready location, route, event-location tie, and evidence-item location tie.

## Output Expectations

A completed geographical-location packet should leave source-supported places, place aliases, map-ready source spans, artifacts for maps/exhibits/photos, claims about location support and uncertainty, events tied to places, event links for entity/event/place relevance, relationships such as `located_at` or `route_includes`, and redactions for sensitive precise geography.
