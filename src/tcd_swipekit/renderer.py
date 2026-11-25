"""HTML/CSS Jinja2 + Playwright Chromium slide renderer for TCD-Swipekit."""

from __future__ import annotations

import contextlib
import html
import re
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from tcd_swipekit.copywriter import build_caption_markdown
from tcd_swipekit.image_utils import extract_ambient_tint, to_data_uri
from tcd_swipekit.models import CoverConfig, DeckSpec, OutroConfig, SlideItem, ThemeConfig
from tcd_swipekit.themes.loader import TEMPLATES_DIR

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


def _find_chromium_executable() -> str | None:
    for candidate in ("/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if Path(candidate).exists():
            return candidate
    return None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return slug[:36] or "slide"


class SlideRenderer:
    """Renders a DeckSpec into high-DPI PNG slides, caption.md, deck.yaml, and preview.html."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir or TEMPLATES_DIR)),
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
    ) -> str:
        scale = min(width / 1180.0, height / 1572.0)
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

        # Adapt max screenshot height based on aspect ratio and footer density
        base_shot_ratio = 0.35 if item.command_or_url else 0.39
        max_shot_height = int(height * base_shot_ratio)

        template = self.env.get_template("slide.html.j2")
        return template.render(
            width=width,
            height=height,
            scale=f"{scale:.4f}",
            theme=theme,
            item=item,
            slide_number=f"{index:02d}",
            title_size=_compute_title_font_size(item.title),
            image_uri=image_uri,
            ambient_tint=ambient_tint,
            max_shot_height=max_shot_height,
        )

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
            theme=theme,
            badge_text=outro.badge_text or "",
            title_lines_html=[format_inline_accent(line) for line in lines],
            subtitle_html=format_inline_bold(outro.subtitle) if outro.subtitle else "",
            actions=actions_ctx,
            handle=outro.handle or theme.watermark or "@trycatchdev",
            footer_note=outro.footer_note or "",
        )

    def render_deck(
        self,
        deck: DeckSpec,
        output_dir: Path,
        write_extras: bool = True,
    ) -> list[Path]:
        """Render cover + all item slides + optional closing CTA slide to PNGs."""
        output_dir.mkdir(parents=True, exist_ok=True)
        width, height = deck.aspect_ratio.dimensions

        rendered_paths: list[Path] = []
        executable = _find_chromium_executable()
        launch_kwargs: dict[str, object] = {"args": ["--no-sandbox"]}
        if executable:
            launch_kwargs["executable_path"] = executable

        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)
            try:
                page = browser.new_page(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                )

                # Slide 01: Cover
                cover_html = self.build_cover_html(deck.cover, deck.theme, width, height)
                page.set_content(cover_html, wait_until="load")
                with contextlib.suppress(Exception):
                    page.wait_for_load_state("networkidle", timeout=5000)
                page.evaluate("document.fonts.ready")
                cover_out = output_dir / "01_cover.png"
                page.screenshot(path=str(cover_out), type="png")
                rendered_paths.append(cover_out)

                # Slides 02..N: Items
                for idx, item in enumerate(deck.items, start=1):
                    slide_html = self.build_item_html(item, idx, deck.theme, width, height)
                    page.set_content(slide_html, wait_until="load")
                    with contextlib.suppress(Exception):
                        page.wait_for_load_state("networkidle", timeout=5000)
                    page.evaluate("document.fonts.ready")
                    filename = f"{idx + 1:02d}_{_slugify(item.title)}.png"
                    slide_out = output_dir / filename
                    page.screenshot(path=str(slide_out), type="png")
                    rendered_paths.append(slide_out)

                # Optional Closing CTA Slide
                if deck.outro and deck.outro.enabled:
                    outro_html = self.build_outro_html(deck.outro, deck.theme, width, height)
                    page.set_content(outro_html, wait_until="load")
                    with contextlib.suppress(Exception):
                        page.wait_for_load_state("networkidle", timeout=5000)
                    page.evaluate("document.fonts.ready")
                    outro_num = len(deck.items) + 2
                    outro_out = output_dir / f"{outro_num:02d}_closing_cta.png"
                    page.screenshot(path=str(outro_out), type="png")
                    rendered_paths.append(outro_out)
            finally:
                browser.close()

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

            # Save interactive preview.html
            preview_tpl = self.env.get_template("preview.html.j2")
            preview_html = preview_tpl.render(
                topic=deck.topic,
                slides=[p.name for p in rendered_paths],
            )
            (output_dir / "preview.html").write_text(preview_html, encoding="utf-8")

        return rendered_paths
