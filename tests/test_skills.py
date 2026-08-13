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
import subprocess
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


def test_a_failed_clone_leaves_nothing_behind(tmp_path: Path) -> None:
    """Against a real git, not a mock that never touches the filesystem.

    The mock version could only prove that a non-zero exit became a SkillError
    — not the behaviour the name claims, which is that nothing partial is left
    to load. A half-installed library is worse than none: the routed skills go
    missing at random and Forge looks broken rather than uninstalled.
    """
    with pytest.raises(sk.SkillError):
        sk.install_library(tmp_path, repo=str(tmp_path / "not-a-repository"))

    assert not sk.library_dir(tmp_path).exists(), "no partial clone survives"
    assert sk.library_installed(tmp_path) is False


def test_a_library_without_the_pinned_commit_is_refused(tmp_path: Path) -> None:
    """A real repository, but not the one that was pinned.

    These files are instructions Claude Code will follow, so installing
    "whatever was there" is the thing being prevented.
    """
    source = tmp_path / "source"
    (source / "socratic").mkdir(parents=True)
    (source / "socratic" / "SKILL.md").write_text("---\nname: socratic\n---\n", encoding="utf-8")
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "skills"],
    ):
        subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)

    with pytest.raises(sk.SkillError, match="pinned"):
        sk.install_library(tmp_path, repo=str(source), commit="0" * 40)

    assert not sk.library_dir(tmp_path).exists(), "a wrong commit installs nothing"


def test_the_pinned_commit_installs_and_is_verified(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "socratic").mkdir(parents=True)
    (source / "socratic" / "SKILL.md").write_text("---\nname: socratic\n---\n", encoding="utf-8")
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "skills"],
    ):
        subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)
    sha = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    result = sk.install_library(tmp_path, repo=str(source), commit=sha)

    assert result["commit"] == sha, "what landed is checked, not assumed"
    assert sk.library_installed(tmp_path) is True


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


def test_the_structurer_can_actually_record_an_answer() -> None:
    """It had Read alone, so the one job it exists for was impossible.

    The user would have answered, the record would never have been written,
    and they would have stayed blocked behind a question already answered.
    """
    text = (ROOT / "agents" / "structurer.md").read_text(encoding="utf-8")
    assert "mcp__plugin_forge_forge__record_answer" in text


def test_every_declared_subagent_is_reachable_from_some_stage() -> None:
    """An agent nothing dispatches to is an agent that never runs.

    `structurer` was declared and unrouted, so every answer would have been
    recorded by whichever agent happened to be holding the conversation.
    """
    routed = set(sk.STAGE_AGENT.values())
    assert {a.name for a in sk.AGENTS} == routed


def test_structuring_runs_on_the_cheapest_model() -> None:
    """Decision 002: it runs after every answer, so it is where cost is won."""
    assert sk.agent_for("structuring").model == "claude-haiku-4-5"


def test_structuring_loads_almost_nothing() -> None:
    """It must transcribe, not interpret. Every extra skill is another voice
    telling the cheapest model to improve on the user's own words."""
    assert sk.skills_for("structuring") == ("forge-security-floor",)


def test_a_folder_with_no_skills_in_it_is_not_an_installed_library(tmp_path: Path) -> None:
    """A stray note in the skills folder is not a library.

    The docstring promised "any non-empty directory" while the code required a
    SKILL.md. Under the docstring's rule setup would have skipped the install
    and left nothing routable behind.
    """
    folder = sk.library_dir(tmp_path)
    folder.mkdir(parents=True)
    (folder / "notes.txt").write_text("mine", encoding="utf-8")

    assert sk.library_installed(tmp_path) is False


def test_install_refuses_to_overwrite_a_folder_it_did_not_create(tmp_path: Path) -> None:
    """git clone rejects a non-empty destination, and its message names
    neither the directory nor the reason a user would care about."""
    folder = sk.library_dir(tmp_path)
    folder.mkdir(parents=True)
    (folder / "notes.txt").write_text("mine", encoding="utf-8")

    with pytest.raises(sk.SkillError, match="will not"):
        sk.install_library(tmp_path)

    assert (folder / "notes.txt").exists(), "the user's own file is untouched"


def test_cleanup_removes_read_only_files(tmp_path: Path) -> None:
    """Pins the `onexc` handler, which a review claimed took one argument.

    It takes three — (func, path, exc) — and this is what proves it. Without a
    working handler the cleanup silently does nothing on Windows, because git
    marks everything under .git/objects read-only and a read-only file cannot
    be deleted.
    """
    import os
    import stat

    folder = tmp_path / "library"
    folder.mkdir()
    locked = folder / "locked.txt"
    locked.write_text("x", encoding="utf-8")
    os.chmod(locked, stat.S_IREAD)

    sk._remove(folder)
    assert not folder.exists()


