"""Static verification of frontend structure and Tailwind gradient styles."""

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


def test_main_component_has_gradient_design() -> None:
    component = (FRONTEND / "src" / "components" / "LeadsDashboard.vue").read_text(
        encoding="utf-8"
    )
    assert "bg-hero-gradient" in component
    assert "bg-card-gradient" in component
    assert "Export CSV" in component
    assert "Search leads" in component


def test_tailwind_config_defines_gradients() -> None:
    config = (FRONTEND / "tailwind.config.js").read_text(encoding="utf-8")
    assert "hero-gradient" in config
    assert "card-gradient" in config