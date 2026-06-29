"""Tests for website stack and antiquity analysis."""

from scripts.common.website_analysis import analyze_website_content, analyze_website_url_only

LEGACY_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta name="generator" content="Microsoft FrontPage 6.0">
  <script src="/jquery-1.7.2.min.js"></script>
</head>
<body>
  <center><font size="4">Welcome</font></center>
  <table width="800"><tr><td>Old layout</td></tr></table>
  <p>Copyright 2011 Example Co</p>
</body>
</html>
"""

MODERN_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.jsdelivr.net/npm/react@18/umd/react.production.min.js"></script>
</head>
<body>
  <div id="root"></div>
  <footer>Copyright 2026 Modern Co</footer>
</body>
</html>
"""


def test_url_only_detects_missing_website() -> None:
    result = analyze_website_url_only(None)
    assert result.has_website is False
    assert result.has_modern_website is False


def test_url_only_flags_http_as_legacy() -> None:
    result = analyze_website_url_only("http://oldshop.example")
    assert result.has_website is True
    assert result.has_modern_website is False
    assert result.estimated_antiquity_years is not None


def test_legacy_html_detects_stack_and_antiquity() -> None:
    result = analyze_website_content(
        website_url="https://legacy.example",
        html=LEGACY_HTML,
        final_url="https://legacy.example",
    )
    assert result.website_reachable is True
    assert "jQuery 1" in result.tech_stack
    assert "Microsoft FrontPage" in result.tech_stack
    assert result.has_modern_website is False
    assert result.estimated_antiquity_years is not None
    assert result.estimated_antiquity_years >= 8


def test_modern_html_detects_react_stack() -> None:
    result = analyze_website_content(
        website_url="https://modern.example",
        html=MODERN_HTML,
        final_url="https://modern.example",
    )
    assert "React" in result.tech_stack
    assert result.has_modern_website is True
    assert result.estimated_antiquity_years == 0