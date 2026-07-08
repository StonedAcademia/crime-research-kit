import type { ConsoleData } from "./visuals/model";
import { loadConsoleData } from "./visuals/model";
import { renderConsoleRoot } from "./visuals/renderers";

const MOBILE_NAV_QUERY = "(max-width: 860px)";

function renderVisuals(scope: ParentNode = document): void {
  scope.querySelectorAll<HTMLElement>("[data-crk-visual-console]").forEach((root) => {
    if (root.dataset.visualRendered === "true") return;
    if (root.dataset.visualLoading === "true") return;
    const deckSlide = root.closest<HTMLElement>(".deck-slide");
    if (deckSlide && !deckSlide.classList.contains("active")) return;
    root.dataset.visualLoading = "true";
    loadConsoleData(root).then((data: ConsoleData | null) => {
      if (!data) return;
      renderConsoleRoot(root, data);
      root.dataset.visualRendered = "true";
    }).catch((error) => {
      root.textContent = error instanceof Error ? error.message : "Unable to load visual data.";
    }).finally(() => {
      delete root.dataset.visualLoading;
    });
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
  renderVisuals();
  document.querySelectorAll<HTMLInputElement>("[data-visual-search]").forEach((input) => input.addEventListener("input", () => {
    const query = input.value.toLowerCase();
    document.querySelectorAll<SVGElement>(".visual-mark").forEach((mark) => mark.classList.toggle("is-dim", query.length > 0 && !(mark.dataset.search || "").includes(query)));
  }));
}

function bootDeck(): void {
  const slides = Array.from(document.querySelectorAll<HTMLElement>(".deck-slide"));
  if (!slides.length) return;
  document.body.classList.add("deck-enhanced");
  const nav = document.querySelector<HTMLElement>("[data-deck-slide-nav], [data-deck-nav]");
  const count = document.querySelector<HTMLElement>("[data-deck-count]");
  const buttons: HTMLButtonElement[] = [];
  let current = 0;
  const go = (idx: number) => {
    current = Math.max(0, Math.min(slides.length - 1, idx));
    slides.forEach((slide, i) => slide.classList.toggle("active", i === current));
    buttons.forEach((button, i) => {
      button.classList.toggle("active", i === current);
      if (i === current) button.setAttribute("aria-current", "step");
      else button.removeAttribute("aria-current");
    });
    if (count) count.textContent = `${current + 1} / ${slides.length}`;
    requestAnimationFrame(() => renderVisuals(slides[current]));
  };
  slides.forEach((slide, i) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${i + 1}. ${slide.dataset.title ?? "Slide"}`;
    button.addEventListener("click", () => go(i));
    buttons.push(button);
    nav?.appendChild(button);
  });
  document.querySelector("[data-deck-prev]")?.addEventListener("click", () => go(current - 1));
  document.querySelector("[data-deck-next]")?.addEventListener("click", () => go(current + 1));
  document.addEventListener("keydown", (event) => {
    const target = event.target as HTMLElement | null;
    if (target?.closest("input, textarea, select, button, [contenteditable='true']")) return;
    if (event.key === "ArrowRight") go(current + 1);
    if (event.key === "ArrowLeft") go(current - 1);
  });
  go(0);
}

document.addEventListener("DOMContentLoaded", () => {
  bootVisualShell();
  bootVisuals();
  bootDeck();
});
