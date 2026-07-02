#!/usr/bin/env bun
import { existsSync, writeFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { buildUfbV2 } from "./ufb/bundle.mjs";
import { parseArgs } from "./ufb/cli.mjs";
import { ensureParent } from "./ufb/io.mjs";
import { buildModel } from "./ufb/model/build.mjs";

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
