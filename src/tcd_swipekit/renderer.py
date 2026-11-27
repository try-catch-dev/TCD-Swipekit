"""HTML/CSS Jinja2 + Playwright Chromium slide renderer for TCD-Swipekit."""

from __future__ import annotations

import base64
import contextlib
import html
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image
from playwright.sync_api import sync_playwright

from tcd_swipekit.copywriter import build_caption_markdown
from tcd_swipekit.image_utils import extract_ambient_tint, to_data_uri
from tcd_swipekit.models import (
    AspectRatio,
    ChecklistBlock,
    CodeBlock,
    CoverConfig,
    DeckSpec,
    OutroConfig,
    SlideItem,
    SlideLayout,
    ThemeConfig,
)
from tcd_swipekit.themes.loader import get_template_search_dirs

ICONS_SVG: dict[str, str] = {
    "github": """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="11.5" fill="#FFFFFF"/>
  <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2.4C6.696 2.4 2.4 6.696 2.4 12C2.4 16.248 5.148 19.836 8.964 21.108C9.444 21.192 9.624 20.904 9.624 20.652C9.624 20.424 9.612 19.668 9.612 18.864C7.2 19.308 6.576 18.276 6.384 17.736C6.276 17.46 5.808 16.608 5.4 16.38C5.064 16.2 4.584 15.756 5.388 15.744C6.144 15.732 6.684 16.44 6.864 16.728C7.728 18.18 9.108 17.772 9.66 17.52C9.744 16.896 9.996 16.476 10.272 16.236C8.136 15.996 5.904 15.168 5.904 11.496C5.904 10.452 6.276 9.588 6.888 8.916C6.792 8.676 6.456 7.692 6.984 6.372C6.984 6.372 7.788 6.12 9.624 7.356C10.392 7.14 11.208 7.032 12.024 7.032C12.84 7.032 13.656 7.14 14.424 7.356C16.26 6.108 17.064 6.372 17.064 6.372C17.592 7.692 17.256 8.676 17.16 8.916C17.772 9.588 18.144 10.44 18.144 11.496C18.144 15.18 15.9 15.996 13.764 16.236C14.112 16.536 14.412 17.112 14.412 18.012C14.412 19.296 14.4 20.328 14.4 20.652C14.4 20.904 14.58 21.204 15.06 21.108C18.864 19.836 21.6 16.236 21.6 12C21.6 6.696 17.304 2.4 12 2.4Z" fill="#0B0B0D"/>
</svg>""",
    "globe": """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="11.5" fill="#FFFFFF"/>
  <circle cx="12" cy="12" r="7.5" stroke="#0B0B0D" stroke-width="1.8"/>
  <ellipse cx="12" cy="12" rx="3.4" ry="7.5" stroke="#0B0B0D" stroke-width="1.6"/>
  <path d="M4.8 12H19.2M5.8 8.5H18.2M5.8 15.5H18.2" stroke="#0B0B0D" stroke-width="1.5"/>
</svg>""",
    "sparkles": """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="11.5" fill="#FFFFFF"/>
  <path d="M12 4.5L13.8 10.2L19.5 12L13.8 13.8L12 19.5L10.2 13.8L4.5 12L10.2 10.2L12 4.5Z" fill="#0B0B0D"/>
</svg>""",
    "none": "",
}

_SYSTEM_FONTS = {
    "sans-serif",
    "serif",
    "monospace",
    "system-ui",
    "-apple-system",
    "blinkmacsystemfont",
    "helvetica",
    "helvetica neue",
    "arial",
    "georgia",
    "times new roman",
    "courier new",
    "ui-sans-serif",
    "ui-monospace",
}

_FONT_MIME_AND_FORMAT: dict[str, tuple[str, str]] = {
    ".woff2": ("font/woff2", "woff2"),
    ".woff": ("font/woff", "woff"),
    ".ttf": ("font/ttf", "truetype"),
    ".otf": ("font/otf", "opentype"),
}


