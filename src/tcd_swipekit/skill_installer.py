"""Install, inspect, update, and auto-sync the TCD-Swipekit Agent Skill (SKILL.md)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

SKILL_NAME = "tcd-swipekit"
SKILL_STAMP_FILENAME = ".swipekit-skill.json"
DEFAULT_GITHUB_REPO = "try-catch-dev/TCD-Swipekit"
SKILL_RELATIVE_FILES = (
    "SKILL.md",
    "references/deck-schema.md",
    "references/brand-themes.md",
)


def _current_package_version() -> str:
    from tcd_swipekit import __version__

    return __version__


def get_bundled_skill_dir() -> Path:
    """Locate the bundled `tcd-swipekit` skill directory (works in repo checkout and installed wheel)."""
    # 1. Source repository layout: <repo_root>/skills/tcd-swipekit (preferred in editable dev mode)
    repo_skill = Path(__file__).resolve().parents[2] / "skills" / SKILL_NAME
    if (repo_skill / "SKILL.md").is_file():
        return repo_skill

    # 2. Packaged inside wheel: src/tcd_swipekit/skill_data/tcd-swipekit
    pkg_skill = Path(__file__).parent / "skill_data" / SKILL_NAME
    if (pkg_skill / "SKILL.md").is_file():
        return pkg_skill

    raise FileNotFoundError("Bundled tcd-swipekit SKILL.md could not be located.")


def compute_skill_digest(skill_dir: Path) -> str:
    """Compute a deterministic SHA-256 content digest across all Markdown files in a skill directory."""
    if not skill_dir.is_dir():
        return ""
    hasher = hashlib.sha256()
    md_files = sorted(p for p in skill_dir.rglob("*.md") if p.is_file())
    for file_path in md_files:
        rel = file_path.relative_to(skill_dir).as_posix()
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(file_path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()[:16]


def read_skill_stamp(skill_dir: Path) -> dict[str, Any]:
    """Read `.swipekit-skill.json` metadata stamp from an installed skill directory if present."""
    stamp_path = skill_dir / SKILL_STAMP_FILENAME
    if not stamp_path.is_file():
        return {}
    try:
        data = json.loads(stamp_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_skill_stamp(
    skill_dir: Path,
    *,
    source: str = "bundled",
    version: str | None = None,
) -> dict[str, Any]:
    """Write `.swipekit-skill.json` stamp with version, SHA-256 digest, source, and UTC timestamp."""
    stamp = {
        "name": SKILL_NAME,
        "version": version or _current_package_version(),
        "sha256": compute_skill_digest(skill_dir),
        "source": source,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    (skill_dir / SKILL_STAMP_FILENAME).write_text(
        json.dumps(stamp, indent=2) + "\n",
        encoding="utf-8",
    )
    return stamp


def _agent_dir_mapping(project_dir: Path | None = None) -> dict[str, Path]:
    home = Path.home()
    cwd = project_dir or Path.cwd()
    return {
        "antigravity": home / ".gemini" / "antigravity" / "skills" / SKILL_NAME,
        "gemini": home / ".gemini" / "skills" / SKILL_NAME,
        "claude": home / ".claude" / "skills" / SKILL_NAME,
        "codex": home / ".codex" / "skills" / SKILL_NAME,
        "agents": home / ".agents" / "skills" / SKILL_NAME,
        "cursor": cwd / ".cursor" / "skills" / SKILL_NAME,
        "copilot": cwd / ".github" / "skills" / SKILL_NAME,
    }


def resolve_agent_skill_dirs(agent: str, project_dir: Path | None = None) -> list[Path]:
    """Return destination skill directories for supported AI coding agents."""
    mapping = _agent_dir_mapping(project_dir=project_dir)
    key = agent.lower().strip()
    if key == "all":
        return [
            mapping["antigravity"],
            mapping["gemini"],
            mapping["claude"],
            mapping["codex"],
            mapping["agents"],
        ]
    if key not in mapping:
        supported = ", ".join([*sorted(mapping.keys()), "all"])
        raise ValueError(f"Unsupported agent '{agent}'. Choose one of: {supported}")
    return [mapping[key]]


def get_skill_status(project_dir: Path | None = None) -> list[dict[str, Any]]:
    """Inspect all supported agent skill directories and compare against the bundled skill."""
    bundled_dir = get_bundled_skill_dir()
    bundled_sha = compute_skill_digest(bundled_dir)
    bundled_ver = _current_package_version()
    mapping = _agent_dir_mapping(project_dir=project_dir)

    rows: list[dict[str, Any]] = []
    for agent_name, dest in mapping.items():
        installed = (dest / "SKILL.md").is_file()
        inst_sha = compute_skill_digest(dest) if installed else None
        stamp = read_skill_stamp(dest) if installed else {}
        up_to_date = bool(installed and inst_sha == bundled_sha)
        rows.append(
            {
                "agent": agent_name,
                "path": dest,
                "installed": installed,
                "up_to_date": up_to_date,
                "installed_version": stamp.get("version"),
                "bundled_version": bundled_ver,
                "installed_sha256": inst_sha,
                "bundled_sha256": bundled_sha,
                "source": stamp.get("source"),
                "updated_at": stamp.get("updated_at"),
            }
        )
    return rows


def install_skill(
    *,
    agent: str | None = None,
    target_dir: Path | None = None,
    overwrite: bool = True,
    project_dir: Path | None = None,
    source_dir: Path | None = None,
    source_label: str = "bundled",
) -> list[Path]:
    """Copy the `tcd-swipekit` skill (SKILL.md + references/) to target agent directory(ies)."""
    source = source_dir or get_bundled_skill_dir()

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
        write_skill_stamp(dest, source=source_label)
        installed.append(dest)

    return installed


def fetch_remote_skill_to_dir(
    dest_dir: Path,
    *,
    repo: str = DEFAULT_GITHUB_REPO,
    branch: str = "main",
    timeout: float = 15.0,
) -> Path:
    """Download the latest `skills/tcd-swipekit/` files directly from GitHub into `dest_dir`."""
    base_url = f"https://raw.githubusercontent.com/{repo}/{branch}/skills/{SKILL_NAME}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        for rel_path in SKILL_RELATIVE_FILES:
            url = f"{base_url}/{rel_path}"
            resp = client.get(url, headers={"User-Agent": "TCD-Swipekit-SkillUpdater"})
            resp.raise_for_status()
            out_file = dest_dir / rel_path
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(resp.text, encoding="utf-8")

    skill_md = dest_dir / "SKILL.md"
    if not skill_md.is_file() or f"name: {SKILL_NAME}" not in skill_md.read_text(encoding="utf-8"):
        raise ValueError(f"Downloaded SKILL.md from {repo}@{branch} is invalid.")
    return dest_dir


def update_skill(
    *,
    agent: str | None = None,
    target_dir: Path | None = None,
    remote: bool = False,
    repo: str = DEFAULT_GITHUB_REPO,
    branch: str = "main",
    force: bool = False,
    project_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Update installed `tcd-swipekit` skill directory(ies) from bundled package or remote GitHub.

    When `agent` and `target_dir` are both omitted, automatically updates all currently
    installed agent skill directories found on the system (or installs to `antigravity` if none exist).
    """
    if target_dir is not None:
        dest = target_dir / SKILL_NAME if target_dir.name != SKILL_NAME else target_dir
        destinations = [dest]
    elif agent is not None:
        destinations = resolve_agent_skill_dirs(agent, project_dir=project_dir)
    else:
        status_rows = get_skill_status(project_dir=project_dir)
        installed_dirs = [row["path"] for row in status_rows if row["installed"]]
        destinations = installed_dirs or resolve_agent_skill_dirs("antigravity", project_dir=project_dir)

    tmp_ctx = tempfile.TemporaryDirectory() if remote else None
    try:
        if remote and tmp_ctx is not None:
            source_dir = fetch_remote_skill_to_dir(
                Path(tmp_ctx.name) / SKILL_NAME,
                repo=repo,
                branch=branch,
            )
            source_label = f"github:{repo}@{branch}"
        else:
            source_dir = get_bundled_skill_dir()
            source_label = "bundled"

        new_sha = compute_skill_digest(source_dir)
        ver = _current_package_version()
        results: list[dict[str, Any]] = []

        for dest in destinations:
            existed = (dest / "SKILL.md").is_file()
            old_sha = compute_skill_digest(dest) if existed else None

            if existed and old_sha == new_sha and not force:
                # Ensure stamp file exists even if previously installed without one
                if not (dest / SKILL_STAMP_FILENAME).is_file():
                    write_skill_stamp(dest, source=source_label, version=ver)
                results.append(
                    {
                        "path": dest,
                        "action": "already_up_to_date",
                        "version": ver,
                        "sha256": new_sha,
                        "source": source_label,
                    }
                )
                continue

            if dest.exists():
                shutil.rmtree(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_dir, dest)
            write_skill_stamp(dest, source=source_label, version=ver)
            results.append(
                {
                    "path": dest,
                    "action": "updated" if existed else "installed",
                    "version": ver,
                    "sha256": new_sha,
                    "source": source_label,
                }
            )
        return results
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


def auto_sync_installed_skills(
    *,
    project_dir: Path | None = None,
    enabled: bool = True,
) -> list[Path]:
    """Silently sync any already-installed agent skill directories if their digest is outdated.

    Skipped when `enabled=False` or `SWIPEKIT_NO_AUTO_SKILL_UPDATE=1` is set.
    """
    if not enabled:
        return []
    env_flag = os.environ.get("SWIPEKIT_NO_AUTO_SKILL_UPDATE", "").strip().lower()
    if env_flag in ("1", "true", "yes"):
        return []

    updated_paths: list[Path] = []
    try:
        bundled_dir = get_bundled_skill_dir()
        bundled_sha = compute_skill_digest(bundled_dir)
        ver = _current_package_version()
        for row in get_skill_status(project_dir=project_dir):
            if not row["installed"]:
                continue
            dest: Path = row["path"]
            if row["installed_sha256"] != bundled_sha:
                shutil.rmtree(dest)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(bundled_dir, dest)
                write_skill_stamp(dest, source="bundled", version=ver)
                updated_paths.append(dest)
            elif not (dest / SKILL_STAMP_FILENAME).is_file():
                write_skill_stamp(dest, source="bundled", version=ver)
    except Exception:
        return updated_paths

    return updated_paths
