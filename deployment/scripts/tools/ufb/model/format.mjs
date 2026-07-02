export function text(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  return String(value);
}

export function compactText(...parts) {
  return parts.map((part) => text(part).trim()).filter(Boolean).join(" ");
}

export function normalize(value) {
  return text(value).trim().toLowerCase();
}

export function modelId(prefix, rawId) {
  const safe = text(rawId, "unknown").replace(/[^A-Za-z0-9_.-]+/g, "_").replace(/^_+|_+$/g, "");
  return `${prefix}_${safe || "unknown"}`;
}

export function safeDate(value, fallback) {
  const raw = text(value).trim();
  if (!raw) return fallback;
  if (/^\d{4}$/.test(raw)) return `${raw}-01-01T00:00:00.000Z`;
  if (/^\d{4}-\d{2}$/.test(raw)) return `${raw}-01T00:00:00.000Z`;
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return `${raw}T00:00:00.000Z`;
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? fallback : date.toISOString();
}

export function publicAllowed(record, includePrivate, recordType) {
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

export function sourceCitation(source, sourceId, locator) {
  return {
    accessDate: source?.date_accessed ?? undefined,
    archiveUrl: source?.archive_url ?? undefined,
    locator: locator || undefined,
    sourceId: source?.source_id ?? sourceId ?? undefined,
    sourceTitle: source?.title ?? sourceId ?? undefined,
    sourceUrl: source?.url ?? undefined,
  };
}

export function locatorToString(value) {
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

export function recordSourceIds(record) {
  if (Array.isArray(record?.source_ids)) return record.source_ids.filter(Boolean);
  if (record?.source_id) return [record.source_id];
  return [];
}

export function firstSourceFor(record, sourceById) {
  const sourceIds = recordSourceIds(record);
  const firstId = sourceIds[0];
  return { source: sourceById.get(firstId), sourceId: firstId };
}

export function evidenceBody(label, recordType, record, extra = "") {
  const details = extra ? `\n\n${extra}` : "";
  return `${label}\n\nTRCR record type: ${recordType}${details}`;
}

export function extractionProvenance(exportedAt, caseLabel) {
  return {
    source: "local-extraction",
    mode: "advanced",
    model: "trcr-ledger",
    sourceLabel: caseLabel,
    extractedAt: exportedAt,
  };
}

export function scavengeRelationType(record) {
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

export function sortedUnique(values) {
  return [...new Set(values.filter(Boolean))].sort((left, right) => left.localeCompare(right));
}
