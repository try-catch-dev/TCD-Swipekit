"""Install and inspect the bundled Agent Skill (SKILL.md) for AI coding agents."""

from __future__ import annotations

import shutil
from pathlib import Path

SKILL_NAME = "tcd-swipekit"


def get_bundled_skill_dir() -> Path:
    """Locate the bundled `tcd-swipekit` skill directory (works in repo checkout and installed wheel)."""
    # 1. Packaged inside wheel: src/tcd_swipekit/skill_data/tcd-swipekit
    pkg_skill = Path(__file__).parent / "skill_data" / SKILL_NAME
    if (pkg_skill / "SKILL.md").is_file():
        return pkg_skill

    # 2. Source repository layout: <repo_root>/skills/tcd-swipekit
    repo_skill = Path(__file__).resolve().parents[2] / "skills" / SKILL_NAME
    if (repo_skill / "SKILL.md").is_file():
        return repo_skill

    raise FileNotFoundError("Bundled tcd-swipekit SKILL.md could not be located.")


def resolve_agent_skill_dirs(agent: str, project_dir: Path | None = None) -> list[Path]:
    """Return destination skill directories for supported AI coding agents."""
    home = Path.home()
    cwd = project_dir or Path.cwd()

    mapping: dict[str, list[Path]] = {
        "antigravity": [home / ".gemini" / "antigravity" / "skills" / SKILL_NAME],
        "claude": [home / ".claude" / "skills" / SKILL_NAME],
        "codex": [home / ".codex" / "skills" / SKILL_NAME],
        "gemini": [home / ".gemini" / "skills" / SKILL_NAME],
        "cursor": [cwd / ".cursor" / "skills" / SKILL_NAME],
        "copilot": [cwd / ".github" / "skills" / SKILL_NAME],
        "agents": [home / ".agents" / "skills" / SKILL_NAME],
    }

    key = agent.lower().strip()
    if key == "all":
        return [
            home / ".gemini" / "antigravity" / "skills" / SKILL_NAME,
            home / ".claude" / "skills" / SKILL_NAME,
            home / ".codex" / "skills" / SKILL_NAME,
            home / ".agents" / "skills" / SKILL_NAME,
        ]
    if key not in mapping:
        supported = ", ".join([*sorted(mapping.keys()), "all"])
        raise ValueError(f"Unsupported agent '{agent}'. Choose one of: {supported}")
    return mapping[key]


def install_skill(
    *,
    agent: str | None = None,
    target_dir: Path | None = None,
    overwrite: bool = True,
    project_dir: Path | None = None,
) -> list[Path]:
    """Copy the bundled `tcd-swipekit` skill (SKILL.md + references/) to target agent directory(ies)."""
    source = get_bundled_skill_dir()

    if target_dir is not None:
        dest = target_dir / SKILL_NAME if target_dir.name != SKILL_NAME else target_dir
        destinations = [dest]
    else:
        destinations = resolve_agent_skill_dirs(agent or "antigravity", project_dir=project_dir)

    installed: list[Path] = []
    for dest in destinations:
        if dest.exists():
            if not overwrite:
                raise FileExistsError(
                    f"Skill already exists at {dest}. Pass --overwrite to replace it."
                )
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest)
        installed.append(dest)

    return installed
