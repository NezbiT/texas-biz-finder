"""Generate HTML reports for saved website analyses."""

from __future__ import annotations

import html
import json

from backend.app.models.lead import Lead
from backend.app.models.website_analysis import WebsiteAnalysis


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [str(item) for item in data] if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def generate_analysis_report(lead: Lead, analysis: WebsiteAnalysis) -> str:
    """Build a printable HTML report for sales proposals."""
    technologies = _parse_json_list(analysis.technologies_json)
    seo_issues = _parse_json_list(analysis.seo_issues_json)
    created = analysis.created_at.strftime("%Y-%m-%d %H:%M UTC")

    tech_items = "".join(f"<li>{html.escape(t)}</li>" for t in technologies) or "<li>None detected</li>"
    issue_items = (
        "".join(f"<li>{html.escape(i)}</li>" for i in seo_issues)
        or "<li>No major SEO issues detected</li>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Website Analysis — {html.escape(lead.name)}</title>
  <style>
    body {{ font-family: Inter, Segoe UI, sans-serif; margin: 2rem; color: #0f172a; line-height: 1.5; }}
    h1, h2 {{ color: #312e81; }}
    .card {{ border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.25rem; margin: 1rem 0; }}
    .muted {{ color: #64748b; font-size: 0.9rem; }}
    ul {{ padding-left: 1.25rem; }}
    .badge {{ display: inline-block; background: #ede9fe; color: #5b21b6; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.8rem; }}
  </style>
</head>
<body>
  <p class="muted">TX BizFinder · txbizfinder.com · Generated {html.escape(created)}</p>
  <h1>Website Analysis Report</h1>
  <div class="card">
    <h2>Business</h2>
    <p><strong>{html.escape(lead.name)}</strong><br />
    {html.escape(lead.city)}, {html.escape(lead.state)} {html.escape(lead.zip_code or "")}</p>
    <p>Lead ID: {lead.id} · Analysis ID: {analysis.id}</p>
  </div>
  <div class="card">
    <h2>URL</h2>
    <p><a href="{html.escape(analysis.url)}">{html.escape(analysis.url)}</a></p>
    {f'<p class="muted">Final URL: {html.escape(analysis.final_url)}</p>' if analysis.final_url else ""}
    <p>Status: <span class="badge">{html.escape(analysis.status)}</span></p>
  </div>
  <div class="card">
    <h2>Performance</h2>
    <ul>
      <li>Load time: {html.escape(str(analysis.load_time_ms or "n/a"))} ms</li>
      <li>DOM content loaded: {html.escape(str(analysis.dom_content_loaded_ms or "n/a"))} ms</li>
      <li>Last modified: {html.escape(analysis.last_modified or "Unknown")}</li>
    </ul>
  </div>
  <div class="card">
    <h2>Technologies</h2>
    <ul>{tech_items}</ul>
  </div>
  <div class="card">
    <h2>SEO Snapshot</h2>
    <p><strong>Title:</strong> {html.escape(analysis.seo_title or "—")}</p>
    <p><strong>Meta description:</strong> {html.escape(analysis.seo_meta_description or "—")}</p>
    <p><strong>H1:</strong> {html.escape(analysis.seo_h1 or "—")}</p>
    <h3>Issues</h3>
    <ul>{issue_items}</ul>
  </div>
  <div class="card">
    <h2>Summary</h2>
    <p>{html.escape(analysis.summary or "No summary available.")}</p>
  </div>
  {f'<div class="card"><h2>Error</h2><p>{html.escape(analysis.error_message)}</p></div>' if analysis.error_message else ""}
</body>
</html>"""