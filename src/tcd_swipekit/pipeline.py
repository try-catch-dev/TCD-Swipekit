"""High-level pipeline orchestration API for TCD-Swipekit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tcd_swipekit.copywriter import maybe_enhance_with_ai, populate_cover_defaults
from tcd_swipekit.models import (
    AspectRatio,
    CoverConfig,
    CoverMode,
    DeckSpec,
    Language,
    WatermarkPosition,
)
from tcd_swipekit.renderer import SlideRenderer
from tcd_swipekit.sources.github import GitHubSource
from tcd_swipekit.sources.manual import ManualDeckSource, load_deck_yaml
from tcd_swipekit.sources.website import WebsiteSource, load_sites_file
from tcd_swipekit.themes.loader import load_theme


def _build_theme_overrides(
    accent_color: str | None = None,
    watermark: str | None = None,
    watermark_position: WatermarkPosition | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overrides: dict[str, Any] = dict(extra or {})
    if accent_color:
        overrides["accent_color"] = accent_color
    if watermark is not None:
        overrides["watermark"] = watermark
    if watermark_position is not None:
        overrides["watermark_position"] = watermark_position
    return overrides


def generate_github_deck(
    *,
    output_dir: Path,
    topic: str | None = None,
    repos: list[str] | None = None,
    limit: int = 6,
    since: str = "weekly",
    prog_lang: str | None = None,
    language: Language = Language.EN,
    aspect_ratio: AspectRatio = AspectRatio.PORTRAIT_3_4,
    part: int = 1,
    theme_name: str = "midnight-emerald",
    accent_color: str | None = None,
    watermark: str | None = None,
    watermark_position: WatermarkPosition | None = None,
    cover_mode: CoverMode | None = None,
    cover_image: Path | None = None,
    cover_badge: str | None = None,
    cover_cta: str | None = None,
    use_ai: bool = False,
    cache_dir: Path | None = None,
) -> tuple[DeckSpec, list[Path]]:
    """Fetch trending or topic-filtered GitHub repos and render a complete carousel deck."""
    cache = cache_dir or (output_dir / ".cache")
    source = GitHubSource(cache_dir=cache, language=language)
    items = source.fetch_items(
        limit=limit,
        topic=topic,
        repos=repos,
        since=since,
        prog_lang=prog_lang,
    )

    theme = load_theme(
        theme_name,
        overrides=_build_theme_overrides(accent_color, watermark, watermark_position),
    )
    resolved_cover_mode = cover_mode or (CoverMode.PHOTO if cover_image else CoverMode.GRADIENT)
    cover = CoverConfig(
        mode=resolved_cover_mode,
        image_path=str(cover_image.resolve()) if cover_image else None,
        badge_icon="github",
        badge_text=cover_badge,
        cta_text=cover_cta,
    )

    deck = DeckSpec(
        topic=topic or "Trending Open Source Tools",
        language=language,
        aspect_ratio=aspect_ratio,
        part=part,
        theme=theme,
        cover=cover,
        items=items,
    )
    deck = populate_cover_defaults(deck, source_kind="github")
    if use_ai:
        deck = maybe_enhance_with_ai(deck)

    paths = SlideRenderer().render_deck(deck, output_dir=output_dir)
    return deck, paths


def generate_website_deck(
    *,
    sites_file: Path,
    output_dir: Path,
    limit: int | None = None,
    topic: str | None = None,
    language: Language | None = None,
    aspect_ratio: AspectRatio | None = None,
    part: int | None = None,
    theme_name: str | None = None,
    accent_color: str | None = None,
    watermark: str | None = None,
    watermark_position: WatermarkPosition | None = None,
    cover_mode: CoverMode | None = None,
    cover_image: Path | None = None,
    use_ai: bool = False,
    cache_dir: Path | None = None,
) -> tuple[DeckSpec, list[Path]]:
    """Read `sites.yml`, capture live desktop screenshots, and render a website carousel."""
    parsed = load_sites_file(sites_file)
    lang = language or parsed.language
    ratio = aspect_ratio or parsed.aspect_ratio
    effective_part = part if part is not None else parsed.part
    effective_topic = topic or parsed.topic

    cache = cache_dir or (output_dir / ".cache")
    source = WebsiteSource(cache_dir=cache, language=lang)
    entries = parsed.sites[:limit] if limit else parsed.sites
    items = source.fetch_from_entries(entries, base_dir=sites_file.parent)

    preset_from_file = str(parsed.theme.get("preset", "cyber-indigo"))
    chosen_theme = theme_name or preset_from_file
    theme = load_theme(
        chosen_theme,
        overrides=_build_theme_overrides(
            accent_color=accent_color,
            watermark=watermark,
            watermark_position=watermark_position,
            extra={k: v for k, v in parsed.theme.items() if k != "preset"},
        ),
    )

    cover = parsed.cover.model_copy(deep=True)
    if cover_image:
        cover.image_path = str(cover_image.resolve())
        cover.mode = cover_mode or CoverMode.PHOTO
    elif cover.image_path:
        cov_path = Path(cover.image_path)
        if not cov_path.is_absolute():
            cov_path = (sites_file.parent / cov_path).resolve()
        cover.image_path = str(cov_path)
        if cover_mode:
            cover.mode = cover_mode
    elif cover_mode:
        cover.mode = cover_mode

    deck = DeckSpec(
        topic=effective_topic,
        language=lang,
        aspect_ratio=ratio,
        part=effective_part,
        theme=theme,
        cover=cover,
        outro=parsed.outro,
        items=items,
        hashtags=parsed.hashtags,
    )
    deck = populate_cover_defaults(deck, source_kind="website")
    if use_ai:
        deck = maybe_enhance_with_ai(deck)

    paths = SlideRenderer().render_deck(deck, output_dir=output_dir)
    return deck, paths


def render_deck_file(
    *,
    deck_file: Path,
    output_dir: Path,
    theme_name: str | None = None,
    accent_color: str | None = None,
    watermark: str | None = None,
    watermark_position: WatermarkPosition | None = None,
    cover_image: Path | None = None,
    cover_mode: CoverMode | None = None,
    aspect_ratio: AspectRatio | None = None,
    cache_dir: Path | None = None,
) -> tuple[DeckSpec, list[Path]]:
    """Load an existing `deck.yaml` (manual or hybrid), enrich missing screenshots, and render."""
    deck = load_deck_yaml(deck_file)
    cache = cache_dir or (output_dir / ".cache")

    # Apply theme preset + file theme fields + CLI overrides
    preset_target = theme_name or deck.theme.preset
    file_theme_overrides = deck.theme.model_dump(exclude_defaults=True)
    file_theme_overrides.pop("preset", None)
    deck.theme = load_theme(
        preset_target,
        overrides=_build_theme_overrides(
            accent_color=accent_color,
            watermark=watermark,
            watermark_position=watermark_position,
            extra=file_theme_overrides,
        ),
    )

    if cover_image:
        deck.cover.image_path = str(cover_image.resolve())
        deck.cover.mode = cover_mode or CoverMode.PHOTO
    elif cover_mode:
        deck.cover.mode = cover_mode
    if aspect_ratio:
        deck.aspect_ratio = aspect_ratio

    manual_source = ManualDeckSource(cache_dir=cache, language=deck.language)
    deck = manual_source.enrich_deck(deck, base_dir=deck_file.parent)
    source_kind = "website" if deck.items and deck.items[0].source == "website" else "github"
    deck = populate_cover_defaults(deck, source_kind=source_kind)

    paths = SlideRenderer().render_deck(deck, output_dir=output_dir)
    return deck, paths
