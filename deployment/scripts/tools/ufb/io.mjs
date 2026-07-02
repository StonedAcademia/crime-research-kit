import { existsSync, mkdirSync, readFileSync } from "node:fs";
import path from "node:path";

export function ensureParent(filePath) {
  mkdirSync(path.dirname(path.resolve(filePath)), { recursive: true });
}

export function readJson(filePath, fallback = null) {
  if (!existsSync(filePath)) return fallback;
  return JSON.parse(readFileSync(filePath, "utf8"));
}

export function readJsonl(recordsDir, name) {
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

export function readNoteEvidence(caseDir, includePrivate) {
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
