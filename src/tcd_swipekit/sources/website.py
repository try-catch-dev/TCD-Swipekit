"""Website source provider: reads sites.yml, captures Playwright screenshots & OpenGraph metadata."""

from __future__ import annotations

import contextlib
import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse

import yaml
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from tcd_swipekit.i18n import t
from tcd_swipekit.models import (
    BadgeStyle,
    Language,
    SiteEntry,
    SitesFile,
    SlideBadge,
    SlideItem,
)
from tcd_swipekit.sources.base import BaseSource

COOKIE_DISMISS_JS = """
() => {
  const selectors = [
    '[id*="cookie" i] button',
    '[class*="cookie" i] button',
    '[aria-label*="accept" i]',
    'button[id*="accept" i]',
    '[class*="consent" i] button'
  ];
  for (const sel of selectors) {
    const btns = document.querySelectorAll(sel);
    for (const btn of btns) {
      const txt = (btn.innerText || '').toLowerCase();
      if (txt.includes('accept') || txt.includes('agree') || txt.includes('ok') || txt.includes('got it') || txt.includes('reject')) {
        try { btn.click(); return true; } catch (e) {}
      }
    }
  }
  return false;
}
"""


def parse_website_metadata(html: str, url: str) -> tuple[str, str]:
    """Extract clean (title, description) from website HTML OpenGraph / meta tags."""
    soup = BeautifulSoup(html, "html.parser")
    domain = urlparse(url).netloc.removeprefix("www.")

    og_title = soup.find("meta", property="og:title")
    title_tag = soup.find("title")
    raw_title = (
        (og_title.get("content") if og_title else None)
        or (title_tag.get_text(" ", strip=True) if title_tag else None)
        or domain
    )
    # Trim verbose tagline after separators if very long
    clean_title = re.split(r"\s+[|\-–—·:]\s+", str(raw_title).strip())[0].strip()
    if len(clean_title) > 36:
        clean_title = clean_title[:36].rsplit(" ", 1)[0]

    og_desc = soup.find("meta", property="og:description")
    meta_desc = soup.find("meta", attrs={"name": "description"})
    raw_desc = (
        (og_desc.get("content") if og_desc else None)
        or (meta_desc.get("content") if meta_desc else None)
        or ""
    )
    clean_desc = re.sub(r"\s+", " ", str(raw_desc)).strip()
    return clean_title or domain, clean_desc


def load_sites_file(path: Path) -> SitesFile:
    """Load and validate a `sites.yml` / `sites.yaml` configuration file."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return SitesFile.model_validate(data)


def _find_chromium_executable() -> str | None:
    for candidate in ("/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if Path(candidate).exists():
            return candidate
    return None


class WebsiteSource(BaseSource):
    """Captures desktop screenshots & metadata for websites defined in `sites.yml`."""

    def __init__(
        self,
        cache_dir: Path,
        language: Language = Language.EN,
        viewport_width: int = 1280,
        viewport_height: int = 800,
    ) -> None:
        super().__init__(cache_dir=cache_dir, language=language)
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

    def _capture_site(
        self,
        page: object,
        entry: SiteEntry,
        base_dir: Path | None = None,
    ) -> tuple[Path | None, str, str]:
        """Navigate to a website via Playwright, capture screenshot and return (path, title, desc)."""
        if entry.screenshot_path:
            p = Path(entry.screenshot_path)
            if not p.is_absolute() and base_dir:
                p = (base_dir / p).resolve()
            if p.exists():
                return p, entry.title or urlparse(entry.url).netloc, entry.description or ""

        digest = hashlib.sha256(entry.url.encode("utf-8")).hexdigest()[:14]
        out_shot = self.cache_dir / f"web_{digest}.png"

        fetched_title = ""
        fetched_desc = ""
        try:
            page.goto(entry.url, wait_until="domcontentloaded", timeout=25000)  # type: ignore[attr-defined]
            with contextlib.suppress(Exception):
                page.wait_for_load_state("networkidle", timeout=6000)  # type: ignore[attr-defined]
            page.evaluate(COOKIE_DISMISS_JS)  # type: ignore[attr-defined]
            page.wait_for_timeout(entry.wait_ms)  # type: ignore[attr-defined]

            html = page.content()  # type: ignore[attr-defined]
            fetched_title, fetched_desc = parse_website_metadata(html, entry.url)
            page.screenshot(path=str(out_shot), type="png", full_page=False)  # type: ignore[attr-defined]
            return out_shot, fetched_title, fetched_desc
        except Exception:
            return (out_shot if out_shot.exists() else None), fetched_title, fetched_desc

    def fetch_from_entries(
        self,
        entries: list[SiteEntry],
        base_dir: Path | None = None,
    ) -> list[SlideItem]:
        """Convert validated SiteEntry rows into SlideItem objects with real screenshots."""
        if not entries:
            return []

        items: list[SlideItem] = []
        executable = _find_chromium_executable()
        launch_kwargs: dict[str, object] = {"args": ["--no-sandbox"]}
        if executable:
            launch_kwargs["executable_path"] = executable

        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_kwargs)
            try:
                for entry in entries:
                    color_scheme = "dark" if entry.dark_mode else "light"
                    context = browser.new_context(
                        viewport={"width": self.viewport_width, "height": self.viewport_height},
                        color_scheme=color_scheme,
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                        ),
                    )
                    page = context.new_page()
                    shot_path, auto_title, auto_desc = self._capture_site(page, entry, base_dir)
                    context.close()

                    domain = urlparse(entry.url).netloc.removeprefix("www.")
                    title = entry.title or auto_title or domain
                    description = entry.description or auto_desc or f"Useful web tool at {domain}."
                    eyebrow = entry.eyebrow or domain

                    if entry.badges:
                        badges = entry.badges
                    else:
                        pricing = entry.pricing or t(self.language, "default_web_badge")
                        category = entry.category or t(self.language, "default_web_type")
                        badges = [
                            SlideBadge(text=pricing, style=BadgeStyle.ACCENT),
                            SlideBadge(text=category, style=BadgeStyle.GLASS),
                            SlideBadge(text=domain, style=BadgeStyle.GLASS),
                        ]

                    items.append(
                        SlideItem(
                            source="website",
                            eyebrow=eyebrow,
                            title=title,
                            description=description,
                            screenshot_path=str(shot_path) if shot_path else None,
                            url=entry.url,
                            badges=badges,
                            command_or_url=entry.command_or_url or entry.url,
                            footnote=entry.footnote,
                            footnote_accent=entry.footnote_accent,
                            image_fit="cover",
                        )
                    )
            finally:
                browser.close()

        return items

    def fetch_items(
        self,
        limit: int = 6,
        *,
        sites_file: Path | None = None,
        entries: list[SiteEntry] | None = None,
        **kwargs: object,
    ) -> list[SlideItem]:
        """Fetch website slides from a `sites.yml` path or a list of SiteEntry models."""
        base_dir: Path | None = None
        if sites_file is not None:
            parsed = load_sites_file(sites_file)
            base_dir = sites_file.parent
            target_entries = parsed.sites[:limit]
        elif entries is not None:
            target_entries = entries[:limit]
        else:
            target_entries = []

        return self.fetch_from_entries(target_entries, base_dir=base_dir)
