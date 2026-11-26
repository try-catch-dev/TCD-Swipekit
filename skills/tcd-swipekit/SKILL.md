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
  --theme tcd-neon-lime \
  --watermark "@yourhandle" \
  --output ./output/github_deck
```

For curated editorial quality (recommended when writing custom Indonesian/English hooks, picking exact repos, or adding a Closing CTA slide), write a `deck.yaml` file and render it:

```bash
swipekit render ./my_deck.yaml --theme tcd-neon-lime --output ./output/github_deck
```

### Workflow B — Useful Websites Carousel (`sites.yml`)

Create a `sites.yml` config (or scaffold one with `swipekit init sites`), then run:

```bash
swipekit generate web --sites ./sites.yml --output ./output/websites_deck
```

`swipekit generate web` automatically launches headless Chromium via Playwright, dismisses common cookie banners, captures crisp `1280×800` desktop screenshots, extracts OpenGraph metadata, and renders the full slide bundle (`01_cover.png`, item slides, optional `closing_cta.png`, `caption.md`, `deck.yaml`, and `preview.html`).

### Workflow C — Custom Cover & Closing CTA

- **Cover modes:**
  - `mode: photo` + `image_path: ./cover.png` — Editorial portrait/photo seamlessly fading into the dark cover canvas.
  - `mode: gradient` — Modern dual-orb mesh gradient with architectural grid lines.
  - `mode: minimal` — Clean editorial typography-first layout.
- **Closing CTA (`outro`):** Always include an `outro:` block in YAML when creating social media carousels so slide `N+1` prompts viewers to **Save**, **Follow**, and **Comment**.

See [references/deck-schema.md](references/deck-schema.md) for full `deck.yaml`, `sites.yml`, and `outro` fields, and [references/brand-themes.md](references/brand-themes.md) for all built-in theme presets (`tcd-neon-lime`, `midnight-emerald`, `cyber-indigo`, `neon-violet`, `editorial-light`) and custom `.yaml` theme overrides.

## 3. Output Artifacts

Every run outputs:
- `01_cover.png` … `NN_<slug>.png` (+ optional `NN_closing_cta.png`)
- `caption.md` — Ready-to-paste social media caption, hashtags, and numbered links
- `deck.yaml` — Editable snapshot for fast re-renders (`swipekit render deck.yaml`)
- `preview.html` — Interactive keyboard-navigable browser preview

## 4. Visual Quality Checklist (Important for Agents)

Before delivering rendered slides to the user, **visually inspect every generated PNG**:
1. **Description length:** Keep item descriptions to **2 crisp lines max** (~105–125 characters) with no orphan single-word 3rd line.
2. **Screenshot quality:** Ensure README or website screenshots are well-proportioned (`0.75 <= width/height <= 2.6`), legible, and free of login walls or ultra-wide skinny banners.
3. **Footer clearance:** Verify footnotes do not crowd the bottom-right `watermark` handle.
4. **Language match:** Default is English (`en`), with native Indonesian (`id`) support via `--lang id` or `language: id` in YAML.
