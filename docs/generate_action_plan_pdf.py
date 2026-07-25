#!/usr/bin/env python3
"""Generate TxBizFinder Intelligence action plan PDF: gaps, APIs, legal, GTM, revenue."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent / "TxBizFinder_Plan_Accion_Completo.pdf"
OUT_ROOT = Path(__file__).resolve().parents[2] / "TxBizFinder_Plan_Accion_Completo.pdf"


class PDF(FPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "TxBizFinder Intelligence - Plan de accion completo", align="L")
        self.ln(8)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            8,
            f"Pagina {self.page_no()}/{{nb}}  |  Confidencial  |  {date.today().isoformat()}",
            align="C",
        )

    def _w(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def h1(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(15, 23, 42)
        self.multi_cell(self._w(), 8, text)
        self.ln(2)

    def h2(self, text: str) -> None:
        self.ln(2)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 64, 175)
        self.multi_cell(self._w(), 6, text)
        self.ln(1)

    def h3(self, text: str) -> None:
        self.ln(1)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(15, 23, 42)
        self.multi_cell(self._w(), 5, text)
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

    def callout(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_fill_color(241, 245, 249)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(30, 30, 30)
        self.multi_cell(self._w(), 5, text, fill=True)
        self.ln(2)

    def table(self, headers: list[str], rows: list[tuple], widths: list[float]) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 7)
        self.set_fill_color(30, 64, 175)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(widths[i], 6, clean(h)[: int(widths[i] / 1.6)], border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 7)
        self.set_text_color(30, 30, 30)
        fill = False
        for r in rows:
            if self.get_y() > 270:
                self.add_page()
            self.set_x(self.l_margin)
            if fill:
                self.set_fill_color(248, 250, 252)
            else:
                self.set_fill_color(255, 255, 255)
            for i, c in enumerate(r):
                self.cell(widths[i], 5, clean(str(c))[: int(widths[i] / 1.55)], border=1, fill=True)
            self.ln()
            fill = not fill
        self.ln(2)


def clean(s: str) -> str:
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
        "€": "EUR",
        "$": "$",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def main() -> None:
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # ── COVER ──
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 62, "F")
    pdf.set_xy(10, 16)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 9, clean("TxBizFinder Intelligence"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(10)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(
        190,
        7,
        clean("Plan de accion: lo que falta + APIs + legal + ventas + ingresos"),
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_x(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(
        190,
        5,
        clean(f"Generado {date.today().isoformat()}  |  Suite Texas SaaS  |  Confidencial"),
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_xy(10, 72)
    pdf.set_text_color(30, 30, 30)
    pdf.h1(clean("0. Resumen ejecutivo (1 pagina mental)"))
    pdf.body(
        clean(
            "Hoy la suite YA funciona en modo demo + algunas fuentes live (NWS, Open-Meteo, NOAA, "
            "FEMA NFHL parcial, permisos multi-ciudad, franchise tax). Para que el sitio sea "
            "credible comercialmente frente a portales tipo FEMA/aseguradoras y genere ingresos, "
            "falta: (1) keys free y cableado de APIs oficiales, (2) disclaimers legales fuertes, "
            "(3) auth + billing + gateway, (4) posicionamiento correcto (no reemplazas FEMA; "
            "aceleras triage), (5) go-to-market a contratistas, MGAs, brokers y, con cuidado, "
            "canales adyacentes a sector publico."
        )
    )
    pdf.h2(clean("Principio de producto (no negociable)"))
    pdf.bullet(clean("API oficial / open data > bulk CSV > scrape HTML (solo workers CLI/Actions)"))
    pdf.bullet(clean("Nunca scrapear en el request del usuario del browser"))
    pdf.bullet(clean("Todo dato demo debe ir con badge demo:true y color gris en UI"))
    pdf.bullet(
        clean(
            "NUNCA vender como: determinacion FEMA, cotizacion de seguro, o feed operativo ERCOT/TCEQ"
        )
    )

    # ── 1 GAPS ──
    pdf.add_page()
    pdf.h1(clean("1. Lo que FALTA para que el sitio funcione bien"))

    pdf.h2(clean("1.1 Por producto - estado y gap critico"))
    pdf.table(
        ["Producto", "Hoy", "Falta para 'bien'", "Prioridad"],
        [
            ("FloodGuard", "NFHL + NWS live + demo pins", "USGS gauges, OpenFEMA claims, badges Official", "P0"),
            ("PowerPulse", "Demo ERCOT-style + ZIP3", "EIA key live; ERCOT ToS o proxy EIA", "P0"),
            ("ChannelWatch", "Open-Meteo/NOAA/NWS live", "AirNow key; TCEQ GIS vs HTML scrape", "P0"),
            ("Emissions Sentinel", "Connectors + demo fuerte", "CAMPD/EIA keys; GHGRP/eGRID bulk", "P1"),
            ("PermitRadar", "Houston xlsx + SODA cities", "Mas ciudades TX; alertas email ZIP", "P1"),
            ("TxBizFinder", "Franchise tax + TABC + research", "Rate limits, CRM export, billing", "P1"),
            ("MapHub", "Proxy capas suite", "Pulse estable; no inventar datos", "P0"),
            ("Suite/Gateway", "Local :3099", "api.txbizfinder.com + API keys + Stripe", "P0"),
        ],
        [34, 48, 68, 20],
    )

    pdf.h2(clean("1.2 Plataforma SaaS (sin esto no cobras bien)"))
    for line in [
        "Auth unificada: Clerk o Supabase Auth (usuarios humanos) + API keys (maquinas)",
        "Gateway api.txbizfinder.com: rate limit por tier Free/Contractor/Pro/Enterprise",
        "Billing Stripe: suscripcion mensual + metered usage opcional (API calls)",
        "Envelope estandar {data, meta:{product,asOf,source,demo,confidence}} en TODOS los endpoints",
        "OpenAPI por producto + suite overview",
        "Monitoring: data_runs / last_success en About y /api/meta/runs",
        "CI smoke: health checks de los 7 productos en GitHub Actions",
        "Dominios y SSL: flood/power/radar/channel/sentinel/finder/map.txbizfinder.com",
        "Rotar ADMIN_API_KEY / admin-dev-key antes de exponer tunnels publicos",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("1.3 UX de credibilidad (semana 1)"))
    for line in [
        "Badge de confianza en UI: Official (verde), Agency open data (azul), Best-effort scrape (ambar), Modeled/demo (gris)",
        "Flag demo:true visible cuando el dato es sintetico",
        "Link 'View official source' junto a cada capa critica (FEMA MSC, NWS, TCEQ, EIA)",
        "About pages con asOf, cadencia, licencia resumida (ya parcialmente en meta APIs)",
        "Footer legal corto + pagina /legal o /terms + /privacy",
    ]:
        pdf.bullet(clean(line))

    # ── 2 APIs ──
    pdf.add_page()
    pdf.h1(clean("2. APIs y datos FALTANTES (checklist accionable)"))

    pdf.h2(clean("2.1 Keys free - REGISTRAR YA (0 USD)"))
    pdf.table(
        ["Env var", "Registro", "Producto", "Uso"],
        [
            ("EIA_API_KEY", "eia.gov/opendata/register.php", "Power + Sentinel", "Gen/demanda/fuels"),
            ("AIRNOW_API_KEY", "docs.airnowapi.org", "Channel + Sentinel", "AQI tiempo real"),
            ("OPENAQ_API_KEY", "openaq.org", "Sentinel", "Monitores ambient"),
            ("CAMPD_API_KEY", "epa.gov power-sector cam-api", "Sentinel", "CEMS plantas"),
            ("SOCRATA_APP_TOKEN", "data.texas.gov / city portals", "Radar + Finder", "Rate limit SODA"),
        ],
        [38, 58, 40, 34],
    )

    pdf.h2(clean("2.2 Como hacer el request (plantillas)"))
    pdf.h3(clean("A) NWS (ya live) - sin key"))
    pdf.body(
        clean(
            "GET https://api.weather.gov/alerts/active?area=TX\n"
            "Headers: User-Agent: TxBizFinderIntelligence/1.0 (contacto@tudominio.com); Accept: application/geo+json\n"
            "Regla: User-Agent DESCRIPTIVO con email de contacto. Sin esto NWS puede bloquear."
        )
    )
    pdf.h3(clean("B) EIA Open Data (PENDIENTE - P0 PowerPulse)"))
    pdf.body(
        clean(
            "1) Registrarte: https://www.eia.gov/opendata/register.php\n"
            "2) Guardar en .env: EIA_API_KEY=...\n"
            "3) Ejemplo series (electricidad):\n"
            "GET https://api.eia.gov/v2/electricity/rto/region-data/data/?api_key=TU_KEY&frequency=hourly&data[0]=value&facets[respondent][]=ERCO&sort[0][column]=period&sort[0][direction]=desc&length=24\n"
            "4) Cachear en warehouse (no llamar EIA en cada click de mapa)."
        )
    )
    pdf.h3(clean("C) EPA AirNow (PENDIENTE - P0 ChannelWatch)"))
    pdf.body(
        clean(
            "1) Registro: https://docs.airnowapi.org/\n"
            "2) .env: AIRNOW_API_KEY=...\n"
            "3) Ejemplo por lat/lon:\n"
            "GET https://www.airnowapi.org/aq/observation/latLong/current/?format=application/json&latitude=29.76&longitude=-95.37&distance=25&API_KEY=TU_KEY\n"
            "4) Mostrar como Official; si falla, fallback Open-Meteo modelado con badge Modeled."
        )
    )
    pdf.h3(clean("D) OpenAQ v3"))
    pdf.body(
        clean(
            "Header: X-API-Key: TU_KEY\n"
            "GET https://api.openaq.org/v3/locations?coordinates=29.76,-95.37&radius=25000&limit=20\n"
            "Usar en Sentinel ambient layer."
        )
    )
    pdf.h3(clean("E) EPA CAMPD"))
    pdf.body(
        clean(
            "Portal: https://www.epa.gov/power-sector/cam-api-portal\n"
            "Registro free key -> CAMPD_API_KEY\n"
            "Usar para CEMS de plantas (emisiones horarias). Preferir API/bulk oficial; NUNCA scrapear EPA HTML."
        )
    )
    pdf.h3(clean("F) FEMA NFHL (FeatureServer) - ya parcialmente"))
    pdf.body(
        clean(
            "Servicios publicos ArcGIS (sin key). Identify/query por lat/lon capa Flood Hazard Zones.\n"
            "Ejemplo conceptual: query geometry=point&geometryType=esriGeometryPoint&inSR=4326&outFields=*&f=json\n"
            "UI: badge Official + link MSC. Si no hay feature en el punto: fallback demo+NWS con disclaimer."
        )
    )
    pdf.h3(clean("G) OpenFEMA NFIP claims (PENDIENTE)"))
    pdf.body(
        clean(
            "https://www.fema.gov/about/openfema/data-sets\n"
            "REST open data - agregar claims density por ZIP para narrativa aseguradoras.\n"
            "NO es cotizacion. Es densidad historica informativa."
        )
    )
    pdf.h3(clean("H) USGS NWIS gauges (PENDIENTE)"))
    pdf.body(
        clean(
            "https://waterservices.usgs.gov/\n"
            "GET IV (instantaneous values) por bbox Texas o site codes cercanos al ZIP.\n"
            "Capa flood/channel: caudales en mapa."
        )
    )
    pdf.h3(clean("I) Bulk sin key (descarga periodica)"))
    for line in [
        "EPA GHGRP facility tables -> data/bulk/ghgrp*  (Sentinel)",
        "EPA eGRID workbook -> data/bulk/egrid*  (Sentinel emission rates)",
        "EPA TRI / Envirofacts API o bulk (Channel facilities - salir de demo)",
        "TCEQ open GIS services (preferir a scrape CAMS/EER HTML)",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("2.3 Donde NO pedir API / no scrapear"))
    for line in [
        "FEMA MSC HTML - usar NFHL MapServer/FeatureServer",
        "weather.gov HTML - usar api.weather.gov",
        "EIA/EPA HTML tables - APIs oficiales",
        "Socrata HTML - SODA JSON",
        "Yelp / MLS / aseguradoras privadas paywalled - fuera de scope",
        "ERCOT: revisar ToS antes de scrapear dashboards; preferir EIA como proxy",
    ]:
        pdf.bullet(clean(line))

    # ── 3 LEGAL ──
    pdf.add_page()
    pdf.h1(clean("3. Datos legales que DEBES poner (copy listo)"))

    pdf.callout(
        clean(
            "Aviso: esto es checklist de producto/ingenieria, NO asesoramiento legal. "
            "Revisa con un abogado de TX (tech + insurance adjacent) antes de cobrar a aseguradoras."
        )
    )

    pdf.h2(clean("3.1 Donde debe aparecer"))
    pdf.table(
        ["Lugar", "Contenido minimo", "Obligatorio"],
        [
            ("Footer global todas las apps", "No FEMA determination / no insurance advice", "Si"),
            ("About + /legal o /terms", "Terminos, limitacion de responsabilidad", "Si"),
            ("/privacy", "Que datos de usuario guardas (ZIP, email, logs)", "Si si hay cuenta"),
            ("Modal primer uso Flood/Power", "Aceptar disclaimer antes de export CSV", "Recomendado"),
            ("Cada capa con badge", "Source + Official/Demo", "Si"),
            ("Emails/alertas digests", "Misma disclaimer corta", "Si"),
            ("API responses meta", "disclaimer URL o codigo", "Pro/Enterprise"),
            ("Contrato Enterprise", "MSA + DPA + no reliance on flood zone for lending", "Si enterprise"),
        ],
        [48, 90, 32],
    )

    pdf.h2(clean("3.2 Textos recomendados (EN - UI)"))
    pdf.h3(clean("FloodGuard / general risk"))
    pdf.body(
        clean(
            '"Educational and informational only. Not an official FEMA flood determination, '
            "not a survey, and not insurance, lending, or underwriting advice. Flood zones and "
            "scores may be incomplete, delayed, or modeled. Always verify with the FEMA Map "
            'Service Center, a licensed surveyor, and your insurer or lender."'
        )
    )
    pdf.h3(clean("PowerPulse / grid"))
    pdf.body(
        clean(
            '"Not an official ERCOT operational feed. Not for trading, dispatch, or emergency '
            "response. Metrics may be demo, delayed, or derived from public EIA/NOAA proxies. "
            'Follow official ERCOT and local utility guidance during grid emergencies."'
        )
    )
    pdf.h3(clean("ChannelWatch / emissions"))
    pdf.body(
        clean(
            '"Public transparency tool. Not affiliated with TCEQ, EPA, or NWS. Modeled AQI does '
            "not replace official monitors. Emission event quantities are industry self-reported "
            'estimates. Verify on official agency portals before any health or compliance decision."'
        )
    )
    pdf.h3(clean("PermitRadar"))
    pdf.body(
        clean(
            '"Independent visualization of public open data. Not affiliated with any Texas city '
            "permitting office. Always verify permit status, conditions, and ownership with the "
            'issuing authority before bidding or investment decisions."'
        )
    )
    pdf.h3(clean("TxBizFinder leads"))
    pdf.body(
        clean(
            '"Business leads derived from public filings and optional web research. Not a credit, '
            "compliance, or background check. Website research is best-effort and may be incomplete. "
            'Comply with TCPA/CAN-SPAM and local solicitation rules when contacting leads."'
        )
    )

    pdf.h2(clean("3.3 Clausulas de terminos (bullet list para abogado)"))
    for line in [
        "Servicio AS IS / AS AVAILABLE; sin garantia de exactitud o uptime salvo SLA Enterprise por escrito",
        "Limitacion de responsabilidad: fees pagados en 12 meses (o 100 USD free tier)",
        "Indemnizacion del cliente si usa datos para decisiones de seguro/lending sin verificacion oficial",
        "Prohibido reventa de datos de agencia si el ToS de la fuente lo prohibe; cache solo para operar el producto",
        "Usuario no eludira rate limits ni hara scraping de tu API",
        "Derecho a marcar/retirar capas si una agencia pide cese o cambia licencia",
        "Datos personales: ZIP, email, IPs de logs; retencion y derechos CCPA si aplica a CA users",
        "No eres productor de seguros ni adjuster; no cobras prima ni emites polizas",
        "Export CSV/API: cliente es responsable del uso downstream",
        "Governing law: Texas; venue en tu condado",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("3.4 Licencias de fuentes (resumen para UI About)"))
    for line in [
        "Datos federales US (FEMA/NWS/USGS/EIA/EPA): generalmente public domain / uso amplio - citar fuente",
        "Socrata ciudades: revisar cada portal (generalmente open data con atribucion)",
        "Open-Meteo: revisar su licencia/ToS de uso comercial",
        "OpenFreeMap tiles: respetar atribucion del estilo/tiles",
        "ERCOT public: ToS estricto - no asumir redistribucion comercial del feed",
        "DuckDuckGo/Playwright research: uso interno lead-gen; no republicar scrapes masivos",
    ]:
        pdf.bullet(clean(line))

    # ── 4 GTM FEMA / INSURERS ──
    pdf.add_page()
    pdf.h1(clean("4. Como ofrecerlo a FEMA, sector publico y aseguradoras"))

    pdf.h2(clean("4.1 Realidad comercial (importante)"))
    pdf.body(
        clean(
            "FEMA no es un 'cliente SaaS tipico' que compra un mapa de startup la semana que llega. "
            "El camino realista es: (A) vender a quien TRABAJA con riesgo de inundacion (MGAs, "
            "carriers regionales, IA firms, adjusters, municipalities, contractors), y (B) usar "
            "datos FEMA PUBLICOS (NFHL, OpenFEMA) como capa de credibilidad - no pretender partnership "
            "oficial FEMA al dia 1."
        )
    )
    pdf.callout(
        clean(
            "Posicionamiento correcto: 'Texas operational intelligence layer on public data' - "
            "mas rapido para triage que portales institucionales, no reemplazo legal de FEMA MSC."
        )
    )

    pdf.h2(clean("4.2 Que NO digas en pitch"))
    for line in [
        "'Somos la alternativa oficial a FEMA' / 'reemplazamos el flood determination'",
        "'Nuestros scores reemplazan underwriting actuarial'",
        "'Feed en tiempo real de ERCOT para trading'",
        "Cualquier claim de certificacion federal sin contrato real",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("4.3 Que SI digas (value props por buyer)"))
    pdf.table(
        ["Buyer", "Dolor", "Tu promesa", "Producto ancla"],
        [
            ("MGA / carrier regional TX", "Triage lento multi-portal", "ZIP risk + NFHL + claims density + industrial", "Flood+Sentinel+MapHub"),
            ("Adjuster / IA firm", "Contexto campo post-evento", "Alertas NWS + permisos + aire en un mapa", "MapHub+Flood+Channel"),
            ("Municipal / emergency mgmt", "Vista fragmentada", "Dashboard TX capas publicas (pilot)", "MapHub white-label"),
            ("Contractor / remodeler", "Quien construye cerca", "Permisos early signal + flood/grid context", "PermitRadar"),
            ("Broker / agency insurance", "Leads + riesgo barrio", "BizFinder leads + FloodGuard ZIP", "Finder+Flood"),
            ("Environmental consultant", "Capas EPA/TCEQ lentas", "Warehouse multi-source + anomalias", "Sentinel+Channel"),
        ],
        [40, 42, 58, 30],
    )

    pdf.h2(clean("4.4 Camino hacia FEMA / sector publico (largo, realista)"))
    pdf.h3(clean("Fase A - Credibilidad tecnica (ahora)"))
    for line in [
        "Usar solo APIs/bulk oficiales; badges Official; About con fuentes citables",
        "Publicar metodologia corta (como se calcula hybrid risk; que es demo)",
        "Case study interno: 'ZIP 77002 lookup en <2s vs 5 portales'",
    ]:
        pdf.bullet(clean(line))
    pdf.h3(clean("Fase B - Adyacentes a gobierno (3-9 meses)"))
    for line in [
        "Piloto con county emergency management o floodplain administrator (TX) - gratis o bajo costo",
        "RFI/RFQ locales cuando pidan 'situational awareness dashboard'",
        "Partner con firmas de ingenieria/GIS que YA venden a municipios (tu eres white-label capa datos)",
        "SAM.gov / Texas SmartBuy solo cuando tengas entidad, insurance (E&O), y producto estable",
    ]:
        pdf.bullet(clean(line))
    pdf.h3(clean("Fase C - Aseguradoras (paralelo, mas rapido que FEMA)"))
    for line in [
        "Entrar por MGA / surplus lines / regional P&C en Texas Gulf Coast - no por Fortune 100 el dia 1",
        "Ofrecer Pro: API ZIP risk batch + webhooks + export; no 'pricing engine'",
        "Pilot 30-60 dias: 5 users, 1 region (Harris/Galveston/Jefferson), success metric = time-to-triage",
        "Security packet: SOC2 roadmap, auth, logs, data retention, pen-test future",
        "Nunca pidas 'reemplazar' su cat model; pide ser 'pre-bind context layer'",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("4.5 One-pager de venta (estructura)"))
    for line in [
        "Headline: Texas multi-hazard intelligence for teams that cannot wait on 6 agency portals",
        "Problem: flood + permits + grid + air data viven en silos; decisiones de campo pierden horas",
        "Solution: MapHub + APIs con meta.demo/confidence; workers frescos; EN/ES",
        "Proof: live NWS, NFHL query, multi-city permits, public data only",
        "Offer: Contractor $X/mo | Pro API $Y/mo | Enterprise white-label",
        "CTA: pilot ZIP pack (10 ZIPs gratis 14 dias) + demo MapHub",
        "Legal footer: not FEMA determination / not insurance advice",
    ]:
        pdf.bullet(clean(line))

    # ── 5 REVENUE ──
    pdf.add_page()
    pdf.h1(clean("5. Como generar ingresos y a quien venderselo"))

    pdf.h2(clean("5.1 Tiers sugeridos (precios objetivo)"))
    pdf.table(
        ["Tier", "Precio", "Quien compra", "Que incluye"],
        [
            ("Free", "$0", "Usuarios curiosos / lead magnet", "Mapas demo, ZIP limitados, delayed data, badges claros"),
            ("Contractor", "$29-79/mo", "Remodelers, GC chicos, roofers", "Saved ZIPs, permit alerts email, CSV export basico"),
            ("Pro", "$199-499/mo", "Brokers, MGAs chicos, consultores", "API keys, NFHL/history, webhooks, higher limits"),
            ("Enterprise", "custom $1k-15k+/mo", "MGA/carrier, municipio, firmas", "SSO, bulk geocode, white-label MapHub, SLA, support"),
        ],
        [28, 32, 48, 62],
    )

    pdf.h2(clean("5.2 Quien es el comprador ideal (ICP) - orden de facilidad de venta"))
    pdf.body(
        clean(
            "1) Contratistas y trade partners TX (PermitRadar) - ticket bajo, ciclo corto, valor obvio.\n"
            "2) Insurance agencies / producers TX Gulf - FloodGuard ZIP + leads BizFinder.\n"
            "3) MGAs y small carriers - Pro API + MapHub; ciclo mediano; requiere legal/security.\n"
            "4) Environmental / industrial consultants - Sentinel + Channel.\n"
            "5) Municipal / EM - Enterprise white-label; ciclo largo; procurement.\n"
            "6) 'Vender a FEMA HQ' - NO es ICP inicial; es branding/aspiracional via open data quality."
        )
    )

    pdf.h2(clean("5.3 Motores de ingreso (stackeables)"))
    for line in [
        "Suscripcion SaaS (principal) - Stripe monthly/annual (2 meses free en annual)",
        "API metered (Pro+): $ por 1k lookups ZIP o 1k API calls extra",
        "One-time data packs: 'Harris County permit+flood pack' CSV historico",
        "White-label MapHub embebido en portal de agencia de seguros (setup fee + monthly)",
        "Servicios: integracion CRM (HubSpot/Salesforce), training 1/2 dia (Enterprise)",
        "Lead marketplace opcional (cuidado legal): leads cualificados a contractors - consentimiento y TCPA",
        "Affiliate: tools de insurance education (no cotizacion) - secundario",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("5.4 Canales de adquisicion (baratos primero)"))
    for line in [
        "SEO local TX: 'building permits Houston ZIP', 'flood zone 77002 check', EN/ES",
        "LinkedIn outbound a producers/MGAs Gulf Coast con case ZIP demo",
        "Grupos de contractors (FB/Nextdoor pro / asociaciones ABC/AGC locales) - PermitRadar",
        "Product Hunt / Show HN solo cuando free tier sea estable",
        "Partnership con CRM de seguros (Fernando CRM u otros) - embed Flood ZIP widget",
        "Webinars cortos: 'Como leer NFHL + permisos antes de ofertar un remodel'",
        "Content: metodologia + disclaimers (genera confianza B2B)",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("5.5 Metricas que importan (no vanity)"))
    for line in [
        "Activation: primer ZIP lookup con badge Official (no solo demo)",
        "Retention W1/W4 Contractor: % que vuelve a ver permisos de su ZIP saved",
        "API paid conversion: free -> Pro key",
        "Time-to-triage en pilot aseguradora (minutos vs baseline)",
        "Data freshness: % fuentes con last_success < 24h",
        "Support load: tickets por 'es esto FEMA oficial?' - baja con mejores disclaimers",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("5.6 Plan de 30 dias para empezar a cobrar"))
    for line in [
        "Semana 1: Keys EIA+AirNow+OpenAQ; cablear Power/Channel; badges Official/Demo en UI; /terms draft",
        "Semana 2: Flood NFHL path solido + OpenFEMA claims por ZIP; Stripe skeleton + Free/Contractor",
        "Semana 3: Gateway API keys rate limit; 10 outreach a contractors Houston + 5 agencies",
        "Semana 4: Pilot Pro con 1 MGA o IA firm; medir triage; cerrar 5 Contractor paid",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("5.7 Script corto de outreach (contractor)"))
    pdf.body(
        clean(
            "Asunto: Permisos nuevos cerca de tus ZIPs (Houston/Austin)\n\n"
            "Hola {Nombre}, construimos PermitRadar: mapa de permisos publicos de TX + contexto de "
            "inundacion/grid para ofertar con mas contexto. Es open data, no afiliado a la ciudad. "
            "Puedo activarte 14 dias Contractor gratis en ZIP {770XX}. Si no te sirve, lo cancelas. "
            "Demo: {link MapHub/Radar}"
        )
    )

    pdf.h2(clean("5.8 Script corto de outreach (MGA / agency)"))
    pdf.body(
        clean(
            "Asunto: Pre-bind Texas ZIP context (NFHL + alerts + industrial) - pilot\n\n"
            "Hola {Nombre}, TxBizFinder Intelligence apila capas publicas (FEMA NFHL, NWS, permisos, "
            "emisiones) en un mapa/API para triage rapido en TX Gulf. NO es flood determination ni "
            "pricing. Buscamos un pilot Pro 30 dias con 5 seats: success = reducir tiempo de contexto "
            "pre-bind. Te comparto un ZIP pack de tu territorio y el disclaimer legal de producto."
        )
    )

    # ── 6 CHECKLIST FINAL ──
    pdf.add_page()
    pdf.h1(clean("6. Checklist maestro (imprimible)"))

    pdf.h2(clean("Credibilidad de datos"))
    for line in [
        "[ ] EIA_API_KEY en PowerPulse + Sentinel y series cacheadas",
        "[ ] AIRNOW_API_KEY en ChannelWatch (Official AQI)",
        "[ ] OPENAQ_API_KEY + CAMPD_API_KEY en Sentinel",
        "[ ] OpenFEMA claims aggregate por ZIP en Flood",
        "[ ] USGS gauges en mapa Flood/Channel",
        "[ ] GHGRP + eGRID bulk cargados en data/bulk",
        "[ ] Badges Official/Demo en todas las capas visibles",
        "[ ] About + meta API con asOf/cadence/source URL por fuente",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("Legal / compliance producto"))
    for line in [
        "[ ] /terms y /privacy publicados EN+ES",
        "[ ] Footer disclaimer en 7 apps",
        "[ ] Modal aceptacion en export CSV y API key create",
        "[ ] TCPA note en BizFinder contact workflows",
        "[ ] Revision ToS ERCOT antes de cualquier scrape grid",
        "[ ] Abogado revisa claims de marketing a insurers",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("Cobrar"))
    for line in [
        "[ ] Stripe productos Free/Contractor/Pro",
        "[ ] Gateway con API keys y rate limits",
        "[ ] Landing pricing en txbizfinder.com",
        "[ ] 20 outreaches Contractor + 10 Agency/MGA",
        "[ ] 1 pilot Enterprise documentado (case study)",
    ]:
        pdf.bullet(clean(line))

    pdf.h2(clean("Operacion"))
    for line in [
        "[ ] Rotar admin-dev-key",
        "[ ] Uptime checks (health) + alertas de ingest fail",
        "[ ] Backup Postgres/Supabase",
        "[ ] Runbook: que hacer si FEMA/NWS/EIA cae (demo labeled)",
    ]:
        pdf.bullet(clean(line))

    pdf.ln(4)
    pdf.h1(clean("7. Referencias en repos"))
    for line in [
        "texas-biz-finder/docs/DATA_SOURCES_PUBLIC.md - catalogo APIs y scraping",
        "texas-biz-finder/docs/TxBizFinder_Data_Roadmap.pdf - roadmap datos",
        "txbizfinder-suite/docs/DATA_ROADMAP.md - indice suite",
        "*/docs/SUITE_SAAS.md - por producto",
        "GET /api/suite/meta o /v1/suite/meta - dataSources + scrapingPolicy live",
    ]:
        pdf.bullet(clean(line))

    pdf.ln(3)
    pdf.callout(
        clean(
            "Aviso final: este plan es de ingenieria y go-to-market. Los datos de inundacion, red "
            "electrica y emisiones son informativos. No constituyen determinacion FEMA, consejo de "
            "seguros, ni instrucciones operativas de ERCOT/TCEQ/EPA. Valida siempre con fuentes "
            "oficiales y profesionales licenciados. No es asesoramiento legal ni financiero."
        )
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    try:
        pdf.output(str(OUT_ROOT))
    except Exception:
        pass
    print(f"Wrote {OUT}")
    if OUT_ROOT.exists():
        print(f"Wrote {OUT_ROOT}")


if __name__ == "__main__":
    main()
