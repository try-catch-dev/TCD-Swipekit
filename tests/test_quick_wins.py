"""Tests for dynamic fonts, safe-zone preview, PDF & multi-ratio export, code/versus layouts, and profiles."""

from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from tcd_swipekit.cli import app
from tcd_swipekit.copywriter import build_default_outro
from tcd_swipekit.models import (
    AspectRatio,
    CodeBlock,
    CoverConfig,
    CoverMode,
    CreatorProfile,
    DeckSpec,
    Language,
    OutroConfig,
    SlideItem,
    SlideLayout,
    ThemeConfig,
    VersusBlock,
    VersusSide,
)
from tcd_swipekit.pipeline import parse_ratios, render_deck_file
from tcd_swipekit.profile import find_profile_path, load_profile
from tcd_swipekit.renderer import (
    SlideRenderer,
    build_font_css,
    export_slides_to_pdf,
    highlight_code_lines,
)
from tcd_swipekit.themes.loader import load_theme

runner = CliRunner()


def test_dynamic_font_css_google_and_local_font_files(tmp_path: Path):
    fake_woff2 = tmp_path / "BrandDisplay.woff2"
    fake_woff2.write_bytes(b"wOF2fakefontbytes")

    theme = ThemeConfig(
        font_heading="BrandDisplay",
        font_body="Plus Jakarta Sans",
        font_mono="Fira Code",
        font_files={"BrandDisplay": str(fake_woff2)},
    )
    css = build_font_css(theme)

    assert "@font-face" in css
    assert "font-family: 'BrandDisplay';" in css
    assert "data:font/woff2;base64," in css
    assert "family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900" in css
    assert "family=Fira+Code:wght@400;500;600;700" in css
    # Locally embedded font should not be requested from Google Fonts
    assert "family=BrandDisplay" not in css


def test_dynamic_font_css_skips_system_fonts():
    theme = ThemeConfig(font_heading="system-ui", font_body="Arial", font_mono="monospace")
    assert build_font_css(theme) == ""


def test_load_theme_resolves_relative_font_files(tmp_path: Path):
    font_file = tmp_path / "custom.ttf"
    font_file.write_bytes(b"TTFDATA")
    theme_yaml = tmp_path / "brand.yaml"
    theme_yaml.write_text(
        "preset: brand\nfont_heading: CustomHead\nfont_files:\n  CustomHead: ./custom.ttf\n",
        encoding="utf-8",
    )
    loaded = load_theme(theme_yaml)
    assert loaded.font_files["CustomHead"] == str(font_file.resolve())


def test_parse_ratios():
    assert parse_ratios("3:4, 4:5, 1:1") == [
        AspectRatio.PORTRAIT_3_4,
        AspectRatio.IG_4_5,
        AspectRatio.SQUARE_1_1,
    ]
    assert parse_ratios("all") == list(AspectRatio)
    assert parse_ratios(None) is None

    try:
        parse_ratios("16:9")
    except ValueError as exc:
        assert "Unsupported aspect ratio" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported aspect ratio")


def test_slide_item_auto_infers_code_and_versus_layouts():
    code_item = SlideItem(
        title="Fast Lookup",
        code_block=CodeBlock(code="x = {u.id: u for u in users}", language="python"),
    )
    assert code_item.layout == SlideLayout.CODE

    versus_item = SlideItem(
        title="pip vs uv",
        versus=VersusBlock(
            left=VersusSide(label="pip", points=["Slower"]),
            right=VersusSide(label="uv", points=["10x faster"], accent=True),
        ),
    )
    assert versus_item.layout == SlideLayout.VERSUS


