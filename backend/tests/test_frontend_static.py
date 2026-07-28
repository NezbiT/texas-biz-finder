"""Static verification of frontend structure and design tokens.

Apunta a frontend-v2/ (Nuxt 4 + Tailwind v4). El frontend Vue 3 + Vite anterior
se retiró a archive/frontend-vite/ y ya no se valida aquí.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend-v2"
APP = FRONTEND / "app"


def test_frontend_package_and_tooling() -> None:
    package = (FRONTEND / "package.json").read_text(encoding="utf-8")
    assert "nuxt" in package
    assert "tailwindcss" in package
    assert "@tailwindcss/vite" in package     # Tailwind v4 va por el plugin de Vite
    assert "typescript" in package
    assert "@nuxtjs/i18n" in package
    assert (FRONTEND / "nuxt.config.ts").exists()
    # El tema vive en @theme (CSS-first); tailwind.config.js ya no debe existir
    assert not (FRONTEND / "tailwind.config.js").exists()


def test_main_component_has_texas_design_system() -> None:
    component = (APP / "components" / "LeadsDashboard.vue").read_text(encoding="utf-8")
    assert "surface-card" in component
    assert 't("exportCsv")' in component
    assert 't("searchLeads")' in component
    assert "PAGE_SIZE = 50" in component
    assert "MobileBottomDock" in component
    assert "useTouchSwipe" in component
    assert "useLeadsApi" in component     # nada de fetch a pelo


def test_shared_api_and_suite_config() -> None:
    api = (APP / "composables" / "useApi.ts").read_text(encoding="utf-8")
    leads = (APP / "composables" / "useLeadsApi.ts").read_text(encoding="utf-8")
    suite_static = (APP / "config" / "suite.ts").read_text(encoding="utf-8")
    suite_env = (APP / "composables" / "useSuite.ts").read_text(encoding="utf-8")
    assert "apiFetch" in api
    assert "X-API-Key" in api
    # La API key sale de runtimeConfig, no de import.meta.env
    assert "useRuntimeConfig" in api
    assert "fetchLeadStats" in leads
    assert "SUITE_PRODUCT_LABELS" in suite_static
    # Las URLs de la suite se resuelven por entorno, no hardcodeadas
    assert "radarUrl" in suite_env
    assert "channelUrl" in suite_env
    assert "sentinelUrl" in suite_env


def test_suite_landing_reuses_shared_components() -> None:
    landing = (APP / "components" / "SuiteLanding.vue").read_text(encoding="utf-8")
    assert "useSuite" in landing
    assert "ProductLink" in landing
    assert "ProductIcon" in landing
    assert "TexasTopoCanvas" in landing
    assert (APP / "components" / "ProductCard.vue").exists()
    assert (APP / "components" / "ProductLink.vue").exists()
    assert (FRONTEND / ".env.example").exists()


def test_routing_pages_replace_vue_router() -> None:
    # El router.ts de la v1 pasó a file-based routing
    assert (APP / "pages" / "index.vue").exists()   # landing de la suite
    assert (APP / "pages" / "app.vue").exists()     # dashboard de leads
    landing_page = (APP / "pages" / "index.vue").read_text(encoding="utf-8")
    assert "SuiteLanding" in landing_page
    config = (FRONTEND / "nuxt.config.ts").read_text(encoding="utf-8")
    assert "/leads" in config          # alias de compatibilidad
    assert "pages:extend" in config    # ruta del dashboard configurable por env


def test_theme_defines_brand_tokens() -> None:
    styles = (APP / "assets" / "css" / "style.css").read_text(encoding="utf-8")
    assert "@theme" in styles                     # Tailwind v4 CSS-first
    assert "--color-brand-copper" in styles
    assert "--color-brand-teal" in styles
    assert "--animate-fade-up" in styles
    # darkMode: "class" de la v3 es ahora un variant declarado a mano
    assert "@custom-variant dark" in styles


def test_mobile_styles_and_sheet() -> None:
    styles = (APP / "assets" / "css" / "style.css").read_text(encoding="utf-8")
    assert "mobile-dock" in styles
    assert "sheet-panel" in styles
    assert "safe-area-inset" in styles


def test_i18n_catalogs_are_in_parity() -> None:
    import json

    locales = FRONTEND / "i18n" / "locales"
    en = json.loads((locales / "en.json").read_text(encoding="utf-8"))
    es = json.loads((locales / "es.json").read_text(encoding="utf-8"))
    assert en.keys() == es.keys(), "en.json y es.json deben tener las mismas claves"
    # Claves de la landing de la suite (la parte que faltaba en el v2 a medias)
    for key in ("suiteName", "suiteHeroTitle", "productRadarName", "suiteStatLeads"):
        assert key in en and key in es


def test_pwa_assets_and_config() -> None:
    public = FRONTEND / "public"
    assert (public / "pwa-192.png").exists()
    assert (public / "pwa-512.png").exists()
    assert (public / "apple-touch-icon.png").exists()
    config = (FRONTEND / "nuxt.config.ts").read_text(encoding="utf-8")
    assert "@vite-pwa/nuxt" in config
    assert "TX BizFinder" in config      # manifest.name
    assert "TXBizFinder" in config       # manifest.short_name
    assert "registerType" in config
