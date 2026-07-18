"""Static verification of frontend structure and design tokens."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
SRC = FRONTEND / "src"


def test_frontend_package_and_tooling() -> None:
    package = (FRONTEND / "package.json").read_text(encoding="utf-8")
    assert "vue" in package
    assert "tailwindcss" in package
    assert "typescript" in package
    assert "vue-router" in package
    assert (FRONTEND / "vite.config.ts").exists()
    assert (FRONTEND / "tailwind.config.js").exists()


def test_main_component_has_texas_design_system() -> None:
    component = (SRC / "components" / "LeadsDashboard.vue").read_text(encoding="utf-8")
    assert "PageShell" in component
    assert "BrandMark" in component
    assert "ChromeToggles" in component
    assert "surface-card" in component
    assert 't("exportCsv")' in component
    assert 't("searchLeads")' in component
    assert "PAGE_SIZE = 50" in component
    assert "MobileBottomDock" in component
    assert "useTouchSwipe" in component
    assert "searchLeads" in component  # lib/leadsApi
    assert "from \"../lib/leadsApi\"" in component or "from '../lib/leadsApi'" in component


def test_shared_api_and_suite_config() -> None:
    api = (SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    leads = (SRC / "lib" / "leadsApi.ts").read_text(encoding="utf-8")
    suite = (SRC / "config" / "suite.ts").read_text(encoding="utf-8")
    env_mod = (SRC / "config" / "env.ts").read_text(encoding="utf-8")
    assert "apiFetch" in api
    assert "X-API-Key" in api
    assert "VITE_ADMIN_API_KEY" in env_mod
    assert "fetchLeadStats" in leads
    assert "SUITE_PRODUCTS" in suite
    assert "radar.txbizfinder.com" in suite
    assert "channel.txbizfinder.com" in suite
    assert "sentinel.txbizfinder.com" in suite


def test_suite_landing_reuses_shared_components() -> None:
    landing = (SRC / "components" / "SuiteLanding.vue").read_text(encoding="utf-8")
    router = (SRC / "router.ts").read_text(encoding="utf-8")
    assert "PageShell" in landing
    assert "ProductCard" in landing
    assert "SUITE_PRODUCTS" in landing
    assert "BIZ_APP_PATH" in router
    assert (SRC / "components" / "ProductCard.vue").exists()
    assert (SRC / "components" / "ProductLink.vue").exists()
    assert (FRONTEND / ".env.example").exists()


def test_tailwind_config_defines_brand_tokens() -> None:
    config = (FRONTEND / "tailwind.config.js").read_text(encoding="utf-8")
    assert "copper:" in config
    assert "teal:" in config
    assert "fade-up" in config


def test_mobile_styles_and_sheet() -> None:
    styles = (SRC / "style.css").read_text(encoding="utf-8")
    assert "mobile-dock" in styles
    assert "sheet-panel" in styles
    assert "safe-area-inset" in styles


def test_pwa_assets_and_config() -> None:
    public = FRONTEND / "public"
    assert (public / "pwa-192.png").exists()
    assert (public / "pwa-512.png").exists()
    assert (public / "apple-touch-icon.png").exists()
    vite = (FRONTEND / "vite.config.ts").read_text(encoding="utf-8")
    assert "VitePWA" in vite
    assert "TxBizFinder" in vite
    assert "loadEnv" in vite
    assert "VITE_API_PROXY_TARGET" in vite
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert "manifest.webmanifest" in html
    assert "apple-touch-icon" in html
