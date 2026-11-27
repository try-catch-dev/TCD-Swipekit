"""Load built-in YAML theme presets, user theme directories, or custom theme files and apply overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tcd_swipekit.models import ThemeConfig

THEMES_DIR = Path(__file__).parent
PRESETS_DIR = THEMES_DIR / "presets"
TEMPLATES_DIR = THEMES_DIR / "templates"

_EXTRA_THEME_DIRS: list[Path] = []
_EXTRA_TEMPLATE_DIRS: list[Path] = []


def register_theme_dir(directory: Path | str) -> None:
    """Register an additional directory to search for `.yaml` theme presets."""
    resolved = Path(directory).expanduser().resolve()
    if resolved not in _EXTRA_THEME_DIRS:
        _EXTRA_THEME_DIRS.append(resolved)


def register_template_dir(directory: Path | str) -> None:
    """Register an additional directory to search for custom `.html.j2` slide templates."""
    resolved = Path(directory).expanduser().resolve()
    if resolved not in _EXTRA_TEMPLATE_DIRS:
        _EXTRA_TEMPLATE_DIRS.append(resolved)


def get_theme_search_dirs(cwd: Path | None = None) -> list[Path]:
    """Return ordered list of theme preset search directories (custom/local -> user global -> built-in)."""
    dirs: list[Path] = []
    for d in _EXTRA_THEME_DIRS:
        if d.is_dir() and d not in dirs:
            dirs.append(d)
    local_dir = ((cwd or Path.cwd()) / "themes").resolve()
    if local_dir.is_dir() and local_dir not in dirs:
        dirs.append(local_dir)
    global_dir = (Path.home() / ".config" / "swipekit" / "themes").resolve()
    if global_dir.is_dir() and global_dir not in dirs:
        dirs.append(global_dir)
    if PRESETS_DIR not in dirs:
        dirs.append(PRESETS_DIR)
    return dirs


def get_template_search_dirs(
    extra_dir: Path | None = None,
    cwd: Path | None = None,
) -> list[Path]:
    """Return ordered list of Jinja2 template directories (explicit -> registered -> local -> global -> built-in)."""
    dirs: list[Path] = []
    if extra_dir is not None:
        resolved_extra = extra_dir.expanduser().resolve()
        if resolved_extra.is_dir():
            dirs.append(resolved_extra)
    for d in _EXTRA_TEMPLATE_DIRS:
        if d.is_dir() and d not in dirs:
            dirs.append(d)
    local_tpl = ((cwd or Path.cwd()) / "templates").resolve()
    if local_tpl.is_dir() and local_tpl not in dirs:
        dirs.append(local_tpl)
    global_tpl = (Path.home() / ".config" / "swipekit" / "templates").resolve()
    if global_tpl.is_dir() and global_tpl not in dirs:
        dirs.append(global_tpl)
    if TEMPLATES_DIR not in dirs:
        dirs.append(TEMPLATES_DIR)
    return dirs


def list_presets(cwd: Path | None = None) -> list[str]:
    """Return sorted names of all available theme presets across built-in and user directories."""
    names: set[str] = set()
    for d in get_theme_search_dirs(cwd=cwd):
        for p in d.glob("*.yaml"):
            names.add(p.stem)
        for p in d.glob("*.yml"):
            names.add(p.stem)
    return sorted(names)


def _find_preset_file(name: str, cwd: Path | None = None) -> Path | None:
    for d in get_theme_search_dirs(cwd=cwd):
        for ext in (".yaml", ".yml"):
            candidate = d / f"{name}{ext}"
            if candidate.is_file():
                return candidate
    return None


def load_theme(
    preset_or_path: str | Path = "midnight-emerald",
    overrides: dict[str, Any] | None = None,
    cwd: Path | None = None,
) -> ThemeConfig:
    """Load a ThemeConfig from a preset name or custom YAML path and merge overrides."""
    candidate_path = Path(str(preset_or_path)).expanduser()
    theme_base_dir: Path | None = None
    if candidate_path.is_file():
        base_data = yaml.safe_load(candidate_path.read_text(encoding="utf-8")) or {}
        theme_base_dir = candidate_path.resolve().parent
    else:
        preset_file = _find_preset_file(str(preset_or_path), cwd=cwd)
        if preset_file is None:
            available = ", ".join(list_presets(cwd=cwd))
            raise ValueError(
                f"Unknown theme preset '{preset_or_path}'. Available presets: {available} "
                "(or provide a path to a custom .yaml theme file)."
            )
        base_data = yaml.safe_load(preset_file.read_text(encoding="utf-8")) or {}
        theme_base_dir = preset_file.resolve().parent

    merged = dict(base_data)
    if overrides:
        for k, v in overrides.items():
            if v is not None:
                merged[k] = v

    if theme_base_dir and isinstance(merged.get("font_files"), dict):
        resolved_fonts: dict[str, str] = {}
        for fam, fpath in merged["font_files"].items():
            p = Path(str(fpath)).expanduser()
            if not p.is_absolute():
                p = (theme_base_dir / p).resolve()
            resolved_fonts[str(fam)] = str(p)
        merged["font_files"] = resolved_fonts

    return ThemeConfig.model_validate(merged)
