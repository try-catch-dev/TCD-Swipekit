"""Tests for plugin extensibility, Markdown-to-Carousel, checklist layout, browser frames, GIF export, and watcher."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from tcd_swipekit.cli import app
from tcd_swipekit.models import (
    ChecklistBlock,
    FrameStyle,
    SlideItem,
    SlideLayout,
    ThemeConfig,
)
from tcd_swipekit.pipeline import generate_custom_source_deck, generate_markdown_deck
from tcd_swipekit.plugins import (
    get_exporter,
    get_layout,
    get_source_class,
    list_exporters,
    list_layouts,
    list_sources,
    load_plugin_file,
    register_layout,
)
from tcd_swipekit.renderer import SlideRenderer, export_slides_to_gif
from tcd_swipekit.sources.markdown import parse_markdown_to_deck
from tcd_swipekit.themes.loader import load_theme, register_template_dir, register_theme_dir
from tcd_swipekit.watcher import run_watch_server

runner = CliRunner()


def test_markdown_parser_auto_detects_code_versus_checklist_and_cover():
    md = """---
topic: "Backend Architecture Notes"
badge_text: "BACKEND · PART 1"
hashtags: ["#python", "#backend"]
---

# Build *Resilient APIs* in Python

Practical patterns for high-throughput microservices.

## 1. Refactor / Use Indexed Lookups

Avoid nested loops when joining records in memory.

```diff title="join.py"
- for order in orders:
-     for u in users:
+ user_map = {u.id: u for u in users}
```

Badges: O(n) | Fast

> Zero allocations outside the dict comprehension.

## 2. Compare / Sync vs Async I/O

Choose the right concurrency model for network-heavy services.

### ❌ Legacy: Blocking Requests
- Blocks OS thread on every network call
- Low concurrency under slow upstream latency

```python
resp = requests.get(url)
```

### ✅ Modern: Async httpx
- Thousands of concurrent connections on one event loop
- Native timeout budgets & connection pooling

```python
resp = await client.get(url)
```

> Use async httpx for I/O-bound microservices.

## 3. Audit / Pre-Launch Checklist

Verify these four items before going live:

1. **Strict Timeouts** — Configure connect and read timeouts on all clients
2. **Idempotency Keys** — Protect mutation endpoints against duplicate retries
3. **Structured Logs** — Output JSON logs with request correlation IDs

