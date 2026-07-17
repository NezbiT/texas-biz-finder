"""Análisis profundo de sitios web con Playwright (Chromium headless, async).

Navega la URL como un navegador real y extrae: tiempos de carga, metadatos
SEO, tecnologías y señales de "sitio anticuado" — la munición de venta.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

# Reutiliza los detectores del pipeline (stack tecnológico y análisis legacy)
from scripts.common.website_analysis import _detect_tech_stack, analyze_website_content


@dataclass
class SeoAudit:
    """Radiografía SEO básica de la página."""
    title: str | None = None                       # <title>
    meta_description: str | None = None            # <meta name=description>
    h1: str | None = None                          # primer H1
    issues: list[str] = field(default_factory=list)   # problemas encontrados


@dataclass
class DeepAnalysisResult:
    """Todo lo que devuelve un análisis (se persiste en website_analyses)."""
    url: str                                       # URL solicitada
    final_url: str | None = None                   # URL final tras redirects
    page_title: str | None = None                  # título según Playwright
    last_modified: str | None = None               # header/meta de última modificación
    load_time_ms: float | None = None              # tiempo total medido
    dom_content_loaded_ms: float | None = None     # DOMContentLoaded del navigation timing
    technologies: list[str] = field(default_factory=list)   # stack detectado
    seo: SeoAudit = field(default_factory=SeoAudit)
    summary: str = ""                              # resumen legible para la nota del lead
    metrics: dict[str, object] = field(default_factory=dict)   # métricas extra
    status: str = "completed"                      # completed | failed
    error_message: str | None = None               # detalle si falló


def _ensure_scheme(url: str) -> str:
    """Añade https:// si el usuario pegó la URL sin esquema."""
    url = url.strip()
    if url.startswith(("http://", "https://")):
        return url
    return f"https://{url}"


def _parse_last_modified(header_value: str | None, html: str) -> str | None:
    """Última modificación: primero el header HTTP, si no, metas del HTML."""
    if header_value:
        return header_value.strip()

    # Variantes de meta que usan CMSs para declarar la fecha de modificación
    meta_patterns = (
        r'<meta[^>]+property=["\']article:modified_time["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+name=["\']last-modified["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+http-equiv=["\']last-modified["\'][^>]+content=["\']([^"\']+)',
    )
    for pattern in meta_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _audit_seo(html: str, page_title: str | None) -> SeoAudit:
    """Extrae title/description/H1 del HTML y lista los problemas SEO clásicos."""
    # <title> del HTML (o el título que reportó Playwright como fallback)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = (title_match.group(1).strip() if title_match else page_title) or None

    # <meta name="description" content="...">
    meta_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)',
        html,
        re.IGNORECASE,
    )
    meta_description = meta_match.group(1).strip() if meta_match else None

    # Todos los H1: se limpian las etiquetas internas y se descartan vacíos
    h1_matches = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    h1_texts = [re.sub(r"<[^>]+>", "", h).strip() for h in h1_matches]
    h1_texts = [h for h in h1_texts if h]
    h1 = h1_texts[0] if h1_texts else None

    # Checklist SEO con los umbrales estándar de la industria
    issues: list[str] = []
    if not title:
        issues.append("Missing <title> tag")
    elif len(title) < 15:
        issues.append("Title is very short (< 15 characters)")
    elif len(title) > 70:
        issues.append("Title is long (> 70 characters) — may truncate in Google")

    if not meta_description:
        issues.append("Missing meta description")
    elif len(meta_description) < 50:
        issues.append("Meta description is short (< 50 characters)")
    elif len(meta_description) > 160:
        issues.append("Meta description is long (> 160 characters)")

    if not h1_texts:
        issues.append("Missing H1 heading")
    elif len(h1_texts) > 1:
        issues.append(f"Multiple H1 headings found ({len(h1_texts)})")

    # Sin meta viewport = probablemente no responsive (móvil roto)
    if not re.search(r"viewport", html, re.IGNORECASE):
        issues.append("Missing viewport meta (mobile responsiveness)")

    # Sin lang en <html> = accesibilidad/SEO internacional pobre
    if not re.search(r"<html[^>]+lang=", html, re.IGNORECASE):
        issues.append("Missing lang attribute on <html>")

    return SeoAudit(title=title, meta_description=meta_description, h1=h1, issues=issues)


def _build_summary(
    *,
    load_time_ms: float | None,
    technologies: list[str],
    seo: SeoAudit,
    legacy_analysis,
    uses_https: bool,
) -> str:
    """Redacta el resumen de venta a partir de los hallazgos técnicos."""
    parts: list[str] = []

    # Velocidad: lenta = argumento de venta directo
    if load_time_ms is not None:
        if load_time_ms > 4000:
            parts.append(f"Slow load time (~{load_time_ms:.0f} ms) — opportunity for a faster modern site.")
        elif load_time_ms > 2500:
            parts.append(f"Moderate load time (~{load_time_ms:.0f} ms).")
        else:
            parts.append(f"Acceptable load time (~{load_time_ms:.0f} ms).")

    # Stack detectado (o la ausencia de uno, también reveladora)
    if technologies:
        parts.append("Technologies: " + ", ".join(technologies) + ".")
    else:
        parts.append("No major CMS/framework detected — may be a basic or custom HTML site.")

    # Conteo de problemas SEO
    if seo.issues:
        parts.append(f"SEO gaps: {len(seo.issues)} issue(s) found.")
    else:
        parts.append("Basic SEO tags look acceptable.")

    # Veredicto de modernidad del análisis legacy → ángulo del pitch
    if legacy_analysis and not legacy_analysis.has_modern_website:
        parts.append("Site signals look dated — strong candidate for a website refresh.")
    elif legacy_analysis and legacy_analysis.has_modern_website:
        parts.append("Site appears relatively modern; pitch should focus on conversion and local SEO.")

    # Sin HTTPS = bandera roja de seguridad/confianza
    if not uses_https:
        parts.append("Site does not use HTTPS — security and trust concern.")

    return " ".join(parts)


