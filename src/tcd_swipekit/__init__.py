"""TCD-Swipekit: Modern photo-slide carousel generator for GitHub repos & websites."""

from tcd_swipekit.models import (
    AspectRatio,
    BadgeStyle,
    CodeBlock,
    CoverConfig,
    CoverMode,
    CreatorProfile,
    DeckSpec,
    Language,
    OutroAction,
    OutroConfig,
    SiteEntry,
    SitesFile,
    SlideBadge,
    SlideItem,
    SlideLayout,
    ThemeConfig,
    VersusBlock,
    VersusSide,
    WatermarkPosition,
)
from tcd_swipekit.pipeline import generate_github_deck, generate_website_deck, render_deck_file

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "AspectRatio",
    "BadgeStyle",
    "CodeBlock",
    "CoverConfig",
    "CoverMode",
    "CreatorProfile",
    "DeckSpec",
    "Language",
    "OutroAction",
    "OutroConfig",
    "SiteEntry",
    "SitesFile",
    "SlideBadge",
    "SlideItem",
    "SlideLayout",
    "ThemeConfig",
    "VersusBlock",
    "VersusSide",
    "WatermarkPosition",
    "generate_github_deck",
    "generate_website_deck",
    "render_deck_file",
]
