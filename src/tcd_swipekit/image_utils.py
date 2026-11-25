"""Image utilities: smart border cropping, ambient tint extraction, and data URIs."""

from __future__ import annotations

import base64
import hashlib
import mimetypes
from pathlib import Path

import httpx
from PIL import Image


def to_data_uri(path: Path) -> str:
    """Convert a local image file to a base64 data URI for deterministic HTML rendering."""
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def smart_crop_margins(
    image_path: Path,
    output_path: Path | None = None,
    white_threshold: int = 246,
    min_border_ratio: float = 0.025,
) -> Path:
    """Trim excessive near-white outer padding from app screenshots (e.g., macOS window shots).

    Only crops when all four outer edges are overwhelmingly near-white so real light UI
    screenshots that extend to the edge are preserved intact.
    """
    im = Image.open(image_path).convert("RGB")
    w, h = im.size
    if w < 100 or h < 100:
        return image_path

    px = im.load()
    if px is None:
        return image_path

    def _is_near_white(rgb: tuple[int, int, int]) -> bool:
        return rgb[0] >= white_threshold and rgb[1] >= white_threshold and rgb[2] >= white_threshold

    # Check if outer perimeter is mostly near-white padding
    sample_step = max(1, min(w, h) // 80)
    border_pixels = []
    for x in range(0, w, sample_step):
        border_pixels.append(px[x, 0])
        border_pixels.append(px[x, h - 1])
    for y in range(0, h, sample_step):
        border_pixels.append(px[0, y])
        border_pixels.append(px[w - 1, y])

    white_ratio = sum(1 for p in border_pixels if _is_near_white(p)) / max(1, len(border_pixels))
    if white_ratio < 0.92:
        return image_path

    # Find bounding box of non-white content (using a slightly lower threshold to skip faint shadows)
    shadow_threshold = 232
    left, top, right, bottom = w, h, 0, 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            if r < shadow_threshold or g < shadow_threshold or b < shadow_threshold:
                if x < left:
                    left = x
                if x > right:
                    right = x
                if y < top:
                    top = y
                if y > bottom:
                    bottom = y

    if right <= left or bottom <= top:
        return image_path

    pad_x = (left + (w - 1 - right)) / w
    pad_y = (top + (h - 1 - bottom)) / h
    if pad_x < min_border_ratio * 2 and pad_y < min_border_ratio * 2:
        return image_path

    # Keep a tiny 2px safety margin so window corners stay clean
    box = (max(0, left - 2), max(0, top - 2), min(w, right + 3), min(h, bottom + 3))
    cropped = im.crop(box)
    target = output_path or image_path.with_name(f"{image_path.stem}_cropped.png")
    cropped.save(target, format="PNG")
    return target


def extract_ambient_tint(image_path: Path, is_light_theme: bool = False) -> str:
    """Compute a subtle rgba tint harmonized with the screenshot's dominant color."""
    try:
        im = Image.open(image_path).convert("RGB").resize((32, 32))
        getter = getattr(im, "get_flattened_data", im.getdata)
        pixels = list(getter())
        r = sum(p[0] for p in pixels) // len(pixels)
        g = sum(p[1] for p in pixels) // len(pixels)
        b = sum(p[2] for p in pixels) // len(pixels)
        if is_light_theme:
            # Blend softly toward warm paper tone
            lr = int(244 * 0.88 + r * 0.12)
            lg = int(242 * 0.88 + g * 0.12)
            lb = int(238 * 0.88 + b * 0.12)
            return f"rgba({lr}, {lg}, {lb}, 0.86)"
        # Deepen color for dark ambient backdrop
        dr = int(r * 0.18)
        dg = int(g * 0.18)
        db = int(b * 0.22)
        return f"rgba({dr}, {dg}, {db}, 0.74)"
    except Exception:
        return "rgba(245, 244, 240, 0.88)" if is_light_theme else "rgba(14, 18, 28, 0.74)"


def download_image(url: str, cache_dir: Path, timeout: float = 20.0) -> Path | None:
    """Download an image URL into a local cache directory and validate it with Pillow."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    ext = Path(url.split("?")[0]).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        ext = ".png"
    target = cache_dir / f"img_{digest}{ext}"
    if target.exists() and target.stat().st_size > 1024:
        return target

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url, headers={"User-Agent": "TCD-Swipekit/0.1"})
            resp.raise_for_status()
            content = resp.content
        if len(content) < 2048:
            return None
        target.write_bytes(content)
        # Validate image dimensions and ensure it is not a tiny icon/badge
        with Image.open(target) as img:
            w, h = img.size
            if w < 320 or h < 180:
                target.unlink(missing_ok=True)
                return None
        return target
    except Exception:
        target.unlink(missing_ok=True)
        return None