def build_font_css(theme: ThemeConfig) -> str:
    """Build dynamic `@font-face` (local offline files) and Google Fonts `@import` CSS."""
    css_parts: list[str] = []
    embedded_families: set[str] = set()

    for family, raw_path in theme.font_files.items():
        font_path = Path(raw_path).expanduser()
        if not font_path.is_file():
            continue
        mime, fmt = _FONT_MIME_AND_FORMAT.get(font_path.suffix.lower(), ("font/ttf", "truetype"))
        encoded = base64.b64encode(font_path.read_bytes()).decode("ascii")
        safe_family = family.replace("'", "\\'")
        css_parts.append(
            f"@font-face {{\n"
            f"  font-family: '{safe_family}';\n"
            f"  src: url('data:{mime};base64,{encoded}') format('{fmt}');\n"
            f"  font-weight: 100 900;\n"
            f"  font-display: swap;\n"
            f"}}"
        )
        embedded_families.add(family.strip().lower())

    google_families: list[str] = []
    seen: set[str] = set()
    for fam in (theme.font_heading, theme.font_body, theme.font_mono):
        cleaned = (fam or "").strip().strip("'\"")
        key = cleaned.lower()
        if not cleaned or key in seen or key in _SYSTEM_FONTS or key in embedded_families:
            continue
        seen.add(key)
        weights = "400;500;600;700" if cleaned == theme.font_mono else "400;500;600;700;800;900"
        google_families.append(f"family={quote_plus(cleaned)}:wght@{weights}")

    if google_families:
        query = "&".join(google_families)
        css_parts.insert(
            0,
            f"@import url('https://fonts.googleapis.com/css2?{query}&display=swap');",
        )

    return "\n".join(css_parts)


def format_inline_accent(line: str) -> str:
    """Convert `*accent text*` markers in cover titles into safe `<span class="accent">` HTML."""
    escaped = html.escape(line)
    return re.sub(r"\*([^*]+)\*", r'<span class="accent">\1</span>', escaped)


def format_inline_bold(text: str) -> str:
    """Convert `**bold text**` markers in cover subtitles into safe `<strong>` HTML."""
    escaped = html.escape(text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)


def _compute_title_font_size(title: str) -> int:
    length = len(title)
    if length <= 10:
        return 108
    if length <= 16:
        return 94
    if length <= 22:
        return 78
    return 66


def _compute_headline_size(lines: list[str]) -> int:
    longest = max((len(line.replace("*", "")) for line in lines), default=12)
    if longest <= 15:
        return 114
    if longest <= 20:
        return 98
    return 84


def _compute_code_font_size(raw_lines: list[str]) -> int:
    """Pick readable monospace font size based on line count and longest line."""
    line_count = len(raw_lines)
    longest = max((len(line) for line in raw_lines), default=20)
    if line_count <= 9 and longest <= 38:
        return 27
    if line_count <= 13 and longest <= 48:
        return 24
    if line_count <= 16 and longest <= 58:
        return 21
    return 19


def _token_to_css_class(token_type: object) -> str | None:
    """Map a Pygments TokenType to a concise CSS class name."""
    name = str(token_type)
    if name.startswith("Token.Generic.Inserted"):
        return "tok-add"
    if name.startswith("Token.Generic.Deleted"):
        return "tok-del"
    if name.startswith("Token.Comment"):
        return "tok-c"
    if name.startswith("Token.Keyword"):
        return "tok-k"
    if name.startswith("Token.Literal.String"):
        return "tok-s"
    if name.startswith("Token.Literal.Number"):
        return "tok-m"
    if name.startswith("Token.Name.Function") or name.startswith("Token.Name.Class"):
        return "tok-f"
    if name.startswith("Token.Name.Decorator"):
        return "tok-d"
    if name.startswith("Token.Name.Builtin") or name.startswith("Token.Name.Tag"):
        return "tok-nb"
    if name.startswith("Token.Operator"):
        return "tok-o"
    return None


