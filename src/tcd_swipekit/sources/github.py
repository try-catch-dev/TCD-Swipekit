"""GitHub source provider: trending repos, topic search, API metadata, and README screenshots."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from tcd_swipekit.i18n import t
from tcd_swipekit.image_utils import download_image, smart_crop_margins
from tcd_swipekit.models import BadgeStyle, Language, SlideBadge, SlideItem
from tcd_swipekit.sources.base import BaseSource

IGNORED_IMAGE_PATTERNS = (
    "shields.io",
    "badgen.net",
    "badge",
    "star-history",
    "trendshift",
    "visitor",
    "codecov",
    "coveralls",
    "workflows",
    "travis-ci",
    "circleci",
    "buymeacoffee",
    "ko-fi",
    "patreon",
    "discord",
    "twitter.com",
    "komarev",
    "contrib.rocks",
    "opencollective",
    "producthunt",
    "render.com/images",
    "vercel.com/button",
    "deploy-to-",
    "sponsor",
    "avatar",
    "favicon",
    ".svg",
    ".gif",
)


def extract_readme_image_urls(markdown: str, owner: str, repo: str, branch: str) -> list[str]:
    """Extract high-value static screenshot URLs from a GitHub README Markdown string."""
    raw_base = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/"
    matches = re.findall(
        r'!\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)|<img[^>]+src=["\']([^"\']+)["\']',
        markdown,
        flags=re.IGNORECASE,
    )
    candidates: list[str] = []
    seen: set[str] = set()

    for md_url, html_url in matches:
        raw_url = (md_url or html_url or "").strip()
        if not raw_url or raw_url.startswith("data:"):
            continue
        lower = raw_url.lower()
        if any(pat in lower for pat in IGNORED_IMAGE_PATTERNS):
            continue

        # Convert github.com/owner/repo/blob/... links to raw.githubusercontent.com
        if "github.com/" in raw_url and "/blob/" in raw_url:
            raw_url = raw_url.replace("github.com/", "raw.githubusercontent.com/").replace(
                "/blob/", "/"
            )
        elif not raw_url.startswith(("http://", "https://")):
            raw_url = urljoin(raw_base, raw_url.lstrip("./"))

        if raw_url not in seen:
            seen.add(raw_url)
            candidates.append(raw_url)

    # Prefer URLs mentioning screenshot/demo/dashboard/preview/ui/hero
    priority_words = ("screenshot", "dashboard", "preview", "ui", "desktop", "home", "hero", "demo")
    candidates.sort(key=lambda u: 0 if any(w in u.lower() for w in priority_words) else 1)
    return candidates


def parse_trending_html(html: str) -> list[dict[str, str]]:
    """Parse GitHub Trending HTML into repo slug, stars, gain, and description."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, str]] = []
    for article in soup.select("article.Box-row"):
        h2 = article.select_one("h2 a")
        if not h2 or not h2.get("href"):
            continue
        slug = str(h2["href"]).strip("/")
        desc_el = article.select_one("p")
        desc = re.sub(r"\s+", " ", desc_el.get_text(" ", strip=True)) if desc_el else ""

        stars_el = article.select_one('a[href$="/stargazers"]')
        stars = stars_el.get_text(strip=True) if stars_el else ""

        gain_text = ""
        gain_el = article.select_one("span.d-inline-block.float-sm-right")
        if gain_el:
            m = re.search(r"([\d,]+)\s+stars\s+(today|this week|this month)", gain_el.get_text(" "))
            if m:
                gain_text = m.group(1)

        results.append(
            {
                "repo": slug,
                "description": desc,
                "stars": stars,
                "gain": gain_text,
            }
        )
    return results


