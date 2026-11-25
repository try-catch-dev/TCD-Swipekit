"""Unit tests for Pydantic models, aspect ratios, defaults, and i18n copywriter."""

from tcd_swipekit.copywriter import (
    build_caption_markdown,
    clean_short_description,
    populate_cover_defaults,
)
from tcd_swipekit.models import (
    AspectRatio,
    BadgeStyle,
    CoverConfig,
    DeckSpec,
    Language,
    SitesFile,
    SlideBadge,
    SlideItem,
    ThemeConfig,
    WatermarkPosition,
)


def test_default_language_is_english():
    deck = DeckSpec()
    assert deck.language == Language.EN
    sites = SitesFile()
    assert sites.language == Language.EN


def test_aspect_ratio_dimensions():
    assert AspectRatio.PORTRAIT_3_4.dimensions == (1180, 1572)
    assert AspectRatio.IG_4_5.dimensions == (1080, 1350)
    assert AspectRatio.STORY_9_16.dimensions == (1080, 1920)
    assert AspectRatio.SQUARE_1_1.dimensions == (1080, 1080)


def test_theme_watermark_config():
    theme = ThemeConfig(watermark="@trycatchdev", watermark_position=WatermarkPosition.TOP_RIGHT)
    assert theme.watermark == "@trycatchdev"
    assert theme.watermark_position == WatermarkPosition.TOP_RIGHT


def test_cover_defaults_en_and_id():
    item = SlideItem(
        source="github",
        eyebrow="owner /",
        title="awesome-tool",
        description="A super fast open-source tool for modern software teams.",
        badges=[SlideBadge(text="★ 10,000", style=BadgeStyle.GLASS)],
    )
    en_deck = populate_cover_defaults(DeckSpec(language=Language.EN, items=[item.model_copy()]), "github")
    assert en_deck.cover.cta_text == "Swipe to see them →"
    assert "TRENDING THIS WEEK" in (en_deck.cover.badge_text or "")
    assert len(en_deck.cover.title_lines) == 3

    id_deck = populate_cover_defaults(
        DeckSpec(language=Language.ID, cover=CoverConfig(), items=[item.model_copy()]),
        "website",
    )
    assert id_deck.cover.cta_text == "Geser buat lihat →"
    assert "WEBSITE WAJIB TAU" in (id_deck.cover.badge_text or "")


def test_clean_short_description_and_caption():
    long_text = "First clear sentence that summarizes the tool well. " + "Extra filler text " * 20
    short = clean_short_description(long_text, max_chars=90)
    assert len(short) <= 90

    deck = DeckSpec(
        topic="Developer Tools",
        language=Language.EN,
        items=[SlideItem(source="github", eyebrow="org /", title="demo", description="Fast CLI.", url="https://github.com/org/demo")],
    )
    md = build_caption_markdown(deck)
    assert "# Developer Tools" in md
    assert "https://github.com/org/demo" in md
    assert "#github" in md
