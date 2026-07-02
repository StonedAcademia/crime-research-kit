import path from "node:path";

import { readJson } from "../io.mjs";
import { addEvidenceGroups, addEvidenceRecord, loadRecords, sanitizeEntityEvidenceIds } from "./evidence.mjs";
import {
  compactText,
  evidenceBody,
  extractionProvenance,
  firstSourceFor,
  locatorToString,
  modelId,
  recordSourceIds,
  safeDate,
  sourceCitation,
  sortedUnique,
} from "./format.mjs";
import { addLedgerRelations, collectClaimEntities, makeCanvasNodes } from "./graph.mjs";

const MODEL_SCHEMA_VERSION = "scavenge-model-v1";

export function buildModel(caseDir, options) {
  const caseJson = readJson(path.join(caseDir, "case.json"), {});
  const caseSlug = path.basename(path.resolve(caseDir));
  const caseId = caseJson.case_id || caseSlug;
  const exportedAt = options.exportedAt;
  const provenance = extractionProvenance(exportedAt, caseSlug);
  const { loaded, filtered } = loadRecords(path.join(caseDir, "records"), caseDir, options.includePrivate);
  const sourceById = new Map(loaded.sources.map((source) => [source.source_id, source]));
  const publicSourceIds = new Set(filtered.sources.map((source) => source.source_id));
  const entityIdMap = new Map();
  const eventIdMap = new Map();
  const claimEvidenceIdMap = new Map();
  const evidence = [];

  const addEvidence = (recordType, rawId, label, body, citation, document, entityIds = [], observedAt) =>
    addEvidenceRecord(evidence, { recordType, rawId, label, body, citation, document, entityIds, observedAt, exportedAt, provenance });

  for (const source of filtered.sources) {
    addEvidence(
      "source",
      source.source_id,
      source.title || source.source_id,
      evidenceBody(source.title || source.source_id, "source", source, compactText(source.publisher, source.notes)),
      sourceCitation(source, source.source_id),
      { crkRecordType: "source", crkRecord: source },
      [],
      safeDate(source.date_published, undefined),
    );
  }

  const entities = [];
  for (const entity of filtered.entities) {
    const id = modelId("entity", entity.entity_id);
    entityIdMap.set(entity.entity_id, id);
    const sourceEvidenceIds = recordSourceIds(entity)
      .filter((sourceId) => options.includePrivate || publicSourceIds.has(sourceId))
      .map((sourceId) => modelId("source", sourceId));
    const claimEvidenceIds = (entity.claim_ids || []).map((claimId) => modelId("claim", claimId));
    entities.push({
      id,
      kind: "person",
      label: entity.display_name || entity.name || entity.entity_id,
      aliases: entity.aliases || [],
      summary: compactText(entity.entity_type ? `CRK entity type: ${entity.entity_type}.` : "", entity.notes),
      evidenceIds: sortedUnique([...sourceEvidenceIds, ...claimEvidenceIds]),
      createdAt: exportedAt,
      updatedAt: exportedAt,
      provenance,
    });
  }

  for (const event of filtered.events) {
    const id = modelId("event", event.event_id);
    eventIdMap.set(event.event_id, id);
    const sourceEvidenceIds = recordSourceIds(event)
      .filter((sourceId) => options.includePrivate || publicSourceIds.has(sourceId))
      .map((sourceId) => modelId("source", sourceId));
    const claimEvidenceIds = (event.claim_ids || []).map((claimId) => modelId("claim", claimId));
    entities.push({
      id,
      kind: "event",
      label: event.title || event.event_id,
      aliases: [],
      summary: compactText(event.event_type ? `CRK event type: ${event.event_type}.` : "", event.status ? `Status: ${event.status}.` : "", event.notes),
      timeRange: {
        start: event.start_date ? safeDate(event.start_date, undefined) : undefined,
        end: event.end_date ? safeDate(event.end_date, undefined) : undefined,
      },
      evidenceIds: sortedUnique([...sourceEvidenceIds, ...claimEvidenceIds]),
      createdAt: exportedAt,
      updatedAt: exportedAt,
      provenance,
    });
  }

  const entityIdsByClaimId = collectClaimEntities(filtered, entityIdMap, eventIdMap);
  for (const claim of filtered.claims) {
    const { source, sourceId } = firstSourceFor(claim, sourceById);
    const entityIds = sortedUnique([...(entityIdsByClaimId.get(claim.claim_id) || [])]);
    const evidenceId = addEvidence(
      "claim",
      claim.claim_id,
      claim.claim_id,
      evidenceBody(claim.claim || claim.claim_id, "claim", claim, compactText(`Status: ${claim.status || "unknown"}.`, claim.notes)),
      sourceCitation(source, sourceId),
      { crkRecordType: "claim", crkRecord: claim },
      entityIds,
    );
    claimEvidenceIdMap.set(claim.claim_id, evidenceId);
  }

  for (const span of filtered.source_spans) {
    const source = sourceById.get(span.source_id);
    addEvidence("source_span", span.source_span_id, span.summary || span.source_span_id, evidenceBody(span.summary || span.source_span_id, "source_span", span, compactText(span.exact_text, span.notes)), sourceCitation(source, span.source_id, locatorToString(span.locator)), { crkRecordType: "source_span", crkRecord: span });
  }
  for (const artifact of filtered.artifacts) {
    const { source, sourceId } = firstSourceFor(artifact, sourceById);
    addEvidence("artifact", artifact.artifact_id, artifact.name || artifact.artifact_id, evidenceBody(artifact.description || artifact.name || artifact.artifact_id, "artifact", artifact, compactText(artifact.artifact_type, artifact.notes)), sourceCitation(source, sourceId), { crkRecordType: "artifact", crkRecord: artifact });
  }
  for (const place of filtered.places) {
    const { source, sourceId } = firstSourceFor(place, sourceById);
    addEvidence("place", place.place_id, place.name || place.place_id, evidenceBody(place.name || place.place_id, "place", place, compactText(place.place_type, place.precision, place.notes)), sourceCitation(source, sourceId), { crkRecordType: "place", crkRecord: place });
  }
  for (const quote of filtered.quotes) {
    const { source, sourceId } = firstSourceFor(quote, sourceById);
    addEvidence("quote", quote.quote_id, quote.quote || quote.quote_id, evidenceBody(quote.quote || quote.quote_id, "quote", quote, quote.notes), sourceCitation(source, sourceId, locatorToString(quote.locator)), { crkRecordType: "quote", crkRecord: quote });
  }
  for (const redaction of filtered.redactions) {
    const { source, sourceId } = firstSourceFor(redaction, sourceById);
    addEvidence("redaction", redaction.redaction_id, redaction.reason || redaction.redaction_id, evidenceBody(redaction.reason || redaction.redaction_id, "redaction", redaction, redaction.notes), sourceCitation(source, sourceId), { crkRecordType: "redaction", crkRecord: redaction });
  }
  for (const note of filtered.notes) {
    addEvidence("note", note.note_id, note.title, note.body, { sourceId: note.path, sourceTitle: note.title, locator: note.path }, { crkRecordType: "case_note", crkRecord: note });
  }

  const evidenceIds = sanitizeEntityEvidenceIds(entities, evidence);
  const groups = addEvidenceGroups(evidence, caseSlug, exportedAt, provenance);
  const modelIds = new Set([...entities.map((item) => item.id), ...evidence.map((item) => item.id), ...groups.map((item) => item.id)]);
  const relations = [];
  addLedgerRelations({ relations, filtered, entityIdMap, eventIdMap, claimEvidenceIdMap, evidenceIds, modelIds, exportedAt, provenance });
  const canvasNodes = makeCanvasNodes(entities, groups);
  const model = {
    schemaVersion: MODEL_SCHEMA_VERSION,
    id: modelId("crk", caseId),
    title: caseJson.title || caseSlug,
    description: compactText(caseJson.research_scope, caseJson.public_interest),
    createdAt: safeDate(caseJson.created_at, exportedAt),
    updatedAt: exportedAt,
    entities,
    evidence,
    evidenceGroups: groups,
    relations,
    canvas: {
      activeMode: "manual",
      nodes: canvasNodes,
      snapshots: {
        manual: {
          engine: "manual",
          nodes: canvasNodes,
          signature: `crk-export:${caseSlug}:${exportedAt}`,
          updatedAt: exportedAt,
        },
      },
    },
  };

  const inputCounts = Object.fromEntries(Object.entries(loaded).map(([key, rows]) => [key, rows.length]));
  const filteredCounts = Object.fromEntries(Object.entries(filtered).map(([key, rows]) => [key, rows.length]));
  const exportedCounts = {
    entities: model.entities.length,
    evidence: model.evidence.length,
    evidenceGroups: model.evidenceGroups.length,
    relations: model.relations.length,
    canvasNodes: model.canvas.nodes.length,
  };
  return { model, inputCounts, filteredCounts, exportedCounts };
}
