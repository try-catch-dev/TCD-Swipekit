"""Integration smoke test for Playwright + Jinja2 SlideRenderer."""

from pathlib import Path

from PIL import Image

from tcd_swipekit.models import (
    AspectRatio,
    BadgeStyle,
    CoverConfig,
    CoverMode,
    DeckSpec,
    Language,
    SlideBadge,
    SlideItem,
    WatermarkPosition,
)
from tcd_swipekit.renderer import SlideRenderer
from tcd_swipekit.themes.loader import load_theme


def test_render_deck_creates_valid_pngs_and_extras(tmp_path: Path):
    # Create synthetic local screenshot so test runs offline
    shot = tmp_path / "sample_ui.png"
    Image.new("RGB", (900, 560), (24, 38, 64)).save(shot)

    theme = load_theme(
        "cyber-indigo",
        overrides={
            "watermark": "@trycatchdev",
            "watermark_position": WatermarkPosition.BOTTOM_RIGHT,
        },
    )
    deck = DeckSpec(
        topic="Useful Dev Tools",
        language=Language.EN,
        aspect_ratio=AspectRatio.PORTRAIT_3_4,
        theme=theme,
        cover=CoverConfig(
            mode=CoverMode.GRADIENT,
            badge_icon="globe",
            badge_text="USEFUL WEBSITES · PART 1",
            title_lines=["2 Websites", "*worth saving*", "right now."],
            subtitle="#1 is **Sample Tool** — fast visual builder.",
            cta_text="Swipe to see them →",
        ),
        items=[
            SlideItem(
                source="website",
                eyebrow="example.dev",
                title="Sample Tool",
                description="Fast visual tool right inside your browser.",
                screenshot_path=str(shot),
                url="https://example.dev",
                badges=[
                    SlideBadge(text="Free", style=BadgeStyle.ACCENT),
                    SlideBadge(text="Web App", style=BadgeStyle.GLASS),
                ],
                command_or_url="https://example.dev",
                footnote="OPEN SOURCE · NO LOGIN",
                footnote_accent=True,
            )
        ],
    )

    out_dir = tmp_path / "rendered"
    paths = SlideRenderer().render_deck(deck, output_dir=out_dir)

    assert len(paths) == 2
    assert (out_dir / "01_cover.png").is_file()
    assert (out_dir / "caption.md").is_file()
    assert (out_dir / "deck.yaml").is_file()
    assert (out_dir / "preview.html").is_file()

    for png in paths:
        with Image.open(png) as img:
            assert img.size == (1180, 1572)