def highlight_code_lines(code_block: CodeBlock) -> list[dict[str, object]]:
    """Tokenize a CodeBlock into per-line safe HTML with optional diff & highlight markers."""
    code_text = code_block.code.strip("\n")
    raw_lines = code_text.splitlines() or [""]
    is_diff = code_block.diff_mode or code_block.language.strip().lower() == "diff"
    highlighted_set = set(code_block.highlight_lines)

    line_htmls: list[str] | None = None
    try:
        from pygments import lex
        from pygments.lexers import TextLexer, get_lexer_by_name

        try:
            lexer = get_lexer_by_name(code_block.language, stripnl=False)
        except Exception:
            lexer = TextLexer(stripnl=False)

        rendered_lines: list[list[str]] = [[]]
        for ttype, value in lex(code_text, lexer):
            css_cls = _token_to_css_class(ttype)
            parts = value.split("\n")
            for idx, part in enumerate(parts):
                if idx > 0:
                    rendered_lines.append([])
                if part:
                    escaped = html.escape(part)
                    if css_cls:
                        rendered_lines[-1].append(f'<span class="{css_cls}">{escaped}</span>')
                    else:
                        rendered_lines[-1].append(escaped)
        if len(rendered_lines) > len(raw_lines) and not rendered_lines[-1]:
            rendered_lines.pop()
        line_htmls = ["".join(chunks) or "&nbsp;" for chunks in rendered_lines]
    except Exception:
        line_htmls = None

    results: list[dict[str, object]] = []
    for i, raw in enumerate(raw_lines, start=1):
        line_html = (
            line_htmls[i - 1]
            if line_htmls is not None and i - 1 < len(line_htmls)
            else (html.escape(raw) or "&nbsp;")
        )
        classes: list[str] = []
        if is_diff and raw.startswith("+") and not raw.startswith("+++"):
            classes.append("is-diff-add")
        elif is_diff and raw.startswith("-") and not raw.startswith("---"):
            classes.append("is-diff-del")
        elif i in highlighted_set:
            classes.append("is-highlight")
        results.append(
            {
                "number": i,
                "html": line_html,
                "css_class": " ".join(classes),
            }
        )
    return results


def export_slides_to_pdf(
    slide_paths: list[Path],
    pdf_path: Path,
    deck: DeckSpec | None = None,
) -> Path:
    """Combine rendered slide PNGs into a single multi-page PDF (ideal for LinkedIn Carousels)."""
    if not slide_paths:
        raise ValueError("Cannot export PDF: no slide images provided.")

    rgb_images: list[Image.Image] = []
    try:
        for path in slide_paths:
            with Image.open(path) as img:
                rgb_images.append(img.convert("RGB"))
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        first, rest = rgb_images[0], rgb_images[1:]
        first.save(pdf_path, "PDF", resolution=144.0, save_all=True, append_images=rest)
    finally:
        for img in rgb_images:
            img.close()
    return pdf_path


def export_slides_to_gif(
    slide_paths: list[Path],
    gif_path: Path,
    deck: DeckSpec | None = None,
    *,
    duration_ms: int = 1800,
    max_width: int = 640,
) -> Path:
    """Export rendered slide PNGs into an animated GIF slideshow (pure Pillow, zero ffmpeg required)."""
    if not slide_paths:
        raise ValueError("Cannot export GIF: no slide images provided.")

    frames: list[Image.Image] = []
    try:
        for path in slide_paths:
            with Image.open(path) as img:
                rgb = img.convert("RGB")
                w, h = rgb.size
                if w > max_width:
                    new_h = int(h * (max_width / w))
                    rgb = rgb.resize((max_width, new_h), Image.Resampling.LANCZOS)
                frames.append(rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT))
        gif_path.parent.mkdir(parents=True, exist_ok=True)
        first, rest = frames[0], frames[1:]
        first.save(
            gif_path,
            format="GIF",
            save_all=True,
            append_images=rest,
            duration=duration_ms,
            loop=0,
            optimize=True,
        )
    finally:
        for frame in frames:
            frame.close()
    return gif_path


