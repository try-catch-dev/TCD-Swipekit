---
name: tcd-swipekit
description: >
  Generate high-resolution social media photo-slide carousels (TikTok Photo Mode,
  Instagram Carousel, LinkedIn, Reels/Shorts) using TCD-Swipekit (`swipekit` CLI).
  Use whenever the user asks to create photo slides, carousels, swipeable tech posts,
  "5 GitHub repos trending", "5 useful websites", or custom-branded slide decks with
  custom themes, creator cover photos, auto-captured website screenshots (`sites.yml`),
  and Save/Follow closing CTA slides.
---

# TCD-Swipekit — AI Agent Skill

Use **TCD-Swipekit** (`swipekit` / `tcd-swipekit`) to generate ready-to-post PNG photo-slide carousels (`1180×1572` 3:4 portrait by default, plus `4:5`, `9:16`, and `1:1`) from GitHub repositories, websites (`sites.yml`), or hybrid `deck.yaml` specs.

## 1. Environment Check

Verify `swipekit` is installed before generating slides:

```bash
swipekit --version
swipekit themes
```

If `swipekit` is not installed yet:

```bash
pip install git+https://github.com/try-catch-dev/TCD-Swipekit.git
playwright install chromium
```

## 2. Choose the Right Workflow

### Workflow A — GitHub Trending or Topic Carousel

Quick CLI generation (English default; pass `--lang id` for Indonesian):

```bash
swipekit generate github \
  --topic "ai" \
  --limit 5 \
  --since weekly \
  --lang en \
  --theme midnight-emerald \
  --watermark "@yourhandle" \
  --outro \
  --ratios 3:4,4:5,1:1 \
  --pdf \
  --output ./output/github_deck
```

For curated editorial quality (recommended when writing custom Indonesian/English hooks, picking exact repos, mixing `layout: code` / `layout: versus` cards, or adding a custom Closing CTA slide), write a `deck.yaml` file and render it:

```bash
swipekit render ./my_deck.yaml --theme midnight-emerald --pdf --output ./output/github_deck
```

### Workflow B — Useful Websites Carousel (`sites.yml`)

Create a `sites.yml` config (or scaffold one with `swipekit init sites`), then run:

```bash
swipekit generate web --sites ./sites.yml --output ./output/websites_deck
```

`swipekit generate web` automatically launches headless Chromium via Playwright, dismisses common cookie banners, captures crisp `1280×800` desktop screenshots, extracts OpenGraph metadata, and renders the full slide bundle (`01_cover.png`, item slides, optional `closing_cta.png`, optional `carousel.pdf`, `caption.md`, `deck.yaml`, and `preview.html`).

### Workflow C — Markdown-to-Carousel, Slide Layouts & Extensibility

- **Markdown-to-Carousel (`swipekit generate markdown`):**
  - Convert any `.md` article, tutorial, or doc directly into a multi-layout deck:
    ```bash
    swipekit generate markdown ./article.md --theme editorial-light --outro --pdf --gif -o ./output/md_deck
    ```
- **Live Watch Server (`swipekit watch`):**
  - Run `swipekit watch ./deck.yaml --port 8765` to auto-re-render on save and hot-reload the browser preview.
- **Cover modes:**
  - `mode: photo` + `image_path: ./cover.png` — Editorial portrait/photo seamlessly fading into the cover canvas.
  - `mode: gradient` — Modern dual-orb mesh gradient with architectural grid lines.
  - `mode: minimal` — Clean editorial typography-first layout.
- **Slide layouts:**
  - `layout: showcase` (default) — Hero screenshot / GitHub repo / website showcase (supports `frame: browser | macos | none`).
  - `layout: code` (`code_block:`) — Syntax-highlighted code window with optional line highlights and diff coloring (`diff_mode: true`).
  - `layout: versus` (`versus:`) — Stacked (portrait) or side-by-side (`1:1`) A-vs-B comparison card with verdict bar.
  - `layout: checklist` (`checklist:`) — Numbered roadmap or checkmark audit card with per-item tags and summary bar.
- **Extensibility (`swipekit plugins`):**
  - Add custom themes in `./themes/`, custom Jinja2 slide layouts in `./templates/slide_<name>.html.j2`, or custom Python plugins (`--plugin ./my_plugin.py` / `swipekit init plugin`) using `@register_source`, `@register_layout`, and `@register_exporter`.
- **Closing CTA (`outro`):** Pass `--outro` on the CLI or include an `outro:` block in YAML so slide `N+1` prompts viewers to **Save**, **Follow**, and **Comment**.
- **Creator Brand Profile:** Run `swipekit init profile` (`.swipekit.yaml` or `--global`) to store default theme, watermark, language, cover photo, and outro once.

See [references/deck-schema.md](references/deck-schema.md) for full `deck.yaml`, `sites.yml`, `code_block`, `versus`, `checklist`, `outro`, and profile fields, and [references/brand-themes.md](references/brand-themes.md) for all 8 built-in theme presets (`midnight-emerald`, `editorial-light`, `arctic-slate`, `nord-frost`, `cyber-indigo`, `neon-violet`, `amber-noir`, `crimson-carbon`) and custom `.yaml` theme overrides.

## 3. Output Artifacts

Every run outputs:
- `01_cover.png` … `NN_<slug>.png` (+ optional `NN_closing_cta.png`)
- `carousel.pdf` (when `--pdf` is enabled — ready for LinkedIn Document Carousels)
- `carousel.gif` (when `--gif` is enabled — animated GIF slideshow preview)
- `caption.md` — Ready-to-paste social media caption, hashtags, and numbered links
- `deck.yaml` — Editable snapshot for fast re-renders (`swipekit render deck.yaml`)
- `preview.html` — Interactive keyboard-navigable browser preview with toggleable TikTok / IG Reels / IG Carousel / LinkedIn Safe-Zone overlays

## 4. Visual Quality Checklist (Important for Agents)

Before delivering rendered slides to the user, **visually inspect every generated PNG**:
1. **Description length:** Keep item descriptions to **2 crisp lines max** (~105–125 characters) with no orphan single-word 3rd line.
2. **Screenshot quality:** Ensure README or website screenshots are well-proportioned (`0.75 <= width/height <= 2.6`), legible, and free of login walls or ultra-wide skinny banners.
3. **Footer clearance:** Verify footnotes do not crowd the bottom-right `watermark` handle.
4. **Language match:** Default is English (`en`), with native Indonesian (`id`) support via `--lang id` or `language: id` in YAML.
