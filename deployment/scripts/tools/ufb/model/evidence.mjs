import { readJsonl, readNoteEvidence } from "../io.mjs";
import { modelId, publicAllowed, sortedUnique } from "./format.mjs";

export function loadRecords(recordsDir, caseDir, includePrivate) {
  const loaded = {
    entities: readJsonl(recordsDir, "entities"),
    events: readJsonl(recordsDir, "events"),
    claims: readJsonl(recordsDir, "claims"),
    relationships: readJsonl(recordsDir, "relationships"),
    event_links: readJsonl(recordsDir, "event_links"),
    sources: readJsonl(recordsDir, "sources"),
    artifacts: readJsonl(recordsDir, "artifacts"),
    places: readJsonl(recordsDir, "places"),
    quotes: readJsonl(recordsDir, "quotes"),
    source_spans: readJsonl(recordsDir, "source_spans"),
    redactions: readJsonl(recordsDir, "redactions"),
    notes: readNoteEvidence(caseDir, includePrivate),
  };
  const filtered = Object.fromEntries(
    Object.entries(loaded).map(([name, rows]) => [name, rows.filter((row) => publicAllowed(row, includePrivate, name))]),
  );
  return { loaded, filtered };
}

export function addEvidenceRecord(
  evidence,
  { recordType, rawId, label, body, citation, document, entityIds = [], observedAt, exportedAt, provenance },
) {
  const id = modelId(recordType, rawId);
  evidence.push({
    id,
    kind: "document",
    scope: entityIds.length ? "person" : "general",
    label: label || id,
    body,
    citation,
    createdAt: exportedAt,
    updatedAt: exportedAt,
    observedAt,
    entityIds: sortedUnique(entityIds),
    groupIds: [],
    document,
    provenance,
  });
  return id;
}

export function addEvidenceGroups(evidence, caseSlug, exportedAt, provenance) {
  const groups = [];
  const groupSpecs = [
    ["sources", "Source packet", "source-packet", (item) => item.id.startsWith("source_")],
    ["claims", "Claim packet", "corroboration-set", (item) => item.id.startsWith("claim_")],
    ["artifacts", "Artifact packet", "chain-of-custody", (item) => item.id.startsWith("artifact_")],
    ["places", "Location packet", "event-packet", (item) => item.id.startsWith("place_")],
    ["source_spans", "Citation locator packet", "source-packet", (item) => item.id.startsWith("source_span_")],
    ["case_notes", "Subcase taxonomy packet", "source-packet", (item) => item.id.startsWith("note_")],
  ];
  for (const [idPart, label, groupType, predicate] of groupSpecs) {
    const memberIds = evidence.filter(predicate).map((item) => item.id);
    if (memberIds.length === 0) continue;
    const id = modelId("group", idPart);
    groups.push({
      id,
      label,
      groupType,
      summary: `${memberIds.length} CRK ${idPart.replace(/_/g, " ")} records exported from ${caseSlug}.`,
      entityIds: [],
      evidenceIds: memberIds,
      createdAt: exportedAt,
      updatedAt: exportedAt,
      provenance,
    });
    for (const item of evidence) {
      if (predicate(item)) item.groupIds.push(id);
    }
  }
  return groups;
}

export function sanitizeEntityEvidenceIds(entities, evidence) {
  const evidenceIds = new Set(evidence.map((record) => record.id));
  for (const entity of entities) {
    entity.evidenceIds = entity.evidenceIds.filter((id) => evidenceIds.has(id));
  }
  return evidenceIds;
}
