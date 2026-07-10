import type cytoscape from "cytoscape";

const MOBILE_GRAPH_QUERY = "(max-width: 700px)";

export function networkZoomBounds(): { minZoom: number; maxZoom: number } {
  const mobile = window.matchMedia(MOBILE_GRAPH_QUERY).matches;
  return mobile ? { minZoom: 0.06, maxZoom: 4.2 } : { minZoom: 0.25, maxZoom: 2.4 };
}

export function networkFitPadding(canvas: HTMLElement): number {
  if (canvas.clientWidth > 700) return 104;
  return Math.round(Math.max(24, Math.min(44, canvas.clientWidth * 0.08)));
}

export function renderedCanvasCenter(canvas: HTMLElement): cytoscape.Position {
  const rect = canvas.getBoundingClientRect();
  return { x: rect.width / 2, y: rect.height / 2 };
}

export function bindMobilePinchZoom(canvas: HTMLElement, cy: cytoscape.Core, signal: AbortSignal): void {
  let pinch: { distance: number; modelCenter: cytoscape.Position; zoom: number } | undefined;

  const begin = (event: TouchEvent) => {
    cy.stop();
    if (event.touches.length < 2) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const center = touchCenter(event.touches, canvas);
    const zoom = cy.zoom();
    const pan = cy.pan();
    pinch = {
      distance: touchDistance(event.touches),
      modelCenter: { x: (center.x - pan.x) / zoom, y: (center.y - pan.y) / zoom },
      zoom,
    };
    canvas.dataset.gesture = "pinch";
  };
  const move = (event: TouchEvent) => {
    if (!pinch || event.touches.length < 2) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const center = touchCenter(event.touches, canvas);
    const zoom = Math.max(cy.minZoom(), Math.min(cy.maxZoom(), pinch.zoom * touchDistance(event.touches) / pinch.distance));
    cy.viewport({
      zoom,
      pan: { x: center.x - pinch.modelCenter.x * zoom, y: center.y - pinch.modelCenter.y * zoom },
      cancelOnFailedZoom: true,
    });
  };
  const finish = (event: TouchEvent) => {
    if (event.touches.length >= 2) return;
    pinch = undefined;
    delete canvas.dataset.gesture;
  };

  canvas.addEventListener("touchstart", begin, { capture: true, passive: false, signal });
  canvas.addEventListener("touchmove", move, { capture: true, passive: false, signal });
  canvas.addEventListener("touchend", finish, { capture: true, passive: true, signal });
  canvas.addEventListener("touchcancel", finish, { capture: true, passive: true, signal });
  signal.addEventListener("abort", () => {
    pinch = undefined;
    delete canvas.dataset.gesture;
  }, { once: true });
}

function touchCenter(touches: TouchList, canvas: HTMLElement): cytoscape.Position {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (touches[0].clientX + touches[1].clientX) / 2 - rect.left,
    y: (touches[0].clientY + touches[1].clientY) / 2 - rect.top,
  };
}

function touchDistance(touches: TouchList): number {
  return Math.max(1, Math.hypot(touches[1].clientX - touches[0].clientX, touches[1].clientY - touches[0].clientY));
}
