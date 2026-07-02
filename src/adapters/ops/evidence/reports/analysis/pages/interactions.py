"""Interactive JavaScript for analysis chart pages."""

from __future__ import annotations


def analysis_chart_script() -> str:
    return """
<script>
(() => {
  const inspector = document.querySelector('[data-inspector]');
  const inspectorBody = document.querySelector('[data-inspector-body]');
  const search = document.querySelector('[data-search]');
  const reset = document.querySelector('[data-reset]');
  const tooltip = document.createElement('div');
  tooltip.className = 'chart-tooltip';
  tooltip.setAttribute('role', 'status');
  document.body.appendChild(tooltip);
  const marks = Array.from(document.querySelectorAll('svg title'))
    .map((title) => title.parentElement)
    .filter(Boolean);
  const stopWords = new Set(['with', 'from', 'this', 'that', 'source', 'status', 'claim', 'event', 'path', 'record', 'count', 'context', 'bridge']);
  function detailFor(el) {
    const title = el.querySelector('title');
    return title ? title.textContent.trim() : '';
  }
  function compactDetail(text, limit = 360) {
    if (!text) return '';
    return text.length > limit ? `${text.slice(0, limit - 1)}...` : text;
  }
  function tokensFor(text) {
    return new Set(
      (text || '')
        .toLowerCase()
        .split(/[^a-z0-9_:-]+/)
        .filter((token) => token.length > 3 && !stopWords.has(token))
        .slice(0, 36)
    );
  }
  function setInspector(text, mode = 'live') {
    if (!inspectorBody) return;
    inspectorBody.textContent = text || 'Hover or click a chart mark to inspect the row, path, source, or status behind it.';
    if (inspector) {
      inspector.classList.toggle('is-live', Boolean(text) && mode === 'live');
      inspector.classList.toggle('is-selected', Boolean(text) && mode === 'selected');
    }
  }
  function eventPoint(event) {
    const target = event && event.target && event.target.getBoundingClientRect ? event.target.getBoundingClientRect() : null;
    const x = event && Number.isFinite(event.clientX) && event.clientX ? event.clientX : (target ? target.right : 24);
    const y = event && Number.isFinite(event.clientY) && event.clientY ? event.clientY : (target ? target.top : 24);
    return { x, y };
  }
  function showTooltip(text, event) {
    if (!text || !event) return;
    const point = eventPoint(event);
    tooltip.textContent = compactDetail(text, 220);
    tooltip.style.left = `${Math.max(8, Math.min(window.innerWidth - 390, point.x + 12))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(window.innerHeight - 140, point.y + 12))}px`;
    tooltip.classList.add('is-visible');
  }
  function hideTooltip() {
    tooltip.classList.remove('is-visible');
  }
  function clickFlash(event) {
    if (!event) return;
    const point = eventPoint(event);
    const flash = document.createElement('span');
    flash.className = 'click-flash';
    flash.style.left = `${point.x}px`;
    flash.style.top = `${point.y}px`;
    document.body.appendChild(flash);
    window.setTimeout(() => flash.remove(), 520);
  }
  function selectMark(el, event) {
    const selectedText = detailFor(el);
    const selectedTokens = tokensFor(selectedText);
    let relatedCount = 0;
    marks.forEach((mark) => {
      mark.classList.remove('is-selected', 'is-related', 'is-dim');
      if (mark === el) return;
      const otherTokens = tokensFor(detailFor(mark));
      const related = [...selectedTokens].some((token) => otherTokens.has(token));
      if (related) {
        mark.classList.add('is-related');
        relatedCount += 1;
      } else {
        mark.classList.add('is-dim');
      }
    });
    el.classList.add('is-selected');
    setInspector(`${selectedText}${relatedCount ? `\n\nRelated marks highlighted: ${relatedCount}` : ''}`, 'selected');
    clickFlash(event);
    showTooltip(selectedText, event);
  }
  function applyQuery(query) {
    const q = (query || '').trim().toLowerCase();
    marks.forEach((el) => {
      const text = detailFor(el).toLowerCase();
      const visible = !q || text.includes(q);
      if (!el.classList.contains('is-selected')) {
        el.classList.toggle('is-dim', !visible);
      }
    });
  }
  marks.forEach((el) => {
    el.classList.add('interactive-mark');
    el.setAttribute('tabindex', '0');
    el.setAttribute('role', 'button');
    el.setAttribute('aria-label', compactDetail(detailFor(el), 120));
    el.addEventListener('mouseenter', (event) => {
      setInspector(detailFor(el), 'live');
      showTooltip(detailFor(el), event);
    });
    el.addEventListener('mousemove', (event) => showTooltip(detailFor(el), event));
    el.addEventListener('mouseleave', hideTooltip);
    el.addEventListener('focus', (event) => {
      setInspector(detailFor(el), 'live');
      showTooltip(detailFor(el), event);
    });
    el.addEventListener('blur', hideTooltip);
    el.addEventListener('click', (event) => {
      event.stopPropagation();
      selectMark(el, event);
    });
    el.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectMark(el, event);
      }
    });
  });
  if (search) {
    search.addEventListener('input', () => applyQuery(search.value));
  }
  document.querySelectorAll('[data-query]').forEach((button) => {
    button.addEventListener('click', () => {
      const value = button.getAttribute('data-query') || '';
      if (search) search.value = value;
      document.querySelectorAll('[data-query]').forEach((btn) => btn.setAttribute('aria-pressed', 'false'));
      button.setAttribute('aria-pressed', 'true');
      applyQuery(value);
      setInspector(value ? `Filtered marks containing: ${value}` : '');
    });
  });
  if (reset) {
    reset.addEventListener('click', () => {
      if (search) search.value = '';
      hideTooltip();
      marks.forEach((mark) => mark.classList.remove('is-dim', 'is-selected', 'is-related'));
      document.querySelectorAll('[data-query]').forEach((btn) => btn.setAttribute('aria-pressed', 'false'));
      setInspector('');
    });
  }
  setInspector('');
})();
</script>
"""