def _showcase_context_builder(
    item: SlideItem,
    index: int,
    total_items: int,
    theme: ThemeConfig,
    width: int,
    height: int,
) -> dict[str, Any]:
    image_uri: str | None = None
    ambient_tint = item.ambient_tint or (
        "rgba(245, 244, 240, 0.88)" if theme.is_light else "rgba(14, 18, 28, 0.74)"
    )
    if item.screenshot_path:
        p = Path(item.screenshot_path)
        if p.is_file():
            image_uri = to_data_uri(p)
            if not item.ambient_tint:
                ambient_tint = extract_ambient_tint(p, is_light_theme=theme.is_light)

    base_shot_ratio = 0.35 if item.command_or_url else 0.39
    max_shot_height = int(height * base_shot_ratio)
    return {
        "image_uri": image_uri,
        "ambient_tint": ambient_tint,
        "max_shot_height": max_shot_height,
    }


def _code_context_builder(
    item: SlideItem,
    index: int,
    total_items: int,
    theme: ThemeConfig,
    width: int,
    height: int,
) -> dict[str, Any]:
    block = item.code_block or CodeBlock(code="", language="text")
    raw_lines = block.code.strip("\n").splitlines() or [""]
    code_lines = highlight_code_lines(block)
    code_lang = block.language.upper()
    code_filename = block.filename or f"snippet.{block.language.lower()}"
    return {
        "title_size": min(_compute_title_font_size(item.title), 86),
        "code_lines": code_lines,
        "code_lang": code_lang,
        "code_filename": code_filename,
        "code_font_size": _compute_code_font_size(raw_lines),
        "show_line_numbers": block.show_line_numbers,
    }


def _versus_context_builder(
    item: SlideItem,
    index: int,
    total_items: int,
    theme: ThemeConfig,
    width: int,
    height: int,
) -> dict[str, Any]:
    return {
        "versus": item.versus,
        "side_by_side": width >= height,
        "title_size": min(_compute_title_font_size(item.title), 84),
    }


def _checklist_context_builder(
    item: SlideItem,
    index: int,
    total_items: int,
    theme: ThemeConfig,
    width: int,
    height: int,
) -> dict[str, Any]:
    return {
        "checklist": item.checklist or ChecklistBlock(),
        "title_size": min(_compute_title_font_size(item.title), 84),
    }


def register_builtin_layouts_and_exporters() -> None:
    """Register the 4 built-in slide layouts and built-in PDF/GIF exporters."""
    from tcd_swipekit.plugins import register_exporter, register_layout

    register_layout(
        SlideLayout.SHOWCASE.value,
        template="slide.html.j2",
        context_builder=_showcase_context_builder,
        description="Hero screenshot / repo / website showcase card (supports browser & macOS frames)",
        builtin=True,
    )
    register_layout(
        SlideLayout.CODE.value,
        template="slide_code.html.j2",
        context_builder=_code_context_builder,
        description="Syntax-highlighted code snippet or terminal diff card (Pygments)",
        builtin=True,
    )
    register_layout(
        SlideLayout.VERSUS.value,
        template="slide_versus.html.j2",
        context_builder=_versus_context_builder,
        description="Responsive A-vs-B comparison card (stacked portrait / side-by-side square)",
        builtin=True,
    )
    register_layout(
        SlideLayout.CHECKLIST.value,
        template="slide_checklist.html.j2",
        context_builder=_checklist_context_builder,
        description="Actionable checklist, roadmap, or step-by-step takeaways card",
        builtin=True,
    )

    register_exporter(
        "pdf",
        export_slides_to_pdf,
        filename="carousel.pdf",
        description="Multi-page PDF document carousel (ready for LinkedIn)",
        builtin=True,
    )
    register_exporter(
        "gif",
        export_slides_to_gif,
        filename="carousel.gif",
        description="Animated GIF slideshow preview for READMEs, X/Twitter, and Slack",
        builtin=True,
    )


