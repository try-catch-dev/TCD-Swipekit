"""Localization strings for TCD-Swipekit (English default, Indonesian supported)."""

from __future__ import annotations

from tcd_swipekit.models import Language

STRINGS: dict[Language, dict[str, str]] = {
    Language.EN: {
        "cta_default": "Swipe to see them →",
        "gh_badge": "TRENDING THIS WEEK · PART {part}",
        "web_badge": "USEFUL WEBSITES · PART {part}",
        "gh_title_1": "{count} GitHub repos",
        "gh_title_2": "*blowing up*",
        "gh_title_3": "right now.",
        "web_title_1": "{count} Websites",
        "web_title_2": "*worth saving*",
        "web_title_3": "right now.",
        "topic_title_1": "{count} Tools for",
        "topic_title_2": "*{topic}*",
        "topic_title_3": "you should try.",
        "subtitle_prefix": "#1 is **{title}** — {desc}",
        "gain_daily": "+{n} today",
        "gain_weekly": "+{n} this week",
        "gain_monthly": "+{n} this month",
        "caption_save": "Save this before your next build, and follow for more ⬇️",
        "caption_cta": "Which one are you trying first? Drop a number below 👇",
        "default_web_badge": "Free",
        "default_web_type": "Web App",
    },
    Language.ID: {
        "cta_default": "Geser buat lihat →",
        "gh_badge": "TRENDING MINGGU INI · PART {part}",
        "web_badge": "WEBSITE WAJIB TAU · PART {part}",
        "gh_title_1": "{count} Tools GitHub",
        "gh_title_2": "*yang lagi viral*",
        "gh_title_3": "minggu ini.",
        "web_title_1": "{count} Website Keren",
        "web_title_2": "*yang wajib kamu*",
        "web_title_3": "bookmark sekarang.",
        "topic_title_1": "{count} Tools buat",
        "topic_title_2": "*{topic}*",
        "topic_title_3": "wajib kamu coba.",
        "subtitle_prefix": "#1 ada **{title}** — {desc}",
        "gain_daily": "+{n} hari ini",
        "gain_weekly": "+{n} minggu ini",
        "gain_monthly": "+{n} bulan ini",
        "caption_save": "Save dulu sebelum hilang, dan follow buat part selanjutnya ⬇️",
        "caption_cta": "Paling penasaran coba yang nomor berapa? Tulis di komen 👇",
        "default_web_badge": "Gratis",
        "default_web_type": "Web App",
    },
}


def t(lang: Language, key: str, **kwargs: object) -> str:
    """Lookup localized string with optional format arguments."""
    template = STRINGS.get(lang, STRINGS[Language.EN])[key]
    return template.format(**kwargs) if kwargs else template
