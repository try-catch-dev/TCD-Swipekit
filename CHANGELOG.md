# Changelog

All notable changes to **TCD-Swipekit** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Slide Layouts (`layout: code` & `layout: versus`)**: Syntax-highlighted code/diff cards powered by Pygments (`diff_mode`, `highlight_lines`, line numbers) and responsive A-vs-B comparison cards (stacked portrait on `3:4`/`4:5`/`9:16`, 2-column side-by-side on `1:1`) with verdict callouts.
- **Multi-Ratio Batch Export (`--ratios`)**: Render multiple aspect ratios (`3:4,4:5,1:1` or `all`) in one browser session without re-fetching sources.
- **LinkedIn PDF Export (`--pdf`)**: Bundle rendered slides into a ready-to-upload multi-page `carousel.pdf`.
- **Platform Safe-Zone Overlays in `preview.html`**: Toggleable HUD overlays (`S` shortcut) for TikTok, IG Reels, IG Carousel, and LinkedIn.
- **Dynamic Google Fonts & Offline Local Fonts (`font_files`)**: Automatically loads fonts declared in `ThemeConfig` or embeds local `.woff2`/`.ttf`/`.otf` files via `@font-face`.
- **Creator Brand Profile (`.swipekit.yaml` / `~/.config/swipekit/config.yaml`)**: Reusable defaults with `swipekit init profile` and `swipekit profile` (`CLI > YAML file > Profile > Defaults`).
- **Closing CTA CLI Flag (`--outro / --no-outro`)**: Auto-generate localized EN/ID Save/Follow/Comment closing slides from any CLI workflow.
- **4 New Built-in Themes**: `arctic-slate`, `nord-frost`, `amber-noir`, and `crimson-carbon` (8 dark & light themes total).
- **`swipekit doctor` Command**: Instant environment diagnostics for Python, Playwright/Chromium, Pillow, Pygments, profiles, and optional tokens.
- **Open-Source Community & Release Setup**: Added `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, GitHub Issue/PR templates, Python 3.10 CI coverage, and PyPI Trusted Publishing release workflow.

### Changed
- Removed personal brand defaults (`tcd-neon-lime`, `@trycatchdev`) from built-in presets and starter configs so open-source users start from clean neutral presets (`midnight-emerald` default, `editorial-light` showcase).
- Hardened headless Chromium launch flags with `--disable-dev-shm-usage` for container/CI stability.

## [0.1.0] - 2026-11-25

### Added
- Initial release with GitHub Trending/Topic source, Website auto-screenshot source (`sites.yml`), hybrid manual decks (`deck.yaml`), 4 built-in themes, EN/ID localization, optional `--ai` copywriting, customizable closing CTA slides, and Agent Skills standard (`SKILL.md`) installer.