def test_highlight_code_lines_diff_and_highlight_and_xss_escape():
    block = CodeBlock(
        language="diff",
        diff_mode=True,
        code="- old = '<script>alert(1)</script>'\n+ new = 'safe'\n  keep = True",
    )
    lines = highlight_code_lines(block)
    assert len(lines) == 3
    assert lines[0]["css_class"] == "is-diff-del"
    assert "<script>" not in str(lines[0]["html"])
    assert "&lt;script&gt;" in str(lines[0]["html"])
    assert lines[1]["css_class"] == "is-diff-add"
    assert lines[2]["css_class"] == ""

    py_block = CodeBlock(
        language="python",
        highlight_lines=[2],
        code="def greet(name):\n    return f'hi {name}'",
    )
    py_lines = highlight_code_lines(py_block)
    assert py_lines[0]["css_class"] == ""
    assert py_lines[1]["css_class"] == "is-highlight"
    assert "tok-k" in str(py_lines[0]["html"])


def test_build_default_outro_en_and_id():
    en_outro = build_default_outro(Language.EN, handle="@devhandle", part=2)
    assert en_outro.enabled is True
    assert "PART 3" in (en_outro.badge_text or "")
    assert any("@devhandle" in act.label for act in en_outro.actions)

    no_handle = build_default_outro(Language.EN, handle=None, part=1)
    assert no_handle.handle is None
    assert all("@trycatchdev" not in act.label for act in no_handle.actions)

    id_outro = build_default_outro(Language.ID, handle="@yourhandle", part=1)
    assert "PART 2" in (id_outro.badge_text or "")
    assert "Save postingan ini" in id_outro.title_lines


def test_creator_profile_discovery_and_relative_paths(tmp_path: Path):
    cover_img = tmp_path / "me.png"
    Image.new("RGB", (200, 200), (10, 20, 30)).save(cover_img)

    profile_file = tmp_path / ".swipekit.yaml"
    profile_file.write_text(
        """
theme: amber-noir
watermark: "@brandcreator"
language: id
aspect_ratio: "4:5"
cover_image: ./me.png
export_pdf: true
outro:
  enabled: true
  badge_text: "CUSTOM OUTRO"
  title_lines: ["Save", "*now*"]
""",
        encoding="utf-8",
    )

    found = find_profile_path(cwd=tmp_path)
    assert found == profile_file.resolve()

    loaded, loaded_path = load_profile(cwd=tmp_path)
    assert loaded is not None
    assert loaded_path == profile_file.resolve()
    assert loaded.theme == "amber-noir"
    assert loaded.watermark == "@brandcreator"
    assert loaded.language == Language.ID
    assert loaded.cover_image == str(cover_img.resolve())
    assert loaded.export_pdf is True
    assert loaded.outro is not None and loaded.outro.badge_text == "CUSTOM OUTRO"


def test_export_slides_to_pdf(tmp_path: Path):
    p1 = tmp_path / "01.png"
    p2 = tmp_path / "02.png"
    Image.new("RGBA", (300, 400), (12, 16, 24, 255)).save(p1)
    Image.new("RGB", (300, 400), (24, 48, 32)).save(p2)

    pdf_out = export_slides_to_pdf([p1, p2], tmp_path / "carousel.pdf")
    assert pdf_out.is_file()
    header = pdf_out.read_bytes()[:5]
    assert header == b"%PDF-"


