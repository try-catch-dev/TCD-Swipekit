"""TCD-Swipekit: Modern photo-slide carousel generator for GitHub repos & websites."""

from tcd_swipekit.models import (
    AspectRatio,
    BadgeStyle,
    CoverConfig,
    CoverMode,
    DeckSpec,
    Language,
    SiteEntry,
    SitesFile,
    SlideBadge,
    SlideItem,
    ThemeConfig,
    WatermarkPosition,
)
from tcd_swipekit.pipeline import generate_github_deck, generate_website_deck, render_deck_file

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "AspectRatio",
    "BadgeStyle",
    "CoverConfig",
    "CoverMode",
    "DeckSpec",
    "Language",
    "SiteEntry",
    "SitesFile",
    "SlideBadge",
    "SlideItem",
    "ThemeConfig",
    "WatermarkPosition",
    "generate_github_deck",
    "generate_website_deck",
    "render_deck_file",
]