> Automate checks in CI.
"""
    deck = parse_markdown_to_deck(md)
    assert deck.topic == "Backend Architecture Notes"
    assert deck.cover.badge_text == "BACKEND · PART 1"
    assert any("*Resilient APIs*" in line for line in deck.cover.title_lines)
    assert "Practical patterns" in (deck.cover.subtitle or "")
    assert len(deck.items) == 3

    slide1 = deck.items[0]
    assert slide1.layout == SlideLayout.CODE
    assert slide1.eyebrow == "Refactor /"
    assert slide1.title == "Use Indexed Lookups"
    assert slide1.code_block is not None
    assert slide1.code_block.diff_mode is True
    assert slide1.code_block.filename == "join.py"
    assert len(slide1.badges) == 2

    slide2 = deck.items[1]
    assert slide2.layout == SlideLayout.VERSUS
    assert slide2.versus is not None
    assert slide2.versus.left.label == "Blocking Requests"
    assert slide2.versus.left.accent is False
    assert slide2.versus.right.label == "Async httpx"
    assert slide2.versus.right.accent is True
    assert "Use async httpx" in (slide2.versus.verdict or "")

    slide3 = deck.items[2]
    assert slide3.layout == SlideLayout.CHECKLIST
    assert slide3.checklist is not None
    assert slide3.checklist.numbered is True
    assert len(slide3.checklist.items) == 3
    assert slide3.checklist.items[0].title == "Strict Timeouts"
    assert "Configure connect" in slide3.checklist.items[0].detail


def test_checklist_shorthand_coercion_and_html_rendering():
    item = SlideItem(
        title="Security Audit",
        eyebrow="sec /",
        checklist=[
            "Rotate API Keys — Every 90 days in production",
            "Enable MFA: Required for all admin accounts",
            "Pin container digests",
        ],  # type: ignore[arg-type]
    )
    assert item.layout == SlideLayout.CHECKLIST
    assert isinstance(item.checklist, ChecklistBlock)
    assert len(item.checklist.items) == 3
    assert item.checklist.items[0].title == "Rotate API Keys"
    assert item.checklist.items[0].detail == "Every 90 days in production"
    assert item.checklist.items[1].title == "Enable MFA"

    renderer = SlideRenderer()
    html = renderer.build_item_html(
        item,
        index=2,
        theme=load_theme("editorial-light"),
        width=1180,
        height=1572,
        total_items=4,
    )
    assert "Rotate API Keys" in html
    assert "Every 90 days in production" in html
    assert "/ 04" in html
    assert "width: 50%;" in html


def test_browser_and_macos_frames_in_showcase_html(tmp_path: Path):
    shot = tmp_path / "web.png"
    Image.new("RGB", (600, 400), (30, 50, 80)).save(shot)

    browser_item = SlideItem(
        title="Excalidraw",
        url="https://excalidraw.com",
        screenshot_path=str(shot),
        frame=FrameStyle.BROWSER,
    )
    renderer = SlideRenderer()
    html_browser = renderer.build_item_html(
        browser_item,
        index=1,
        theme=load_theme("arctic-slate"),
        width=1180,
        height=1572,
        total_items=3,
    )
    assert "frame-window" in html_browser
    assert "frame-url-pill" in html_browser
    assert "https://excalidraw.com" in html_browser

    macos_item = SlideItem(
        title="Terminal App",
        screenshot_path=str(shot),
        frame=FrameStyle.MACOS,
    )
    html_macos = renderer.build_item_html(
        macos_item,
        index=1,
        theme=load_theme("nord-frost"),
        width=1180,
        height=1572,
        total_items=3,
    )
    assert "frame-window" in html_macos
    assert "frame-title" in html_macos


def test_export_slides_to_gif(tmp_path: Path):
    s1 = tmp_path / "01.png"
    s2 = tmp_path / "02.png"
    Image.new("RGB", (400, 500), (20, 40, 60)).save(s1)
    Image.new("RGB", (400, 500), (80, 30, 50)).save(s2)

    gif_path = export_slides_to_gif([s1, s2], tmp_path / "carousel.gif", max_width=240)
    assert gif_path.is_file()
    assert gif_path.read_bytes()[:6] in (b"GIF87a", b"GIF89a")
    with Image.open(gif_path) as gif_img:
        assert gif_img.size[0] == 240
        assert getattr(gif_img, "n_frames", 1) == 2


def test_plugin_registries_custom_source_layout_template_and_exporter(tmp_path: Path):
    # 1. Register a custom theme directory
    custom_theme_dir = tmp_path / "my_themes"
    custom_theme_dir.mkdir()
    (custom_theme_dir / "ocean-pulse.yaml").write_text(
        "preset: ocean-pulse\naccent_color: '#06B6D4'\n",
        encoding="utf-8",
    )
    register_theme_dir(custom_theme_dir)
    loaded_theme = load_theme("ocean-pulse")
    assert loaded_theme.accent_color == "#06B6D4"

    # 2. Register a custom template directory + custom layout
    custom_tpl_dir = tmp_path / "my_templates"
    custom_tpl_dir.mkdir()
    (custom_tpl_dir / "slide_quote.html.j2").write_text(
        """<!DOCTYPE html><html><body style="width:{{ width }}px;height:{{ height }}px;background:{{ theme.bg_color }};color:{{ theme.text_color }};">
        <h1>{{ item.title }}</h1><p class="speaker">{{ speaker_name }}</p></body></html>""",
        encoding="utf-8",
    )
    register_template_dir(custom_tpl_dir)

    @register_layout("quote", template="slide_quote.html.j2", description="Pull-quote card")
    def _quote_ctx(item: SlideItem, index: int, total: int, theme: ThemeConfig, w: int, h: int):
        return {"speaker_name": item.extra.get("speaker", "Anonymous")}

    assert "quote" in list_layouts()
    assert get_layout("quote") is not None

    quote_item = SlideItem(
        layout="quote",
        title="Simplicity is prerequisite for reliability.",
        extra={"speaker": "Edsger W. Dijkstra"},
    )
    rendered_quote_html = SlideRenderer().build_item_html(
        quote_item,
        index=1,
        theme=loaded_theme,
        width=1080,
        height=1080,
    )
    assert "Edsger W. Dijkstra" in rendered_quote_html

    # 3. Register a custom content source & custom exporter via a standalone plugin file
    plugin_py = tmp_path / "custom_plugin.py"
    runner.invoke(app, ["init", "plugin", "--output", str(plugin_py)])
    assert plugin_py.is_file()
    load_plugin_file(plugin_py)

    assert "demo-feed" in list_sources()
    assert "json" in list_exporters()
    assert get_source_class("demo-feed") is not None
    assert get_exporter("json") is not None

    out_dir = tmp_path / "custom_source_out"
    deck, paths = generate_custom_source_deck(
        source_name="demo-feed",
        output_dir=out_dir,
        source_kwargs={"tag": "python"},
        limit=2,
        theme_name="ocean-pulse",
        export_gif=True,
        exporters=["json"],
    )
    assert len(deck.items) == 2
    assert len(paths) == 3  # cover + 2 items
    assert (out_dir / "carousel.gif").is_file()
    assert (out_dir / "slides_manifest.json").is_file()
    preview_text = (out_dir / "preview.html").read_text(encoding="utf-8")
    assert "carousel.gif" in preview_text
    assert "slides_manifest.json" in preview_text


def test_generate_markdown_deck_and_plugins_cli(tmp_path: Path):
    md_file = tmp_path / "guide.md"
    res_init = runner.invoke(app, ["init", "markdown", "--output", str(md_file)])
    assert res_init.exit_code == 0
    assert md_file.is_file()

    out_dir = tmp_path / "md_out"
    deck, paths = generate_markdown_deck(
        markdown_source=md_file,
        output_dir=out_dir,
        theme_name="editorial-light",
        include_outro=True,
        export_pdf=True,
        export_gif=True,
    )
    assert len(deck.items) == 3
    assert [i.layout for i in deck.items] == [
        SlideLayout.CODE,
        SlideLayout.VERSUS,
        SlideLayout.CHECKLIST,
    ]
    assert len(paths) == 5  # cover + 3 items + closing CTA
    assert (out_dir / "carousel.pdf").is_file()
    assert (out_dir / "carousel.gif").is_file()

    res_plugins = runner.invoke(app, ["plugins"])
    assert res_plugins.exit_code == 0
    assert "markdown" in res_plugins.stdout
    assert "checklist" in res_plugins.stdout
    assert "gif" in res_plugins.stdout


def test_watcher_detects_file_modification_and_rebuilds(tmp_path: Path):
    target = tmp_path / "watch_me.md"
    target.write_text("# V1\n\n## Slide 1\n- Item A\n- Item B\n", encoding="utf-8")

    renders: list[str] = []
    rebuilds: list[int] = []

    def _render_cb() -> None:
        renders.append(target.read_text(encoding="utf-8"))

    def _modify_soon() -> None:
        time.sleep(0.12)
        target.write_text("# V2\n\n## Slide 1\n- Item A\n- Item B\n", encoding="utf-8")

    t = threading.Thread(target=_modify_soon, daemon=True)
    t.start()

    final_ver = run_watch_server(
        target_file=target,
        output_dir=tmp_path,
        render_callback=_render_cb,
        poll_interval=0.08,
        serve_http=False,
        max_cycles=4,
        on_rebuild=lambda ver, _p: rebuilds.append(ver),
    )
    t.join(timeout=1.0)
    assert final_ver >= 2
    assert len(renders) >= 2
    assert rebuilds == [2]
