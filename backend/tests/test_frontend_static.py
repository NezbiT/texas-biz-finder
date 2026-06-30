"""Static verification of frontend structure and design tokens."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def test_frontend_package_and_tooling() -> None:
    package = (FRONTEND / "package.json").read_text(encoding="utf-8")
    assert "vue" in package
    assert "tailwindcss" in package
    assert "typescript" in package
    assert (FRONTEND / "vite.config.ts").exists()
    assert (FRONTEND / "tailwind.config.js").exists()


def test_main_component_has_texas_design_system() -> None:
    component = (FRONTEND / "src" / "components" / "LeadsDashboard.vue").read_text(
        encoding="utf-8"
    )
    assert "page-shell" in component
    assert "surface-card" in component
    assert "LocaleToggle" in component
    assert 't("exportCsv")' in component
    assert 't("searchLeads")' in component
    assert "PAGE_SIZE = 50" in component


def test_tailwind_config_defines_brand_tokens() -> None:
    config = (FRONTEND / "tailwind.config.js").read_text(encoding="utf-8")
    assert "copper:" in config
    assert "teal:" in config
    assert "fade-up" in config