class GitHubSource(BaseSource):
    """Fetches GitHub trending or topic-filtered repositories with official screenshots."""

    def __init__(
        self,
        cache_dir: Path,
        language: Language = Language.EN,
        token: str | None = None,
    ) -> None:
        super().__init__(cache_dir=cache_dir, language=language)
        self.token = token or os.environ.get("GITHUB_TOKEN")

    def _headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": "TCD-Swipekit/0.1",
            "Accept": "application/vnd.github+json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _fetch_trending_slugs(self, since: str = "weekly", prog_lang: str | None = None) -> list[dict[str, str]]:
        path = f"https://github.com/trending/{prog_lang}" if prog_lang else "https://github.com/trending"
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            resp = client.get(path, params={"since": since}, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        return parse_trending_html(resp.text)

    def _search_by_topic(self, topic: str, limit: int = 12, prog_lang: str | None = None) -> list[dict[str, str]]:
        q_parts = [topic]
        if prog_lang:
            q_parts.append(f"language:{prog_lang}")
        query = " ".join(q_parts)
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            resp = client.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "sort": "stars", "order": "desc", "per_page": min(limit, 30)},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[dict[str, str]] = []
        for item in data.get("items", []):
            results.append(
                {
                    "repo": item["full_name"],
                    "description": item.get("description") or "",
                    "stars": f"{item.get('stargazers_count', 0):,}",
                    "gain": "",
                }
            )
        return results

    def _fetch_repo_html_fallback(self, slug: str) -> dict[str, object] | None:
        """Fallback parser for public GitHub repo HTML when api.github.com is rate-limited."""
        try:
            with httpx.Client(follow_redirects=True, timeout=15.0) as client:
                resp = client.get(
                    f"https://github.com/{slug}",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code != 200:
                    return None
            soup = BeautifulSoup(resp.text, "html.parser")
            stars_label = ""
            star_el = soup.select_one("#repo-stars-counter-star") or soup.select_one(
                'a[href$="/stargazers"] strong'
            )
            if star_el:
                raw_val = str(star_el.get("title") or star_el.get_text(strip=True)).strip()
                if raw_val and raw_val[0].isdigit():
                    stars_label = raw_val

            desc_el = soup.select_one("p.f4.my-3")
            desc = desc_el.get_text(" ", strip=True) if desc_el else ""

            lic = "Open Source"
            lic_match = re.search(
                r"\b(MIT|Apache-2\.0|GPL-3\.0|GPL-2\.0|AGPL-3\.0|BSD-3-Clause|BSD-2-Clause|MPL-2\.0)\b",
                resp.text,
            )
            if lic_match:
                lic = lic_match.group(1)

            lang_el = soup.select_one('a[href*="search?l="] span.color-fg-default')
            primary_lang = lang_el.get_text(strip=True) if lang_el else "Open Source"

            return {
                "stargazers_count": 0,
                "stargazers_label": stars_label,
                "default_branch": "HEAD",
                "license": {"spdx_id": lic},
                "description": desc,
                "language": primary_lang,
            }
        except Exception:
            return None

    def fetch_repo(
        self,
        slug: str,
        gain_num: str | None = None,
        since: str = "weekly",
        crop_margins: bool = True,
    ) -> SlideItem | None:
        """Fetch metadata & README screenshot for a single `owner/repo` slug."""
        owner, repo = slug.split("/", 1)
        meta: dict[str, object] | None = None
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            meta_resp = client.get(f"https://api.github.com/repos/{slug}", headers=self._headers())
            if meta_resp.status_code == 200:
                meta = meta_resp.json()

        if meta is None:
            meta = self._fetch_repo_html_fallback(slug)
        if meta is None:
            return None

        stars = int(meta.get("stargazers_count") or 0)
        branch = str(meta.get("default_branch") or "HEAD")
        lic_obj = meta.get("license")
        spdx = lic_obj.get("spdx_id") if isinstance(lic_obj, dict) else None
        license_label = str(spdx) if spdx and spdx != "NOASSERTION" else "Open Source"
        raw_desc = str(meta.get("description") or "").strip()

        # Fetch README to find official screenshot
        screenshot_path: Path | None = None
        branches_to_try = [branch] if branch == "HEAD" else [branch, "HEAD"]
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            for br in branches_to_try:
                for readme_name in ("README.md", "README_EN.md", "readme.md"):
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{br}/{readme_name}"
                    r = client.get(raw_url, headers={"User-Agent": "TCD-Swipekit/0.1"})
                    if r.status_code == 200 and r.text:
                        candidates = extract_readme_image_urls(r.text, owner, repo, br)
                        for img_url in candidates[:6]:
                            downloaded = download_image(img_url, self.cache_dir)
                            if downloaded is not None:
                                screenshot_path = (
                                    smart_crop_margins(downloaded) if crop_margins else downloaded
                                )
                                break
                        if screenshot_path is not None:
                            break
                if screenshot_path is not None:
                    break

        stars_str = str(meta.get("stargazers_label") or f"{stars:,}")
        badges = []
        if stars_str and stars_str != "0":
            badges.append(SlideBadge(text=f"★ {stars_str}", style=BadgeStyle.GLASS))
        if gain_num:
            gain_key = {
                "daily": "gain_daily",
                "weekly": "gain_weekly",
                "monthly": "gain_monthly",
            }.get(since, "gain_weekly")
            badges.append(
                SlideBadge(text=t(self.language, gain_key, n=gain_num), style=BadgeStyle.ACCENT)
            )
        else:
            lang_name = str(meta.get("language") or "Open Source")
            badges.append(SlideBadge(text=lang_name, style=BadgeStyle.ACCENT))

        badges.append(SlideBadge(text=license_label, style=BadgeStyle.GLASS))

        return SlideItem(
            source="github",
            eyebrow=f"{owner} /",
            title=repo,
            description=raw_desc or f"Open-source project by {owner}.",
            screenshot_path=str(screenshot_path) if screenshot_path else None,
            url=f"https://github.com/{slug}",
            repo=slug,
            badges=badges,
            command_or_url=f"$ git clone https://github.com/{slug}",
            footnote=str(meta.get("language") or "OPEN SOURCE").upper(),
        )

    def fetch_items(
        self,
        limit: int = 6,
        *,
        topic: str | None = None,
        repos: list[str] | None = None,
        since: str = "weekly",
        prog_lang: str | None = None,
        require_screenshot: bool = True,
        **kwargs: object,
    ) -> list[SlideItem]:
        """Fetch up to `limit` GitHub repositories matching trending, topic, or explicit slugs."""
        candidates: list[dict[str, str]] = []
        if repos:
            candidates = [{"repo": r.strip(), "gain": ""} for r in repos if "/" in r]
        else:
            # Start with live trending; if a specific topic is given, filter trending first then fall back to search
            try:
                trending = self._fetch_trending_slugs(since=since, prog_lang=prog_lang)
            except Exception:
                trending = []

            if topic:
                tokens = [w.lower() for w in re.split(r"[\s,/-]+", topic) if len(w) > 1]
                matched = [
                    c
                    for c in trending
                    if any(tok in (c["repo"] + " " + c["description"]).lower() for tok in tokens)
                ]
                candidates.extend(matched)
                if len(candidates) < limit * 2:
                    try:
                        searched = self._search_by_topic(
                            topic=topic, limit=max(limit * 3, 15), prog_lang=prog_lang
                        )
                        existing = {c["repo"].lower() for c in candidates}
                        for s in searched:
                            if s["repo"].lower() not in existing:
                                candidates.append(s)
                    except Exception:
                        pass
            else:
                candidates = trending

        items: list[SlideItem] = []
        fallback_items: list[SlideItem] = []

        for cand in candidates:
            if len(items) >= limit:
                break
            item = self.fetch_repo(cand["repo"], gain_num=cand.get("gain") or None, since=since)
            if item is None:
                continue
            if item.screenshot_path or not require_screenshot:
                items.append(item)
            else:
                fallback_items.append(item)

        # If fewer than `limit` had README images, fill remaining from fallback items
        if len(items) < limit:
            items.extend(fallback_items[: limit - len(items)])

        return items[:limit]
