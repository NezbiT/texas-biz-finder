#!/usr/bin/env python3
"""Generate TxBizFinder Intelligence data & implementation roadmap PDF."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent / "TxBizFinder_Data_Roadmap.pdf"


class PDF(FPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "TxBizFinder Intelligence - Roadmap de datos y APIs", align="L")
        self.ln(8)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            8,
            f"Pagina {self.page_no()}/{{nb}}  |  Confidencial - plan de producto  |  {date.today().isoformat()}",
            align="C",
        )

    def _w(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def h1(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(15, 23, 42)
        self.multi_cell(self._w(), 8, text)
        self.ln(2)

    def h2(self, text: str) -> None:
        self.ln(2)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(30, 64, 175)
        self.multi_cell(self._w(), 7, text)
        self.ln(1)

    def h3(self, text: str) -> None:
        self.ln(1)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(15, 23, 42)
        self.multi_cell(self._w(), 6, text)
        self.ln(0.5)

    def body(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 30, 30)
        self.multi_cell(self._w(), 5, text)
        self.ln(1)

    def bullet(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 30, 30)
        self.multi_cell(self._w(), 5, f"- {text}")

    def kv(self, label: str, value: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(15, 23, 42)
        self.multi_cell(self._w(), 5, f"{label}: {value}")


def clean(s: str) -> str:
    """FPDF core fonts: keep latin-1 safe text."""
    repl = {
        "—": "-",
        "–": "-",
        "•": "-",
        "→": "->",
        "×": "x",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "...",
        "≤": "<=",
        "≥": ">=",
        "✓": "[OK]",
        "❌": "[X]",
        "⚠": "!",
        "ñ": "n",
        "Ñ": "N",
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "Á": "A",
        "É": "E",
        "Í": "I",
        "Ó": "O",
        "Ú": "U",
        "¿": "?",
        "¡": "!",
        "°": " deg",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def main() -> None:
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # Cover
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 55, "F")
    pdf.set_xy(10, 18)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 9, clean("TxBizFinder Intelligence"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(10)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(190, 7, clean("Roadmap: lo que falta + APIs publicas + scraping"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(190, 5, clean(f"Generado {date.today().isoformat()}  |  Suite Texas SaaS"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(10, 65)
    pdf.set_text_color(30, 30, 30)
    pdf.h1(clean("1. Resumen ejecutivo"))
    pdf.body(
        clean(
            "Este documento describe (1) que falta implementar para convertir la suite en un SaaS "
            "credible frente a portales tipo FEMA/aseguradoras, (2) de donde obtener datos con APIs "
            "publicas (preferido: mayor validacion y estabilidad), y (3) donde el scraping es "
            "necesario o util como fallback, con riesgos legales y tecnicos."
        )
    )
    pdf.body(
        clean(
            "Principio de diseno: API oficial o open data > bulk CSV/geospatial > scrape HTML. "
            "Nunca scrapear en el request del usuario; siempre workers (CLI + cron/Actions)."
        )
    )

    pdf.h2(clean("Apps de la suite y puertos locales"))
    for line in [
        "MapHub Texas (command center): http://127.0.0.1:3015",
        "FloodGuard Texas: http://127.0.0.1:3013",
        "PowerPulse Texas: http://127.0.0.1:3014",
        "PermitRadar Houston: http://127.0.0.1:3010",
        "ChannelWatch: http://127.0.0.1:3011",
        "Emissions Sentinel API: http://127.0.0.1:8001",
        "TxBizFinder API: http://127.0.0.1:8000",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("Estado actual (ya implementado)"))
    for line in [
        "FloodGuard: NWS live alerts (api.weather.gov) + demo risk por ZIP + boost hibrido",
        "PowerPulse: demo ERCOT-style + ZIP3 -> region",
        "MapHub: multi-layer + /api/suite/overview (Texas pulse)",
        "PermitRadar: permisos Houston (xlsx) + multi-city open data (ingest CLI)",
        "ChannelWatch: live Open-Meteo/NOAA/NWS + ingest TCEQ/AirNow opcional",
        "Emissions Sentinel: warehouse multi-source + anomalías (demo fallback fuerte)",
        "TxBizFinder: franchise tax + TABC join + research web Playwright",
        "Contratos suite: /api/health y /api/suite/meta en productos Nuxt",
    ]:
        pdf.bullet(clean(line))

    # Section 2
    pdf.add_page()
    pdf.h1(clean("2. Lo que FALTA implementar (backlog priorizado)"))

    pdf.h2(clean("P0 — Credibilidad comercial (4-8 semanas)"))
    items_p0 = [
        ("Gateway SaaS", "api.txbizfinder.com con API keys, rate limits por tier (Free/Contractor/Pro/Enterprise), billing Stripe."),
        ("Auth unificada", "Clerk o Supabase Auth para seats humanos; API keys para maquinas; rotar admin-dev-key."),
        ("FEMA NFHL", "Poligonos SFHA oficiales en FloodGuard Pro (FeatureServer/WMS). Diferenciador vs demo."),
        ("OpenFEMA NFIP", "Claims/density por ZIP para narrativa aseguradoras (no cotizacion)."),
        ("EIA + AirNow keys", "Energia y AQI reales en PowerPulse/Channel/Sentinel (registro free)."),
        ("Envelope + OpenAPI", "Respuesta estandar {data, meta} y OpenAPI por producto + gateway."),
        ("Legal/ToS", "Disclaimers fuertes: no FEMA determination, no insurance advice, no ERCOT ops."),
    ]
    for title, desc in items_p0:
        pdf.h3(clean(title))
        pdf.body(clean(desc))

    pdf.h2(clean("P1 — Datos y producto (siguiente sprint)"))
    for title, desc in [
        ("USGS NWIS gauges", "Caudales/rios en mapa flood/channel."),
        ("CAMPD + GHGRP + eGRID bulk", "Capas industriales para underwriting / Sentinel."),
        ("ERCOT public feeds", "Reemplazar demo de PowerPulse (revisar terminos de uso)."),
        ("TCEQ GIS services", "Inventarios y capas TX estables vs scrape HTML frágil."),
        ("Alertas Contractor", "Saved ZIP, email/SMS digest de permisos y flood watches."),
        ("Webhooks Pro", "Nuevo permiso por ZIP/tag; anomalia high en facility."),
        ("Tests + CI smoke", "pytest + health checks suite overview en Actions."),
    ]:
        pdf.h3(clean(title))
        pdf.body(clean(desc))

    pdf.h2(clean("P2 — Escala SaaS"))
    for line in [
        "MCP server + CLI (npx txbiz) estilo World Monitor",
        "SDK TypeScript/Python thin clients",
        "White-label MapHub + SSO Enterprise",
        "Bulk geocode + parcel join (seguros)",
        "Monorepo packages compartidos (@txbiz/suite-meta, map tokens)",
    ]:
        pdf.bullet(clean(line))

    # Section 3
    pdf.add_page()
    pdf.h1(clean("3. APIs publicas — MAYOR VALIDACION (preferir)"))
    pdf.body(
        clean(
            "Estas fuentes tienen documentacion oficial, SLAs implicitos de agencia, o contratos de open data. "
            "Usar primero. Validacion: schema estable, auth documentada, historico, citables en disclaimers."
        )
    )

    pdf.h2(clean("3.1 Inundacion / clima / hidrologia"))
    rows = [
        ("NWS api.weather.gov", "Free + User-Agent", "Alertas activas TX", "FloodGuard [OK] live", "Alta"),
        ("FEMA NFHL ArcGIS", "Free", "Zonas inundables oficiales", "Flood Pro PENDIENTE", "Muy alta (oficial)"),
        ("OpenFEMA datasets", "Free REST", "NFIP claims, desastres", "PENDIENTE", "Alta (federal)"),
        ("USGS Water Services", "Free", "Gauges / streamflow", "PENDIENTE", "Alta"),
        ("NOAA CO-OPS", "Free", "Nivel mar / marea TX", "ChannelWatch live parcial", "Alta"),
        ("Open-Meteo", "Free", "Weather + AQI modelado", "ChannelWatch live", "Media-alta"),
        ("NOAA ATLAS 14", "Free/bulk", "Precipitacion design", "PENDIENTE", "Alta (ingenieria)"),
    ]
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(42, 6, "Fuente", border=1)
    pdf.cell(32, 6, "Auth", border=1)
    pdf.cell(40, 6, "Uso", border=1)
    pdf.cell(40, 6, "Estado suite", border=1)
    pdf.cell(26, 6, "Validacion", border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    for r in rows:
        pdf.set_x(pdf.l_margin)
        for i, c in enumerate(r):
            w = [42, 32, 40, 40, 26][i]
            pdf.cell(w, 5, clean(c)[:28], border=1)
        pdf.ln()

    pdf.ln(3)
    pdf.h2(clean("3.2 Aire / emisiones / energia"))
    rows2 = [
        ("EPA AirNow", "Free key", "AQI tiempo real", "Opcional Channel/Sentinel", "Alta"),
        ("OpenAQ API", "Free key", "Monitores ambient", "Connector Sentinel", "Alta"),
        ("EPA CAMPD", "Free key", "CEMS plantas", "Parcial/demo Sentinel", "Alta"),
        ("EIA Open Data", "Free key", "Gen/demanda/fuels", "PENDIENTE Power/Sentinel", "Muy alta"),
        ("EPA GHGRP", "Bulk CSV", "GHG facilities", "Demo/bulk path", "Alta"),
        ("EPA eGRID", "Bulk", "Emission rates", "PENDIENTE", "Alta"),
        ("EPA TRI / Envirofacts", "API/bulk", "Releases toxicos", "Demo Channel", "Alta"),
        ("TCEQ open GIS", "Free services", "Inventarios TX", "Parcial", "Alta (estatal)"),
        ("ERCOT public", "Varies/ToS", "Grid TX", "Demo PowerPulse", "Media (ToS)"),
    ]
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 8)
    for i, h in enumerate(["Fuente", "Auth", "Uso", "Estado suite", "Validacion"]):
        pdf.cell([42, 32, 40, 40, 26][i], 6, h, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    for r in rows2:
        pdf.set_x(pdf.l_margin)
        for i, c in enumerate(r):
            pdf.cell([42, 32, 40, 40, 26][i], 5, clean(c)[:28], border=1)
        pdf.ln()

    pdf.ln(3)
    pdf.h2(clean("3.3 Permisos / negocios / geo"))
    rows3 = [
        ("data.texas.gov (Socrata)", "Free", "Franchise tax ~3.3M", "BizFinder bulk", "Alta"),
        ("TABC mixed beverage", "Free Socrata", "Alcohol receipts", "BizFinder join", "Alta"),
        ("Austin SODA", "Free (+token)", "Building permits", "ingest texas", "Alta"),
        ("Dallas Open Data", "Free", "Permits", "ingest texas", "Alta"),
        ("San Antonio CKAN", "Free", "Permits", "ingest texas", "Alta"),
        ("US Census Geocoder", "Free", "Batch lat/lon", "PermitRadar", "Alta"),
        ("Zippopotam / Census", "Free", "ZIP geocode", "MapHub/Channel", "Media"),
        ("OpenFreeMap tiles", "Free", "Map style", "Todas map apps", "Media"),
    ]
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 8)
    for i, h in enumerate(["Fuente", "Auth", "Uso", "Estado suite", "Validacion"]):
        pdf.cell([42, 32, 40, 40, 26][i], 6, h, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    for r in rows3:
        pdf.set_x(pdf.l_margin)
        for i, c in enumerate(r):
            pdf.cell([42, 32, 40, 40, 26][i], 5, clean(c)[:28], border=1)
        pdf.ln()

    pdf.ln(3)
    pdf.h3(clean("Como obtener keys free (pasos)"))
    for line in [
        "EIA: https://www.eia.gov/opendata/register.php -> EIA_API_KEY",
        "AirNow: https://docs.airnowapi.org/ -> AIRNOW_API_KEY",
        "OpenAQ: https://openaq.org/ -> OPENAQ_API_KEY",
        "CAMPD: https://www.epa.gov/power-sector/cam-api-portal -> CAMPD_API_KEY",
        "Socrata app token (opcional rate limit): data.texas.gov / city portals",
        "NWS: NO key; solo User-Agent descriptivo con contacto",
        "FEMA NFHL: services publicos ArcGIS (URL FeatureServer en docs FEMA)",
    ]:
        pdf.bullet(clean(line))

    # Section 4 scraping
    pdf.add_page()
    pdf.h1(clean("4. Donde HACER SCRAPER (y donde NO)"))
    pdf.body(
        clean(
            "Scraping solo cuando: (a) no hay API/open data, (b) el dueno publica datos para uso publico, "
            "(c) se respeta robots.txt, rate limits, y ToS, (d) se cachea en warehouse, (e) hay fallback."
        )
    )

    pdf.h2(clean("4.1 Scraping JUSTIFICADO / ya en uso"))
    scrape_ok = [
        (
            "Houston Permitting Center — weekly Permit Activity Reports (xlsx)",
            "https://www.houstonpermittingcenter.org/sold-permits-search",
            "PermitRadar ingest CLI + GitHub Actions semanal",
            "Pagina HTML con links a .xlsx; parse openpyxl/xlrd; geocode Census; upsert Supabase. "
            "Riesgo: cambio de markup o bloqueo DNS. Mitigar: selectors flexibles + alertas de fallos.",
        ),
        (
            "TCEQ CAMS daily summary / EER emission events",
            "Sitios TCEQ (URLs en config sources.yaml ChannelWatch)",
            "ChannelWatch FastAPI collectors (best-effort + fixture fallback)",
            "HTML fragil. Preferir migrar a TCEQ GIS/open data cuando exista capa equivalente.",
        ),
        (
            "DuckDuckGo HTML / search (descubrimiento de websites de leads)",
            "Servicio DDG + Playwright deep analysis",
            "TxBizFinder website research (1 job concurrente)",
            "Rate limit agresivo; no es dato gubernamental. Uso interno lead-gen.",
        ),
        (
            "ERCOT public dashboards (si no hay feed JSON estable)",
            "Paginas publicas ERCOT de demanda/condiciones",
            "PowerPulse PENDIENTE",
            "Revisar terminos antes de scrape; preferir EIA series como proxy nacional/regional.",
        ),
    ]
    for title, url, product, notes in scrape_ok:
        pdf.h3(clean(title))
        pdf.kv("URL / origen", clean(url))
        pdf.kv("Producto", clean(product))
        pdf.body(clean(notes))

    pdf.h2(clean("4.2 Scraping POSIBLE (bajo valor o alto riesgo) — evaluar caso a caso"))
    for line in [
        "TCEQ TAMIS (marcado planned en Sentinel) — preferir open data",
        "Portales municipales sin SODA/CKAN (ciudades chicas TX) — xlsx/PDF semanal",
        "Wayback Machine (API existe; no scrapear UI) para historico de dominios",
        "Listings comerciales de terceros (Yelp, etc.) — EVITAR (ToS + legal)",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("4.3 NO scrapear (usar API/bulk oficial)"))
    for line in [
        "FEMA flood maps / MSC — usar NFHL MapServer/FeatureServer",
        "EPA AQS/CAMPD/TRI — APIs y bulk oficiales",
        "EIA — Open Data API",
        "NWS — api.weather.gov (no scrapear weather.gov HTML)",
        "data.texas.gov / Socrata cities — SODA JSON, no HTML tables",
        "Sitios de aseguradoras privadas o paywalled MLS — fuera de scope",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("4.4 Patron de implementacion de scrapers"))
    for line in [
        "Worker Python CLI (python -m ingest ...) + cron/Actions — nunca en request HTTP del browser",
        "Idempotencia: tabla ingest_runs con checksum de archivo/URL",
        "Timeouts, retries exponential, User-Agent honesto con contacto",
        "Almacenar raw en data/raw/ y processed en Postgres",
        "Fixture/demo fallback si falla (ya en Channel EER y varios connectors)",
        "Monitoreo: data_runs / last_success visible en UI About o /api/meta/runs",
        "Legal: robots.txt, no sobrecargar, no eludir CAPTCHA/paywall",
    ]:
        pdf.bullet(clean(line))

    # Section 5 validation
    pdf.add_page()
    pdf.h1(clean("5. Mayor validacion — checklist por capa de datos"))
    pdf.body(clean("Para cada fuente, documentar en la UI (About) y en meta API:"))
    for line in [
        "Nombre de la fuente + URL oficial + fecha de ultima actualizacion (asOf)",
        "Cadencia (tiempo real / diario / semanal / anual)",
        "Licencia o ToS resumida",
        "Campos transformados vs crudos",
        "Flag demo:true cuando el dato es sintetico o ilustrativo",
        "Error rates del scraper en 7d",
        "Comparacion spot-check: muestra de 20 registros vs portal oficial",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("Niveles de confianza sugeridos en UI"))
    for line in [
        "Official (verde): FEMA NFHL, NWS alert, OpenFEMA, EIA series",
        "Agency open data (azul): Socrata city permits, data.texas.gov, USGS",
        "Best-effort scrape (ambar): Houston xlsx, TCEQ HTML",
        "Modeled / demo (gris): scores sinteticos, IsolationForest labels, ZIP3 map",
    ]:
        pdf.bullet(clean(line))

    pdf.h1(clean("6. Mapa producto -> fuente prioritaria"))
    mapping = [
        ("FloodGuard", "FEMA NFHL + NWS + USGS + OpenFEMA", "Solo si falta capa local no expuesta"),
        ("PowerPulse", "EIA + ERCOT public (ToS) + NOAA heat", "ERCOT HTML solo fallback"),
        ("ChannelWatch", "Open-Meteo + NOAA + AirNow + TCEQ GIS", "CAMS/EER HTML actual"),
        ("Emissions Sentinel", "EIA + CAMPD + OpenAQ + GHGRP/eGRID bulk", "Evitar scrapes ad-hoc"),
        ("PermitRadar", "SODA/CKAN multi-city + Houston xlsx", "Houston xlsx (ya)"),
        ("TxBizFinder", "data.texas.gov + TABC Socrata", "DDG/Playwright research"),
        ("MapHub", "Proxy a APIs de la suite (no inventa datos)", "N/A"),
    ]
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(36, 6, "Producto", border=1)
    pdf.cell(90, 6, "Prioridad API/open data", border=1)
    pdf.cell(54, 6, "Scrape", border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    for a, b, c in mapping:
        pdf.set_x(pdf.l_margin)
        pdf.cell(36, 6, clean(a)[:20], border=1)
        pdf.cell(90, 6, clean(b)[:52], border=1)
        pdf.cell(54, 6, clean(c)[:32], border=1)
        pdf.ln()

    pdf.ln(4)
    pdf.h1(clean("7. Plan de 30 dias (ejecutable)"))
    for i, line in enumerate(
        [
            "Semana 1: Registrar EIA + AirNow + OpenAQ; cablear Power/Channel; badges Official/Demo en UI",
            "Semana 2: Integrar FEMA NFHL FeatureServer (lookup por lat/lon + ZIP centroid) en Flood Pro path",
            "Semana 3: OpenFEMA claims aggregate por ZIP; USGS gauges en mapa Flood/Channel",
            "Semana 4: Gateway API keys + rate limit + Stripe skeleton; OpenAPI del suite overview",
        ],
        1,
    ):
        pdf.bullet(clean(f"{i}. {line}"))

    pdf.ln(3)
    pdf.h1(clean("8. Referencias de documentacion en repos"))
    for line in [
        "texas-biz-finder/docs/DATA_SOURCES_PUBLIC.md",
        "texas-biz-finder/docs/SUITE_SAAS.md",
        "texas-biz-finder/docs/SAAS_PLATFORM_REPORT.md",
        "*/docs/SUITE_SAAS.md en cada producto",
        "World Monitor (inspiracion UX/API, no copiar codigo AGPL a ciegas): github.com/koala73/worldmonitor",
    ]:
        pdf.bullet(clean(line))

    pdf.ln(4)
    pdf.set_x(pdf.l_margin)
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(
        pdf._w(),
        5,
        clean(
            "Aviso legal: este roadmap es plan de ingenieria. Los datos de riesgo de inundacion, red electrica "
            "y emisiones son informativos. No constituyen determinacion FEMA, consejo de seguros, ni instrucciones "
            "operativas de ERCOT/TCEQ/EPA. Validar siempre con fuentes oficiales y profesionales licenciados."
        ),
        fill=True,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
