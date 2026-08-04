"""Forge Mentor — which skills load at which stage, and who runs the job.

Two layers, and keeping them apart is the point (decision 028):

**Forge's own skills** ship inside the plugin. Four of them, versioned with the
code: the teaching voice, the coding standards, the security floor, and the
explain-back gate. These are the product. Forge's behaviour cannot depend on
what a user happens to have installed, so none of them are drawn from a library.

**The library** is installed on the user's machine at setup — all 438 of it, so
a routed skill is never missing. Forge names skills from it; it never ships them.

**The routing is a table, not a judgement.** Phase 7's bar is that interrogation
steps load the Socratic set and build steps load the coding standards
*deterministically* — decided by the stage, not by a model deciding what feels
relevant. A model that can talk itself out of loading the coding standards is a
model that will, on the step where it matters.

The security floor is in every stage's list on purpose. It is the one skill that
is never conditional, because decision 004's fail-closed rule and the floor's
non-overridable minimums have to hold on the steps nobody was thinking about.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# The user's curated collection (decision 028). Installed whole at setup, so
# every machine running Forge has the same set available.
LIBRARY_REPO = "https://github.com/Hassaan146/claude-skills"
LIBRARY_DIRNAME = "skills"

# Pinned, and checked after the clone.
#
# These files are instructions that Claude Code loads and follows. Fetching a
# mutable default branch means whatever is on `main` the day a user runs setup
# becomes their agent's instructions — a change to that repository silently
# changes the behaviour of every install, with no review in between. Pinning is
# what makes "the same set on every machine" true rather than aspirational.
#
# To move it: pick the new commit deliberately, read what changed, and bump
# this line in a commit of its own.
LIBRARY_COMMIT = "033736c5ab973f55b783cd1251571e176195f949"

# Forge's own, bundled in the plugin. Absence is a packaging bug, not a
# fallback — `missing_bundled` exists so it fails loudly at setup.
BUNDLED = (
    "forge-teaching",  # how a decision is taught and questioned
    "forge-coding-standards",  # how generated code is written
    "forge-security-floor",  # the minimums no decision can override
    "forge-explain-back",  # the gate at the end of a step
)

# Stage -> the skills that load. Ordered: the floor first, so it is never the
# thing that got truncated.
ROUTE: dict[str, tuple[str, ...]] = {
    "interrogation": ("forge-security-floor", "forge-teaching", "socratic", "socrates", "learn"),
    "challenge": ("forge-security-floor", "premortem", "redteam"),
    "planning": ("forge-security-floor", "forge-teaching", "writing-plans"),
    "building": (
        "forge-security-floor",
        "forge-coding-standards",
        "vibe-coding-rules",
        "test-driven-development",
    ),
    "review-fix": (
        "forge-security-floor",
        "forge-coding-standards",
        "systematic-debugging",
        "receiving-code-review",
    ),
    "teach-back": ("forge-security-floor", "forge-explain-back", "socratic"),
    # Runs after every answer, turning what the user said into a record. It
    # loads almost nothing on purpose: this is the one stage that must not
    # interpret, only transcribe, and every extra skill is another voice
    # telling the cheapest model in the pipeline to improve on the user's
    # words. The floor stays because the floor always stays.
    "structuring": ("forge-security-floor",),
}

# Which subagent does a stage's work, and the job name it reports.
STAGE_AGENT: dict[str, str] = {
    "interrogation": "planner",
    "challenge": "planner",
    "planning": "planner",
    "building": "builder",
    "review-fix": "review-fixer",
    "teach-back": "planner",
    # The structurer was declared in AGENTS but nothing dispatched to it, so
    # the agent existed and could never run — every answer would have been
    # recorded by whichever agent happened to be holding the conversation.
    "structuring": "structurer",
}


class SkillError(Exception):
    """A skill or the library could not be found or installed."""


@dataclass(frozen=True)
class Agent:
    """One subagent: what it is for, and the model that runs it.

    The model here is documentation of what the agent file declares. Decision
    029 makes the agent file authoritative, because Claude Code reads it at
    dispatch — a table that disagreed with the file would report one model
    while another did the work.
    """

    name: str
    job: str
    model: str
    does: str


AGENTS: tuple[Agent, ...] = (
    Agent("planner", "planning", "claude-fable-5", "teaches, questions, and compiles phases"),
    Agent("builder", "building", "claude-opus-4-8", "writes the code for a recorded decision"),
    Agent("structurer", "structuring", "claude-haiku-4-5", "turns free text into a decision record"),
    Agent("review-fixer", "fixing", "claude-opus-4-8", "applies what the reviewers found"),
)

AGENTS_BY_NAME: dict[str, Agent] = {agent.name: agent for agent in AGENTS}


def skills_for(stage: str) -> tuple[str, ...]:
    """The skills that load at a stage. Same answer every time, by design."""
    try:
        return ROUTE[stage]
    except KeyError:
        raise SkillError(
            f"No skills are mapped to the stage {stage!r}. "
            f"Known stages: {', '.join(sorted(ROUTE))}."
        ) from None


def agent_for(stage: str) -> Agent:
    """Which subagent runs a stage, and therefore which model."""
    try:
        return AGENTS_BY_NAME[STAGE_AGENT[stage]]
    except KeyError:
        raise SkillError(f"No subagent is mapped to the stage {stage!r}.") from None


# --------------------------------------------------------------------------
# the plugin's own skills
# --------------------------------------------------------------------------


def plugin_root() -> Path:
    """The installed plugin directory — this file's parent's parent."""
    return Path(__file__).resolve().parents[1]


def missing_bundled(root: Path | None = None) -> list[str]:
    """Any of Forge's own skills that did not ship.

    Checked rather than assumed: a skill silently absent degrades Forge into
    ordinary Claude Code wearing a banner, and the coding-standards skill going
    missing would not announce itself in the output — only in the code.
    """
    base = (root or plugin_root()) / "skills"
    return [name for name in BUNDLED if not (base / name / "SKILL.md").is_file()]


def routed_library_skills() -> tuple[str, ...]:
    """Every skill the route names that is not one of Forge's own."""
    named = {skill for skills in ROUTE.values() for skill in skills}
    return tuple(sorted(named - set(BUNDLED)))


