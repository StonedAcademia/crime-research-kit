#!/usr/bin/env bun
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const DEFAULT_PHANESTEAD_ROOT = "../../phanestead-full";
const MODEL_SCHEMA_VERSION = "scavenge-model-v1";
const CREATED_BY = "trcr-ufb-exporter";
const SCAVENGE_BUNDLE_ARTIFACT_TYPE = "scavenge.bundle";
const BUNDLE_SCHEMA_V2 = "forensic-bundle-v2";
const SCAVENGE_OBJECT_GRAPH_SCHEMA_V1 = "scavenge-object-graph-v1";

function usage() {
  return `Usage:
  bun deployment/scripts/export_trcr_ufb.mjs <case_dir> --out <bundle.ufb_v2> [options]

Options:
  --include-private           Include records marked non-public/private. Default is public-safe.
  --exported-at <iso>         Use a stable export timestamp.
  --phanestead-root <dir>     Path to phanestead-full. Default: ${DEFAULT_PHANESTEAD_ROOT}
  --model-out <file>          Also write the intermediate Scavenge model JSON.
  --summary-out <file>        Write export summary JSON. Default: <out>.summary.json
  --no-verify                 Skip Phanestead round-trip import verification.
  --help                      Show this help.
`;
}

function parseArgs(argv) {
  const args = [...argv];
  if (args.includes("--help") || args.length === 0) {
    console.log(usage());
    process.exit(0);
  }
  const options = {
    caseDir: null,
    out: null,
    includePrivate: false,
    exportedAt: null,
    phanesteadRoot: DEFAULT_PHANESTEAD_ROOT,
    modelOut: null,
    summaryOut: null,
    verify: true,
  };
  while (args.length) {
    const arg = args.shift();
    if (!arg) continue;
    if (!arg.startsWith("--") && !options.caseDir) {
      options.caseDir = arg;
      continue;
    }
    if (arg === "--include-private") {
      options.includePrivate = true;
      continue;
    }
    if (arg === "--no-verify") {
      options.verify = false;
      continue;
    }
    if (arg === "--out") {
      options.out = args.shift();
      continue;
    }
    if (arg === "--exported-at") {
      options.exportedAt = args.shift();
      continue;
    }
    if (arg === "--phanestead-root") {
      options.phanesteadRoot = args.shift();
      continue;
    }
    if (arg === "--model-out") {
      options.modelOut = args.shift();
      continue;
    }
    if (arg === "--summary-out") {
      options.summaryOut = args.shift();
      continue;
    }
    throw new Error(`Unknown argument: ${arg}`);
  }
  if (!options.caseDir) throw new Error("Missing <case_dir>.");
  if (!options.out) throw new Error("Missing --out <bundle.ufb_v2>.");
  options.exportedAt = options.exportedAt ?? new Date().toISOString();
  options.summaryOut = options.summaryOut ?? `${options.out}.summary.json`;
  return options;
}

function ensureParent(filePath) {
  mkdirSync(path.dirname(path.resolve(filePath)), { recursive: true });
}

function readJson(filePath, fallback = null) {
  if (!existsSync(filePath)) return fallback;
  return JSON.parse(readFileSync(filePath, "utf8"));
}

function readJsonl(recordsDir, name) {
  const filePath = path.join(recordsDir, `${name}.jsonl`);
  if (!existsSync(filePath)) return [];
  return readFileSync(filePath, "utf8")
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0)
    .map((line, index) => {
      try {
        return JSON.parse(line);
      } catch (error) {
        throw new Error(`${filePath}:${index + 1}: ${error.message}`);
      }
    });
}

function readNoteEvidence(caseDir, includePrivate) {
  const notesDir = path.join(caseDir, "notes");
  const taxonomyPath = path.join(notesDir, "subcase_taxonomy_2026-06-30.md");
  if (!existsSync(taxonomyPath)) return [];
  const body = readFileSync(taxonomyPath, "utf8");
  return [{
    note_id: "subcase_taxonomy_2026-06-30",
    title: "High-control societies subcase taxonomy",
    path: path.relative(caseDir, taxonomyPath),
    body: includePrivate ? body : body,
    public_export: true,
  }];
}

function text(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  return String(value);
}

