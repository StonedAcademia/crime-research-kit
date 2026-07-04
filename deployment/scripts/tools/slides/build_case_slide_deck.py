#!/usr/bin/env python3
"""Build a self-contained slide deck from a CRK case export package."""

from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import re
from collections import Counter
from pathlib import Path


DEFAULT_CASE = Path("data/cases/roach_morava_wwasp")
DEFAULT_OUT = Path("exports/internal/roach_morava_wwasp_final_slides.html")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def titleize(value: str) -> str:
    value = re.sub(r"^\d+_", "", value)
    return value.replace("_", " ").replace("-", " ").strip().title()


def file_title(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    if match:
        title = html.unescape(re.sub(r"\s+", " ", match.group(1))).strip()
        return title.replace(" - Steven and Glenda Roach / Morava Academy / WWASPS Source-Traceable Case", "")
    return titleize(path.stem)


def encode_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def summary_rows(csv_path: Path, limit: int = 6) -> list[dict]:
    if not csv_path.exists():
        return []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))[:limit]


def md_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= {"-", ":"}:
            headers = [html.escape(part.strip()) for part in line.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([html.escape(part.strip()) for part in lines[i].strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead><tbody>")
            for row in rows:
                out.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
            out.append("</tbody></table>")
            continue
        elif line:
            out.append(f"<p>{html.escape(line)}</p>")
        i += 1
    return "\n".join(out)


def counts(case_dir: Path) -> dict[str, int]:
    record_dir = case_dir / "records"
    return {
        "Sources": len(read_jsonl(record_dir / "sources.jsonl")),
        "Entities": len(read_jsonl(record_dir / "entities.jsonl")),
        "Claims": len(read_jsonl(record_dir / "claims.jsonl")),
        "Events": len(read_jsonl(record_dir / "events.jsonl")),
        "Relationships": len(read_jsonl(record_dir / "relationships.jsonl")),
        "Source spans": len(read_jsonl(record_dir / "source_spans.jsonl")),
    }


def build_chart_payload(case_dir: Path) -> list[dict]:
    analysis_dir = case_dir / "exports" / "internal" / "analysis_charts"
    charts_dir = case_dir / "exports" / "internal" / "charts"
    files = [
        analysis_dir / "analysis_charts.html",
        charts_dir / "people_graph.html",
        charts_dir / "subcase_timelines.html",
        *sorted(path for path in analysis_dir.glob("[0-9][0-9]_*.html")),
    ]
    return [
        {
            "title": file_title(path),
            "kind": "Generated HTML",
            "file": path.relative_to(case_dir).as_posix(),
            "b64": encode_file(path),
        }
        for path in files
        if path.exists()
    ]


def audit_cards(case_dir: Path) -> list[dict]:
    exports = case_dir / "exports"
    specs = [
        ("Public export", exports / "public_export_audit.json", "issue_count"),
        ("Privacy redaction", exports / "privacy_redaction_audit.json", "issue_count"),
        ("Narrative readiness", exports / "narrative_readiness_review.json", "issue_count"),
        ("Source independence", exports / "source_independence_report.json", "flag_count"),
        ("Contradictions", exports / "claim_contradiction_audit.json", "flag_count"),
    ]
    cards = []
    for label, path, count_key in specs:
        data = read_json(path)
        summary = ", ".join(f"{k}: {v}" for k, v in data.get("summary", {}).items()) or "none"
        cards.append({"label": label, "count": data.get(count_key, 0), "summary": summary})
    return cards


def claim_status(case_dir: Path) -> list[tuple[str, int]]:
    rows = read_jsonl(case_dir / "records" / "claims.jsonl")
    return Counter(row.get("status", "unknown") for row in rows).most_common()


def slide_data(case_dir: Path) -> dict:
    return {
        "case": read_json(case_dir / "case.json"),
        "counts": counts(case_dir),
        "audits": audit_cards(case_dir),
        "claim_status": claim_status(case_dir),
        "charts": build_chart_payload(case_dir),
        "source_rows": summary_rows(case_dir / "exports" / "internal" / "analysis_charts" / "source_quality_dashboard.csv"),
        "readiness_rows": summary_rows(case_dir / "exports" / "internal" / "analysis_charts" / "public_narrative_readiness.csv"),
        "evidence_html": md_to_html((case_dir / "exports" / "evidence_board.md").read_text(encoding="utf-8")),
    }


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render(data: dict) -> str:
    case = data["case"]
    counts_html = "".join(f"<div class='metric'><b>{v}</b><span>{esc(k)}</span></div>" for k, v in data["counts"].items())
    audit_html = "".join(
        f"<article class='audit'><b>{esc(a['count'])}</b><span>{esc(a['label'])}</span><p>{esc(a['summary'])}</p></article>"
        for a in data["audits"]
    )
    status_html = "".join(f"<li><span>{esc(status)}</span><b>{count}</b></li>" for status, count in data["claim_status"])
    source_html = "".join(
        "<tr>"
        f"<td>{esc(row.get('source_id', ''))}</td><td>{esc(row.get('grade', row.get('reliability_grade', '')))}</td>"
        f"<td>{esc(row.get('title', ''))}</td><td>{esc(row.get('publisher', ''))}</td>"
        "</tr>"
        for row in data["source_rows"]
    )
    readiness_html = "".join(
        "<tr>"
        f"<td>{esc(row.get('claim_id', row.get('record_id', '')))}</td><td>{esc(row.get('status', ''))}</td>"
        f"<td>{esc(row.get('public_export', ''))}</td><td>{esc(row.get('privacy_review', ''))}</td>"
        "</tr>"
        for row in data["readiness_rows"]
    )
    chart_slides = "".join(
        f"<section class='slide chart-slide' data-title='{esc(chart['title'])}'><div class='slide-head'><p>{esc(chart['kind'])}</p><h2>{esc(chart['title'])}</h2><code>{esc(chart['file'])}</code></div><iframe title='{esc(chart['title'])}' data-chart-index='{idx}' loading='lazy'></iframe></section>"
        for idx, chart in enumerate(data["charts"])
    )
    charts_json = json.dumps(data["charts"], separators=(",", ":")).replace("</", "<\\/")
    total = 5 + len(data["charts"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(case.get('title'))} - Internal Slide Deck</title>
<script>(function(){{try{{var s=localStorage.getItem('crk-slide-theme');var d=s?s==='dark':matchMedia('(prefers-color-scheme: dark)').matches;document.documentElement.classList.toggle('dark',d)}}catch(e){{}}}})();</script>
<style>
:root{{--bg:#f7f4ee;--ink:#191817;--muted:#68625b;--panel:#fffdf8;--line:#d6cec2;--accent:#b9472d;--blue:#315b77;--green:#3b705c;--amber:#a17122;--shadow:0 16px 48px rgba(31,27,22,.12);--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;--sans:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--serif:Georgia,"Times New Roman",serif}}html.dark{{--bg:#141618;--ink:#f4f1ea;--muted:#b9b2a7;--panel:#1f2326;--line:#3b4144;--accent:#e06b50;--blue:#7aa7c7;--green:#84b69c;--amber:#d1a454;--shadow:0 18px 60px rgba(0,0,0,.45)}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);overflow:hidden}}button{{font:inherit;color:inherit}}.deck{{height:100vh;width:100vw;display:grid;grid-template-columns:260px 1fr}}.rail{{border-right:1px solid var(--line);padding:18px;background:color-mix(in srgb,var(--panel) 84%,transparent);overflow:auto}}.brand{{font-family:var(--serif);font-size:20px;line-height:1.2;margin-bottom:12px}}.notice{{font-size:12px;line-height:1.45;color:var(--muted);border:1px solid var(--line);border-radius:8px;padding:10px;margin:14px 0}}.nav{{display:grid;gap:5px;margin:16px 0}}.nav button,.topbar button{{border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:8px 10px;text-align:left;cursor:pointer}}.nav button[aria-current=true]{{border-color:var(--accent);box-shadow:inset 3px 0 0 var(--accent)}}.topbar{{position:fixed;right:18px;top:14px;display:flex;gap:8px;z-index:5}}.stage{{position:relative;height:100vh;overflow:hidden}}.slide{{position:absolute;inset:0;padding:6vh 5vw;display:none;align-items:center;justify-content:center}}.slide.active{{display:flex}}.inner{{width:min(1120px,100%);max-height:88vh}}.eyebrow{{font-family:var(--mono);font-size:12px;text-transform:uppercase;color:var(--accent);margin-bottom:18px}}h1,h2{{font-family:var(--serif);font-weight:500;letter-spacing:0;line-height:1.08;margin:0}}h1{{font-size:clamp(38px,6vw,78px)}}h2{{font-size:clamp(28px,4vw,52px)}}p{{line-height:1.55}}.subtitle{{font-size:18px;max-width:760px;color:var(--muted)}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:34px}}.metric,.audit{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px;box-shadow:var(--shadow)}}.metric b,.audit b{{font-size:34px;display:block}}.metric span,.audit span{{font-family:var(--mono);font-size:12px;color:var(--muted);text-transform:uppercase}}.audit-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:28px}}.audit p{{font-size:12px;color:var(--muted);margin:10px 0 0}}.status-list{{list-style:none;padding:0;margin:28px 0;display:grid;gap:10px;max-width:620px}}.status-list li{{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding:10px 0}}.split{{display:grid;grid-template-columns:.85fr 1.15fr;gap:32px;align-items:start}}table{{width:100%;border-collapse:collapse;font-size:12px;background:var(--panel);border:1px solid var(--line)}}th,td{{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:8px}}th{{font-family:var(--mono);color:var(--muted)}}.scroll{{max-height:70vh;overflow:auto;border:1px solid var(--line);border-radius:8px;background:var(--panel);padding:18px}}.scroll h1{{font-size:24px}}.scroll h2{{font-size:20px;margin-top:22px}}.scroll h3{{font-size:15px;margin-top:18px}}.chart-slide{{padding:3.5vh 3.5vw;display:none;flex-direction:column;align-items:stretch;gap:12px}}.chart-slide.active{{display:flex}}.slide-head{{display:grid;grid-template-columns:1fr auto;gap:6px 18px;align-items:end}}.slide-head p{{grid-column:1/-1;margin:0;color:var(--accent);font-family:var(--mono);font-size:12px;text-transform:uppercase}}.slide-head h2{{font-size:24px}}.slide-head code{{font-family:var(--mono);font-size:12px;color:var(--muted)}}iframe{{width:100%;height:calc(100vh - 128px);border:1px solid var(--line);border-radius:8px;background:white;box-shadow:var(--shadow)}}#counter{{position:fixed;left:18px;bottom:16px;font-family:var(--mono);font-size:12px;color:var(--muted)}}@media(max-width:900px){{.deck{{grid-template-columns:1fr}}.rail{{display:none}}.metrics,.audit-grid,.split{{grid-template-columns:1fr}}.slide{{padding:7vh 6vw}}}}
</style>
</head>
<body>
<div class="deck">
<aside class="rail"><div class="brand">Roach / Morava / WWASPS</div><div class="notice">Internal review deck. Includes private/excluded and weak-claim rows because chart exports used --include-private.</div><nav class="nav" id="nav"></nav></aside>
<main class="stage" id="stage">
<section class="slide active" data-title="Title"><div class="inner"><div class="eyebrow">Internal evidence deck</div><h1>{esc(case.get('title'))}</h1><p class="subtitle">One-file slide wrapper around the generated CRK evidence board, case charts, and analysis dashboards. This is not a public-safe export.</p><div class="metrics">{counts_html}</div></div></section>
<section class="slide" data-title="Safety Gate"><div class="inner"><div class="eyebrow">Public-output status</div><h2>Public chart exports are blocked; this deck is for internal review.</h2><div class="audit-grid">{audit_html}</div></div></section>
<section class="slide" data-title="Claim Status"><div class="inner split"><div><div class="eyebrow">Claim posture</div><h2>Use status and confidence before narration.</h2><ul class="status-list">{status_html}</ul></div><div><div class="eyebrow">Readiness rows</div><table><thead><tr><th>Record</th><th>Status</th><th>Public</th><th>Privacy</th></tr></thead><tbody>{readiness_html}</tbody></table></div></div></section>
<section class="slide" data-title="Sources"><div class="inner"><div class="eyebrow">Source ledger sample</div><h2>Captured sources remain the evidence base.</h2><table><thead><tr><th>ID</th><th>Grade</th><th>Title</th><th>Publisher</th></tr></thead><tbody>{source_html}</tbody></table></div></section>
<section class="slide" data-title="Evidence Board"><div class="inner"><div class="eyebrow">Generated Markdown report</div><h2>Evidence board</h2><div class="scroll">{data['evidence_html']}</div></div></section>
{chart_slides}
</main>
</div>
<div class="topbar"><button id="prev" title="Previous slide">Prev</button><button id="next" title="Next slide">Next</button><button id="open" title="Open embedded chart in a new tab">Open chart</button><button id="theme" title="Toggle theme">Theme</button></div><div id="counter">1 / {total}</div>
<script id="chart-data" type="application/json">{charts_json}</script>
<script>
(()=>{{const slides=Array.from(document.querySelectorAll('.slide')),charts=JSON.parse(document.getElementById('chart-data').textContent),nav=document.getElementById('nav'),counter=document.getElementById('counter');let current=0;function srcDoc(i){{const chart=charts[i];return chart?atob(chart.b64):''}}function loadSlide(slide){{const frame=slide.querySelector('iframe[data-chart-index]');if(!frame||frame.dataset.loaded)return;frame.srcdoc=srcDoc(Number(frame.dataset.chartIndex));frame.dataset.loaded='true'}}function go(index){{current=Math.max(0,Math.min(slides.length-1,index));slides.forEach((slide,idx)=>{{slide.classList.toggle('active',idx===current);nav.children[idx].setAttribute('aria-current',idx===current?'true':'false')}});loadSlide(slides[current]);loadSlide(slides[current+1]||slides[current]);counter.textContent=`${{current+1}} / ${{slides.length}}`}}slides.forEach((slide,idx)=>{{const button=document.createElement('button');button.textContent=`${{idx+1}}. ${{slide.dataset.title||'Slide'}}`;button.addEventListener('click',()=>go(idx));nav.appendChild(button)}});document.getElementById('prev').addEventListener('click',()=>go(current-1));document.getElementById('next').addEventListener('click',()=>go(current+1));document.getElementById('theme').addEventListener('click',()=>{{document.documentElement.classList.toggle('dark');localStorage.setItem('crk-slide-theme',document.documentElement.classList.contains('dark')?'dark':'light')}});document.getElementById('open').addEventListener('click',()=>{{const frame=slides[current].querySelector('iframe');if(frame&&frame.srcdoc)window.open(URL.createObjectURL(new Blob([frame.srcdoc],{{type:'text/html'}})),'_blank','noopener')}});document.addEventListener('keydown',event=>{{if(['ArrowRight','ArrowDown','PageDown',' '].includes(event.key)){{event.preventDefault();go(current+1)}}if(['ArrowLeft','ArrowUp','PageUp'].includes(event.key)){{event.preventDefault();go(current-1)}}if(event.key==='Home')go(0);if(event.key==='End')go(slides.length-1)}});go(0)}})();
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    case_dir = args.case_dir
    out = args.out or case_dir / DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(slide_data(case_dir)), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
