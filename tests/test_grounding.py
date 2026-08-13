"""Tests for catching a reference to something that does not exist.

A model writes `import fastapi_cache` into a project whose requirements name no
such package, or `from .helpers import slugify` when there is no helpers.py, or
"as decided in decision 014" when 014 is about something else. Every one is
confident, plausible and wrong, and none is caught by tests written in the same
turn that invented the reference.

Whether code is *correct* is not decidable here and nothing in this file claims
otherwise. Whether it refers to something that exists is, cheaply, from the
file and the project's own manifests.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import forge_grounding as gr
import forge_state as fs
import grounded

HOOK = Path(__file__).resolve().parents[1] / "scripts" / "grounded.py"


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    fs.init(tmp_path)
    (tmp_path / "requirements.txt").write_text("fastapi>=0.110\nhttpx\n", encoding="utf-8")
    return tmp_path


def write(project: Path, name: str, text: str) -> Path:
    path = project / name
    path.write_text(text, encoding="utf-8")
    return path


# ==========================================================================
# what it catches
# ==========================================================================


def test_an_invented_package_is_caught(project: Path) -> None:
    path = write(project, "app.py", "import fastapi_cache\n")
    claims = gr.check_file(path, project)

    assert [c.name for c in claims] == ["fastapi_cache"]
    assert claims[0].kind == "unknown-import"
    assert "not in this project's dependencies" in claims[0].question()


def test_a_declared_package_is_not_a_finding(project: Path) -> None:
    path = write(project, "app.py", "import fastapi\nfrom httpx import AsyncClient\n")
    assert gr.check_file(path, project) == []


def test_a_submodule_of_a_declared_package_is_fine(project: Path) -> None:
    path = write(project, "app.py", "from fastapi.responses import JSONResponse\n")
    assert gr.check_file(path, project) == []


def test_the_standard_library_is_never_a_finding(project: Path) -> None:
    path = write(project, "app.py", "import json, sqlite3, dataclasses\nimport os.path\n")
    assert gr.check_file(path, project) == []


def test_the_project_s_own_modules_are_not_findings(project: Path) -> None:
    write(project, "helpers.py", "def slugify(text):\n    return text\n")
    path = write(project, "app.py", "import helpers\n")
    assert gr.check_file(path, project) == []


def test_a_package_installed_but_never_declared_is_still_a_finding(
    project: Path,
) -> None:
    """Read from the manifests, not from the environment.

    What happens to be installed on the machine that wrote the file is not what
    the project depends on, and a package that is present by accident is the
    reason this class of bug survives review.
    """
    path = write(project, "app.py", "import pytest\n")
    claims = gr.check_file(path, project)
    assert [c.name for c in claims] == ["pytest"]


def test_a_relative_import_with_no_file_behind_it_is_caught(project: Path) -> None:
    path = write(project, "app.js", "import { slugify } from './helpers.js';\n")
    claims = gr.check_file(path, project)

    assert claims[0].kind == "missing-file"
    assert "no such file" in claims[0].question()


def test_a_relative_import_that_exists_is_fine(project: Path) -> None:
    write(project, "helpers.js", "export const slugify = s => s;\n")
    path = write(project, "app.js", "import { slugify } from './helpers.js';\n")
    assert gr.check_file(path, project) == []


def test_node_builtins_and_declared_packages_are_fine(project: Path) -> None:
    (project / "package.json").write_text(
        json.dumps({"dependencies": {"express": "^4"}}), encoding="utf-8"
    )
    path = write(project, "server.js", "const fs = require('fs');\nimport express from 'express';\n")
    assert gr.check_file(path, project) == []


def test_a_citation_of_a_decision_that_does_not_exist_is_caught(project: Path) -> None:
    """The most convincing sentence a model can write, and free to verify.

    A wrong citation is worse than none: it borrows the authority of a record
    nobody will open.
    """
    forge = project / fs.FORGE_DIR
    asked = fs.ask(forge, "which database")
    fs.answer(forge, asked.id, "# SQLite\n\n## Why\n\none file\n")

    claims = gr.check_decisions("As we settled in decision 014, this uses Postgres.", forge)
    assert claims[0].kind == "unrecorded-decision"
    assert claims[0].name == "014"

    assert gr.check_decisions("Decision 001 says SQLite.", forge) == []


def test_a_file_that_will_not_parse_is_not_a_crash(project: Path) -> None:
    path = write(project, "broken.py", "def (:\n")
    assert gr.check_file(path, project) == []


# ==========================================================================
# the hook
# ==========================================================================


def run_hook(cwd: Path, target: Path) -> dict:
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Write",
                "cwd": str(cwd),
                "tool_input": {"file_path": str(target)},
            }
        ),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout or "{}")


def test_the_hook_hands_the_question_over_rather_than_fixing_it(project: Path) -> None:
    path = write(project, "app.py", "import fastapi_cache\n")
    out = run_hook(project, path)

    context = out["hookSpecificOutput"]["additionalContext"]
    assert "fastapi_cache" in context
    assert "Stop and ask the user" in context
    assert "do not assume it is a package to install" in context


def test_the_hook_is_silent_when_everything_resolves(project: Path) -> None:
    path = write(project, "app.py", "import fastapi\n")
    assert run_hook(project, path) == {}


def test_the_hook_says_nothing_outside_a_forge_project(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("import whatever_this_is\n", encoding="utf-8")
    assert run_hook(tmp_path, target) == {}


def test_the_hook_stands_down_where_forge_is_paused(project: Path) -> None:
    (project / fs.FORGE_DIR / "paused.md").write_text("off\n", encoding="utf-8")
    path = write(project, "app.py", "import fastapi_cache\n")
    assert run_hook(project, path) == {}


def test_the_switch_turns_it_off(project: Path, monkeypatch) -> None:
    path = write(project, "app.py", "import fastapi_cache\n")
    monkeypatch.setenv("FORGE_NO_GROUNDING", "1")
    assert grounded.message(
        {"cwd": str(project), "tool_input": {"file_path": str(path)}}
    ) == ""


def test_the_hook_never_crashes_on_nonsense() -> None:
    done = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0
    assert json.loads(done.stdout or "{}") == {}


def test_the_hook_is_registered_where_it_will_run() -> None:
    hooks = json.loads(
        (Path(__file__).resolve().parents[1] / "hooks" / "hooks.json").read_text(
            encoding="utf-8"
        )
    )
    commands = [
        hook["command"]
        for entry in hooks["hooks"]["PostToolUse"]
        for hook in entry["hooks"]
    ]
    assert any("grounded.py" in command for command in commands)
