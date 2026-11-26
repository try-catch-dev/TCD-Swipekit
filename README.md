# TCD-Swipekit

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**TCD-Swipekit** is a modular Python CLI and library for generating high-resolution social media photo-slide carousels (TikTok Photo Mode, Instagram Carousel, LinkedIn, Shorts/Reels) from **GitHub repositories**, **useful websites (`sites.yml`)**, or **hybrid YAML decks**.

---

## Features

- **Multi-Source Engine:**
  - **GitHub Source:** Automatically pulls trending repositories (`daily` / `weekly` / `monthly`), topic-filtered searches, live star counts, licenses, and official README screenshots (with smart white-margin cropping).
  - **Website Source (`sites.yml`):** Reads a clean `sites.yml` config, automatically captures crisp desktop screenshots via Playwright (with cookie-banner dismissal), and extracts OpenGraph titles & descriptions.
  - **Hybrid Manual Decks (`deck.yaml`):** Mix GitHub repos, websites, and custom cards in one editable YAML file and re-render in seconds.
- **Customizable Themes & Covers:**
  - 4 built-in presets (`midnight-emerald`, `cyber-indigo`, `neon-violet`, `editorial-light`) + custom `.yaml` themes.
  - 3 cover modes (`photo`, `gradient`, `minimal`) with custom background image, badge icons (`github`, `globe`, `sparkles`), accent line highlighting (`*accent*`), and configurable creator watermark (`watermark` & `watermark_position`).
- **Multi-Language & Multi-Ratio:**
  - English (`--lang en`, default) and Indonesian (`--lang id`) built in.
  - Aspect ratios: `3:4` (`1180×1572`, TikTok default), `4:5` (`1080×1350`, Instagram), `9:16` (`1080×1920`, Stories/Reels), `1:1` (`1080×1080`).
- **Ready-to-Post Output Bundle:** Every run exports numbered PNG slides, `caption.md` (with hashtags & links), `deck.yaml` (editable snapshot), and an interactive `preview.html`.

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/try-catch-dev/TCD-Swipekit.git
cd TCD-Swipekit

pip install -e ".[dev]"
playwright install chromium
```

### 2. Generate from GitHub Trending or Topic

```bash
# Default English, 6 weekly trending repos
swipekit generate github --limit 6 --output ./out/github_weekly

# Filter by topic, custom cover photo, Indonesian language, and watermark
swipekit generate github \
  --topic "ai" \
  --limit 6 \
  --lang id \
  --theme midnight-emerald \
  --cover-image ./my_photo.jpg \
  --watermark "@trycatchdev" \
  --output ./out/github_ai
```

### 3. Generate from Useful Websites (`sites.yml`)

```bash
# Scaffold a starter sites.yml
swipekit init sites

# Capture desktop screenshots automatically and render slides
swipekit generate web --sites examples/sites.yml --output ./out/useful_websites
```

### 4. Re-render an Edited `deck.yaml` (or Custom Theme)

```bash
swipekit render examples/github_trending.yaml \
  --theme examples/custom_theme.yaml \
  --output ./out/custom_render
```

### 5. List Built-in Themes

```bash
swipekit themes
```

---

## `sites.yml` Configuration Example

```yaml
topic: "Useful Websites for Developers"
language: en          # en (default) or id
aspect_ratio: "3:4"   # 3:4 | 4:5 | 9:16 | 1:1
part: 1

theme:
  preset: cyber-indigo
  watermark: "@trycatchdev"
  watermark_position: bottom-right   # bottom-right | top-right | bottom-left

cover:
  mode: gradient       # photo | gradient | minimal
  image_path: null     # set path to use mode: photo
  badge_icon: globe    # github | globe | sparkles | none
  badge_text: "USEFUL WEBSITES · PART 1"
  title_lines:
    - "3 Websites"
    - "*worth saving*"
    - "right now."
  cta_text: "Swipe to see them →"

sites:
  - url: "https://excalidraw.com"
    title: "Excalidraw"
    description: "Virtual hand-drawn whiteboard for system diagrams and wireframes."
    pricing: "Free"
    category: "Whiteboard"
    footnote: "OPEN SOURCE · REAL-TIME COLLAB"
    footnote_accent: true
```

---

## Install as an AI Agent Skill

TCD-Swipekit follows the **Agent Skills Open Standard** (`skills/tcd-swipekit/SKILL.md`), compatible with **Antigravity, Claude Code, Codex, Cursor, Gemini CLI, and GitHub Copilot**.

### Option 1 — Via `skills` CLI (`npx`)

```bash
npx skills add try-catch-dev/TCD-Swipekit
```

### Option 2 — Via Built-in `swipekit skill install`

```bash
# Install for a specific agent (antigravity, claude, codex, cursor, gemini, copilot, agents)
swipekit skill install --agent antigravity
swipekit skill install --agent claude
swipekit skill install --agent cursor

# Or install across all global agent skill directories at once
swipekit skill install --agent all

# Inspect the bundled SKILL.md
swipekit skill show
```

---

## Optional AI Copywriting

TCD-Swipekit runs **100% without API keys** by default. If you want an LLM to rewrite/shorten descriptions for social media punchiness:

```bash
pip install -e ".[ai]"
export OPENAI_API_KEY="sk-..."
swipekit generate github --topic "devtools" --ai
```

---

## Project Structure

```text
TCD-Swipekit/
├── src/tcd_swipekit/
│   ├── cli.py              # Typer + Rich CLI (`swipekit`)
│   ├── pipeline.py         # High-level orchestration API
│   ├── models.py           # Pydantic v2 schemas (DeckSpec, SitesFile, ThemeConfig, CoverConfig)
│   ├── i18n.py             # EN (default) & ID localization
│   ├── copywriter.py       # Cover defaults, caption builder, optional AI enhancer
│   ├── image_utils.py      # Smart border cropping & ambient color extraction
│   ├── renderer.py         # Jinja2 + Playwright Chromium PNG renderer
│   ├── sources/
│   │   ├── base.py         # Pluggable BaseSource interface
│   │   ├── github.py       # GitHub Trending / Search API / README screenshot parser
│   │   ├── website.py      # `sites.yml` loader + Playwright auto-screenshot + OG metadata
│   │   └── manual.py       # Hybrid `deck.yaml` loader & enricher
│   └── themes/
│       ├── loader.py       # Preset & custom YAML theme loader
│       ├── presets/        # midnight-emerald, cyber-indigo, neon-violet, editorial-light
│       └── templates/      # cover.html.j2, slide.html.j2, preview.html.j2
├── examples/
│   ├── sites.yml
│   ├── github_trending.yaml
│   └── custom_theme.yaml
└── tests/
```

---

## Development

```bash
ruff check src tests
pytest -v
```

## License

MIT © Try Catch Dev
