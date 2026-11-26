"""Pydantic v2 data models for TCD-Swipekit decks, covers, themes, and sources."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Language(str, Enum):
    """Supported content languages (English default, Indonesian supported)."""

    EN = "en"
    ID = "id"


class AspectRatio(str, Enum):
    """Supported social media slide aspect ratios."""

    PORTRAIT_3_4 = "3:4"  # 1180x1572 (TikTok Photo Mode default)
    IG_4_5 = "4:5"        # 1080x1350 (Instagram Carousel)
    STORY_9_16 = "9:16"   # 1080x1920 (Stories / Reels / Shorts)
    SQUARE_1_1 = "1:1"    # 1080x1080 (LinkedIn / X / Square)

    @property
    def dimensions(self) -> tuple[int, int]:
        mapping = {
            AspectRatio.PORTRAIT_3_4: (1180, 1572),
            AspectRatio.IG_4_5: (1080, 1350),
            AspectRatio.STORY_9_16: (1080, 1920),
            AspectRatio.SQUARE_1_1: (1080, 1080),
        }
        return mapping[self]

    @property
    def folder_slug(self) -> str:
        """Filesystem-safe folder name for multi-ratio batch exports (e.g., '3x4')."""
        return self.value.replace(":", "x")


class CoverMode(str, Enum):
    """Visual layout mode for Slide 1 cover."""

    PHOTO = "photo"
    GRADIENT = "gradient"
    MINIMAL = "minimal"


class BadgeStyle(str, Enum):
    """Visual style for slide metadata pills."""

    GLASS = "glass"
    ACCENT = "accent"


class WatermarkPosition(str, Enum):
    """Placement of optional creator watermark handle."""

    BOTTOM_RIGHT = "bottom-right"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"


class SlideLayout(str, Enum):
    """Visual layout variant for content slides."""

    SHOWCASE = "showcase"  # Hero screenshot / repo / website card (default)
    CODE = "code"          # Syntax-highlighted code snippet or terminal diff card
    VERSUS = "versus"      # Side-by-side or stacked A-vs-B comparison card


class SlideBadge(BaseModel):
    """Metadata pill shown beneath the hero screenshot."""

    text: str
    style: BadgeStyle = BadgeStyle.GLASS


class CodeBlock(BaseModel):
    """Configuration for a syntax-highlighted code or diff slide (`layout: code`)."""

    code: str
    language: str = "python"
    filename: str | None = None
    highlight_lines: list[int] = Field(default_factory=list)
    show_line_numbers: bool = True
    diff_mode: bool = False


class VersusSide(BaseModel):
    """One side (Left/Top or Right/Bottom) of a comparison slide (`layout: versus`)."""

    label: str
    badge: str | None = None
    headline: str | None = None
    points: list[str] = Field(default_factory=list)
    code: str | None = None
    accent: bool = False


class VersusBlock(BaseModel):
    """Structured A-vs-B comparison block (`layout: versus`)."""

    left: VersusSide
    right: VersusSide
    verdict: str | None = None


class CoverConfig(BaseModel):
    """Customizable configuration for the Slide 1 cover hook."""

    mode: CoverMode = CoverMode.GRADIENT
    image_path: str | None = None
    badge_icon: Literal["github", "globe", "sparkles", "none"] = "github"
    badge_text: str | None = None
    title_lines: list[str] = Field(default_factory=list)
    subtitle: str | None = None
    cta_text: str | None = None
    gradient_from: str | None = None
    gradient_to: str | None = None


class ThemeConfig(BaseModel):
    """Visual theme tokens supporting built-in presets and custom overrides."""

    preset: str = "midnight-emerald"
    is_light: bool = False
    bg_color: str = "#0B0C0F"
    cover_bg_color: str = "#000000"
    text_color: str = "#FFFFFF"
    muted_color: str = "rgba(255, 255, 255, 0.72)"
    subtle_color: str = "rgba(255, 255, 255, 0.52)"
    divider_color: str = "rgba(255, 255, 255, 0.16)"
    accent_color: str = "#48DF76"
    accent_text_color: str = "#09130C"
    pill_accent_bg: str = "#2EB84B"
    pill_accent_text: str = "#FFFFFF"
    pill_glass_bg: str = "rgba(255, 255, 255, 0.08)"
    pill_glass_border: str = "rgba(255, 255, 255, 0.16)"
    cli_bg: str = "rgba(8, 9, 12, 0.88)"
    cli_border: str = "rgba(255, 255, 255, 0.12)"
    cli_text: str = "#E4E4E7"
    font_heading: str = "Inter"
    font_body: str = "Inter"
    font_mono: str = "JetBrains Mono"
    font_files: dict[str, str] = Field(default_factory=dict)
    ambient_blur: bool = True
    ambient_brightness: float = 0.34
    ambient_saturation: float = 1.45
    card_radius: int = 24
    watermark: str | None = None
    watermark_position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT


class SlideItem(BaseModel):
    """Unified schema for a single content slide (GitHub, Website, Code, Versus, or Manual)."""

    source: Literal["github", "website", "manual"] = "manual"
    layout: SlideLayout = SlideLayout.SHOWCASE
    eyebrow: str = ""
    title: str
    description: str = ""
    screenshot_path: str | None = None
    screenshot_url: str | None = None
    url: str | None = None
    badges: list[SlideBadge] = Field(default_factory=list)
    command_or_url: str | None = None
    footnote: str | None = None
    footnote_accent: bool = False
    image_fit: Literal["contain", "cover"] = "contain"
    ambient_tint: str | None = None
    repo: str | None = None
    code_block: CodeBlock | None = None
    versus: VersusBlock | None = None

    @model_validator(mode="after")
    def _infer_layout_from_content(self) -> SlideItem:
        if self.layout == SlideLayout.SHOWCASE:
            if self.code_block is not None:
                self.layout = SlideLayout.CODE
            elif self.versus is not None:
                self.layout = SlideLayout.VERSUS
        return self


class OutroAction(BaseModel):
    """Single call-to-action row on the closing slide (e.g., Save, Follow, Comment)."""

    icon: Literal["bookmark", "follow", "comment", "share"] = "bookmark"
    label: str
    sublabel: str = ""
    accent: bool = False


class OutroConfig(BaseModel):
    """Optional closing CTA slide configuration."""

    enabled: bool = True
    badge_text: str | None = None
    title_lines: list[str] = Field(default_factory=list)
    subtitle: str | None = None
    actions: list[OutroAction] = Field(default_factory=list)
    handle: str | None = None
    footer_note: str | None = None


class CreatorProfile(BaseModel):
    """Reusable creator brand defaults loaded from `.swipekit.yaml` or `~/.config/swipekit/config.yaml`."""

    theme: str | None = None
    accent_color: str | None = None
    watermark: str | None = None
    watermark_position: WatermarkPosition | None = None
    language: Language | None = None
    aspect_ratio: AspectRatio | None = None
    ratios: list[AspectRatio] | None = None
    cover_mode: CoverMode | None = None
    cover_image: str | None = None
    outro: OutroConfig | None = None
    export_pdf: bool | None = None
    hashtags: list[str] | None = None


class DeckSpec(BaseModel):
    """Complete serializable specification for a photo-slide carousel."""

    topic: str = "Trending Open Source Tools"
    language: Language = Language.EN
    aspect_ratio: AspectRatio = AspectRatio.PORTRAIT_3_4
    part: int = 1
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    cover: CoverConfig = Field(default_factory=CoverConfig)
    outro: OutroConfig | None = None
    items: list[SlideItem] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)


class SiteEntry(BaseModel):
    """Single website item inside a `sites.yml` configuration file."""

    url: str
    title: str | None = None
    eyebrow: str | None = None
    description: str | None = None
    category: str | None = None
    pricing: str | None = None
    badges: list[SlideBadge] = Field(default_factory=list)
    command_or_url: str | None = None
    footnote: str | None = None
    footnote_accent: bool = False
    screenshot_path: str | None = None
    dark_mode: bool = False
    wait_ms: int = 1200


class SitesFile(BaseModel):
    """Top-level schema for `sites.yml` used by `swipekit generate web`."""

    topic: str = "Useful Websites Worth Bookmarking"
    language: Language = Language.EN
    aspect_ratio: AspectRatio = AspectRatio.PORTRAIT_3_4
    part: int = 1
    theme: dict[str, object] = Field(default_factory=dict)
    cover: CoverConfig = Field(default_factory=lambda: CoverConfig(badge_icon="globe"))
    outro: OutroConfig | None = None
    hashtags: list[str] = Field(default_factory=list)
    sites: list[SiteEntry] = Field(default_factory=list)
