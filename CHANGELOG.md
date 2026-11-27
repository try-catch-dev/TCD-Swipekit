# Changelog

All notable changes to **TCD-Swipekit** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-11-26

### Added
- **First-Class Plugin & Extensibility Architecture (`plugins.py` & `swipekit plugins`)**:
  - Content Source Registry (`@register_source`, `get_source_class`, `list_sources`) + `swipekit generate custom <source> --opt key=value`.
  - Slide Layout Registry (`@register_layout`, `get_layout`, `list_layouts`) + zero-Python drop-in Jinja2 templates (`./templates/slide_<name>.html.j2`, `~/.config/swipekit/templates/`, or `custom_template` per slide).
  - Bundle Exporter Registry (`@register_exporter`, `get_exporter`, `list_exporters`) + `--export <name>`.
  - Automatic discovery of Python entry points (`tcd_swipekit.plugins`, `tcd_swipekit.sources`, `tcd_swipekit.layouts`, `tcd_swipekit.exporters`), user global plugins (`~/.config/swipekit/plugins/*.py`), and CLI `--plugin ./my_plugin.py` (with `swipekit init plugin` scaffolding).
  - User & local theme preset directory discovery (`./themes/*.yaml`, `~/.config/swipekit/themes/*.yaml`, and `register_theme_dir()`).
- **Markdown-to-Carousel Engine (`swipekit generate markdown` & `MarkdownSource`)**:
  - Converts local `.md` files or remote Markdown URLs into multi-layout decks (`code`, `versus`, `checklist`, `showcase`), extracting YAML frontmatter, `# H1` cover titles, `## H2` sections, fenced code/diff blocks, `### H3` comparison sides, and numbered/bullet checklists (with `swipekit init markdown` scaffolding and `examples/python_tips_article.md`).
- **New Slide Layouts (`code`, `versus`, `checklist`) & Device Mockup Frames (`frame: browser | macos`)**:
  - `layout: code` — Syntax-highlighted code/diff window powered by Pygments (`diff_mode`, `highlight_lines`, line numbers).
  - `layout: versus` — Responsive A-vs-B comparison cards (stacked portrait on `3:4`/`4:5`/`9:16`, 2-column side-by-side on `1:1`) with verdict callouts.
  - `layout: checklist` — Actionable checklist, roadmap, or step-by-step takeaways card (`numbered`, per-item `badge`, `accent`, `summary`).
  - Browser & macOS window frames (`frame: browser | macos | none`) on `showcase` slides, plus top **Slide Progress Bar & Fraction Counter (`01 / 04`)** (`theme.show_progress`).
- **Multi-Ratio Batch (`--ratios`), LinkedIn PDF (`--pdf`) & Animated GIF (`--gif`) Exporters**:
  - Render multiple aspect ratios (`3:4,4:5,1:1` or `all`) in one browser session, export `carousel.pdf`, and generate an animated `carousel.gif` slideshow via Pillow.
- **Live Watch & Hot-Reload Server (`swipekit watch`)**:
  - Watches `deck.yaml`, `.md` articles, and custom themes, re-rendering on save and hot-reloading the browser preview over HTTP.
- **Platform Safe-Zone Overlays in `preview.html`**: Toggleable HUD overlays (`S` shortcut) for TikTok, IG Reels, IG Carousel, and LinkedIn.
- **Dynamic Google Fonts & Offline Local Fonts (`font_files`)**: Automatically loads fonts declared in `ThemeConfig` or embeds local `.woff2`/`.ttf`/`.otf` files via `@font-face`.
- **Creator Brand Profile (`.swipekit.yaml` / `~/.config/swipekit/config.yaml`)**: Reusable defaults with `swipekit init profile` and `swipekit profile`.
- **4 New Built-in Themes**: `arctic-slate`, `nord-frost`, `amber-noir`, and `crimson-carbon` (8 dark & light themes total).
- **`swipekit doctor` Command**: Instant environment diagnostics for Python, Playwright/Chromium, Pillow, Pygments, plugin registry, installed Agent Skills, profiles, and optional tokens.
- **Agent Skill Updater & Auto-Sync (`swipekit skill update`, `swipekit skill status`, `swipekit update`)**:
  - Tracks SHA-256 content digests and `.swipekit-skill.json` metadata stamps across all installed AI agent skill directories (`antigravity`, `gemini`, `claude`, `codex`, `cursor`, `copilot`, `agents`).
  - Supports `--remote` to pull the latest `SKILL.md` and `references/` straight from GitHub without waiting for a package upgrade.
  - Automatically syncs outdated installed Agent Skills whenever `swipekit` commands run (`auto_update_skill: true` by default).

### Changed
- Neutralized open-source defaults (`midnight-emerald` default preset, `editorial-light` README showcase, `@yourhandle` placeholder) and removed personal brand preset files.
- Hardened Playwright rendering with isolated per-slide pages, `--disable-dev-shm-usage`, `--disable-gpu`, and automatic crash recovery.

## [0.1.0] - 2026-11-25

### Added
- Initial release with GitHub Trending/Topic source, Website auto-screenshot source (`sites.yml`), hybrid manual decks (`deck.yaml`), 4 built-in themes, EN/ID localization, optional `--ai` copywriting, customizable closing CTA slides, and Agent Skills standard (`SKILL.md`) installer.