function compactText(...parts) {
  return parts.map((part) => text(part).trim()).filter(Boolean).join(" ");
}

function normalize(value) {
  return text(value).trim().toLowerCase();
}

function modelId(prefix, rawId) {
  const safe = text(rawId, "unknown").replace(/[^A-Za-z0-9_.-]+/g, "_").replace(/^_+|_+$/g, "");
  return `${prefix}_${safe || "unknown"}`;
}

function safeDate(value, fallback) {
  const raw = text(value).trim();
  if (!raw) return fallback;
  if (/^\d{4}$/.test(raw)) return `${raw}-01-01T00:00:00.000Z`;
  if (/^\d{4}-\d{2}$/.test(raw)) return `${raw}-01T00:00:00.000Z`;
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return `${raw}T00:00:00.000Z`;
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? fallback : date.toISOString();
}

function publicAllowed(record, includePrivate, recordType) {
  if (includePrivate) return true;
  if (record?.public_export === false) return false;
  const privacyLevel = normalize(record?.privacy_level);
  if (["private", "private_person", "minor", "sensitive"].includes(privacyLevel)) return false;
  if (record?.privacy_sensitive === true) return false;
  const privacyReview = normalize(record?.privacy_review);
  if (["needs_redaction", "exclude", "excluded", "private", "blocked"].includes(privacyReview)) return false;
  if (recordType === "claims" && normalize(record?.status) === "excluded_from_public_script") return false;
  if (recordType === "artifacts" && ["high", "restricted"].includes(normalize(record?.sensitivity))) return false;
  return true;
}

function sourceCitation(source, sourceId, locator) {
  return {
    accessDate: source?.date_accessed ?? undefined,
    archiveUrl: source?.archive_url ?? undefined,
    locator: locator || undefined,
    sourceId: source?.source_id ?? sourceId ?? undefined,
    sourceTitle: source?.title ?? sourceId ?? undefined,
    sourceUrl: source?.url ?? undefined,
  };
}

function locatorToString(value) {
  if (!value) return "";
  if (typeof value === "string") return value;
  if (typeof value !== "object") return text(value);
  const parts = [];
  if (value.section) parts.push(`section: ${value.section}`);
  if (value.page) parts.push(`page: ${value.page}`);
  if (value.paragraph) parts.push(`paragraph: ${value.paragraph}`);
  if (value.timestamp) parts.push(`timestamp: ${value.timestamp}`);
  if (value.line_start || value.line_end) parts.push(`lines: ${value.line_start ?? "?"}-${value.line_end ?? "?"}`);
  if (value.quote_hint) parts.push(`quote: ${value.quote_hint}`);
  return parts.join("; ");
}

function recordSourceIds(record) {
  if (Array.isArray(record?.source_ids)) return record.source_ids.filter(Boolean);
  if (record?.source_id) return [record.source_id];
  return [];
}

function firstSourceFor(record, sourceById) {
  const sourceIds = recordSourceIds(record);
  const firstId = sourceIds[0];
  return { source: sourceById.get(firstId), sourceId: firstId };
}

function evidenceBody(label, recordType, record, extra = "") {
  const details = extra ? `\n\n${extra}` : "";
  return `${label}\n\nTRCR record type: ${recordType}${details}`;
}

function extractionProvenance(exportedAt, caseLabel) {
  return {
    source: "local-extraction",
    mode: "advanced",
    model: "trcr-ledger",
    sourceLabel: caseLabel,
    extractedAt: exportedAt,
  };
}

function scavengeRelationType(record) {
  const value = normalize(record?.relation_type ?? record?.relationship_class);
  if (["contradicts", "denies", "disputes"].some((part) => value.includes(part))) return "disputes";
  if (["corroborates", "supports"].some((part) => value.includes(part))) return "supports";
  if (["source", "derived"].some((part) => value.includes(part))) return "derived-from";
  if (["cite", "citation"].some((part) => value.includes(part))) return "cites";
  if (["communicat", "correspond"].some((part) => value.includes(part))) return "communicated-with";
  if (["founder", "cofounder", "member", "participant", "attend", "student"].some((part) => value.includes(part))) return "participated-in";
  if (["allege", "accuse"].some((part) => value.includes(part))) return "alleges";
  if (["precede", "successor"].some((part) => value.includes(part))) return "precedes";
  if (["document"].some((part) => value.includes(part))) return "documents";
  if (["affiliat", "institution", "organization"].some((part) => value.includes(part))) return "affiliated-with";
  return "mentions";
}

