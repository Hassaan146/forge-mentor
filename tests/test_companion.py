"""Tests for the hook that brings the companion plugin in with Forge.

Routing ponytail at the building stage puts it in a table, and a table is read
by whatever asks the table. If the builder does not ask, nothing happens and
nothing says so, which is the failure this repository has repeated more than any
other: the rule was in the code and the code was not in the path.

So it is a hook, and these are the tests that it stays a quiet one. A companion
is optional by definition (decision 058); a hook that wedges a session to
recommend a plugin has done more harm than the plugin could do good.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import companion
import forge_state as fs

HOOK = Path(__file__).resolve().parents[1] / "scripts" / "companion.py"


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    fs.init(tmp_path)
    return tmp_path


def run(cwd: Path) -> dict:
    """Drive it the way Claude Code does: a subprocess, over stdin."""
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(cwd)}),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout or "{}")


def test_it_says_nothing_outside_a_forge_project(tmp_path: Path) -> None:
    """Forge acts only where it was started. That holds for suggestions too."""
    assert run(tmp_path) == {}


def test_an_installed_companion_is_named_once_a_session(
    project: Path, monkeypatch
) -> None:
    monkeypatch.setattr(companion, "_installed", lambda: True)
    text = companion.message(project)

    assert "ponytail is installed" in text
    assert "security floor" in text, "and which one wins where they disagree"


def test_a_missing_companion_is_reported_every_session(
    project: Path, monkeypatch
) -> None:
    """Required, not suggested (decision 062, superseding 058).

    It was said once per project while it was a preference. A missing
    requirement mentioned once in March is a requirement nobody has by June.
    """
    monkeypatch.setattr(companion, "_installed", lambda: False)

    first = companion.message(project)
    assert "required and it is not installed" in first
    assert "/plugin install ponytail@forge-marketplace" in first

    assert companion.message(project) == first, "and it keeps saying so"


def test_carrying_on_without_it_is_possible_and_leaves_a_trace(
    project: Path, monkeypatch
) -> None:
    """Required is not the same as unescapable.

    Decision 004's shape: blocked by default, one explicit way through, and the
    way through is recorded. A requirement with no override is a product that
    strands somebody at two in the morning over a plugin install.
    """
    monkeypatch.setattr(companion, "_installed", lambda: False)
    text = companion.message(project)

    assert "record_override" in text
    assert "their call" in text


def test_required_names_what_setup_will_not_finish_without() -> None:
    import forge_skills as sk

    assert "ponytail" in sk.REQUIRED
    assert sk.missing_required(home=Path("/nowhere-at-all")) == ["ponytail"]


def test_it_is_silent_where_forge_was_switched_off(project: Path, monkeypatch) -> None:
    monkeypatch.setattr(companion, "_installed", lambda: True)
    (project / fs.FORGE_DIR / "paused.md").write_text("off\n", encoding="utf-8")

    assert companion.message(project) == ""


def test_the_switch_turns_it_off(project: Path, monkeypatch) -> None:
    monkeypatch.setenv("FORGE_NO_COMPANION", "1")
    monkeypatch.setattr(companion, "_installed", lambda: True)

    assert companion.message(project) == ""


def test_it_never_blocks_and_never_crashes(project: Path, monkeypatch) -> None:
    """Silence is the correct behaviour on every failure.

    The whole output is one line of advice about an optional plugin. There is
    no error here worth costing somebody a session over.
    """
    def explode() -> bool:
        raise RuntimeError("no idea")

    monkeypatch.setattr(companion, "_installed", explode)
    with pytest.raises(RuntimeError):
        companion.message(project)  # the helper itself is allowed to raise

    # The hook is not. It swallows everything and prints valid JSON.
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not json at all",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert done.returncode == 0
    assert json.loads(done.stdout or "{}") == {}


def test_the_hook_is_registered_where_it_will_actually_run() -> None:
    """A hook script nothing invokes is a file. This repository has shipped four."""
    hooks = json.loads(
        (Path(__file__).resolve().parents[1] / "hooks" / "hooks.json").read_text(
            encoding="utf-8"
        )
    )
    commands = [
        hook["command"]
        for entry in hooks["hooks"]["SessionStart"]
        for hook in entry["hooks"]
    ]
    assert any("companion.py" in command for command in commands)


def test_the_source_of_the_companion_is_written_down() -> None:
    """Where it comes from is a fact about the product, not a link in a README."""
    import forge_skills as sk

    assert sk.COMPANION_REPOS["ponytail"] == "https://github.com/DietrichGebert/ponytail"
    assert companion.REPO == sk.COMPANION_REPOS["ponytail"]
