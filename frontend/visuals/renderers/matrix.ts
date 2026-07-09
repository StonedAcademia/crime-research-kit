import * as d3 from "d3";

import type { ConsoleData, Row } from "../model";
import { short, text } from "../model";
import { bindMark, countBy, gradeWeight, matrixKey, modeButton, sourceGradeColor, statusWeight, truthy } from "./shared";

const STRONGEST_MATRIX_LIMIT = 24;

export function renderMatrix(root: HTMLElement, data: ConsoleData): void {
  root.replaceChildren();
  const rawRows = data.data.matrix ?? [];
  const supportRows = Array.from(new Map(rawRows.filter((row) => text(row.claim_id) && text(row.source_id)).map((row) => [matrixKey(row), row])).values());
  const claimInfo = new Map<string, Row>();
  for (const row of data.data.claims ?? []) {
    const id = text(row.claim_id);
    if (id) claimInfo.set(id, row);
  }
  for (const row of supportRows) {
    const id = text(row.claim_id);
    if (id && !claimInfo.has(id)) claimInfo.set(id, row);
  }
  const sourceInfo = strongestSources(supportRows);
  const supportCounts = countBy(supportRows, "claim_id");
  const sourceCounts = countBy(supportRows, "source_id");
  const allClaims = Array.from(new Set(supportRows.map((row) => text(row.claim_id)))).filter(Boolean);
  const allSources = Array.from(new Set(supportRows.map((row) => text(row.source_id)))).filter(Boolean);
  const { strongest, full, summary, scroll } = matrixShell(root);
  let mode: "strongest" | "full" = "strongest";
  const draw = () => {
    const selected = matrixSelection(mode);
    strongest.setAttribute("aria-pressed", String(mode === "strongest"));
    full.setAttribute("aria-pressed", String(mode === "full"));
    summary.textContent = `${mode === "strongest" ? "Strongest" : "Full"}: ${selected.rows.length} support links across ${selected.claims.length} claims and ${selected.sources.length} sources.`;
    scroll.replaceChildren();
    drawMatrixSvg(scroll, selected.claims, selected.sources, selected.rows, mode);
  };
  strongest.addEventListener("click", () => { mode = "strongest"; draw(); });
  full.addEventListener("click", () => { mode = "full"; draw(); });
  draw();

  function matrixSelection(nextMode: "strongest" | "full"): { claims: string[]; sources: string[]; rows: Row[] } {
    const rankedClaims = allClaims.sort((left, right) => claimScore(right) - claimScore(left) || left.localeCompare(right));
    const rankedSources = allSources.sort((left, right) => sourceScore(right) - sourceScore(left) || left.localeCompare(right));
    const claims = nextMode === "strongest" ? rankedClaims.slice(0, STRONGEST_MATRIX_LIMIT) : rankedClaims;
    const sources = nextMode === "strongest" ? rankedSources.slice(0, STRONGEST_MATRIX_LIMIT) : rankedSources;
    const claimSet = new Set(claims);
    const sourceSet = new Set(sources);
    const rows = supportRows.filter((row) => claimSet.has(text(row.claim_id)) && sourceSet.has(text(row.source_id)))
      .sort((left, right) => cellScore(right) - cellScore(left) || text(left.claim_id).localeCompare(text(right.claim_id)) || text(left.source_id).localeCompare(text(right.source_id)));
    return { claims, sources, rows };
  }

  function claimScore(id: string): number {
    const row = claimInfo.get(id) ?? {};
    const sourceCount = Number(row.source_count ?? supportCounts.get(id) ?? 0);
    const independentCount = Number(row.independent_source_count ?? 0);
    const confidence = Number(row.confidence ?? row.claim_confidence ?? 0);
    const statusScore = Number(row.status_score ?? 0);
    return (supportCounts.get(id) ?? 0) * 6 + sourceCount * 3 + independentCount * 4
      + (Number.isFinite(confidence) ? confidence * 4 : 0)
      + (Number.isFinite(statusScore) && statusScore > 0 ? statusScore * 5 : statusWeight(row.status || row.claim_status) * 2)
      + gradeWeight(row.best_source_grade);
  }

  function sourceScore(id: string): number {
    const row = sourceInfo.get(id) ?? {};
    return (sourceCounts.get(id) ?? 0) * 6 + gradeWeight(row.source_grade) * 4;
  }

  function cellScore(row: Row): number {
    return claimScore(text(row.claim_id)) + sourceScore(text(row.source_id)) + gradeWeight(row.source_grade) * 2;
  }

  function claimLabel(id: string): string {
    const row = claimInfo.get(id) ?? {};
    return text(row.claim || row.claim_label || id);
  }

  function sourceLabel(id: string): string {
    const row = sourceInfo.get(id) ?? {};
    return text(row.source_title || id);
  }

  function drawMatrixSvg(target: HTMLElement, claims: string[], sources: string[], rows: Row[], nextMode: "strongest" | "full"): void {
    const compact = nextMode === "full";
    const cell = compact ? 18 : 24;
    const left = compact ? 280 : 240;
    const top = compact ? 176 : 156;
    const width = Math.max(920, left + sources.length * cell + 76);
    const height = Math.max(520, top + claims.length * cell + 64);
    const chart = d3.select(target).append("svg").attr("class", "visual-matrix-chart").attr("viewBox", `0 0 ${width} ${height}`).attr("width", width).attr("height", height).attr("role", "img");
    chart.append("text").attr("x", 24).attr("y", 34).attr("class", "visual-title").text("Claim-source support matrix");
    chart.append("text").attr("x", 24).attr("y", 57).attr("class", "matrix-summary-label").text(compact ? "Full sparse view: actual support links only." : "Strongest view: highest-support claims and sources.");
    if (!rows.length) {
      chart.append("text").attr("x", width / 2).attr("y", height / 2).attr("class", "matrix-summary-label").attr("text-anchor", "middle").text("No claim-source support links.");
      return;
    }
    const sourceX = new Map(sources.map((id, idx) => [id, left + idx * cell]));
    const claimY = new Map(claims.map((id, idx) => [id, top + idx * cell]));
    chart.selectAll("line.matrix-row-guide").data(claims).join("line").attr("class", "matrix-row-guide").attr("x1", left - 6).attr("x2", left + sources.length * cell).attr("y1", (id) => (claimY.get(id) ?? top) + cell / 2).attr("y2", (id) => (claimY.get(id) ?? top) + cell / 2);
    chart.selectAll("text.matrix-source-label").data(sources).join("text").attr("class", "matrix-source-label").attr("x", (id) => (sourceX.get(id) ?? left) + cell / 2).attr("y", top - 12).attr("transform", (id) => `rotate(-55 ${(sourceX.get(id) ?? left) + cell / 2} ${top - 12})`).text((id) => short(sourceLabel(id), compact ? 20 : 24));
    chart.selectAll("text.matrix-claim-label").data(claims).join("text").attr("class", "matrix-claim-label").attr("x", left - 12).attr("y", (id) => (claimY.get(id) ?? top) + cell * 0.68).text((id) => short(claimLabel(id), compact ? 48 : 42));
    bindMark(chart.selectAll("rect.matrix-cell").data(rows).join("rect").attr("class", "matrix-cell").attr("x", (row) => sourceX.get(text(row.source_id)) ?? left).attr("y", (row) => claimY.get(text(row.claim_id)) ?? top).attr("width", cell - 3).attr("height", cell - 3).attr("rx", compact ? 2 : 3).attr("fill", (row) => sourceGradeColor(row.source_grade)).attr("stroke", (row) => truthy(row.contradiction_flag) ? "#b9472d" : truthy(row.boundary_flag) ? "#9c5a39" : "#ffffff").attr("stroke-width", (row) => truthy(row.contradiction_flag) || truthy(row.boundary_flag) ? 2.4 : 1), root);
  }
}

function strongestSources(rows: Row[]): Map<string, Row> {
  const sources = new Map<string, Row>();
  for (const row of rows) {
    const id = text(row.source_id);
    if (!id) continue;
    const current = sources.get(id);
    if (!current || gradeWeight(row.source_grade) > gradeWeight(current.source_grade)) sources.set(id, row);
  }
  return sources;
}

function matrixShell(root: HTMLElement): { strongest: HTMLButtonElement; full: HTMLButtonElement; summary: HTMLElement; scroll: HTMLElement } {
  const shell = document.createElement("div");
  shell.className = "visual-matrix-shell";
  const controls = document.createElement("div");
  controls.className = "visual-matrix-controls";
  const strongest = modeButton("Strongest");
  const full = modeButton("Full");
  const summary = document.createElement("div");
  summary.className = "visual-matrix-summary";
  const scroll = document.createElement("div");
  scroll.className = "visual-matrix-scroll";
  controls.append(strongest, full);
  shell.append(controls, summary, scroll);
  root.appendChild(shell);
  return { strongest, full, summary, scroll };
}