# --------------------------------------------------------------------------
# the library — installed once, at setup
# --------------------------------------------------------------------------


def library_dir(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".claude" / LIBRARY_DIRNAME


def library_installed(home: Path | None = None) -> bool:
    """Is there at least one usable skill there?

    **At least one `SKILL.md`, not merely a non-empty directory.** The
    docstring used to promise the second while the code did the first, and the
    two are not the same test: a skills folder holding a stray note or an
    editor's dotfile would have counted as an installed library and setup would
    have skipped the install, leaving nothing routable behind.

    A count is deliberately not the signal either. A user may prune the library
    to what they use; demanding an exact 438 would call that broken.
    """
    folder = library_dir(home)
    return folder.is_dir() and any(folder.glob("*/SKILL.md"))


def missing_routed(home: Path | None = None) -> list[str]:
    """Routed skills the installed library does not actually contain.

    Reported rather than raised. A missing library skill degrades one stage;
    stopping the whole session over it would be worse than saying so.
    """
    folder = library_dir(home)
    if not folder.is_dir():
        return list(routed_library_skills())
    return [
        name for name in routed_library_skills() if not (folder / name / "SKILL.md").is_file()
    ]


def install_library(
    home: Path | None = None,
    repo: str = LIBRARY_REPO,
    commit: str = LIBRARY_COMMIT,
) -> dict[str, object]:
    """Put the library on this machine. Runs once, at setup (decision 028).

    Clones rather than downloading a zip so the user can update it with `git
    pull` and see what changed — the same reasoning as state living in the
    repository (decision 011).
    """
    folder = library_dir(home)
    if library_installed(home):
        return {"installed": True, "already": True, "path": str(folder)}

    # There but holding no skills — a half-finished install, or a folder the
    # user made themselves. `git clone` refuses a non-empty destination, so
    # without this the user would get git's error about a directory that
    # "already exists and is not empty" and no idea which directory or why.
    if folder.exists() and any(folder.iterdir()):
        raise SkillError(
            f"{folder} already exists but holds no skills. Forge will not "
            "overwrite it — move or delete it, then run setup again."
        )

    folder.parent.mkdir(parents=True, exist_ok=True)

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["git", *args], capture_output=True, text=True, timeout=600
            )
        except FileNotFoundError:
            raise SkillError(
                "git is not installed, so the skill library cannot be fetched."
            ) from None
        except subprocess.TimeoutExpired:
            raise SkillError("Fetching the skill library timed out.") from None

    # Fetch the pinned commit specifically rather than cloning a branch. What
    # arrives is instructions the agent will follow, so "whatever is on main
    # today" is not an acceptable answer to what got installed.
    result = git("clone", "--no-checkout", repo, str(folder))
    if result.returncode != 0:
        _remove(folder)
        raise SkillError(f"Could not fetch the skill library: {result.stderr.strip()[:300]}")

    result = git("-C", str(folder), "checkout", "--quiet", commit)
    if result.returncode != 0:
        # Nothing half-installed is left behind. A partial library is worse
        # than none: the routed skills would appear to be missing at random.
        _remove(folder)
        raise SkillError(
            f"The skill library does not contain the pinned commit {commit[:12]}. "
            "Nothing was installed."
        )

    landed = git("-C", str(folder), "rev-parse", "HEAD").stdout.strip()
    if landed != commit:
        _remove(folder)
        raise SkillError(
            f"The skill library checked out {landed[:12]}, not the pinned "
            f"{commit[:12]}. Nothing was installed."
        )

    return {"installed": True, "already": False, "path": str(folder), "commit": landed}


def _remove(folder: Path) -> None:
    """Take a failed install back out, so nothing partial is left to load.

    Git marks the files under `.git/objects` read-only, and on Windows a
    read-only file cannot be deleted — so `ignore_errors=True` quietly left the
    whole directory behind and the cleanup did nothing at all. The handler
    clears the flag and retries.
    """

    def force(func, path, _exc):  # noqa: ANN001 - shutil's callback shape
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            pass  # a file we cannot remove is not worth failing the error path

    if not folder.exists():
        return
    # `onexc` replaced `onerror` in 3.12; the older name still works but warns.
    if sys.version_info >= (3, 12):
        shutil.rmtree(folder, onexc=force)
    else:  # pragma: no cover - the plugin targets 3.12+
        shutil.rmtree(folder, onerror=force)


def status(home: Path | None = None, root: Path | None = None) -> dict[str, object]:
    """What is present and what is not — for setup, and for the tests."""
    bundled_gaps = missing_bundled(root)
    routed_gaps = missing_routed(home)
    return {
        "library_installed": library_installed(home),
        "library_path": str(library_dir(home)),
        "missing_bundled": bundled_gaps,
        "missing_routed": routed_gaps,
        # Forge's own skills going missing is a packaging fault and breaks the
        # product; a library gap only weakens a stage.
        "ready": not bundled_gaps,
    }
