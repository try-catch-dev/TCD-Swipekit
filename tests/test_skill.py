"""Unit tests for the bundled TCD-Swipekit Agent Skill and CLI installer."""

from pathlib import Path

import pytest
import yaml

from tcd_swipekit.skill_installer import (
    SKILL_NAME,
    get_bundled_skill_dir,
    install_skill,
    resolve_agent_skill_dirs,
)


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


def test_install_skill_to_custom_target_and_overwrite(tmp_path: Path):
    installed = install_skill(target_dir=tmp_path, overwrite=False)
    assert len(installed) == 1
    dest = installed[0]
    assert dest == tmp_path / SKILL_NAME
    assert (dest / "SKILL.md").is_file()
    assert (dest / "references" / "deck-schema.md").is_file()

    with pytest.raises(FileExistsError):
        install_skill(target_dir=tmp_path, overwrite=False)

    reinstalled = install_skill(target_dir=tmp_path, overwrite=True)
    assert reinstalled == [dest]


def test_resolve_agent_skill_dirs_variants(tmp_path: Path):
    assert len(resolve_agent_skill_dirs("antigravity")) == 1
    assert len(resolve_agent_skill_dirs("claude")) == 1
    assert resolve_agent_skill_dirs("cursor", project_dir=tmp_path)[0] == tmp_path / ".cursor" / "skills" / SKILL_NAME
    assert len(resolve_agent_skill_dirs("all")) >= 4

    with pytest.raises(ValueError, match="Unsupported agent"):
        resolve_agent_skill_dirs("unknown-agent")
