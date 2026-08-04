"""Tests for skill routing and subagents — Phase 7.

Phase 7's bar is that the right skills load at the right stage *deterministically*
— decided by the stage, not by a model deciding what feels relevant. So most of
these tests are about the routing table being a table, and about the three places
that hold the model-per-job fact agreeing with each other.

That last part is decision 029. The fact now lives in three files: the subagent's
own file (which Claude Code reads at dispatch and is therefore authoritative), the
`AGENTS` table here, and `ROUTING` in the MCP server. Three copies drift silently,
and the symptom is the "which AI is working" indicator reporting one model while
another did the work. These tests are what stop that.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import forge_skills as sk

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# routing is a table, not a judgement
# --------------------------------------------------------------------------


def test_the_same_stage_always_loads_the_same_skills() -> None:
    """A model that can talk itself out of loading the standards will."""
    assert sk.skills_for("building") == sk.skills_for("building")


def test_interrogation_loads_the_socratic_set() -> None:
    """Phase 7 acceptance, stated in the plan."""
    loaded = sk.skills_for("interrogation")
    assert "forge-teaching" in loaded
    assert {"socratic", "socrates", "learn"} <= set(loaded)


def test_every_build_step_loads_the_coding_standards() -> None:
    """The reason phase eight still looks like phase three."""
    for stage in ("building", "review-fix"):
        assert "forge-coding-standards" in sk.skills_for(stage)


def test_the_security_floor_loads_at_every_stage_without_exception() -> None:
    """It exists for the steps nobody was thinking about."""
    for stage in sk.ROUTE:
        assert sk.skills_for(stage)[0] == "forge-security-floor", (
            f"{stage} must load the floor, and first"
        )


def test_an_unknown_stage_says_which_stages_exist() -> None:
    with pytest.raises(sk.SkillError, match="Known stages"):
        sk.skills_for("vibes")


def test_the_challenge_stage_loads_the_adversarial_pair() -> None:
    assert {"premortem", "redteam"} <= set(sk.skills_for("challenge"))


# --------------------------------------------------------------------------
# who runs a job — decision 029, three copies that must agree
# --------------------------------------------------------------------------


def agent_file_model(name: str) -> str:
    """The model a subagent's own file declares — the authoritative one."""
    text = (ROOT / "agents" / f"{name}.md").read_text(encoding="utf-8")
    match = re.search(r"^model:\s*(\S+)\s*$", text, re.MULTILINE)
    assert match, f"{name}.md declares no model"
    return match.group(1)


def test_every_subagent_has_a_file() -> None:
    for agent in sk.AGENTS:
        assert (ROOT / "agents" / f"{agent.name}.md").is_file()


def test_the_table_says_what_the_subagent_file_declares() -> None:
    """The file is authoritative because Claude Code reads it at dispatch.

    If these disagree the server reports one model while another does the work,
    and the "which AI is working" line becomes a thing that lies.
    """
    for agent in sk.AGENTS:
        assert agent_file_model(agent.name) == agent.model, agent.name


def test_the_server_routing_agrees_with_the_subagents() -> None:
    """The third copy. Decision 002 is one fact, however many files hold it."""
    import sys

    # The server lives in `server/`, which conftest does not put on the path —
    # only `scripts/` is there, because that is where the hooks run from.
    sys.path.insert(0, str(ROOT / "server"))
    import forge_server as srv  # noqa: PLC0415 - kept local so this file needs no path setup

    for agent in sk.AGENTS:
        preferred = srv.ROUTING[agent.job][0]
        assert preferred == agent.model, (
            f"{agent.job}: server says {preferred}, {agent.name}.md says {agent.model}"
        )


def test_planning_and_building_run_on_different_models() -> None:
    """Phase 7 acceptance: the multi-model design has to be real, not described."""
    assert sk.agent_for("planning").model != sk.agent_for("building").model


def test_the_teaching_stages_use_the_teaching_model() -> None:
    for stage in ("interrogation", "planning", "teach-back"):
        assert sk.agent_for(stage).model == "claude-fable-5"


