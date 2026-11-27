"""Markdown-to-Carousel content source: turns `.md` articles, tutorials, and docs into slide decks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import httpx
import yaml

from tcd_swipekit.copywriter import clean_short_description
from tcd_swipekit.image_utils import download_image, smart_crop_margins
from tcd_swipekit.models import (
    AspectRatio,
    BadgeStyle,
    ChecklistBlock,
    ChecklistEntry,
    CodeBlock,
    CoverConfig,
    CoverMode,
    DeckSpec,
    FrameStyle,
    Language,
    SlideBadge,
    SlideItem,
    SlideLayout,
    VersusBlock,
    VersusSide,
)
from tcd_swipekit.sources.base import BaseSource

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_CODE_FENCE_RE = re.compile(
    r"```([a-zA-Z0-9_+-]*)(?:[:\s]+([^\n`]+))?\n(.*?)```",
    re.DOTALL,
)
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _parse_frontmatter(raw_md: str) -> tuple[dict[str, Any], str]:
    """Extract optional YAML frontmatter and return (metadata_dict, markdown_body)."""
    match = _FRONTMATTER_RE.match(raw_md)
    if not match:
        return {}, raw_md
    try:
        meta = yaml.safe_load(match.group(1)) or {}
        if not isinstance(meta, dict):
            meta = {}
    except Exception:
        meta = {}
    return meta, raw_md[match.end() :]


def _strip_md_inline(text: str) -> str:
    """Clean inline Markdown markers (`**bold**`, `` `code` ``, `[link](url)`) into plain text."""
    out = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    out = re.sub(r"\*\*([^*]+)\*\*", r"\1", out)
    out = re.sub(r"\*([^*]+)\*", r"\1", out)
    out = re.sub(r"`([^`]+)`", r"\1", out)
    return re.sub(r"\s+", " ", out).strip()


def _split_heading_eyebrow(raw_heading: str) -> tuple[str, str]:
    """Extract optional eyebrow and clean title from a section heading.

    Supports:
    - `## 1. Python / Avoid N+1 Loops` -> eyebrow='Python /', title='Avoid N+1 Loops'
    - `## [Security] Validate Inputs`   -> eyebrow='security', title='Validate Inputs'
    - `## Step 1: Lock Dependencies`    -> eyebrow='Step 1', title='Lock Dependencies'
    """
    cleaned = re.sub(r"^\d+[\.\)\-:]\s*", "", raw_heading.strip()).strip()
    bracket_match = re.match(r"^\[([^\]]+)\]\s*(.+)$", cleaned)
    if bracket_match:
        return bracket_match.group(1).strip(), _strip_md_inline(bracket_match.group(2))
    if " / " in cleaned:
        left, right = cleaned.split(" / ", 1)
        if len(left) <= 28 and right.strip():
            return f"{left.strip()} /", _strip_md_inline(right)
    if ": " in cleaned:
        left, right = cleaned.split(": ", 1)
        if len(left) <= 18 and right.strip():
            return left.strip(), _strip_md_inline(right)
    return "", _strip_md_inline(cleaned)


def _split_title_lines(title: str) -> list[str]:
    """Split a long H1 title into 2–3 balanced cover headline lines with an accented middle line."""
    accent_parts = [p.strip() for p in re.split(r"(\*[^*]+\*)", title.strip()) if p.strip()]
    if len(accent_parts) >= 2 and any(p.startswith("*") and p.endswith("*") for p in accent_parts):
        return accent_parts[:3]

    cleaned = _strip_md_inline(title)
    words = cleaned.split()
    if len(words) <= 3:
        return [cleaned]
    if len(words) <= 6:
        mid = len(words) // 2
        first = " ".join(words[:mid])
        second = f"*{' '.join(words[mid:])}*"
        return [first, second]
    third = max(2, len(words) // 3)
    line1 = " ".join(words[:third])
    line2 = f"*{' '.join(words[third : third * 2])}*"
    line3 = " ".join(words[third * 2 :])
    return [line1, line2, line3]


def _extract_code_filename(info_tail: str | None, lang: str) -> str | None:
    if not info_tail:
        return None
    tail = info_tail.strip()
    m = re.search(r'(?:title|file|filename)=["\']?([^"\'\s]+)["\']?', tail)
    if m:
        return m.group(1)
    if "." in tail or "/" in tail:
        return tail.strip("\"'")
    return None


def _parse_subsection_side(heading: str, body: str, is_second: bool) -> VersusSide:
    """Parse a `### H3` subsection into a `VersusSide` model."""
    raw_head = heading.strip()
    accent = is_second
    badge: str | None = None

    lower_head = raw_head.lower()
    if any(tok in lower_head for tok in ("✅", "after", "modern", "recommended", "good", "do", "fast")):
        accent = True
    elif any(tok in lower_head for tok in ("❌", "before", "legacy", "avoid", "bad", "don't", "slow")):
        accent = False

    clean_head = re.sub(r"^[✅❌⚡🐢]\s*", "", raw_head).strip()
    if ":" in clean_head:
        prefix, rest = clean_head.split(":", 1)
        if len(prefix.strip()) <= 16 and rest.strip():
            badge = prefix.strip().upper()
            clean_head = rest.strip()

    if not badge:
        badge = "RECOMMENDED" if accent else "LEGACY"

    code_snippet: str | None = None
    code_match = _CODE_FENCE_RE.search(body)
    if code_match:
        code_snippet = code_match.group(3).strip()
        body = body[: code_match.start()] + body[code_match.end() :]

    points: list[str] = []
    headline_lines: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(">"):
            continue
        bullet_m = re.match(r"^(?:[-*+]|\d+\.)\s+(?:\[[ xX]\]\s+)?(.+)$", line)
        if bullet_m:
            points.append(_strip_md_inline(bullet_m.group(1)))
        elif not points and not headline_lines:
            headline_lines.append(_strip_md_inline(line))

    return VersusSide(
        label=_strip_md_inline(clean_head),
        badge=badge,
        headline=headline_lines[0] if headline_lines else None,
        points=points[:4],
        code=code_snippet,
        accent=accent,
    )


def _parse_section_into_slide(
    heading: str,
    body: str,
    *,
    base_dir: Path | None,
    cache_dir: Path,
) -> SlideItem:
    """Convert a single Markdown `## H2` section into the most fitting SlideItem layout."""
    eyebrow, title = _split_heading_eyebrow(heading)

    # Extract trailing blockquotes (`> ...`) for verdict/summary/footnote
    quotes: list[str] = []
    non_quote_lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            q_text = _strip_md_inline(stripped.lstrip(">").strip())
            if q_text:
                quotes.append(q_text)
        else:
            non_quote_lines.append(line)
    cleaned_body = "\n".join(non_quote_lines).strip()
    quote_summary = " ".join(quotes).strip() if quotes else None

    # Extract optional inline badge line: `Badges: Fast | Python 3.11+`
    badges: list[SlideBadge] = []
    body_without_badges: list[str] = []
    for line in cleaned_body.splitlines():
        bm = re.match(r"^\s*(?:\*\*?)?(?:badges?|tags?)(?:\*\*?)?:\s*(.+)$", line, flags=re.IGNORECASE)
        if bm:
            raw_tokens = [
                _strip_md_inline(tok)
                for tok in re.split(r"[|,·]", bm.group(1))
                if _strip_md_inline(tok)
            ]
            for idx, tok in enumerate(raw_tokens[:3]):
                badges.append(
                    SlideBadge(
                        text=tok,
                        style=BadgeStyle.ACCENT if idx == 0 else BadgeStyle.GLASS,
                    )
                )
        else:
            body_without_badges.append(line)
    cleaned_body = "\n".join(body_without_badges).strip()

    # 1. Check for `### H3` subsections -> `layout: versus` when 2 subsections exist
    h3_matches = list(re.finditer(r"^###\s+(.+)$", cleaned_body, flags=re.MULTILINE))
    if len(h3_matches) == 2:
        intro_text = cleaned_body[: h3_matches[0].start()].strip()
        desc = clean_short_description(_strip_md_inline(intro_text), max_chars=128) if intro_text else ""
        sub1_head = h3_matches[0].group(1)
        sub1_body = cleaned_body[h3_matches[0].end() : h3_matches[1].start()]
        sub2_head = h3_matches[1].group(1)
        sub2_body = cleaned_body[h3_matches[1].end() :]

        left_side = _parse_subsection_side(sub1_head, sub1_body, is_second=False)
        right_side = _parse_subsection_side(sub2_head, sub2_body, is_second=True)
        return SlideItem(
            source="markdown",
            layout=SlideLayout.VERSUS,
            eyebrow=eyebrow,
            title=title,
            description=desc,
            badges=badges,
            versus=VersusBlock(
                left=left_side,
                right=right_side,
                verdict=quote_summary,
            ),
        )

    # 2. Check for fenced code block -> `layout: code`
    code_match = _CODE_FENCE_RE.search(cleaned_body)
    if code_match:
        lang = (code_match.group(1) or "text").strip().lower()
        filename = _extract_code_filename(code_match.group(2), lang)
        code_content = code_match.group(3).strip("\n")
        prose_before = cleaned_body[: code_match.start()].strip()
        prose_after = cleaned_body[code_match.end() :].strip()
        raw_desc = prose_before or prose_after
        first_para = raw_desc.split("\n\n")[0] if raw_desc else ""
        desc = clean_short_description(_strip_md_inline(first_para), max_chars=128)

        code_lines = [ln for ln in code_content.splitlines() if ln.strip()]
        is_diff = lang == "diff" or (
            any(ln.startswith("+ ") or ln.startswith("- ") for ln in code_lines)
            and any(ln.startswith("+") for ln in code_lines)
            and any(ln.startswith("-") for ln in code_lines)
        )
        return SlideItem(
            source="markdown",
            layout=SlideLayout.CODE,
            eyebrow=eyebrow,
            title=title,
            description=desc,
            badges=badges,
            footnote=quote_summary,
            footnote_accent=bool(quote_summary),
            code_block=CodeBlock(
                code=code_content,
                language="diff" if is_diff and lang == "text" else lang,
                filename=filename,
                diff_mode=is_diff,
            ),
        )

    # 3. Check for bullet list / task list / numbered list -> `layout: checklist`
    bullet_entries: list[ChecklistEntry] = []
    prose_lines: list[str] = []
    is_numbered_list = False
    for raw_line in cleaned_body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        task_m = re.match(r"^[-*+]\s+\[([ xX])\]\s+(.+)$", line)
        num_m = re.match(r"^(\d+)[\.\)]\s+(.+)$", line)
        bul_m = re.match(r"^[-*+]\s+(.+)$", line)
        if task_m:
            checked = task_m.group(1).lower() == "x"
            entry = ChecklistEntry.model_validate(_strip_md_inline(task_m.group(2)))
            entry.checked = checked
            entry.accent = checked
            bullet_entries.append(entry)
        elif num_m:
            is_numbered_list = True
            entry = ChecklistEntry.model_validate(_strip_md_inline(num_m.group(2)))
            bullet_entries.append(entry)
        elif bul_m:
            entry = ChecklistEntry.model_validate(_strip_md_inline(bul_m.group(1)))
            bullet_entries.append(entry)
        elif not bullet_entries:
            prose_lines.append(_strip_md_inline(line))

    if len(bullet_entries) >= 2:
        # Highlight first or explicitly marked item if none accented yet
        if not any(e.accent for e in bullet_entries):
            bullet_entries[0].accent = True
        desc = clean_short_description(" ".join(prose_lines), max_chars=128) if prose_lines else ""
        return SlideItem(
            source="markdown",
            layout=SlideLayout.CHECKLIST,
            eyebrow=eyebrow,
            title=title,
            description=desc,
            badges=badges,
            checklist=ChecklistBlock(
                items=bullet_entries[:5],
                numbered=is_numbered_list,
                summary=quote_summary,
            ),
        )

    # 4. Fallback: `layout: showcase` (with optional image)
    screenshot_path: str | None = None
    img_match = _IMAGE_RE.search(cleaned_body)
    if img_match:
        img_target = img_match.group(2).strip()
        cleaned_body = (cleaned_body[: img_match.start()] + cleaned_body[img_match.end() :]).strip()
        if img_target.startswith(("http://", "https://")):
            dl = download_image(img_target, cache_dir)
            if dl:
                screenshot_path = str(smart_crop_margins(dl))
        else:
            candidate = Path(img_target)
            if not candidate.is_absolute() and base_dir:
                candidate = (base_dir / candidate).resolve()
            if candidate.is_file():
                screenshot_path = str(candidate)

    paragraphs = [
        _strip_md_inline(p)
        for p in re.split(r"\n\s*\n", cleaned_body)
        if _strip_md_inline(p)
    ]
    desc = clean_short_description(paragraphs[0] if paragraphs else "", max_chars=128)

    return SlideItem(
        source="markdown",
        layout=SlideLayout.SHOWCASE,
        frame=FrameStyle.BROWSER if screenshot_path else FrameStyle.NONE,
        eyebrow=eyebrow,
        title=title,
        description=desc,
        screenshot_path=screenshot_path,
        badges=badges,
        footnote=quote_summary,
        footnote_accent=bool(quote_summary),
    )


def parse_markdown_to_deck(
    raw_md: str,
    *,
    base_dir: Path | None = None,
    cache_dir: Path | None = None,
    limit: int = 10,
    default_language: Language = Language.EN,
) -> DeckSpec:
    """Parse a Markdown document (with optional frontmatter) into a structured DeckSpec."""
    effective_cache = cache_dir or Path("./.cache")
    effective_cache.mkdir(parents=True, exist_ok=True)
    meta, body = _parse_frontmatter(raw_md)

    lang_raw = str(meta.get("language", default_language.value)).lower()
    language = Language.ID if lang_raw == "id" else Language.EN
    ratio_raw = str(meta.get("aspect_ratio", AspectRatio.PORTRAIT_3_4.value))
    aspect_ratio = next((r for r in AspectRatio if r.value == ratio_raw), AspectRatio.PORTRAIT_3_4)

    # Extract optional H1 title and intro subtitle before the first H2
    h1_title: str | None = None
    intro_subtitle: str | None = None

    h2_splits = list(re.finditer(r"^##\s+(.+)$", body, flags=re.MULTILINE))
    preamble = body[: h2_splits[0].start()].strip() if h2_splits else body.strip()

    h1_match = re.search(r"^#\s+(.+)$", preamble, flags=re.MULTILINE)
    if h1_match:
        h1_title = h1_match.group(1).strip()
        after_h1 = preamble[h1_match.end() :].strip()
        intro_paras = [
            _strip_md_inline(p)
            for p in re.split(r"\n\s*\n", after_h1)
            if _strip_md_inline(p) and not p.strip().startswith("---")
        ]
        if intro_paras:
            intro_subtitle = clean_short_description(intro_paras[0], max_chars=96)

    topic = str(meta.get("topic") or _strip_md_inline(h1_title or "") or "Developer Guide")
    title_lines = meta.get("title_lines")
    if not isinstance(title_lines, list) or not title_lines:
        title_lines = _split_title_lines(str(meta.get("title") or h1_title or topic))

    cover = CoverConfig(
        mode=CoverMode.GRADIENT,
        badge_icon="sparkles",
        badge_text=str(meta["badge_text"]) if "badge_text" in meta else None,
        title_lines=[str(line) for line in title_lines],
        subtitle=str(meta.get("subtitle") or intro_subtitle)
        if (meta.get("subtitle") or intro_subtitle)
        else None,
        cta_text=str(meta["cta_text"]) if "cta_text" in meta else None,
    )

    items: list[SlideItem] = []
    if h2_splits:
        for idx, match in enumerate(h2_splits[:limit]):
            sec_heading = match.group(1).strip()
            sec_start = match.end()
            sec_end = h2_splits[idx + 1].start() if idx + 1 < len(h2_splits) else len(body)
            sec_body = body[sec_start:sec_end].strip()
            items.append(
                _parse_section_into_slide(
                    sec_heading,
                    sec_body,
                    base_dir=base_dir,
                    cache_dir=effective_cache,
                )
            )
    else:
        # Fallback: split by `---` horizontal rules
        chunks = [c.strip() for c in re.split(r"^---+\s*$", body, flags=re.MULTILINE) if c.strip()]
        for idx, chunk in enumerate(chunks[:limit], start=1):
            lines = chunk.splitlines()
            head = lines[0].lstrip("#").strip() if lines else f"Key Point {idx}"
            rest = "\n".join(lines[1:]).strip()
            items.append(
                _parse_section_into_slide(
                    head,
                    rest,
                    base_dir=base_dir,
                    cache_dir=effective_cache,
                )
            )

    hashtags = [str(tag) for tag in meta.get("hashtags", [])] if isinstance(meta.get("hashtags"), list) else []
    return DeckSpec(
        topic=topic,
        language=language,
        aspect_ratio=aspect_ratio,
        part=int(meta.get("part", 1)),
        cover=cover,
        items=items,
        hashtags=hashtags,
    )


class MarkdownSource(BaseSource):
    """Converts local or remote Markdown documents into multi-layout carousel slides."""

    def __init__(self, cache_dir: Path, language: Language = Language.EN) -> None:
        super().__init__(cache_dir=cache_dir, language=language)

    def load_markdown(self, source_path_or_url: Path | str) -> tuple[str, Path | None]:
        """Load raw Markdown text from a local file path or remote URL."""
        raw_str = str(source_path_or_url).strip()
        if raw_str.startswith(("http://", "https://")):
            if "github.com/" in raw_str and "/blob/" in raw_str:
                raw_str = raw_str.replace("github.com/", "raw.githubusercontent.com/").replace(
                    "/blob/", "/"
                )
            with httpx.Client(follow_redirects=True, timeout=20.0) as client:
                resp = client.get(raw_str, headers={"User-Agent": "TCD-Swipekit/0.1"})
                resp.raise_for_status()
                return resp.text, None

        local_path = Path(raw_str).expanduser().resolve()
        if not local_path.is_file():
            raise FileNotFoundError(f"Markdown file not found: {source_path_or_url}")
        return local_path.read_text(encoding="utf-8"), local_path.parent

    def build_deck(
        self,
        markdown_source: Path | str,
        *,
        limit: int = 10,
    ) -> DeckSpec:
        """Load a Markdown file/URL and parse it into a complete DeckSpec."""
        raw_md, base_dir = self.load_markdown(markdown_source)
        return parse_markdown_to_deck(
            raw_md,
            base_dir=base_dir,
            cache_dir=self.cache_dir,
            limit=limit,
            default_language=self.language,
        )

    def fetch_items(
        self,
        limit: int = 10,
        *,
        markdown_file: Path | str | None = None,
        markdown_text: str | None = None,
        **kwargs: object,
    ) -> list[SlideItem]:
        """Fetch parsed SlideItem objects from a Markdown file, URL, or raw string."""
        if markdown_text is not None:
            deck = parse_markdown_to_deck(
                markdown_text,
                cache_dir=self.cache_dir,
                limit=limit,
                default_language=self.language,
            )
            return deck.items
        if markdown_file is None:
            return []
        deck = self.build_deck(markdown_file, limit=limit)
        return deck.items
