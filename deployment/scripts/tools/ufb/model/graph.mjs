import { compactText, modelId, recordSourceIds, scavengeRelationType, sortedUnique } from "./format.mjs";

function addClaimEntity(entityIdsByClaimId, claimId, modelEntityId) {
  if (!claimId || !modelEntityId) return;
  if (!entityIdsByClaimId.has(claimId)) entityIdsByClaimId.set(claimId, new Set());
  entityIdsByClaimId.get(claimId).add(modelEntityId);
}

export function collectClaimEntities(filtered, entityIdMap, eventIdMap) {
  const entityIdsByClaimId = new Map();
  for (const entity of filtered.entities) for (const claimId of entity.claim_ids || []) addClaimEntity(entityIdsByClaimId, claimId, entityIdMap.get(entity.entity_id));
  for (const event of filtered.events) for (const claimId of event.claim_ids || []) addClaimEntity(entityIdsByClaimId, claimId, eventIdMap.get(event.event_id));
  for (const relation of filtered.relationships) {
    for (const claimId of relation.claim_ids || []) {
      addClaimEntity(entityIdsByClaimId, claimId, entityIdMap.get(relation.src_entity_id));
      addClaimEntity(entityIdsByClaimId, claimId, entityIdMap.get(relation.dst_entity_id));
    }
  }
  for (const eventLink of filtered.event_links) {
    for (const claimId of eventLink.claim_ids || []) {
      addClaimEntity(entityIdsByClaimId, claimId, entityIdMap.get(eventLink.entity_id));
      addClaimEntity(entityIdsByClaimId, claimId, eventIdMap.get(eventLink.event_id));
    }
  }
  return entityIdsByClaimId;
}

export function makeCanvasNodes(entities, groups) {
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
  const baseY = Math.max(900, 180 + Math.ceil(Math.max(personNodes.length / 6, eventNodes.length / 4)) * 140);
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

function addRelation(relations, modelIds, evidenceIds, exportedAt, provenance, id, fromId, toId, relationType, evidenceIdsForRelation, note) {
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
}

export function addLedgerRelations({
  relations,
  filtered,
  entityIdMap,
  eventIdMap,
  claimEvidenceIdMap,
  evidenceIds,
  modelIds,
  exportedAt,
  provenance,
}) {
  const pushRelation = (...args) => addRelation(relations, modelIds, evidenceIds, exportedAt, provenance, ...args);
  for (const relation of filtered.relationships) {
    pushRelation(
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
    pushRelation(
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
      pushRelation(
        modelId("claim_support", `${claim.claim_id}_${supported}`),
        claimEvidenceIdMap.get(claim.claim_id),
        claimEvidenceIdMap.get(supported),
        "supports",
        [claimEvidenceIdMap.get(claim.claim_id), claimEvidenceIdMap.get(supported)],
        "TRCR claim support edge.",
      );
    }
    for (const contradicted of claim.contradicts || []) {
      pushRelation(
        modelId("claim_contradiction", `${claim.claim_id}_${contradicted}`),
        claimEvidenceIdMap.get(claim.claim_id),
        claimEvidenceIdMap.get(contradicted),
        "contradicts",
        [claimEvidenceIdMap.get(claim.claim_id), claimEvidenceIdMap.get(contradicted)],
        "TRCR claim contradiction edge.",
      );
    }
  }
}
