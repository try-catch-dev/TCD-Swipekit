"""Load built-in YAML theme presets or custom theme files and apply overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tcd_swipekit.models import ThemeConfig

THEMES_DIR = Path(__file__).parent
PRESETS_DIR = THEMES_DIR / "presets"
TEMPLATES_DIR = THEMES_DIR / "templates"


def list_presets() -> list[str]:
    """Return sorted names of all built-in theme presets."""
    return sorted(p.stem for p in PRESETS_DIR.glob("*.yaml"))


def load_theme(
    preset_or_path: str | Path = "midnight-emerald",
    overrides: dict[str, Any] | None = None,
) -> ThemeConfig:
    """Load a ThemeConfig from a preset name or custom YAML path and merge overrides."""
    candidate_path = Path(str(preset_or_path))
    if candidate_path.is_file():
        base_data = yaml.safe_load(candidate_path.read_text(encoding="utf-8")) or {}
    else:
        preset_file = PRESETS_DIR / f"{preset_or_path}.yaml"
        if not preset_file.is_file():
            available = ", ".join(list_presets())
            raise ValueError(
                f"Unknown theme preset '{preset_or_path}'. Available presets: {available} "
                "(or provide a path to a custom .yaml theme file)."
            )
        base_data = yaml.safe_load(preset_file.read_text(encoding="utf-8")) or {}

    merged = dict(base_data)
    if overrides:
        for k, v in overrides.items():
            if v is not None:
                merged[k] = v

    return ThemeConfig.model_validate(merged)