def test_a_library_that_was_already_there_is_still_checked(tmp_path: Path) -> None:
    """The install-time check only runs on a fresh clone.

    A directory that was already in place skipped it entirely — and these
    files are instructions Claude Code loads and follows, so "something is
    installed" was being read as "the reviewed set is installed". Different
    claims.
    """
    make_library(tmp_path, "socratic")

    assert sk.library_installed(tmp_path) is True
    assert sk.library_verified(tmp_path) is False

    report = sk.status(home=tmp_path, root=ROOT)
    assert report["library_verified"] is False
    assert "not the reviewed commit" in str(report["library_warning"])


def test_a_verified_library_raises_no_warning(tmp_path: Path, monkeypatch) -> None:
    make_library(tmp_path, "socratic")
    monkeypatch.setattr(sk, "library_commit", lambda home=None: sk.LIBRARY_COMMIT)
    # Verification is the commit *and* an untouched worktree — a modified
    # SKILL.md leaves the commit id exactly where it was.
    monkeypatch.setattr(sk, "library_is_clean", lambda home=None: True)

    report = sk.status(home=tmp_path, root=ROOT)
    assert report["library_verified"] is True
    assert report["library_warning"] == ""


def test_an_edited_skill_file_fails_verification(tmp_path: Path) -> None:
    """Matching HEAD is not enough on its own.

    Editing a SKILL.md leaves the commit id exactly where it was, so a
    modified instruction file passed verification unchanged — which is the
    very thing being verified against.
    """
    source = tmp_path / "source"
    (source / "socratic").mkdir(parents=True)
    (source / "socratic" / "SKILL.md").write_text("---\nname: socratic\n---\n", encoding="utf-8")
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "skills"],
    ):
        subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)
    sha = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    sk.install_library(tmp_path, repo=str(source), commit=sha)
    assert sk.library_verified(tmp_path, commit=sha) is True

    edited = sk.library_dir(tmp_path) / "socratic" / "SKILL.md"
    edited.write_text("---\nname: socratic\n---\nnow do something else\n", encoding="utf-8")

    assert sk.library_commit(tmp_path) == sha, "the commit id has not moved"
    assert sk.library_is_clean(tmp_path) is False
    assert sk.library_verified(tmp_path, commit=sha) is False, "but it is not the reviewed set"


def test_an_added_skill_file_also_fails_verification(tmp_path: Path) -> None:
    """Adding a skill is as much a change as editing one."""
    source = tmp_path / "source"
    (source / "socratic").mkdir(parents=True)
    (source / "socratic" / "SKILL.md").write_text("---\nname: socratic\n---\n", encoding="utf-8")
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "skills"],
    ):
        subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)
    sha = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    sk.install_library(tmp_path, repo=str(source), commit=sha)
    smuggled = sk.library_dir(tmp_path) / "smuggled"
    smuggled.mkdir()
    (smuggled / "SKILL.md").write_text("---\nname: smuggled\n---\n", encoding="utf-8")

    assert sk.library_verified(tmp_path, commit=sha) is False


# --------------------------------------------------------------------------
# companions: other people's plugins, used where they are better than ours
# --------------------------------------------------------------------------


def test_companions_are_additive_and_never_part_of_the_guarantee() -> None:
    """Somebody else's plugin cannot be load-bearing.

    ROUTE is deterministic because its skills ship with Forge or with the
    pinned library. A companion is installed separately, updated on someone
    else's schedule, and may be absent. Folding one into ROUTE would turn "the
    same skills every time" into "the same skills every time, unless the user
    happened to install something", which is not a guarantee.
    """
    for stage, companions in sk.COMPANIONS.items():
        routed = sk.skills_for(stage)
        for name in companions:
            assert name not in routed, f"{name} is load-bearing at {stage}"
            assert name in sk.COMPANION_SOURCE, f"{name} has no install line"


def test_a_missing_companion_is_not_a_failure(tmp_path: Path) -> None:
    """Forge works without them, and says so quietly rather than breaking."""
    assert sk.companion_installed("ponytail", home=tmp_path) is False
    assert sk.skills_for("building"), "the stage still has its own skills"


def test_a_companion_is_found_where_a_plugin_actually_puts_it(tmp_path: Path) -> None:
    skill = tmp_path / ".claude" / "plugins" / "ponytail" / "skills" / "ponytail"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: ponytail\n---\n", encoding="utf-8")

    assert sk.companion_installed("ponytail", home=tmp_path) is True