function makeCanvasNodes(entities, groups) {
  const nodes = [];
  const personNodes = entities.filter((entity) => entity.kind === "person");
  const eventNodes = entities.filter((entity) => entity.kind === "event");
  for (const [index, entity] of personNodes.entries()) {
    nodes.push({
      id: entity.id,
      type: "person",
      x: 120 + (index % 6) * 210,
      y: 120 + Math.floor(index / 6) * 140,
      width: 180,
      height: 88,
    });
  }
  for (const [index, entity] of eventNodes.entries()) {
    nodes.push({
      id: entity.id,
      type: "event",
      x: 1520 + (index % 4) * 230,
      y: 120 + Math.floor(index / 4) * 140,
      width: 200,
      height: 96,
    });
  }
  const baseY = Math.max(
    900,
    180 + Math.ceil(Math.max(personNodes.length / 6, eventNodes.length / 4)) * 140,
  );
  for (const [index, group] of groups.entries()) {
    nodes.push({
      id: group.id,
      type: "group",
      x: 120 + (index % 4) * 360,
      y: baseY + Math.floor(index / 4) * 170,
      width: 300,
      height: 120,
    });
  }
  return nodes;
}

function bundleManifest(model, exportedAt) {
  const sourceDocuments = new Set(
    model.evidence.map((record) => record.citation.sourceId ?? record.citation.sourceUrl ?? record.citation.sourceTitle ?? record.id),
  );
  const extractionRuns = new Set(
    [...model.entities, ...model.evidence, ...model.evidenceGroups, ...model.relations]
      .map((record) => record.provenance)
      .filter(Boolean)
      .map((provenance) => `${provenance.model ?? "local"}:${provenance.sourceLabel ?? "source"}:${provenance.extractedAt}`),
  );
  return {
    artifact: {
      artifactType: SCAVENGE_BUNDLE_ARTIFACT_TYPE,
      sourceArtifactId: model.id,
      status: "active",
    },
    title: model.title,
    description: model.description,
    exportedAt,
    producer: {
      app: "scavenge",
      appVersion: "0.8.0-dev.1",
      sdkVersion: "0.8.0-dev.1",
    },
    schema: {
      bundle: BUNDLE_SCHEMA_V2,
      payload: SCAVENGE_OBJECT_GRAPH_SCHEMA_V1,
    },
    counts: {
      entities: model.entities.length,
      evidence: model.evidence.length,
      evidenceGroups: model.evidenceGroups.length,
      relations: model.relations.length,
      canvasNodes: model.canvas.nodes.length,
      sourceDocuments: sourceDocuments.size,
      sourceSpans: model.evidence.filter((record) => record.citation.locator).length,
      extractionRuns: extractionRuns.size,
    },
    capabilities: ["object-read", "object-graph", "indexed-lookup", "source-trace", "integrity-proof", "scavenge-round-trip"],
    redaction: {
      encryptedBodies: false,
      publicLabels: "manifest-only",
    },
  };
}

async function buildUfbV2(model, exportedAt, phanesteadRoot) {
  const v2ModulePath = path.join(phanesteadRoot, "lib/packages/domain/forensic-bundle/src/v2/index.ts");
  const scavengeModulePath = path.join(phanesteadRoot, "lib/packages/domain/forensic-bundle/src/scavenge/index.ts");
  if (!existsSync(v2ModulePath)) throw new Error(`Phanestead v2 module not found: ${v2ModulePath}`);
  if (!existsSync(scavengeModulePath)) throw new Error(`Phanestead Scavenge module not found: ${scavengeModulePath}`);
  const { buildUnencryptedForensicBundleV2 } = await import(pathToFileURL(v2ModulePath).href);
  const { scavengeModelToBundleObjects } = await import(pathToFileURL(scavengeModulePath).href);
  return buildUnencryptedForensicBundleV2({
    manifest: bundleManifest(model, exportedAt),
    objects: scavengeModelToBundleObjects(model),
    versions: [
      {
        sourceVersionId: `${model.id}:${model.updatedAt}`,
        parents: [],
        objectRootId: `scavenge.model:${model.id}`,
        createdBy: CREATED_BY,
        createdAt: model.updatedAt || exportedAt,
        meta: { title: model.title, modelId: model.id, savedAt: model.updatedAt },
      },
    ],
  });
}

