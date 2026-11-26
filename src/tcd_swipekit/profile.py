"""Creator brand profile discovery and loading (`.swipekit.yaml` / `~/.config/swipekit/config.yaml`)."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from tcd_swipekit.models import CreatorProfile

LOCAL_PROFILE_NAMES = (".swipekit.yaml", ".swipekit.yml")
GLOBAL_PROFILE_PATHS = (
    Path.home() / ".config" / "swipekit" / "config.yaml",
    Path.home() / ".config" / "swipekit" / "config.yml",
    Path.home() / ".config" / "swipekit" / "profile.yaml",
)

STARTER_PROFILE_YAML = """# TCD-Swipekit Creator Brand Profile
# Place in your project as `.swipekit.yaml` or globally at `~/.config/swipekit/config.yaml`

theme: midnight-emerald
watermark: "@yourhandle"
watermark_position: bottom-right   # bottom-right | top-right | bottom-left
language: en                       # en | id
aspect_ratio: "3:4"                # 3:4 | 4:5 | 9:16 | 1:1
# ratios: ["3:4", "4:5", "1:1"]    # optional multi-ratio batch export by default
# cover_mode: gradient             # photo | gradient | minimal
# cover_image: ./assets/cover.png
export_pdf: false

outro:
  enabled: true
  badge_text: "DONE · WANT PART 2?"
  title_lines:
    - "Save this post"
    - "*& follow*"
    - "for more tools."
  subtitle: "Weekly curated **open-source repos, dev tips & useful websites**."
  actions:
    - icon: bookmark
      label: "Save this post"
      sublabel: "Keep it handy for your next build"
      accent: false
    - icon: follow
      label: "Follow @yourhandle"
      sublabel: "Don't miss Part 2 and weekly drops"
      accent: true
    - icon: comment
      label: "Comment 'PART 2'"
      sublabel: "Drop your favorite pick below"
      accent: false
  handle: "@yourhandle"
  footer_note: "OPEN SOURCE · DEV TOOLS"
"""


def find_profile_path(
    explicit_path: Path | None = None,
    cwd: Path | None = None,
) -> Path | None:
    """Discover the active Creator Brand Profile file.

    Search order:
    1. Explicit path argument (`--profile`)
    2. `SWIPEKIT_PROFILE` environment variable
    3. `.swipekit.yaml` or `.swipekit.yml` in `cwd`
    4. `~/.config/swipekit/config.yaml` (or `.yml` / `profile.yaml`)
    """
    if explicit_path is not None:
        resolved = explicit_path.expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Creator profile not found: {explicit_path}")
        return resolved

    env_path = os.environ.get("SWIPEKIT_PROFILE")
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if candidate.is_file():
            return candidate

    search_dir = (cwd or Path.cwd()).resolve()
    for name in LOCAL_PROFILE_NAMES:
        local = search_dir / name
        if local.is_file():
            return local

    for global_path in GLOBAL_PROFILE_PATHS:
        if global_path.is_file():
            return global_path

    return None


def load_profile(
    explicit_path: Path | None = None,
    cwd: Path | None = None,
    enabled: bool = True,
) -> tuple[CreatorProfile | None, Path | None]:
    """Load the active CreatorProfile (resolving relative asset paths against the profile file)."""
    if not enabled:
        return None, None

    path = find_profile_path(explicit_path=explicit_path, cwd=cwd)
    if path is None:
        return None, None

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profile = CreatorProfile.model_validate(raw)
    base_dir = path.parent

    if profile.cover_image:
        cov = Path(profile.cover_image).expanduser()
        if not cov.is_absolute():
            cov = (base_dir / cov).resolve()
        profile.cover_image = str(cov)

    if profile.theme:
        theme_candidate = Path(profile.theme).expanduser()
        if not theme_candidate.is_absolute():
            rel_theme = (base_dir / theme_candidate).resolve()
            if rel_theme.is_file():
                profile.theme = str(rel_theme)

    return profile, path
