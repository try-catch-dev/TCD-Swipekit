# Contributing to TCD-Swipekit

Thank you for your interest in contributing to **TCD-Swipekit**! Whether you are fixing a bug, designing a new theme preset, adding a content source, or improving documentation, every contribution is welcome.

---

## Development Setup

### Option A — Using `uv` (Recommended)

```bash
git clone https://github.com/try-catch-dev/TCD-Swipekit.git
cd TCD-Swipekit

uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
playwright install chromium
swipekit doctor
```

### Option B — Using Python `venv` + `pip`

```bash
git clone https://github.com/try-catch-dev/TCD-Swipekit.git
cd TCD-Swipekit

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -e ".[dev]"
playwright install chromium
swipekit doctor
```

---

## Quality Checks

Before opening a pull request, make sure linting and tests pass cleanly:

```bash
ruff check src tests
pytest -v
# Or with uv:
# uv run ruff check src tests && uv run pytest -v
```

---

## Great First Contributions

### 1. Adding a New Theme Preset
Theme presets live in `src/tcd_swipekit/themes/presets/*.yaml`.
1. Copy an existing preset (e.g., `midnight-emerald.yaml` or `editorial-light.yaml`) and pick a descriptive kebab-case name.
2. Keep `watermark` unset in built-in presets so users can supply their own handle.
3. Verify contrast for both headings and badges, and render `examples/code_and_versus_deck.yaml` with `--theme <your-preset>` to inspect the PNGs visually.
4. Add your preset to `tests/test_themes.py` and `skills/tcd-swipekit/references/brand-themes.md`.

### 2. Adding a New Slide Layout or Content Source
- **Content Sources** implement `BaseSource` in `src/tcd_swipekit/sources/base.py` and return a list of `SlideItem` models.
- **Slide Layouts** extend `SlideLayout` in `src/tcd_swipekit/models.py`, add a matching Jinja2 template in `src/tcd_swipekit/themes/templates/`, and dispatch inside `SlideRenderer.build_item_html`.

---

## Pull Request Guidelines

- Keep PRs focused on one feature or fix.
- Include unit or integration tests in `tests/` for new behavior.
- For visual or template changes, attach before/after PNG screenshots in the PR description.
- Follow conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
