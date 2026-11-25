"""Unit tests for Pillow smart margin cropping and ambient tint extraction."""

from pathlib import Path

from PIL import Image, ImageDraw

from tcd_swipekit.image_utils import extract_ambient_tint, smart_crop_margins, to_data_uri


def test_smart_crop_trims_white_padding(tmp_path: Path):
    img = Image.new("RGB", (600, 400), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([60, 50, 539, 349], fill=(24, 24, 28))
    src = tmp_path / "padded.png"
    img.save(src)

    cropped_path = smart_crop_margins(src)
    assert cropped_path != src
    with Image.open(cropped_path) as out:
        w, h = out.size
        assert 475 <= w <= 490
        assert 295 <= h <= 310


def test_smart_crop_preserves_full_bleed_image(tmp_path: Path):
    img = Image.new("RGB", (500, 350), (30, 60, 120))
    src = tmp_path / "fullbleed.png"
    img.save(src)

    result = smart_crop_margins(src)
    assert result == src


def test_ambient_tint_and_data_uri(tmp_path: Path):
    img = Image.new("RGB", (120, 120), (40, 160, 220))
    src = tmp_path / "swatch.png"
    img.save(src)

    dark_tint = extract_ambient_tint(src, is_light_theme=False)
    light_tint = extract_ambient_tint(src, is_light_theme=True)
    assert dark_tint.startswith("rgba(")
    assert light_tint.startswith("rgba(")

    uri = to_data_uri(src)
    assert uri.startswith("data:image/png;base64,")
