"""High-level pipeline orchestration API for TCD-Swipekit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tcd_swipekit.copywriter import (
    build_default_outro,
    maybe_enhance_with_ai,
    populate_cover_defaults,
)
from tcd_swipekit.models import (
    AspectRatio,
    CoverConfig,
    CoverMode,
    CreatorProfile,
    DeckSpec,
    Language,
    OutroConfig,
    WatermarkPosition,
)
from tcd_swipekit.renderer import SlideRenderer
from tcd_swipekit.sources.github import GitHubSource
from tcd_swipekit.sources.manual import ManualDeckSource, load_deck_yaml
from tcd_swipekit.sources.website import WebsiteSource, load_sites_file
from tcd_swipekit.themes.loader import load_theme


def parse_ratios(raw: str | None) -> list[AspectRatio] | None:
    """Parse a comma-separated ratio list like '3:4,4:5,1:1' or 'all'."""
    if not raw:
        return None
    cleaned = raw.strip().lower()
    if cleaned == "all":
        return list(AspectRatio)
    valid = {r.value: r for r in AspectRatio}
    result: list[AspectRatio] = []
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if token not in valid:
            allowed = ", ".join(valid.keys())
            raise ValueError(f"Unsupported aspect ratio '{token}'. Choose from: {allowed}, or 'all'.")
        ratio = valid[token]
        if ratio not in result:
            result.append(ratio)
    return result or None


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


def _resolve_outro(
    *,
    include_outro: bool | None,
    file_outro: OutroConfig | None,
    profile: CreatorProfile | None,
    language: Language,
    handle: str | None,
    part: int,
) -> OutroConfig | None:
    if include_outro is False:
        return None
    if file_outro is not None:
        return file_outro
    if profile and profile.outro is not None:
        return profile.outro.model_copy(deep=True)
    if include_outro is True:
        return build_default_outro(language=language, handle=handle, part=part)
    return None


def _render_with_ratios(
    deck: DeckSpec,
    output_dir: Path,
    ratios: list[AspectRatio] | None,
    export_pdf: bool,
) -> list[Path]:
    renderer = SlideRenderer()
    target_ratios = ratios or [deck.aspect_ratio]
    if len(target_ratios) == 1:
        single_deck = deck.model_copy(update={"aspect_ratio": target_ratios[0]})
        return renderer.render_deck(single_deck, output_dir=output_dir, export_pdf=export_pdf)

    by_ratio = renderer.render_multi_ratio(
        deck,
        output_dir=output_dir,
        ratios=target_ratios,
        export_pdf=export_pdf,
    )
    flattened: list[Path] = []
    for ratio_paths in by_ratio.values():
        flattened.extend(ratio_paths)
    return flattened


def generate_github_deck(
    *,
    output_dir: Path,
    topic: str | None = None,
    repos: list[str] | None = None,
    limit: int = 6,
    since: str = "weekly",
    prog_lang: str | None = None,
    language: Language | None = None,
    aspect_ratio: AspectRatio | None = None,
    ratios: list[AspectRatio] | None = None,
    part: int = 1,
    theme_name: str | None = None,
    accent_color: str | None = None,
    watermark: str | None = None,
    watermark_position: WatermarkPosition | None = None,
    cover_mode: CoverMode | None = None,
    cover_image: Path | None = None,
    cover_badge: str | None = None,
    cover_cta: str | None = None,
    include_outro: bool | None = None,
    export_pdf: bool | None = None,
    use_ai: bool = False,
    cache_dir: Path | None = None,
    profile: CreatorProfile | None = None,
) -> tuple[DeckSpec, list[Path]]:
    """Fetch trending or topic-filtered GitHub repos and render a complete carousel deck."""
    effective_lang = language or (profile.language if profile and profile.language else Language.EN)
    effective_ratio = aspect_ratio or (
        profile.aspect_ratio if profile and profile.aspect_ratio else AspectRatio.PORTRAIT_3_4
    )
    effective_ratios = ratios or (
        [aspect_ratio]
        if aspect_ratio is not None
        else (profile.ratios if profile and profile.ratios else [effective_ratio])
    )
    effective_theme_name = theme_name or (
        profile.theme if profile and profile.theme else "midnight-emerald"
    )
    effective_accent = accent_color or (profile.accent_color if profile else None)
    effective_watermark = watermark if watermark is not None else (
        profile.watermark if profile else None
    )
    effective_wm_pos = watermark_position or (
        profile.watermark_position if profile else None
    )
    effective_cover_image: str | None = (
        str(cover_image.resolve())
        if cover_image
        else (profile.cover_image if profile else None)
    )
    resolved_cover_mode = (
        cover_mode
        or (CoverMode.PHOTO if effective_cover_image else None)
        or (profile.cover_mode if profile and profile.cover_mode else CoverMode.GRADIENT)
    )
    effective_pdf = (
        export_pdf
        if export_pdf is not None
        else (bool(profile.export_pdf) if profile and profile.export_pdf is not None else False)
    )

    cache = cache_dir or (output_dir / ".cache")
    source = GitHubSource(cache_dir=cache, language=effective_lang)
    items = source.fetch_items(
        limit=limit,
        topic=topic,
        repos=repos,
        since=since,
        prog_lang=prog_lang,
    )

    theme = load_theme(
        effective_theme_name,
        overrides=_build_theme_overrides(effective_accent, effective_watermark, effective_wm_pos),
    )
    cover = CoverConfig(
        mode=resolved_cover_mode,
        image_path=effective_cover_image,
        badge_icon="github",
        badge_text=cover_badge,
        cta_text=cover_cta,
    )
    outro = _resolve_outro(
        include_outro=include_outro,
        file_outro=None,
        profile=profile,
        language=effective_lang,
        handle=theme.watermark,
        part=part,
    )

    deck = DeckSpec(
        topic=topic or "Trending Open Source Tools",
        language=effective_lang,
        aspect_ratio=effective_ratios[0],
        part=part,
        theme=theme,
        cover=cover,
        outro=outro,
        items=items,
        hashtags=list(profile.hashtags) if profile and profile.hashtags else [],
    )
    deck = populate_cover_defaults(deck, source_kind="github")
    if use_ai:
        deck = maybe_enhance_with_ai(deck)

    paths = _render_with_ratios(
        deck=deck,
        output_dir=output_dir,
        ratios=effective_ratios,
        export_pdf=effective_pdf,
    )
    return deck, paths


def generate_website_deck(
    *,
    sites_file: Path,
    output_dir: Path,
    limit: int | None = None,
    topic: str | None = None,
    language: Language | None = None,
    aspect_ratio: AspectRatio | None = None,
    ratios: list[AspectRatio] | None = None,
    part: int | None = None,
    theme_name: str | None = None,
    accent_color: str | None = None,
    watermark: str | None = None,
    watermark_position: WatermarkPosition | None = None,
    cover_mode: CoverMode | None = None,
    cover_image: Path | None = None,
    include_outro: bool | None = None,
    export_pdf: bool | None = None,
    use_ai: bool = False,
    cache_dir: Path | None = None,
    profile: CreatorProfile | None = None,
) -> tuple[DeckSpec, list[Path]]:
    """Read `sites.yml`, capture live desktop screenshots, and render a website carousel."""
    raw_sites = yaml.safe_load(sites_file.read_text(encoding="utf-8")) or {}
    parsed = load_sites_file(sites_file)

    lang = (
        language
        or (parsed.language if "language" in raw_sites else None)
        or (profile.language if profile and profile.language else parsed.language)
    )
    ratio = (
        aspect_ratio
        or (parsed.aspect_ratio if "aspect_ratio" in raw_sites else None)
        or (profile.aspect_ratio if profile and profile.aspect_ratio else parsed.aspect_ratio)
    )
    effective_ratios = ratios or (
        [aspect_ratio]
        if aspect_ratio is not None
        else (
            [parsed.aspect_ratio]
            if "aspect_ratio" in raw_sites
            else (profile.ratios if profile and profile.ratios else [ratio])
        )
    )
    effective_part = part if part is not None else parsed.part
    effective_topic = topic or parsed.topic

    cache = cache_dir or (output_dir / ".cache")
    source = WebsiteSource(cache_dir=cache, language=lang)
    entries = parsed.sites[:limit] if limit else parsed.sites
    items = source.fetch_from_entries(entries, base_dir=sites_file.parent)

    file_preset = parsed.theme.get("preset")
    chosen_theme = (
        theme_name
        or (str(file_preset) if file_preset else None)
        or (profile.theme if profile and profile.theme else "cyber-indigo")
    )
    profile_theme_defaults: dict[str, Any] = {}
    if profile:
        if profile.accent_color and "accent_color" not in parsed.theme:
            profile_theme_defaults["accent_color"] = profile.accent_color
        if profile.watermark and "watermark" not in parsed.theme:
            profile_theme_defaults["watermark"] = profile.watermark
        if profile.watermark_position and "watermark_position" not in parsed.theme:
            profile_theme_defaults["watermark_position"] = profile.watermark_position

    file_theme_extra = {k: v for k, v in parsed.theme.items() if k != "preset"}
    theme = load_theme(
        chosen_theme,
        overrides=_build_theme_overrides(
            accent_color=accent_color,
            watermark=watermark,
            watermark_position=watermark_position,
            extra={**profile_theme_defaults, **file_theme_extra},
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
    elif profile and profile.cover_image and "cover" not in raw_sites:
        cover.image_path = profile.cover_image
        cover.mode = cover_mode or profile.cover_mode or CoverMode.PHOTO
    elif cover_mode:
        cover.mode = cover_mode

    outro = _resolve_outro(
        include_outro=include_outro,
        file_outro=parsed.outro,
        profile=profile,
        language=lang,
        handle=theme.watermark,
        part=effective_part,
    )
    effective_pdf = (
        export_pdf
        if export_pdf is not None
        else (bool(profile.export_pdf) if profile and profile.export_pdf is not None else False)
    )

    deck = DeckSpec(
        topic=effective_topic,
        language=lang,
        aspect_ratio=effective_ratios[0],
        part=effective_part,
        theme=theme,
        cover=cover,
        outro=outro,
        items=items,
        hashtags=parsed.hashtags or (list(profile.hashtags) if profile and profile.hashtags else []),
    )
    deck = populate_cover_defaults(deck, source_kind="website")
    if use_ai:
        deck = maybe_enhance_with_ai(deck)

    paths = _render_with_ratios(
        deck=deck,
        output_dir=output_dir,
        ratios=effective_ratios,
        export_pdf=effective_pdf,
    )
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
    ratios: list[AspectRatio] | None = None,
    include_outro: bool | None = None,
    export_pdf: bool | None = None,
    cache_dir: Path | None = None,
    profile: CreatorProfile | None = None,
) -> tuple[DeckSpec, list[Path]]:
    """Load an existing `deck.yaml` (manual or hybrid), enrich missing screenshots, and render."""
    raw_deck = yaml.safe_load(deck_file.read_text(encoding="utf-8")) or {}
    deck = load_deck_yaml(deck_file)
    cache = cache_dir or (output_dir / ".cache")

    if "language" not in raw_deck and profile and profile.language:
        deck.language = profile.language

    raw_theme = raw_deck.get("theme") if isinstance(raw_deck.get("theme"), dict) else {}
    preset_target = (
        theme_name
        or (str(raw_theme["preset"]) if "preset" in raw_theme else None)
        or (profile.theme if profile and profile.theme else deck.theme.preset)
    )
    profile_theme_defaults: dict[str, Any] = {}
    if profile:
        if profile.accent_color and "accent_color" not in raw_theme:
            profile_theme_defaults["accent_color"] = profile.accent_color
        if profile.watermark and "watermark" not in raw_theme:
            profile_theme_defaults["watermark"] = profile.watermark
        if profile.watermark_position and "watermark_position" not in raw_theme:
            profile_theme_defaults["watermark_position"] = profile.watermark_position

    file_theme_overrides = deck.theme.model_dump(exclude_defaults=True)
    file_theme_overrides.pop("preset", None)
    if isinstance(file_theme_overrides.get("font_files"), dict):
        resolved_fonts: dict[str, str] = {}
        for fam, fpath in file_theme_overrides["font_files"].items():
            p = Path(str(fpath)).expanduser()
            if not p.is_absolute():
                p = (deck_file.parent / p).resolve()
            resolved_fonts[str(fam)] = str(p)
        file_theme_overrides["font_files"] = resolved_fonts

    deck.theme = load_theme(
        preset_target,
        overrides=_build_theme_overrides(
            accent_color=accent_color,
            watermark=watermark,
            watermark_position=watermark_position,
            extra={**profile_theme_defaults, **file_theme_overrides},
        ),
    )

    if cover_image:
        deck.cover.image_path = str(cover_image.resolve())
        deck.cover.mode = cover_mode or CoverMode.PHOTO
    elif cover_mode:
        deck.cover.mode = cover_mode
    elif not deck.cover.image_path and "cover" not in raw_deck and profile and profile.cover_image:
        deck.cover.image_path = profile.cover_image
        deck.cover.mode = profile.cover_mode or CoverMode.PHOTO

    if aspect_ratio:
        deck.aspect_ratio = aspect_ratio
    elif "aspect_ratio" not in raw_deck and profile and profile.aspect_ratio:
        deck.aspect_ratio = profile.aspect_ratio

    effective_ratios = ratios or (
        [aspect_ratio]
        if aspect_ratio is not None
        else (
            [deck.aspect_ratio]
            if "aspect_ratio" in raw_deck
            else (profile.ratios if profile and profile.ratios else [deck.aspect_ratio])
        )
    )
    deck.aspect_ratio = effective_ratios[0]

    deck.outro = _resolve_outro(
        include_outro=include_outro,
        file_outro=deck.outro,
        profile=profile,
        language=deck.language,
        handle=deck.theme.watermark,
        part=deck.part,
    )
    if not deck.hashtags and profile and profile.hashtags:
        deck.hashtags = list(profile.hashtags)

    effective_pdf = (
        export_pdf
        if export_pdf is not None
        else (bool(profile.export_pdf) if profile and profile.export_pdf is not None else False)
    )

    manual_source = ManualDeckSource(cache_dir=cache, language=deck.language)
    deck = manual_source.enrich_deck(deck, base_dir=deck_file.parent)
    source_kind = "website" if deck.items and deck.items[0].source == "website" else "github"
    deck = populate_cover_defaults(deck, source_kind=source_kind)

    paths = _render_with_ratios(
        deck=deck,
        output_dir=output_dir,
        ratios=effective_ratios,
        export_pdf=effective_pdf,
    )
    return deck, paths
