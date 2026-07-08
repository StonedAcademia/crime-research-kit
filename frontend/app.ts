import type { ConsoleData, VisualMode } from "./visuals/model";
import { clearVisualLoading, loadConsoleData, showVisualError, showVisualLoading, waitForVisualPaint } from "./visuals/model";
import { renderConsoleRoot } from "./visuals/renderers";

const MOBILE_NAV_QUERY = "(max-width: 860px)";
const MODE_STORAGE_KEY = "crkVisualMode";

function renderVisuals(scope: ParentNode = document): void {
  scope.querySelectorAll<HTMLElement>("[data-crk-visual-console]").forEach((root) => {
    if (root.dataset.visualRendered === "true") return;
    if (root.dataset.visualLoading === "true") return;
    root.dataset.visualMode = currentMode();
    showVisualLoading(root);
    void (async () => {
      await waitForVisualPaint();
      const data: ConsoleData | null = await loadConsoleData(root, "default", currentMode());
      if (!data) throw new Error("No exported visual data was found for this console.");
      clearVisualLoading(root);
      renderConsoleRoot(root, data);
      root.dataset.visualRendered = "true";
    })().catch((error) => {
      showVisualError(root, error instanceof Error ? error.message : "Unable to load visual data.");
    }).finally(() => {
      delete root.dataset.visualLoading;
    });
  });
}

function currentMode(): VisualMode {
  return document.body.dataset.crkVisualMode === "private" ? "private" : "public";
}

function privateAvailable(): boolean {
  return document.body.dataset.crkPrivateAvailable === "true";
}

function setVisualMode(mode: VisualMode): void {
  const nextMode: VisualMode = mode === "private" && privateAvailable() ? "private" : "public";
  document.body.dataset.crkVisualMode = nextMode;
  try {
    sessionStorage.setItem(MODE_STORAGE_KEY, nextMode);
  } catch {
    // Session storage can be unavailable in hardened local browser contexts.
  }
  syncModeChrome();
  resetInspectors();
  document.querySelectorAll<HTMLElement>("[data-crk-visual-console]").forEach((root) => {
    delete root.dataset.visualRendered;
    root.replaceChildren();
  });
  renderVisuals();
}

function initialMode(): VisualMode {
  if (!privateAvailable()) return "public";
  try {
    return sessionStorage.getItem(MODE_STORAGE_KEY) === "private" ? "private" : "public";
  } catch {
    return "public";
  }
}

function syncModeChrome(): void {
  const mode = currentMode();
  const scope = document.body.dataset[mode === "private" ? "crkPrivateScope" : "crkPublicScope"] || "";
  const warning = document.body.dataset[mode === "private" ? "crkPrivateWarnings" : "crkPublicWarnings"] || "";
  document.querySelectorAll<HTMLElement>("[data-crk-scope]").forEach((node) => { node.textContent = scope; });
  document.querySelectorAll<HTMLElement>("[data-crk-warning]").forEach((node) => {
    node.textContent = warning;
    node.hidden = !warning;
  });
  document.querySelectorAll<HTMLButtonElement>("[data-crk-mode-option]").forEach((button) => {
    const value = button.dataset.crkModeOption === "private" ? "private" : "public";
    button.setAttribute("aria-pressed", String(value === mode));
    if (value === "private") button.disabled = !privateAvailable();
  });
  const note = document.querySelector<HTMLElement>("[data-crk-mode-note]");
  if (note) {
    note.textContent = privateAvailable()
      ? mode === "private"
        ? "Internal review data is active. Do not publish this bundled export."
        : "Public data loads first. Internal mode switches to the bundled private review data."
      : "Internal data was not bundled in this export.";
  }
  const auditPrefix = mode === "private" ? "audit/private" : "audit";
  document.querySelectorAll<HTMLElement>("[data-visual-audit-file]").forEach((item) => {
    const file = item.dataset.visualAuditFile || "";
    const code = item.querySelector("code");
    if (code) code.textContent = `${auditPrefix}/${file}`;
  });
}

function resetInspectors(): void {
  document.querySelectorAll<HTMLElement>("[data-visual-inspector-body]").forEach((body) => {
    body.replaceChildren();
    const placeholder = document.createElement("p");
    placeholder.textContent = "Select or hover a mark to inspect its evidence state.";
    body.appendChild(placeholder);
  });
}

function bootVisualShell(): void {
  const body = document.body;
  const toggle = document.querySelector<HTMLButtonElement>("[data-crk-nav-toggle]");
  const scrim = document.querySelector<HTMLElement>("[data-crk-sidebar-scrim]");
  const close = document.querySelector<HTMLButtonElement>("[data-crk-nav-close]");
  const mobile = window.matchMedia(MOBILE_NAV_QUERY);
  if (!toggle) return;

  const isMobile = () => mobile.matches;
  const closeMobile = () => {
    body.classList.remove("nav-open");
    syncState();
  };
  const syncState = () => {
    if (!isMobile()) body.classList.remove("nav-open");
    const expanded = isMobile() ? body.classList.contains("nav-open") : !body.classList.contains("nav-collapsed");
    toggle.setAttribute("aria-expanded", String(expanded));
  };

  body.classList.add("nav-ready");
  toggle.addEventListener("click", () => {
    if (isMobile()) {
      body.classList.toggle("nav-open");
    } else {
      body.classList.toggle("nav-collapsed");
    }
    syncState();
  });
  scrim?.addEventListener("click", closeMobile);
  close?.addEventListener("click", closeMobile);
  document.querySelectorAll<HTMLAnchorElement>(".crk-sidebar a").forEach((link) => link.addEventListener("click", () => {
    if (isMobile()) closeMobile();
  }));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && body.classList.contains("nav-open")) closeMobile();
  });
  mobile.addEventListener("change", syncState);
  syncState();
}

function bootVisuals(): void {
  setVisualMode(initialMode());
  renderVisuals();
  document.querySelectorAll<HTMLInputElement>("[data-visual-search]").forEach((input) => input.addEventListener("input", () => {
    const query = input.value.toLowerCase();
    document.querySelectorAll<SVGElement>(".visual-mark").forEach((mark) => mark.classList.toggle("is-dim", query.length > 0 && !(mark.dataset.search || "").includes(query)));
  }));
  document.querySelectorAll<HTMLButtonElement>("[data-visual-reset]").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll<HTMLInputElement>("[data-visual-search]").forEach((input) => {
      input.value = "";
      input.dispatchEvent(new Event("input"));
    });
  }));
  document.querySelectorAll<HTMLButtonElement>("[data-crk-mode-option]").forEach((button) => button.addEventListener("click", () => {
    setVisualMode(button.dataset.crkModeOption === "private" ? "private" : "public");
  }));
}

document.addEventListener("DOMContentLoaded", () => {
  bootVisualShell();
  bootVisuals();
});