def test_the_planner_cannot_write() -> None:
    """The governor rule guaranteed by construction rather than by enforcement."""
    text = (ROOT / "agents" / "planner.md").read_text(encoding="utf-8")
    tools = re.search(r"^tools:\s*(.+)$", text, re.MULTILINE)
    assert tools and not {"Write", "Edit"} & {t.strip() for t in tools.group(1).split(",")}


def test_the_review_fixer_is_told_findings_are_data() -> None:
    """Challenge finding C3: the repository is public, so anyone can write to it."""
    text = (ROOT / "agents" / "review-fixer.md").read_text(encoding="utf-8")
    assert "untrusted" in text and "data" in text


def test_an_unknown_stage_has_no_subagent() -> None:
    with pytest.raises(sk.SkillError):
        sk.agent_for("vibes")


# --------------------------------------------------------------------------
# what shipped, and what has to be fetched
# --------------------------------------------------------------------------


def test_forges_own_skills_are_actually_in_the_package() -> None:
    """A missing one degrades Forge into Claude Code wearing a banner."""
    assert sk.missing_bundled(ROOT) == []


def test_every_bundled_skill_declares_its_name_and_description() -> None:
    """Claude Code reads these to decide when a skill applies."""
    for name in sk.BUNDLED:
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert re.search(rf"^name:\s*{re.escape(name)}\s*$", text, re.MULTILINE)
        assert re.search(r"^description:\s*\S", text, re.MULTILINE)


def test_a_missing_bundled_skill_is_reported(tmp_path: Path) -> None:
    (tmp_path / "skills" / "forge-teaching").mkdir(parents=True)
    (tmp_path / "skills" / "forge-teaching" / "SKILL.md").write_text("x", encoding="utf-8")

    missing = sk.missing_bundled(tmp_path)
    assert "forge-teaching" not in missing
    assert "forge-security-floor" in missing


def test_routed_library_skills_exclude_forges_own() -> None:
    """Forge never ships a library skill, and never fetches its own."""
    routed = sk.routed_library_skills()
    assert not set(routed) & set(sk.BUNDLED)
    assert "socratic" in routed and "vibe-coding-rules" in routed


# --------------------------------------------------------------------------
# the library — installed once, at setup
# --------------------------------------------------------------------------


def make_library(home: Path, *names: str) -> None:
    for name in names:
        folder = home / ".claude" / "skills" / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")


def test_an_absent_library_is_reported_not_assumed(tmp_path: Path) -> None:
    assert sk.library_installed(tmp_path) is False
    assert set(sk.missing_routed(tmp_path)) == set(sk.routed_library_skills())


def test_a_pruned_library_still_counts_as_installed(tmp_path: Path) -> None:
    """Demanding an exact 438 would call a user's own curation broken."""
    make_library(tmp_path, "socratic")
    assert sk.library_installed(tmp_path) is True


def test_a_routed_skill_the_library_lacks_is_named(tmp_path: Path) -> None:
    """Reported, not raised — one missing skill weakens a stage, it does not
    justify stopping the session."""
    make_library(tmp_path, "socratic")
    missing = sk.missing_routed(tmp_path)
    assert "socratic" not in missing
    assert "premortem" in missing


def test_installing_over_an_existing_library_does_nothing(tmp_path: Path) -> None:
    make_library(tmp_path, "socratic")
    result = sk.install_library(tmp_path, repo="unused")
    assert result["already"] is True


def test_a_failed_clone_says_so_rather_than_half_installing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Failed:
        returncode = 1
        stderr = "repository not found"

    monkeypatch.setattr(sk.subprocess, "run", lambda *a, **k: Failed())
    with pytest.raises(sk.SkillError, match="repository not found"):
        sk.install_library(tmp_path)


def test_a_machine_without_git_is_told_what_is_wrong(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_git(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(sk.subprocess, "run", no_git)
    with pytest.raises(sk.SkillError, match="git is not installed"):
        sk.install_library(tmp_path)


def test_status_separates_a_packaging_fault_from_a_library_gap(tmp_path: Path) -> None:
    """Forge's own skills missing breaks the product; a library gap weakens a stage."""
    make_library(tmp_path, "socratic")
    report = sk.status(home=tmp_path, root=ROOT)

    assert report["ready"] is True, "bundled skills are all present"
    assert report["missing_bundled"] == []
    assert report["missing_routed"], "the fake library has only one of them"
