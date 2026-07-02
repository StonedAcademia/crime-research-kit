import { existsSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const CREATED_BY = "trcr-ufb-exporter";
const SCAVENGE_BUNDLE_ARTIFACT_TYPE = "scavenge.bundle";
const BUNDLE_SCHEMA_V2 = "forensic-bundle-v2";
const SCAVENGE_OBJECT_GRAPH_SCHEMA_V1 = "scavenge-object-graph-v1";

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

export async function buildUfbV2(model, exportedAt, phanesteadRoot) {
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