function sortedUnique(values) {
  return [...new Set(values.filter(Boolean))].sort((left, right) => left.localeCompare(right));
}

function buildModel(caseDir, options) {
  const caseJson = readJson(path.join(caseDir, "case.json"), {});
  const recordsDir = path.join(caseDir, "records");
  const caseSlug = path.basename(path.resolve(caseDir));
  const caseId = caseJson.case_id || caseSlug;
  const exportedAt = options.exportedAt;
  const provenance = extractionProvenance(exportedAt, caseSlug);
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
    notes: readNoteEvidence(caseDir, options.includePrivate),
  };
  const filtered = Object.fromEntries(
    Object.entries(loaded).map(([name, rows]) => [name, rows.filter((row) => publicAllowed(row, options.includePrivate, name))]),
  );

  const sourceById = new Map(loaded.sources.map((source) => [source.source_id, source]));
  const publicSourceIds = new Set(filtered.sources.map((source) => source.source_id));
  const entityIdMap = new Map();
  const eventIdMap = new Map();
  const claimEvidenceIdMap = new Map();
  const evidence = [];

  function addEvidence(recordType, rawId, label, body, citation, document, entityIds = [], observedAt) {
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

  for (const source of filtered.sources) {
    addEvidence(
      "source",
      source.source_id,
      source.title || source.source_id,
      evidenceBody(source.title || source.source_id, "source", source, compactText(source.publisher, source.notes)),
      sourceCitation(source, source.source_id),
      { trcrRecordType: "source", trcrRecord: source },
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
      summary: compactText(entity.entity_type ? `TRCR entity type: ${entity.entity_type}.` : "", entity.notes),
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
      summary: compactText(event.event_type ? `TRCR event type: ${event.event_type}.` : "", event.status ? `Status: ${event.status}.` : "", event.notes),
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

  const entityIdsByClaimId = new Map();
  function addClaimEntity(claimId, modelEntityId) {
    if (!claimId || !modelEntityId) return;
    if (!entityIdsByClaimId.has(claimId)) entityIdsByClaimId.set(claimId, new Set());
    entityIdsByClaimId.get(claimId).add(modelEntityId);
  }
  for (const entity of filtered.entities) for (const claimId of entity.claim_ids || []) addClaimEntity(claimId, entityIdMap.get(entity.entity_id));
  for (const event of filtered.events) for (const claimId of event.claim_ids || []) addClaimEntity(claimId, eventIdMap.get(event.event_id));
  for (const relation of filtered.relationships) {
    for (const claimId of relation.claim_ids || []) {
      addClaimEntity(claimId, entityIdMap.get(relation.src_entity_id));
      addClaimEntity(claimId, entityIdMap.get(relation.dst_entity_id));
    }
  }
  for (const eventLink of filtered.event_links) {
    for (const claimId of eventLink.claim_ids || []) {
      addClaimEntity(claimId, entityIdMap.get(eventLink.entity_id));
      addClaimEntity(claimId, eventIdMap.get(eventLink.event_id));
    }
  }

  for (const claim of filtered.claims) {
    const { source, sourceId } = firstSourceFor(claim, sourceById);
    const entityIds = sortedUnique([...(entityIdsByClaimId.get(claim.claim_id) || [])]);
    const evidenceId = addEvidence(
      "claim",
      claim.claim_id,
      claim.claim_id,
      evidenceBody(claim.claim || claim.claim_id, "claim", claim, compactText(`Status: ${claim.status || "unknown"}.`, claim.notes)),
      sourceCitation(source, sourceId),
      { trcrRecordType: "claim", trcrRecord: claim },
      entityIds,
    );
    claimEvidenceIdMap.set(claim.claim_id, evidenceId);
  }

  for (const span of filtered.source_spans) {
    const source = sourceById.get(span.source_id);
    addEvidence(
      "source_span",
      span.source_span_id,
      span.summary || span.source_span_id,
      evidenceBody(span.summary || span.source_span_id, "source_span", span, compactText(span.exact_text, span.notes)),
      sourceCitation(source, span.source_id, locatorToString(span.locator)),
      { trcrRecordType: "source_span", trcrRecord: span },
    );
  }

  for (const artifact of filtered.artifacts) {
    const { source, sourceId } = firstSourceFor(artifact, sourceById);
    addEvidence(
      "artifact",
      artifact.artifact_id,
      artifact.name || artifact.artifact_id,
      evidenceBody(artifact.description || artifact.name || artifact.artifact_id, "artifact", artifact, compactText(artifact.artifact_type, artifact.notes)),
      sourceCitation(source, sourceId),
      { trcrRecordType: "artifact", trcrRecord: artifact },
    );
  }

  for (const place of filtered.places) {
    const { source, sourceId } = firstSourceFor(place, sourceById);
    addEvidence(
      "place",
      place.place_id,
      place.name || place.place_id,
      evidenceBody(place.name || place.place_id, "place", place, compactText(place.place_type, place.precision, place.notes)),
      sourceCitation(source, sourceId),
      { trcrRecordType: "place", trcrRecord: place },
    );
  }

  for (const quote of filtered.quotes) {
    const { source, sourceId } = firstSourceFor(quote, sourceById);
    addEvidence(
      "quote",
      quote.quote_id,
      quote.quote || quote.quote_id,
      evidenceBody(quote.quote || quote.quote_id, "quote", quote, quote.notes),
      sourceCitation(source, sourceId, locatorToString(quote.locator)),
      { trcrRecordType: "quote", trcrRecord: quote },
    );
  }

  for (const redaction of filtered.redactions) {
    const { source, sourceId } = firstSourceFor(redaction, sourceById);
    addEvidence(
      "redaction",
      redaction.redaction_id,
      redaction.reason || redaction.redaction_id,
      evidenceBody(redaction.reason || redaction.redaction_id, "redaction", redaction, redaction.notes),
      sourceCitation(source, sourceId),
      { trcrRecordType: "redaction", trcrRecord: redaction },
    );
  }

  for (const note of filtered.notes) {
    addEvidence(
      "note",
      note.note_id,
      note.title,
      note.body,
      { sourceId: note.path, sourceTitle: note.title, locator: note.path },
      { trcrRecordType: "case_note", trcrRecord: note },
    );
  }

  const evidenceIds = new Set(evidence.map((record) => record.id));
  for (const entity of entities) {
    entity.evidenceIds = entity.evidenceIds.filter((id) => evidenceIds.has(id));
  }

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
      summary: `${memberIds.length} TRCR ${idPart.replace(/_/g, " ")} records exported from ${caseSlug}.`,
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

  const modelIds = new Set([...entities.map((item) => item.id), ...evidence.map((item) => item.id), ...groups.map((item) => item.id)]);
  const relations = [];
  const addRelation = (id, fromId, toId, relationType, evidenceIdsForRelation, note) => {
    if (!fromId || !toId || !modelIds.has(fromId) || !modelIds.has(toId)) return;
    relations.push({
      id,
      fromId,
      toId,
      relationType,
      evidenceIds: sortedUnique(evidenceIdsForRelation.filter((item) => evidenceIds.has(item))),
      note,
      createdAt: exportedAt,
      provenance,
    });
  };
  for (const relation of filtered.relationships) {
    addRelation(
      modelId("relation", relation.rel_id),
      entityIdMap.get(relation.src_entity_id),
      entityIdMap.get(relation.dst_entity_id),
      scavengeRelationType(relation),
      [
        ...(relation.claim_ids || []).map((claimId) => claimEvidenceIdMap.get(claimId)),
        ...recordSourceIds(relation).map((sourceId) => modelId("source", sourceId)),
      ],
      compactText(relation.relation_type, relation.relationship_class, relation.status, relation.notes),
    );
  }
  for (const eventLink of filtered.event_links) {
    addRelation(
      modelId("event_link", eventLink.event_link_id),
      entityIdMap.get(eventLink.entity_id),
      eventIdMap.get(eventLink.event_id),
      scavengeRelationType(eventLink),
      [
        ...(eventLink.claim_ids || []).map((claimId) => claimEvidenceIdMap.get(claimId)),
        ...recordSourceIds(eventLink).map((sourceId) => modelId("source", sourceId)),
      ],
      compactText(eventLink.relation_type, eventLink.relationship_class, eventLink.status, eventLink.basis, eventLink.notes),
    );
  }
  for (const claim of filtered.claims) {
    for (const supported of claim.supports || []) {
      addRelation(
        modelId("claim_support", `${claim.claim_id}_${supported}`),
        claimEvidenceIdMap.get(claim.claim_id),
        claimEvidenceIdMap.get(supported),
        "supports",
        [claimEvidenceIdMap.get(claim.claim_id), claimEvidenceIdMap.get(supported)],
        "TRCR claim support edge.",
      );
    }
    for (const contradicted of claim.contradicts || []) {
      addRelation(
        modelId("claim_contradiction", `${claim.claim_id}_${contradicted}`),
        claimEvidenceIdMap.get(claim.claim_id),
        claimEvidenceIdMap.get(contradicted),
        "contradicts",
        [claimEvidenceIdMap.get(claim.claim_id), claimEvidenceIdMap.get(contradicted)],
        "TRCR claim contradiction edge.",
      );
    }
  }

  const canvasNodes = makeCanvasNodes(entities, groups);
  const model = {
    schemaVersion: MODEL_SCHEMA_VERSION,
    id: modelId("trcr", caseId),
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
          signature: `trcr-export:${caseSlug}:${exportedAt}`,
          updatedAt: exportedAt,
        },
      },
    },
  };

  const inputCounts = Object.fromEntries(Object.entries(loaded).map(([key, rows]) => [key, rows.length]));
  const exportedCounts = {
    entities: model.entities.length,
    evidence: model.evidence.length,
    evidenceGroups: model.evidenceGroups.length,
    relations: model.relations.length,
    canvasNodes: model.canvas.nodes.length,
  };
  const filteredCounts = Object.fromEntries(Object.entries(filtered).map(([key, rows]) => [key, rows.length]));
  return { model, inputCounts, filteredCounts, exportedCounts };
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const caseDir = path.resolve(options.caseDir);
  if (!existsSync(caseDir)) throw new Error(`Case directory does not exist: ${caseDir}`);
  const phanesteadRoot = path.resolve(options.phanesteadRoot);
  const modulePath = path.join(phanesteadRoot, "lib/apps/scavenge/src/lib/model/forensic-bundle.ts");
  if (!existsSync(modulePath)) throw new Error(`Phanestead forensic-bundle module not found: ${modulePath}`);

  const { importScavengeForensicBundle } = await import(pathToFileURL(modulePath).href);
  const { model, inputCounts, filteredCounts, exportedCounts } = buildModel(caseDir, options);
  const bundle = await buildUfbV2(model, options.exportedAt, phanesteadRoot);
  const bundleText = JSON.stringify(bundle, null, 2);

  ensureParent(options.out);
  writeFileSync(options.out, `${bundleText}\n`, "utf8");

  if (options.modelOut) {
    ensureParent(options.modelOut);
    writeFileSync(options.modelOut, `${JSON.stringify(model, null, 2)}\n`, "utf8");
  }

  let reopenedCounts = null;
  if (options.verify) {
    const reopened = await importScavengeForensicBundle(bundleText);
    reopenedCounts = {
      entities: reopened.entities.length,
      evidence: reopened.evidence.length,
      evidenceGroups: reopened.evidenceGroups.length,
      relations: reopened.relations.length,
      canvasNodes: reopened.canvas.nodes.length,
    };
  }

  const summary = {
    caseDir,
    out: path.resolve(options.out),
    modelOut: options.modelOut ? path.resolve(options.modelOut) : null,
    includePrivate: options.includePrivate,
    exportedAt: options.exportedAt,
    format: bundle.format,
    manifest: bundle.manifest,
    inputCounts,
    filteredCounts,
    exportedCounts,
    reopenedCounts,
    bundleObjectCounts: bundle.manifest.counts,
    bundleHash: bundle.integrity.bundleHash,
    publicBodyHash: bundle.integrity.publicBodyHash,
  };
  ensureParent(options.summaryOut);
  writeFileSync(options.summaryOut, `${JSON.stringify(summary, null, 2)}\n`, "utf8");

  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