def test_render_code_versus_multi_ratio_pdf_and_safe_zone_preview(tmp_path: Path):
    deck = DeckSpec(
        topic="Code & Versus Showcase",
        language=Language.EN,
        theme=load_theme("editorial-light", overrides={"watermark": "@yourhandle"}),
        cover=CoverConfig(
            mode=CoverMode.GRADIENT,
            badge_icon="sparkles",
            badge_text="DEV TIPS · PART 1",
            title_lines=["Clean Code", "*& Fast Tools*"],
            cta_text="Swipe →",
        ),
        outro=build_default_outro(Language.EN, handle="@yourhandle", part=1),
        items=[
            SlideItem(
                layout=SlideLayout.CODE,
                eyebrow="python / refactor",
                title="Dict Lookup",
                description="O(1) dict lookup instead of nested loops.",
                code_block=CodeBlock(
                    filename="lookup.py",
                    language="diff",
                    diff_mode=True,
                    code="- for u in users:\n+ user = by_id.get(uid)",
                ),
            ),
            SlideItem(
                layout=SlideLayout.VERSUS,
                eyebrow="tooling / compare",
                title="pip vs uv",
                description="Modern Python package management.",
                versus=VersusBlock(
                    left=VersusSide(label="pip", badge="LEGACY", points=["Slower installs"]),
                    right=VersusSide(
                        label="uv",
                        badge="RECOMMENDED",
                        points=["10–100x faster installs"],
                        code="uv sync",
                        accent=True,
                    ),
                    verdict="Use uv for faster CI.",
                ),
            ),
        ],
    )

    out_dir = tmp_path / "batch_out"
    results = SlideRenderer().render_multi_ratio(
        deck,
        output_dir=out_dir,
        ratios=[AspectRatio.PORTRAIT_3_4, AspectRatio.SQUARE_1_1],
        export_pdf=True,
    )

    assert set(results.keys()) == {AspectRatio.PORTRAIT_3_4, AspectRatio.SQUARE_1_1}
    assert len(results[AspectRatio.PORTRAIT_3_4]) == 4
    assert len(results[AspectRatio.SQUARE_1_1]) == 4

    with Image.open(out_dir / "3x4" / "02_dict_lookup.png") as img_34:
        assert img_34.size == (1180, 1572)
    with Image.open(out_dir / "1x1" / "03_pip_vs_uv.png") as img_11:
        assert img_11.size == (1080, 1080)

    assert (out_dir / "3x4" / "carousel.pdf").read_bytes()[:5] == b"%PDF-"
    assert (out_dir / "1x1" / "carousel.pdf").read_bytes()[:5] == b"%PDF-"

    preview_html = (out_dir / "3x4" / "preview.html").read_text(encoding="utf-8")
    assert "Safe Zone:" in preview_html
    assert "TikTok" in preview_html
    assert "IG Reels" in preview_html
    assert "LinkedIn" in preview_html
    assert "carousel.pdf" in preview_html
    assert "1180×1572" in preview_html


def test_render_deck_file_applies_profile_precedence_and_cli_outro_flag(tmp_path: Path):
    deck_yaml = tmp_path / "minimal_deck.yaml"
    deck_yaml.write_text(
        """
topic: "Minimal Code Deck"
items:
  - title: "Quick Tip"
    code_block:
      language: python
      code: "print('hello')"
""",
        encoding="utf-8",
    )

    profile = CreatorProfile(
        theme="cyber-indigo",
        watermark="@profilehandle",
        language=Language.ID,
        outro=OutroConfig(enabled=True, badge_text="PROFILE OUTRO", title_lines=["Save"]),
        export_pdf=True,
    )

    out_dir = tmp_path / "out_with_profile"
    deck, paths = render_deck_file(
        deck_file=deck_yaml,
        output_dir=out_dir,
        profile=profile,
    )
    assert deck.theme.preset == "cyber-indigo"
    assert deck.theme.watermark == "@profilehandle"
    assert deck.language == Language.ID
    assert deck.outro is not None and deck.outro.badge_text == "PROFILE OUTRO"
    assert len(paths) == 3  # cover + 1 item + profile outro
    assert (out_dir / "carousel.pdf").is_file()

    # Explicitly disabling outro via include_outro=False overrides profile outro
    out_no_outro = tmp_path / "out_no_outro"
    deck2, paths2 = render_deck_file(
        deck_file=deck_yaml,
        output_dir=out_no_outro,
        include_outro=False,
        export_pdf=False,
        profile=profile,
    )
    assert deck2.outro is None
    assert len(paths2) == 2
    assert not (out_no_outro / "carousel.pdf").exists()


def test_cli_init_profile_and_show_profile(tmp_path: Path):
    profile_dest = tmp_path / ".swipekit.yaml"
    res_init = runner.invoke(app, ["init", "profile", "--output", str(profile_dest)])
    assert res_init.exit_code == 0
    assert profile_dest.is_file()

    res_show = runner.invoke(app, ["profile", "--profile", str(profile_dest)])
    assert res_show.exit_code == 0
    assert "midnight-emerald" in res_show.stdout
    assert "@yourhandle" in res_show.stdout


def test_cli_doctor():
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "Chromium" in res.stdout
    assert "Built-in Themes" in res.stdout
