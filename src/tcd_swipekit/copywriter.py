"""Copywriting, cover defaults, caption generation, and optional AI enhancement."""

from __future__ import annotations

import os
import re

from tcd_swipekit.i18n import t
from tcd_swipekit.models import DeckSpec, Language


def clean_short_description(text: str, max_chars: int = 128) -> str:
    """Keep slide descriptions punchy (roughly 2 lines) without awkward mid-word cuts."""
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    # Try cutting at first sentence if reasonably long
    first_sentence = re.split(r"(?<=[.!?])\s+", cleaned)[0]
    if 38 <= len(first_sentence) <= max_chars:
        return first_sentence
    trimmed = cleaned[: max_chars - 1].rsplit(" ", 1)[0].rstrip(",;:-")
    return f"{trimmed}…"


def populate_cover_defaults(deck: DeckSpec, source_kind: str = "github") -> DeckSpec:
    """Fill missing CoverConfig fields based on topic, source type, and language."""
    lang = deck.language
    count = len(deck.items)
    cover = deck.cover

    if not cover.badge_text:
        badge_key = "web_badge" if source_kind == "website" else "gh_badge"
        cover.badge_text = t(lang, badge_key, part=deck.part)

    if not cover.title_lines:
        is_generic = deck.topic.lower() in {
            "",
            "trending",
            "trending open source tools",
            "useful websites worth bookmarking",
        }
        if not is_generic and len(deck.topic) <= 24:
            cover.title_lines = [
                t(lang, "topic_title_1", count=count),
                t(lang, "topic_title_2", topic=deck.topic),
                t(lang, "topic_title_3"),
            ]
        elif source_kind == "website":
            cover.title_lines = [
                t(lang, "web_title_1", count=count),
                t(lang, "web_title_2"),
                t(lang, "web_title_3"),
            ]
        else:
            cover.title_lines = [
                t(lang, "gh_title_1", count=count),
                t(lang, "gh_title_2"),
                t(lang, "gh_title_3"),
            ]

    if not cover.subtitle and deck.items:
        first = deck.items[0]
        short = clean_short_description(first.description, max_chars=72).rstrip(".")
        if short:
            short = short[0].lower() + short[1:]
        cover.subtitle = t(lang, "subtitle_prefix", title=first.title, desc=short) + "."

    if not cover.cta_text:
        cover.cta_text = t(lang, "cta_default")

    for item in deck.items:
        item.description = clean_short_description(item.description, max_chars=128)

    return deck


def build_caption_markdown(deck: DeckSpec) -> str:
    """Generate a ready-to-post social media caption and item link list."""
    lang = deck.language
    default_tags = (
        ["#github", "#opensource", "#devtools", "#softwareengineer", "#programming", "#tech"]
        if any(i.source == "github" for i in deck.items)
        else ["#websites", "#productivity", "#techtools", "#usefulwebsites", "#webtools"]
    )
    if lang == Language.ID:
        default_tags.append("#tipsdigital")
    hashtags = deck.hashtags or default_tags
    tag_line = " ".join(tag if tag.startswith("#") else f"#{tag}" for tag in hashtags)

    lines = [
        f"# {deck.topic}",
        "",
        "## Caption",
        "",
        t(lang, "caption_save"),
        "",
        t(lang, "caption_cta"),
        "",
        tag_line,
        "",
        "## Items & Links",
        "",
    ]
    for idx, item in enumerate(deck.items, start=1):
        link = item.url or item.command_or_url or ""
        label = f"{item.eyebrow} {item.title}".strip()
        lines.append(f"{idx:02d}. **{label}** — {item.description}")
        if link:
            lines.append(f"    - {link}")
    lines.append("")
    return "\n".join(lines)


def maybe_enhance_with_ai(deck: DeckSpec) -> DeckSpec:
    """Optionally polish descriptions & cover hook using an OpenAI-compatible API if configured.

    Activated only when explicitly requested via `--ai` and `OPENAI_API_KEY` is set.
    Gracefully returns the original deck if the optional SDK or API key is absent.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return deck
    try:
        from openai import OpenAI  # type: ignore[import-not-found]
    except ImportError:
        return deck

    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("SWIPEKIT_AI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key, base_url=base_url)
    lang_label = "Indonesian" if deck.language == Language.ID else "English"

    for item in deck.items:
        prompt = (
            f"Rewrite this tool description in {lang_label} as 1–2 punchy, jargon-free sentences "
            f"(maximum 115 characters total) for a TikTok/Instagram slide card. Return only the text.\n"
            f"Tool: {item.title}\nOriginal: {item.description}"
        )
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0.5,
            )
            rewritten = (resp.choices[0].message.content or "").strip().strip('"')
            if rewritten:
                item.description = clean_short_description(rewritten, max_chars=128)
        except Exception:
            continue

    return deck