def _find_chromium_executable() -> str | None:
    for candidate in ("/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if Path(candidate).exists():
            return candidate
    return None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return slug[:36] or "slide"


class SlideRenderer:
    """Renders a DeckSpec into high-DPI PNG slides, optional PDF/GIF/exporters, caption.md, deck.yaml, and preview.html."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        search_paths = [str(p) for p in get_template_search_dirs(extra_dir=templates_dir)]
        self.env = Environment(
            loader=FileSystemLoader(search_paths),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def build_cover_html(
        self,
        cover: CoverConfig,
        theme: ThemeConfig,
        width: int,
        height: int,
    ) -> str:
        scale = min(width / 1180.0, height / 1572.0)
        cover_image_uri: str | None = None
        if cover.image_path:
            img_path = Path(cover.image_path)
            if img_path.is_file():
                cover_image_uri = to_data_uri(img_path)

        lines = cover.title_lines or ["Trending Tools", "*worth saving*", "right now."]
        template = self.env.get_template("cover.html.j2")
        return template.render(
            width=width,
            height=height,
            scale=f"{scale:.4f}",
            font_css=build_font_css(theme),
            theme=theme,
            cover=cover,
            cover_image_uri=cover_image_uri,
            badge_text=cover.badge_text,
            badge_icon_svg=ICONS_SVG.get(cover.badge_icon, ""),
            title_lines_html=[format_inline_accent(line) for line in lines],
            headline_size=_compute_headline_size(lines),
            subtitle_html=format_inline_bold(cover.subtitle) if cover.subtitle else "",
            cta_text=cover.cta_text or "",
        )

    def build_item_html(
        self,
        item: SlideItem,
        index: int,
        theme: ThemeConfig,
        width: int,
        height: int,
        total_items: int = 1,
    ) -> str:
        from tcd_swipekit.plugins import get_layout

        scale = min(width / 1180.0, height / 1572.0)
        font_css = build_font_css(theme)
        effective_total = max(total_items, index, 1)
        progress_percent = int(round((index / effective_total) * 100))

        base_ctx: dict[str, Any] = {
            **item.extra,
            "extra": item.extra,
            "width": width,
            "height": height,
            "scale": f"{scale:.4f}",
            "font_css": font_css,
            "theme": theme,
            "item": item,
            "slide_number": f"{index:02d}",
            "total_items": effective_total,
            "total_items_str": f"{effective_total:02d}",
            "progress_percent": progress_percent,
            "title_size": _compute_title_font_size(item.title),
        }

        layout_key = item.layout.value if isinstance(item.layout, SlideLayout) else str(item.layout)
        layout_reg = get_layout(layout_key)

        if layout_reg is not None and layout_reg.context_builder is not None:
            base_ctx.update(
                layout_reg.context_builder(item, index, effective_total, theme, width, height)
            )
        else:
            # Always provide default showcase image/ambient variables for custom drop-in templates
            base_ctx.update(
                _showcase_context_builder(item, index, effective_total, theme, width, height)
            )

        if item.custom_template:
            custom_path = Path(item.custom_template).expanduser()
            if custom_path.is_file():
                tpl = self.env.from_string(custom_path.read_text(encoding="utf-8"))
                return tpl.render(**base_ctx)
            tpl = self.env.get_template(item.custom_template)
            return tpl.render(**base_ctx)

        template_name = layout_reg.template if layout_reg is not None else f"slide_{layout_key}.html.j2"
        template = self.env.get_template(template_name)
        return template.render(**base_ctx)

    def build_outro_html(
        self,
        outro: OutroConfig,
        theme: ThemeConfig,
        width: int,
        height: int,
    ) -> str:
        scale = min(width / 1180.0, height / 1572.0)
        action_svgs = {
            "bookmark": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>',
            "follow": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>',
            "comment": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
            "share": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>',
        }
        lines = outro.title_lines or ["Save this post", "*& follow*", "for more tools."]
        actions_ctx = [
            {
                "label": act.label,
                "sublabel": act.sublabel,
                "accent": act.accent,
                "icon_svg": action_svgs.get(act.icon, action_svgs["bookmark"]),
            }
            for act in outro.actions
        ]
        template = self.env.get_template("outro.html.j2")
        return template.render(
            width=width,
            height=height,
            scale=f"{scale:.4f}",
            font_css=build_font_css(theme),
            theme=theme,
            badge_text=outro.badge_text or "",
            title_lines_html=[format_inline_accent(line) for line in lines],
            subtitle_html=format_inline_bold(outro.subtitle) if outro.subtitle else "",
            actions=actions_ctx,
            handle=outro.handle or theme.watermark or "",
            footer_note=outro.footer_note or "",
        )

    @staticmethod
    def _capture_html_to_png(
        browser: Any,
        html_content: str,
        out_path: Path,
        width: int,
        height: int,
    ) -> None:
        """Render an HTML document into a PNG using a fresh isolated page (with crash-retry)."""
        last_err: Exception | None = None
        for _attempt in range(2):
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
            try:
                page.set_content(html_content, wait_until="load")
                with contextlib.suppress(Exception):
                    page.wait_for_load_state("networkidle", timeout=5000)
                page.evaluate("document.fonts.ready")
                page.screenshot(path=str(out_path), type="png")
                return
            except Exception as exc:
                last_err = exc
            finally:
                with contextlib.suppress(Exception):
                    page.close()
        if last_err is not None:
            raise last_err

    def _render_single_with_browser(
        self,
        browser: Any,
        deck: DeckSpec,
        output_dir: Path,
        write_extras: bool = True,
        export_pdf: bool = False,
        export_gif: bool = False,
        exporters: list[str] | None = None,
    ) -> list[Path]:
        """Render a single DeckSpec using an already-open Playwright browser."""
        from tcd_swipekit.plugins import get_exporter

        output_dir.mkdir(parents=True, exist_ok=True)
        width, height = deck.aspect_ratio.dimensions

        rendered_paths: list[Path] = []
        total_items = len(deck.items)

        # Slide 01: Cover
        cover_html = self.build_cover_html(deck.cover, deck.theme, width, height)
        cover_out = output_dir / "01_cover.png"
        self._capture_html_to_png(browser, cover_html, cover_out, width, height)
        rendered_paths.append(cover_out)

        # Slides 02..N: Items
        for idx, item in enumerate(deck.items, start=1):
            slide_html = self.build_item_html(
                item,
                idx,
                deck.theme,
                width,
                height,
                total_items=total_items,
            )
            filename = f"{idx + 1:02d}_{_slugify(item.title)}.png"
            slide_out = output_dir / filename
            self._capture_html_to_png(browser, slide_html, slide_out, width, height)
            rendered_paths.append(slide_out)

        # Optional Closing CTA Slide
        if deck.outro and deck.outro.enabled:
            outro_html = self.build_outro_html(deck.outro, deck.theme, width, height)
            outro_num = len(deck.items) + 2
            outro_out = output_dir / f"{outro_num:02d}_closing_cta.png"
            self._capture_html_to_png(browser, outro_html, outro_out, width, height)
            rendered_paths.append(outro_out)

        requested_exporters: list[str] = []
        if export_pdf:
            requested_exporters.append("pdf")
        if export_gif:
            requested_exporters.append("gif")
        if exporters:
            for exp_name in exporters:
                norm = exp_name.strip().lower()
                if norm and norm not in requested_exporters:
                    requested_exporters.append(norm)

        pdf_filename: str | None = None
        gif_filename: str | None = None
        extra_exports: list[str] = []

        for exp_name in requested_exporters:
            reg = get_exporter(exp_name)
            out_file = output_dir / reg.filename
            reg.fn(rendered_paths, out_file, deck)
            if exp_name == "pdf":
                pdf_filename = out_file.name
            elif exp_name == "gif":
                gif_filename = out_file.name
            else:
                extra_exports.append(out_file.name)

        if write_extras:
            # Save caption.md
            caption_path = output_dir / "caption.md"
            caption_path.write_text(build_caption_markdown(deck), encoding="utf-8")

            # Save deck.yaml snapshot for quick re-rendering after manual edits
            deck_yaml_path = output_dir / "deck.yaml"
            deck_yaml_path.write_text(
                yaml.safe_dump(
                    deck.model_dump(mode="json", exclude_none=True),
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )

            # Save interactive preview.html with Safe-Zone Overlay
            preview_tpl = self.env.get_template("preview.html.j2")
            preview_html = preview_tpl.render(
                topic=deck.topic,
                slides=[p.name for p in rendered_paths],
                aspect_ratio=deck.aspect_ratio.value,
                width=width,
                height=height,
                pdf_filename=pdf_filename,
                gif_filename=gif_filename,
                extra_exports=extra_exports,
            )
            (output_dir / "preview.html").write_text(preview_html, encoding="utf-8")

        return rendered_paths

    def render_deck(
        self,
        deck: DeckSpec,
        output_dir: Path,
        write_extras: bool = True,
        export_pdf: bool = False,
        export_gif: bool = False,
        exporters: list[str] | None = None,
    ) -> list[Path]:
        """Render cover + all item slides + optional closing CTA slide to PNGs (and optional PDF/GIF/exporters)."""
        executable = _find_chromium_executable()
        launch_kwargs: dict[str, object] = {
            "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        }
        if executable:
            launch_kwargs["executable_path"] = executable

        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)
            try:
                return self._render_single_with_browser(
                    browser=browser,
                    deck=deck,
                    output_dir=output_dir,
                    write_extras=write_extras,
                    export_pdf=export_pdf,
                    export_gif=export_gif,
                    exporters=exporters,
                )
            finally:
                browser.close()

    def render_multi_ratio(
        self,
        deck: DeckSpec,
        output_dir: Path,
        ratios: list[AspectRatio],
        write_extras: bool = True,
        export_pdf: bool = False,
        export_gif: bool = False,
        exporters: list[str] | None = None,
    ) -> dict[AspectRatio, list[Path]]:
        """Render the same DeckSpec across multiple aspect ratios in one browser session.

        When a single ratio is provided, renders directly into `output_dir`.
        When multiple ratios are provided, renders each ratio into `output_dir/<folder_slug>/`.
        """
        unique_ratios = list(dict.fromkeys(ratios))
        if not unique_ratios:
            unique_ratios = [deck.aspect_ratio]

        if len(unique_ratios) == 1:
            single_deck = deck.model_copy(update={"aspect_ratio": unique_ratios[0]})
            return {
                unique_ratios[0]: self.render_deck(
                    single_deck,
                    output_dir=output_dir,
                    write_extras=write_extras,
                    export_pdf=export_pdf,
                    export_gif=export_gif,
                    exporters=exporters,
                )
            }

        executable = _find_chromium_executable()
        launch_kwargs: dict[str, object] = {
            "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        }
        if executable:
            launch_kwargs["executable_path"] = executable

        results: dict[AspectRatio, list[Path]] = {}
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)
            try:
                for ratio in unique_ratios:
                    ratio_deck = deck.model_copy(update={"aspect_ratio": ratio})
                    sub_dir = output_dir / ratio.folder_slug
                    results[ratio] = self._render_single_with_browser(
                        browser=browser,
                        deck=ratio_deck,
                        output_dir=sub_dir,
                        write_extras=write_extras,
                        export_pdf=export_pdf,
                        export_gif=export_gif,
                        exporters=exporters,
                    )
            finally:
                browser.close()

        return results
