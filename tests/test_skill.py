"""Unit tests for the bundled TCD-Swipekit Agent Skill, updater, status check, and auto-sync."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from tcd_swipekit.cli import app
from tcd_swipekit.skill_installer import (
    SKILL_NAME,
    SKILL_STAMP_FILENAME,
    auto_sync_installed_skills,
    compute_skill_digest,
    get_bundled_skill_dir,
    get_skill_status,
    install_skill,
    read_skill_stamp,
    resolve_agent_skill_dirs,
    update_skill,
)

runner = CliRunner()


def test_bundled_skill_has_valid_frontmatter_and_references():
    skill_dir = get_bundled_skill_dir()
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.is_file()

    text = skill_md.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    parts = text.split("---\n", 2)
    meta = yaml.safe_load(parts[1])
    assert meta["name"] == SKILL_NAME
    assert len(meta["description"]) > 40

    assert (skill_dir / "references" / "deck-schema.md").is_file()
    assert (skill_dir / "references" / "brand-themes.md").is_file()


def test_install_skill_to_custom_target_and_writes_stamp(tmp_path: Path):
    installed = install_skill(target_dir=tmp_path, overwrite=False)
    assert len(installed) == 1
    dest = installed[0]
    assert dest == tmp_path / SKILL_NAME
    assert (dest / "SKILL.md").is_file()
    assert (dest / "references" / "deck-schema.md").is_file()
    assert (dest / SKILL_STAMP_FILENAME).is_file()

    stamp = read_skill_stamp(dest)
    assert stamp["name"] == SKILL_NAME
    assert stamp["sha256"] == compute_skill_digest(get_bundled_skill_dir())

    with pytest.raises(FileExistsError):
        install_skill(target_dir=tmp_path, overwrite=False)

    reinstalled = install_skill(target_dir=tmp_path, overwrite=True)
    assert reinstalled == [dest]


def test_update_skill_lifecycle_and_force(tmp_path: Path):
    # 1. First update on empty target installs the skill
    res1 = update_skill(target_dir=tmp_path)
    assert len(res1) == 1
    assert res1[0]["action"] == "installed"
    dest = res1[0]["path"]

    # 2. Second update when unchanged reports already_up_to_date
    res2 = update_skill(target_dir=tmp_path)
    assert res2[0]["action"] == "already_up_to_date"

    # 3. Tamper with installed SKILL.md to simulate an outdated v0.1 skill
    (dest / "SKILL.md").write_text("---\nname: tcd-swipekit\n---\nOld skill content\n", encoding="utf-8")
    res3 = update_skill(target_dir=tmp_path)
    assert res3[0]["action"] == "updated"
    assert compute_skill_digest(dest) == compute_skill_digest(get_bundled_skill_dir())

    # 4. Force update even when already up to date
    res4 = update_skill(target_dir=tmp_path, force=True)
    assert res4[0]["action"] == "updated"


def test_auto_sync_installed_skills_updates_outdated_project_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Install skill into project-scoped cursor directory (.cursor/skills/tcd-swipekit)
    install_skill(agent="cursor", project_dir=tmp_path)
    cursor_skill = tmp_path / ".cursor" / "skills" / SKILL_NAME
    assert (cursor_skill / "SKILL.md").is_file()

    # Simulate outdated skill content
    (cursor_skill / "SKILL.md").write_text("---\nname: tcd-swipekit\n---\nOutdated v0.1\n", encoding="utf-8")
    status_before = {r["agent"]: r for r in get_skill_status(project_dir=tmp_path)}
    assert status_before["cursor"]["installed"] is True
    assert status_before["cursor"]["up_to_date"] is False

    # Disabled via flag or env var does not sync
    assert auto_sync_installed_skills(project_dir=tmp_path, enabled=False) == []
    monkeypatch.setenv("SWIPEKIT_NO_AUTO_SKILL_UPDATE", "1")
    assert auto_sync_installed_skills(project_dir=tmp_path, enabled=True) == []
    monkeypatch.delenv("SWIPEKIT_NO_AUTO_SKILL_UPDATE", raising=False)

    # Enabled auto-sync updates the outdated skill in-place
    synced = auto_sync_installed_skills(project_dir=tmp_path, enabled=True)
    assert cursor_skill in synced
    status_after = {r["agent"]: r for r in get_skill_status(project_dir=tmp_path)}
    assert status_after["cursor"]["up_to_date"] is True


def test_cli_skill_status_and_update(tmp_path: Path):
    res_status = runner.invoke(app, ["skill", "status"])
    assert res_status.exit_code == 0
    assert "antigravity" in res_status.stdout
    assert "claude" in res_status.stdout

    res_update = runner.invoke(app, ["skill", "update", "--target", str(tmp_path)])
    assert res_update.exit_code == 0
    assert "INSTALLED" in res_update.stdout

    res_update_again = runner.invoke(app, ["skill", "update", "--target", str(tmp_path)])
    assert res_update_again.exit_code == 0
    assert "UP TO DATE" in res_update_again.stdout


def test_resolve_agent_skill_dirs_variants(tmp_path: Path):
    assert len(resolve_agent_skill_dirs("antigravity")) == 1
    assert len(resolve_agent_skill_dirs("gemini")) == 1
    assert len(resolve_agent_skill_dirs("claude")) == 1
    assert resolve_agent_skill_dirs("cursor", project_dir=tmp_path)[0] == tmp_path / ".cursor" / "skills" / SKILL_NAME
    assert len(resolve_agent_skill_dirs("all")) >= 5

    with pytest.raises(ValueError, match="Unsupported agent"):
        resolve_agent_skill_dirs("unknown-agent")
