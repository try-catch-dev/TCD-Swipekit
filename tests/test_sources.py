"""Unit tests for GitHub README/trending parsers and Website metadata/sites.yml loaders."""

from pathlib import Path

from tcd_swipekit.models import Language
from tcd_swipekit.sources.github import extract_readme_image_urls, parse_trending_html
from tcd_swipekit.sources.website import load_sites_file, parse_website_metadata


def test_extract_readme_image_urls_filters_badges_and_prioritizes_screenshots():
    md = """
    ![Build](https://img.shields.io/badge/build-passing-green)
    ![Logo](assets/logo.svg)
    ![Banner](docs/banner.png)
    <img src="docs/screenshots/dashboard.webp" />
    ![Blob](https://github.com/acme/tool/blob/main/images/ui-preview.png)
    """
    urls = extract_readme_image_urls(md, owner="acme", repo="tool", branch="main")
    assert all("shields.io" not in u and not u.endswith(".svg") for u in urls)
    assert "https://raw.githubusercontent.com/acme/tool/main/docs/screenshots/dashboard.webp" in urls
    assert "https://raw.githubusercontent.com/acme/tool/main/images/ui-preview.png" in urls
    # Dashboard/preview screenshots should rank ahead of generic banner
    assert urls[0].endswith(("dashboard.webp", "ui-preview.png"))


def test_parse_trending_html():
    html = """
    <article class="Box-row">
      <h2><a href="/acme/cooltool">acme / cooltool</a></h2>
      <p>Fast open-source tool for testing.</p>
      <a href="/acme/cooltool/stargazers">12,345</a>
      <span class="d-inline-block float-sm-right">1,234 stars this week</span>
    </article>
    """
    rows = parse_trending_html(html)
    assert len(rows) == 1
    assert rows[0]["repo"] == "acme/cooltool"
    assert rows[0]["stars"] == "12,345"
    assert rows[0]["gain"] == "1,234"


def test_parse_website_metadata():
    html = """
    <html>
      <head>
        <title>Excalidraw | Hand-drawn look &amp; feel</title>
        <meta property="og:description" content="Virtual collaborative whiteboard tool." />
      </head>
      <body></body>
    </html>
    """
    title, desc = parse_website_metadata(html, "https://excalidraw.com")
    assert title == "Excalidraw"
    assert desc == "Virtual collaborative whiteboard tool."


def test_load_sites_yml(tmp_path: Path):
    cfg = tmp_path / "sites.yml"
    cfg.write_text(
        """
topic: "Dev Websites"
language: id
sites:
  - url: "https://example.com"
    title: "Example"
    pricing: "Gratis"
""",
        encoding="utf-8",
    )
    parsed = load_sites_file(cfg)
    assert parsed.topic == "Dev Websites"
    assert parsed.language == Language.ID
    assert len(parsed.sites) == 1
    assert parsed.sites[0].url == "https://example.com"
