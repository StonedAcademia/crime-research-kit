const DEFAULT_PHANESTEAD_ROOT = "../../phanestead-full";

function usage() {
  return `Usage:
  bun deployment/scripts/tools/export_crk_ufb.mjs <case_dir> --out <bundle.ufb_v2> [options]

Options:
  --include-private           Include records marked non-public/private. Default is public-safe.
  --exported-at <iso>         Use a stable export timestamp.
  --phanestead-root <dir>     Path to phanestead. Default: ${DEFAULT_PHANESTEAD_ROOT}
  --model-out <file>          Also write the intermediate Scavenge model JSON.
  --summary-out <file>        Write export summary JSON. Default: <out>.summary.json
  --no-verify                 Skip Phanestead round-trip import verification.
  --help                      Show this help.
`;
}

export function parseArgs(argv) {
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
