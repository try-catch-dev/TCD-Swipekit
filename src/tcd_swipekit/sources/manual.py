"""Manual / hybrid deck loader supporting YAML specs with optional auto-enrichment."""

from __future__ import annotations

from pathlib import Path

import yaml

from tcd_swipekit.image_utils import download_image, smart_crop_margins
from tcd_swipekit.models import DeckSpec, Language, SiteEntry, SlideItem
from tcd_swipekit.sources.base import BaseSource
from tcd_swipekit.sources.github import GitHubSource
from tcd_swipekit.sources.website import WebsiteSource


def load_deck_yaml(path: Path) -> DeckSpec:
    """Load and validate a DeckSpec from a YAML file."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return DeckSpec.model_validate(raw)


class ManualDeckSource(BaseSource):
    """Loads a hybrid `deck.yaml` and enriches missing screenshots for GitHub/website items."""

    def __init__(self, cache_dir: Path, language: Language = Language.EN) -> None:
        super().__init__(cache_dir=cache_dir, language=language)

    def enrich_deck(self, deck: DeckSpec, base_dir: Path | None = None) -> DeckSpec:
        """Resolve local paths and auto-fetch missing screenshots for GitHub/website entries."""
        if deck.cover.image_path and base_dir:
            cov = Path(deck.cover.image_path)
            if not cov.is_absolute():
                resolved = (base_dir / cov).resolve()
                if resolved.exists():
                    deck.cover.image_path = str(resolved)

        gh_source = GitHubSource(cache_dir=self.cache_dir, language=deck.language)
        web_source = WebsiteSource(cache_dir=self.cache_dir, language=deck.language)
        enriched: list[SlideItem] = []

        for item in deck.items:
            # Resolve relative local screenshot paths
            if item.screenshot_path and base_dir:
                p = Path(item.screenshot_path)
                if not p.is_absolute():
                    resolved = (base_dir / p).resolve()
                    if resolved.exists():
                        item.screenshot_path = str(resolved)

            # Download remote screenshot_url if provided
            if not item.screenshot_path and item.screenshot_url:
                dl = download_image(item.screenshot_url, self.cache_dir)
                if dl:
                    item.screenshot_path = str(smart_crop_margins(dl))

            # Auto-enrich GitHub items missing screenshot or badges
            if item.source == "github" and item.repo and (not item.screenshot_path or not item.badges):
                fetched = gh_source.fetch_repo(item.repo)
                if fetched:
                    item.screenshot_path = item.screenshot_path or fetched.screenshot_path
                    item.badges = item.badges or fetched.badges
                    item.eyebrow = item.eyebrow or fetched.eyebrow
                    item.description = item.description or fetched.description
                    item.url = item.url or fetched.url

            # Auto-screenshot website items missing screenshot
            if item.source == "website" and item.url and not item.screenshot_path:
                fetched_list = web_source.fetch_from_entries(
                    [
                        SiteEntry(
                            url=item.url,
                            title=item.title,
                            eyebrow=item.eyebrow or None,
                            description=item.description or None,
                            badges=item.badges,
                            command_or_url=item.command_or_url,
                            footnote=item.footnote,
                        )
                    ]
                )
                if fetched_list:
                    fetched_web = fetched_list[0]
                    item.screenshot_path = fetched_web.screenshot_path
                    item.badges = item.badges or fetched_web.badges
                    item.description = item.description or fetched_web.description
                    item.eyebrow = item.eyebrow or fetched_web.eyebrow

            enriched.append(item)

        deck.items = enriched
        return deck

    def fetch_items(
        self,
        limit: int = 12,
        *,
        deck_file: Path | None = None,
        **kwargs: object,
    ) -> list[SlideItem]:
        if deck_file is None:
            return []
        deck = load_deck_yaml(deck_file)
        deck = self.enrich_deck(deck, base_dir=deck_file.parent)
        return deck.items[:limit]
