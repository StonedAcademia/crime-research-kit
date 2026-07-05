import type { ConsoleData } from "./visuals/model";
import { renderConsoleRoot } from "./visuals/renderers";

function readConsole(root: HTMLElement): ConsoleData | null {
  const id = root.dataset.visualDataId;
  const script = id ? document.getElementById(id) : null;
  if (!script?.textContent) return null;
  return JSON.parse(script.textContent) as ConsoleData;
}

function renderVisuals(scope: ParentNode = document): void {
  scope.querySelectorAll<HTMLElement>("[data-crk-visual-console]").forEach((root) => {
    if (root.dataset.visualRendered === "true") return;
    const deckSlide = root.closest<HTMLElement>(".deck-slide");
    if (deckSlide && !deckSlide.classList.contains("active")) return;
    const data = readConsole(root);
    if (!data) return;
    renderConsoleRoot(root, data);
    root.dataset.visualRendered = "true";
  });
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
  const nav = document.querySelector<HTMLElement>("[data-deck-nav]");
  const count = document.querySelector<HTMLElement>("[data-deck-count]");
  let current = 0;
  const go = (idx: number) => {
    current = Math.max(0, Math.min(slides.length - 1, idx));
    slides.forEach((slide, i) => slide.classList.toggle("active", i === current));
    if (count) count.textContent = `${current + 1} / ${slides.length}`;
    requestAnimationFrame(() => renderVisuals(slides[current]));
  };
  slides.forEach((slide, i) => {
    const button = document.createElement("button");
    button.textContent = `${i + 1}. ${slide.dataset.title ?? "Slide"}`;
    button.addEventListener("click", () => go(i));
    nav?.appendChild(button);
  });
  document.querySelector("[data-deck-prev]")?.addEventListener("click", () => go(current - 1));
  document.querySelector("[data-deck-next]")?.addEventListener("click", () => go(current + 1));
  document.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight") go(current + 1);
    if (event.key === "ArrowLeft") go(current - 1);
  });
  go(0);
}

document.addEventListener("DOMContentLoaded", () => {
  bootVisuals();
  bootDeck();
});
