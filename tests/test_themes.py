"""Unit tests for theme presets, custom YAML loading, and HTML formatting."""

from pathlib import Path

import pytest

from tcd_swipekit.models import WatermarkPosition
from tcd_swipekit.renderer import format_inline_accent, format_inline_bold
from tcd_swipekit.themes.loader import list_presets, load_theme


def test_builtin_presets_load():
    presets = list_presets()
    assert {"midnight-emerald", "cyber-indigo", "neon-violet", "editorial-light"}.issubset(set(presets))
    for name in presets:
        cfg = load_theme(name)
        assert cfg.preset == name
        assert cfg.accent_color.startswith("#")


def test_theme_overrides_and_watermark():
    cfg = load_theme(
        "cyber-indigo",
        overrides={
            "accent_color": "#FF6B00",
            "watermark": "@trycatchdev",
            "watermark_position": WatermarkPosition.TOP_RIGHT,
        },
    )
    assert cfg.accent_color == "#FF6B00"
    assert cfg.watermark == "@trycatchdev"
    assert cfg.watermark_position == WatermarkPosition.TOP_RIGHT


def test_load_custom_theme_yaml(tmp_path: Path):
    custom = tmp_path / "brand.yaml"
    custom.write_text(
        "preset: custom-brand\naccent_color: '#10B981'\nwatermark: '@custom'\n",
        encoding="utf-8",
    )
    cfg = load_theme(custom)
    assert cfg.preset == "custom-brand"
    assert cfg.accent_color == "#10B981"
    assert cfg.watermark == "@custom"


def test_unknown_preset_raises():
    with pytest.raises(ValueError, match="Unknown theme preset"):
        load_theme("does-not-exist-theme")


def test_inline_html_formatters_escape_xss():
    assert format_inline_accent("*blowing up* <script>") == '<span class="accent">blowing up</span> &lt;script&gt;'
    assert format_inline_bold("Try **this** & more") == "Try <strong>this</strong> &amp; more"