async def analyze_url_with_playwright(
    url: str,
    *,
    navigation_timeout_ms: int = 25_000,   # tope para que la página cargue
    total_timeout_ms: int = 30_000,        # tope de las demás operaciones
) -> DeepAnalysisResult:
    """Navega con Playwright y extrae rendimiento, SEO y señales de stack."""
    target = _ensure_scheme(url)
    started = time.perf_counter()   # cronómetro del tiempo de carga total

    # Import perezoso: si Playwright no está instalado, error claro sin tumbar la API
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeout
        from playwright.async_api import async_playwright
    except ImportError as exc:
        return DeepAnalysisResult(
            url=target,
            status="failed",
            error_message="Playwright is not installed. Run: pip install playwright && playwright install chromium",
        )

    try:
        async with async_playwright() as playwright:
            # Chromium invisible (headless) — el navegador real completo
            browser = await playwright.chromium.launch(headless=True)
            try:
                # Contexto con User-Agent identificable (cortesía con los sitios)
                context = await browser.new_context(
                    user_agent="TXBizFinder/3.0 (+https://www.txbizfinder.com)",
                )
                page = await context.new_page()
                page.set_default_timeout(total_timeout_ms)

                # Navega y espera al DOMContentLoaded (no a todos los recursos)
                response = await page.goto(
                    target,
                    wait_until="domcontentloaded",
                    timeout=navigation_timeout_ms,
                )
                await page.wait_for_timeout(500)   # margen para JS tardío

                html = await page.content()        # HTML final (post-JavaScript)
                final_url = page.url               # URL tras redirects
                page_title = await page.title()

                # Navigation Timing API del navegador: métricas de carga reales
                timing = await page.evaluate(
                    """() => {
                        const nav = performance.getEntriesByType('navigation')[0];
                        if (!nav) return null;
                        return {
                            domContentLoaded: nav.domContentLoadedEventEnd,
                            loadEventEnd: nav.loadEventEnd,
                            responseEnd: nav.responseEnd,
                        };
                    }"""
                )

                load_time_ms = (time.perf_counter() - started) * 1000
                # DOMContentLoaded validado (número positivo o None)
                dom_ms = None
                if isinstance(timing, dict):
                    dom_ms = timing.get("domContentLoaded")
                    if isinstance(dom_ms, (int, float)) and dom_ms > 0:
                        dom_ms = float(dom_ms)

                # Headers de la respuesta normalizados a minúsculas
                headers: dict[str, str] = {}
                if response:
                    headers = {k.lower(): v for k, v in response.headers.items()}

                # Las tres extracciones principales
                last_modified = _parse_last_modified(headers.get("last-modified"), html)
                technologies = _detect_tech_stack(html, headers)
                seo = _audit_seo(html, page_title)

                # Análisis "legacy" del pipeline (modernidad, antigüedad, notas)
                legacy = analyze_website_content(
                    website_url=target,
                    html=html,
                    final_url=final_url,
                    headers=headers,
                )
                uses_https = urlparse(final_url).scheme == "https"

                # Métricas sueltas que van al campo metrics_json
                metrics: dict[str, object] = {
                    "http_status": response.status if response else None,
                    "uses_https": uses_https,
                    "has_modern_website": legacy.has_modern_website,
                    "estimated_antiquity_years": legacy.estimated_antiquity_years,
                    "legacy_notes": legacy.analysis_notes,
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                }
                if timing:
                    metrics["navigation_timing"] = timing

                summary = _build_summary(
                    load_time_ms=load_time_ms,
                    technologies=technologies,
                    seo=seo,
                    legacy_analysis=legacy,
                    uses_https=uses_https,
                )

                # Resultado completo y exitoso
                return DeepAnalysisResult(
                    url=target,
                    final_url=final_url,
                    page_title=page_title,
                    last_modified=last_modified,
                    load_time_ms=round(load_time_ms, 1),
                    dom_content_loaded_ms=dom_ms,
                    technologies=technologies,
                    seo=seo,
                    summary=summary,
                    metrics=metrics,
                    status="completed",
                )
            finally:
                await browser.close()   # SIEMPRE cerrar el navegador (aunque falle)

    except PlaywrightTimeout:
        # El sitio no cargó a tiempo → resultado failed con explicación
        return DeepAnalysisResult(
            url=target,
            status="failed",
            error_message=f"Playwright timed out after {navigation_timeout_ms} ms",
        )
    except Exception as exc:  # noqa: BLE001 — cualquier otro fallo también se reporta
        return DeepAnalysisResult(
            url=target,
            status="failed",
            error_message=str(exc),
        )


def deep_result_to_json_fields(result: DeepAnalysisResult) -> dict[str, str | None]:
    """Serializa las listas/dicts a JSON para las columnas TEXT de la tabla."""
    return {
        "technologies_json": json.dumps(result.technologies),
        "seo_issues_json": json.dumps(result.seo.issues),
        "metrics_json": json.dumps(result.metrics),
    }
