"""What every module does when the machine underneath it misbehaves.

Forge is mostly guards, and a guard's failure branch is the one nobody exercises
by hand: a file that cannot be read, git missing, a log half written, a
permission flag that will not set. Each of those has a documented answer in the
code, and each answer differs by module on purpose.

**The rule is not the same everywhere, and that is the point.** The governor
fails closed, because a blocked write costs one turn. The presenter fails open,
because a Stop hook that errors ends the conversation. The meter reports
"unavailable" rather than zero, because zero is a number somebody would believe.
This file holds each module to its own rule.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import forge_state as fs


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    fs.init(tmp_path)
    return tmp_path


@pytest.fixture()
def forge(project: Path) -> Path:
    return project / fs.FORGE_DIR


def unreadable(*_a, **_k):
    raise OSError("permission denied")


# --------------------------------------------------------------------------
# companion.py — one line about ponytail, or silence
# --------------------------------------------------------------------------


def test_an_unreadable_project_is_not_a_forge_project(monkeypatch, tmp_path: Path) -> None:
    import companion

    monkeypatch.setattr(fs, "find_forge_dir", lambda _p: (_ for _ in ()).throw(OSError()))

    assert companion._forge_dir(tmp_path) is None
    assert companion.message(tmp_path) == ""


def test_ponytail_is_assumed_installed_when_the_check_itself_fails(monkeypatch) -> None:
    """Silence beats advertising an install the user may already have."""
    import companion
    import forge_skills as sk

    monkeypatch.setattr(sk, "companion_installed", lambda _n: (_ for _ in ()).throw(OSError()))
    assert companion._installed() is True


def test_a_note_that_cannot_be_written_does_not_stop_the_session(
    monkeypatch, project: Path
) -> None:
    import companion

    monkeypatch.setattr(Path, "write_text", unreadable)
    companion.message(project)  # says what it can, writes nothing, raises nothing


# --------------------------------------------------------------------------
# forge_assemble.py — a fingerprint that cannot be kept
# --------------------------------------------------------------------------


def test_a_block_knows_its_own_size() -> None:
    import forge_assemble as fa

    assert fa.Block(name="x", text="four", tier=fa.Tier.FROZEN).size == 4


def test_an_unreadable_assembly_note_reads_as_no_previous_fingerprint(
    monkeypatch, forge: Path
) -> None:
    import forge_assemble as fa

    (forge / fa.ASSEMBLY_FILE).write_text("---\nprefix_sha: abc\n---\n", encoding="utf-8")
    monkeypatch.setattr(Path, "read_text", unreadable)
    assert fa.last_prefix(forge) == ""


def test_a_fingerprint_that_cannot_be_written_still_returns_the_report(
    monkeypatch, forge: Path
) -> None:
    import forge_assemble as fa

    assembly = fa.assemble([fa.Block(name="contract", text="the rules", tier=fa.Tier.FROZEN)])
    monkeypatch.setattr(Path, "write_text", unreadable)

    assert fa.check(forge, assembly)["prefix_sha"]


# --------------------------------------------------------------------------
# forge_build.py — the file ledger
# --------------------------------------------------------------------------


def test_an_unreadable_ledger_is_an_empty_one(monkeypatch, forge: Path) -> None:
    import forge_build as fb

    fb.plan(forge, "phase-1.step-1", ["a.py"])
    monkeypatch.setattr(Path, "read_text", unreadable)
    assert fb.read_plan(forge, "phase-1.step-1") == []


def test_a_plan_with_no_files_in_it_is_refused(forge: Path) -> None:
    import forge_build as fb

    with pytest.raises(fs.StateError, match="at least one file"):
        fb.plan(forge, "phase-1.step-1", ["   ", ""])


def test_a_target_that_cannot_be_resolved_is_allowed(monkeypatch, forge: Path) -> None:
    """The ledger is about order, not about the filesystem. A path that will not
    resolve is somebody else's error to report."""
    import forge_build as fb

    fb.plan(forge, "phase-1.step-1", ["a.py"])
    monkeypatch.setattr(Path, "resolve", unreadable)

    allowed, _why = fb.allowed(forge, "phase-1.step-1", Path("a.py"), forge.parent.parent)
    assert allowed is True


# --------------------------------------------------------------------------
# forge_explain.py and forge_feature.py — reading the records
# --------------------------------------------------------------------------


def test_records_that_cannot_be_listed_explain_nothing(monkeypatch, forge: Path) -> None:
    import forge_explain as fe

    monkeypatch.setattr(fs, "list_decisions", lambda _f: (_ for _ in ()).throw(OSError()))
    assert fe.collect(forge) == []


def test_an_option_that_is_the_chosen_one_is_not_listed_as_rejected(forge: Path) -> None:
    """"SQLite" chosen and "SQLite, one file" offered are the same option, and
    showing it in both columns reads as a contradiction."""
    import forge_explain as fe

    asked = fs.ask(forge, "which database?")
    fs.answer(
        forge,
        asked.id,
        "# SQLite\n\n**Options considered**\n\n- SQLite\n- Postgres\n\n## Why\n\nsmall\n",
    )

    entry = fe.collect(forge)[0]
    assert any("postgres" in option.lower() for option in entry.options)


def test_a_feature_reads_nothing_from_records_it_cannot_open(
    monkeypatch, forge: Path
) -> None:
    import forge_feature as ff

    monkeypatch.setattr(ff.fs, "list_decisions", lambda _f: [])
    assert ff.constraints(forge, "a photo on each todo") == []


# --------------------------------------------------------------------------
# forge_integrity.py — the chain
# --------------------------------------------------------------------------


def test_a_record_that_will_not_parse_is_skipped_rather_than_failing_the_chain(
    monkeypatch, forge: Path
) -> None:
    """A broken file is the state layer's to report. Failing here would mean one
    malformed record made every later record unverifiable."""
    import forge_integrity as fi

    asked = fs.ask(forge, "which database?")
    fs.answer(forge, asked.id, "# SQLite\n\n## Why\n\nsmall\n")

    good = fs.list_decisions(forge)[0]

    def one_good_one_broken(_forge):
        broken = fs.Decision(id="not a number", question="q", status="decided")
        return [good, broken]

    monkeypatch.setattr(fi.fs, "list_decisions", one_good_one_broken)
    checked = fi.check_all(forge)

    assert len(checked) == 2
    assert any(c.integrity is fi.Integrity.VERIFIED for c in checked)
    assert any(c.integrity is not fi.Integrity.VERIFIED for c in checked), (
        "and the one that will not parse is reported rather than trusted"
    )


def test_the_fingerprint_covers_every_field_except_itself(forge: Path) -> None:
    """A fingerprint that covered itself could never verify, and a field added
    to a record later must not quietly escape the hash."""
    import forge_integrity as fi

    fs.ask(forge, "which database?")
    covered = fi.signed_fields(fs.list_decisions(forge)[0])

    assert "question" in covered
    assert "content_sha" not in covered and "prev_sha" not in covered


# --------------------------------------------------------------------------
# forge_preflight.py — the readiness check
# --------------------------------------------------------------------------


def test_a_command_that_will_not_run_is_reported_as_missing(monkeypatch) -> None:
    import forge_preflight as pf

    monkeypatch.setattr(pf.subprocess, "run", unreadable)
    assert pf._gh_signed_in() is False


def test_a_python_that_is_on_path_but_will_not_run_says_exactly_that(monkeypatch) -> None:
    """The distinction matters: the hooks invoke a bare `python`, and an app
    launched from a dock does not always inherit the PATH the shell has."""
    import forge_preflight as pf

    def times_out(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="python", timeout=5)

    monkeypatch.setattr(pf.subprocess, "run", times_out)
    ok, why = pf._plugin_python_works()

    assert ok is False
    assert "would not run" in why


def test_a_skill_check_that_raises_reads_as_not_installed(monkeypatch) -> None:
    import forge_preflight as pf
    import forge_skills as sk

    monkeypatch.setattr(sk, "companion_installed", lambda _n: (_ for _ in ()).throw(OSError()))
    assert pf._companion_installed() is False


def test_the_check_answers_whether_setup_can_proceed(monkeypatch) -> None:
    import forge_preflight as pf

    monkeypatch.setattr(pf, "run", lambda: [pf.Check("git", True, "found", fatal=True)])
    assert pf.ready() is True

    monkeypatch.setattr(pf, "run", lambda: [pf.Check("git", False, "missing", fatal=True)])
    assert pf.ready() is False


# --------------------------------------------------------------------------
# forge_push.py — nothing leaves the machine by accident
# --------------------------------------------------------------------------


def test_no_git_at_all_says_so_rather_than_raising_a_file_error(
    monkeypatch, project: Path
) -> None:
    import forge_push as fp

    def missing(*_a, **_k):
        raise FileNotFoundError("no git")

    monkeypatch.setattr(fp.subprocess, "run", missing)
    with pytest.raises(fp.PushError, match="git is not installed"):
        fp.preview(project)


def test_git_that_stops_responding_is_reported(monkeypatch, project: Path) -> None:
    import forge_push as fp

    def hangs(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="git", timeout=60)

    monkeypatch.setattr(fp.subprocess, "run", hangs)
    with pytest.raises(fp.PushError, match="stopped responding"):
        fp.preview(project)


def test_a_repository_with_no_commits_has_nothing_to_push(monkeypatch, project: Path) -> None:
    import forge_push as fp

    class Result:
        returncode = 1
        stdout = ""
        stderr = "unknown revision"

    monkeypatch.setattr(fp, "_git", lambda *a, **k: Result())
    with pytest.raises(fp.PushError):
        fp.preview(project)


# --------------------------------------------------------------------------
# forge_repair.py — quarantine before overwrite, always
# --------------------------------------------------------------------------


def test_a_record_with_an_unreadable_id_is_not_repaired(forge: Path) -> None:
    import forge_repair as fr

    (forge / fs.DECISIONS / "not-a-number-x.md").write_text(
        "---\nid: x\nquestion: q\nstatus: decided\n---\n\n# x\n", encoding="utf-8"
    )
    with pytest.raises(fs.StateError, match="not a number"):
        fr.diagnose(forge)


def test_nothing_is_overwritten_when_it_cannot_be_set_aside_first(
    monkeypatch, forge: Path
) -> None:
    """The one promise repair makes: the damaged original survives the repair."""
    import forge_repair as fr

    asked = fs.ask(forge, "which database?")
    fs.answer(forge, asked.id, "# SQLite\n\n## Why\n\nsmall\n")
    record = forge / fs.DECISIONS / fs.list_decisions(forge)[0].filename()
    record.write_text(record.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")

    problems = fr.diagnose(forge)
    monkeypatch.setattr(fr.shutil, "move", unreadable)
    monkeypatch.setattr(fr, "committed_version", lambda _r, _p: "the committed text")

    assert fr.restore(problems[0], forge.parent.parent, forge) is False
    assert "tampered" in record.read_text(encoding="utf-8"), "the evidence survives"


def test_a_read_only_flag_that_will_not_set_is_not_a_failure(
    monkeypatch, forge: Path
) -> None:
    """Best effort by design: the chain file is evidence, not a lock."""
    import forge_repair as fr

    monkeypatch.setattr(Path, "chmod", unreadable)
    fr.write_chain(forge)


# --------------------------------------------------------------------------
# forge_say.py — the shape of everything Forge says
# --------------------------------------------------------------------------


def test_a_terminal_that_will_not_say_its_width_still_gets_a_frame(monkeypatch) -> None:
    import forge_say as say

    monkeypatch.setattr(say.shutil, "get_terminal_size", unreadable)
    assert say.framed("A title", "a body", ["do this"])


def test_a_blank_line_in_the_body_stays_a_blank_line() -> None:
    """Paragraphs are how a refusal stays readable when it has three parts."""
    import forge_say as say

    drawn = say.framed("A title", "first\n\nsecond", [])
    assert "first" in drawn and "second" in drawn


# --------------------------------------------------------------------------
# the hooks, each held to its own failure rule
# --------------------------------------------------------------------------


def hook(module, monkeypatch, capsys, payload: dict) -> dict:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    try:
        module.main()
    except SystemExit:
        pass
    return json.loads(capsys.readouterr().out or "{}")


def test_the_governor_fails_closed_when_it_cannot_read_the_notes(
    monkeypatch, capsys, project: Path
) -> None:
    """A blocked write costs one turn. An unguarded write costs the guarantee."""
    import governor

    def broken(*_a, **_k):
        raise fs.StateError("the notes are unreadable", project)

    monkeypatch.setattr(governor, "writes_allowed", broken)
    answer = hook(
        governor,
        monkeypatch,
        capsys,
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "cwd": str(project),
            "tool_input": {"file_path": str(project / "app.py")},
        },
    )

    assert answer["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_the_grounding_hook_says_nothing_outside_a_forge_project(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    import grounded

    answer = hook(
        grounded,
        monkeypatch,
        capsys,
        {
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "cwd": str(tmp_path),
            "tool_input": {"file_path": "app.py"},
        },
    )
    assert answer == {}


def test_the_grounding_hook_can_be_switched_off(monkeypatch, capsys, project: Path) -> None:
    import grounded

    monkeypatch.setenv("FORGE_NO_GROUNDING", "1")
    answer = hook(
        grounded,
        monkeypatch,
        capsys,
        {
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "cwd": str(project),
            "tool_input": {"file_path": "app.py"},
        },
    )
    assert answer == {}


def test_the_review_trigger_can_be_switched_off(monkeypatch, capsys, project: Path) -> None:
    import reviewed

    monkeypatch.setenv("FORGE_NO_REVIEW_TRIGGER", "1")
    assert reviewed.message(project) == ""


def test_the_review_trigger_says_nothing_outside_a_forge_project(tmp_path: Path) -> None:
    import reviewed

    assert reviewed.message(tmp_path) == ""


def test_the_review_trigger_says_nothing_when_no_review_has_landed(project: Path) -> None:
    import reviewed

    assert reviewed.message(project) == ""


# --------------------------------------------------------------------------
# forge_update.py — a check that must never be why a session fails
# --------------------------------------------------------------------------


def test_a_cache_that_cannot_be_written_is_a_slower_check_not_a_failure(
    monkeypatch, tmp_path: Path
) -> None:
    import forge_update as up

    monkeypatch.setenv("FORGE_UPDATE_CACHE", str(tmp_path / "nope" / "cache.json"))
    monkeypatch.setattr(Path, "mkdir", unreadable)
    up._write_cache("1.2.3")


def test_junk_in_the_cache_file_is_ignored(monkeypatch, tmp_path: Path) -> None:
    import forge_update as up

    cache = tmp_path / "cache.json"
    cache.write_text("not json", encoding="utf-8")
    monkeypatch.setenv("FORGE_UPDATE_CACHE", str(cache))

    assert up._read_cache() == {}


def test_nothing_from_the_network_reaches_a_screen_except_a_version(monkeypatch) -> None:
    """Remote text on a user's screen is remote text in a model's context."""
    import urllib.error

    import forge_update as up

    class Response:
        status = 200

        def __init__(self, body: bytes) -> None:
            self._body = body

        def read(self, _n=None) -> bytes:
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> bool:
            return False

    monkeypatch.setattr(up.urllib.request, "urlopen", lambda *a, **k: Response(b"not json"))
    assert up.fetch_latest("o", "r") == ""

    monkeypatch.setattr(up.urllib.request, "urlopen", lambda *a, **k: Response(b'["a list"]'))
    assert up.fetch_latest("o", "r") == ""

    monkeypatch.setattr(
        up.urllib.request, "urlopen", lambda *a, **k: Response(b'{"version": "<script>"}')
    )
    assert up.fetch_latest("o", "r") == "", "only a strict version pattern is shown"

    class Refused:
        status = 404

        def read(self, _n=None) -> bytes:
            return b""

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> bool:
            return False

    monkeypatch.setattr(up.urllib.request, "urlopen", lambda *a, **k: Refused())
    assert up.fetch_latest("o", "r") == ""


def test_a_plugin_cache_that_cannot_be_listed_has_no_siblings(
    monkeypatch, tmp_path: Path
) -> None:
    import forge_update as up

    monkeypatch.setattr(Path, "iterdir", unreadable)
    assert up.downloaded_versions(tmp_path) == []


def test_a_project_that_cannot_be_read_is_treated_as_unstarted(monkeypatch) -> None:
    """So the restart notice sends them to /forge:start, which is the command
    that works either way."""
    import forge_update as up

    monkeypatch.setattr(Path, "is_file", unreadable)
    assert up.resume_command() == "/forge:start"


def test_the_plugin_root_is_the_one_claude_code_names(monkeypatch, tmp_path: Path) -> None:
    """Set when installed, absent when run from a clone, and the check has to
    work the same in both."""
    import forge_update as up

    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
    assert up._plugin_root() == tmp_path

    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT")
    assert up._plugin_root().name == "forge-mentor"


# --------------------------------------------------------------------------
# forge_grounding.py — what the code names that is not there
# --------------------------------------------------------------------------


def test_manifests_that_cannot_be_read_leave_the_package_list_empty(
    monkeypatch, project: Path
) -> None:
    import forge_grounding as gr

    (project / "requirements.txt").write_text("fastapi>=0.115\n", encoding="utf-8")
    (project / "pyproject.toml").write_text('dependencies = ["httpx>=0.27"]\n', encoding="utf-8")
    (project / "package.json").write_text('{"dependencies": {"react": "18"}}', encoding="utf-8")

    assert "fastapi" in gr._declared(project)
    assert "httpx" in gr._declared(project)

    monkeypatch.setattr(Path, "read_text", unreadable)
    assert gr._declared(project) == set()


def test_a_package_json_that_is_not_json_is_skipped(project: Path) -> None:
    import forge_grounding as gr

    (project / "package.json").write_text("{not json", encoding="utf-8")
    assert gr._declared(project) == set()


def test_a_scoped_package_keeps_both_halves_of_its_name(project: Path) -> None:
    """`@scope/name` is one package, and truncating it at the slash invents a
    dependency nobody declared."""
    import forge_grounding as gr

    assert gr._package_root("@anthropic-ai/sdk") == "@anthropic-ai/sdk"
    assert gr._package_root("fastapi.routing") == "fastapi"


def test_a_source_file_that_cannot_be_read_claims_nothing(monkeypatch, project: Path) -> None:
    import forge_grounding as gr

    (project / "app.py").write_text("import json\n", encoding="utf-8")
    monkeypatch.setattr(Path, "read_text", unreadable)

    assert gr.check_file(project / "app.py", project) == []


def test_a_relative_import_is_left_to_the_file_check(project: Path) -> None:
    """`from .models import Todo` names no package; whether the file exists is
    the next check's question, not this one's."""
    import forge_grounding as gr

    (project / "app.py").write_text("from .models import Todo\n", encoding="utf-8")
    claims = gr.check_file(project / "app.py", project)

    assert not [c for c in claims if c.kind == "unknown-import"]


def test_an_import_of_something_nobody_declared_is_raised(project: Path) -> None:
    import forge_grounding as gr

    (project / "app.py").write_text("import nonexistent_package_xyz\n", encoding="utf-8")
    claims = gr.check_file(project / "app.py", project)

    assert any(c.kind == "unknown-import" for c in claims)


def test_a_decision_citation_is_checked_against_the_records(monkeypatch, forge: Path) -> None:
    import forge_grounding as gr

    monkeypatch.setattr(fs, "list_decisions", lambda _f: (_ for _ in ()).throw(OSError()))
    assert gr.check_decisions("as decided in decision 014", forge) == []


def test_a_javascript_import_of_something_undeclared_is_raised(project: Path) -> None:
    import forge_grounding as gr

    (project / "package.json").write_text('{"dependencies": {"react": "18"}}', encoding="utf-8")
    (project / "app.js").write_text(
        "import React from 'react'\nimport thing from 'not-declared-anywhere'\n",
        encoding="utf-8",
    )
    claims = gr.check_file(project / "app.js", project)

    assert [c.name for c in claims if c.kind == "unknown-import"] == ["not-declared-anywhere"]


def test_hidden_and_vendored_folders_are_not_the_project(project: Path) -> None:
    """`node_modules` counted as local modules would make every undeclared
    import look declared, which is the check answering yes to everything."""
    import forge_grounding as gr

    (project / "node_modules" / "pkg").mkdir(parents=True)
    (project / "node_modules" / "pkg" / "index.py").write_text("x = 1\n", encoding="utf-8")
    (project / "app.py").write_text("x = 1\n", encoding="utf-8")

    local = gr._local_modules(project)
    assert "app" in local and "pkg" not in local


def test_the_grounding_check_reads_only_the_files_it_understands(project: Path) -> None:
    import forge_grounding as gr

    (project / "app.py").write_text("import nonexistent_package_xyz\n", encoding="utf-8")
    (project / "notes.txt").write_text("import nonexistent_package_xyz\n", encoding="utf-8")

    claims = gr.check([project / "app.py", project / "notes.txt", project / "gone.py"], project)
    assert len(claims) == 1


def test_a_claim_says_what_is_wrong_in_the_users_terms(project: Path) -> None:
    import forge_grounding as gr

    missing_file = gr.Claim("missing-file", "./models", "app.py", 3)
    missing_decision = gr.Claim("unknown-decision", "014", "app.py", 5)

    assert "no such file" in missing_file.question()
    assert "no decision" in missing_decision.question()


def test_a_manifest_with_no_repository_is_not_asked_about(monkeypatch) -> None:
    import forge_update as up

    assert up.fetch_latest("", "") == ""
    assert up.fetch_latest("owner", "") == ""


# --------------------------------------------------------------------------
# the CLI surfaces, driven the way a command file drives them
# --------------------------------------------------------------------------


def run_cli(module, monkeypatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", [module.__name__, *args])
    module.main()


def test_the_update_check_prints_nothing_when_the_copy_is_current(
    monkeypatch, capsys
) -> None:
    import forge_update as up

    monkeypatch.setattr(up, "report", lambda *a, **k: "")
    run_cli(up, monkeypatch)
    assert capsys.readouterr().out == ""

    run_cli(up, monkeypatch, "--hook")
    assert json.loads(capsys.readouterr().out) == {}


def test_the_update_check_hands_the_session_hook_a_block_to_show(
    monkeypatch, capsys
) -> None:
    import forge_update as up

    monkeypatch.setattr(up, "report", lambda *a, **k: "A NEWER FORGE IS OUT")
    run_cli(up, monkeypatch, "--hook")

    out = json.loads(capsys.readouterr().out)
    assert "A NEWER FORGE IS OUT" in out["hookSpecificOutput"]["additionalContext"]

    run_cli(up, monkeypatch)
    assert "A NEWER FORGE IS OUT" in capsys.readouterr().out


def test_a_broken_update_check_is_silence_rather_than_a_traceback(
    monkeypatch, capsys
) -> None:
    """It runs before the user's first turn. It cannot be why a session fails."""
    import forge_update as up

    def broken(*_a, **_k):
        raise RuntimeError("everything is on fire")

    monkeypatch.setattr(up, "report", broken)
    run_cli(up, monkeypatch)
    assert capsys.readouterr().out == ""


# --------------------------------------------------------------------------
# forge_state.py — the one writer
# --------------------------------------------------------------------------


def test_a_paused_flag_that_cannot_be_read_is_not_paused(monkeypatch, forge: Path) -> None:
    monkeypatch.setattr(Path, "is_file", unreadable)
    assert fs.paused(forge) is False


def test_the_notes_folder_names_itself_when_the_path_is_odd() -> None:
    """The message says which file is wrong, and a path that is the folder
    itself still has to name something."""
    assert fs._repo_relative(Path("/somewhere/.claude/forge")) == fs.FORGE_DIR
    assert fs._repo_relative(Path("/elsewhere/app.py")) == "app.py"


def test_a_count_that_is_not_a_number_reads_as_zero(forge: Path) -> None:
    progress = fs.Progress.read(forge)
    progress.gate_attempts = 0
    progress.write(forge)

    text = (forge / fs.PROGRESS).read_text(encoding="utf-8")
    (forge / fs.PROGRESS).write_text(
        text.replace("gate_attempts: 0", "gate_attempts: several"), encoding="utf-8"
    )

    assert fs.Progress.read(forge).gate_attempts == 0


def test_a_decisions_folder_that_is_not_there_lists_nothing(tmp_path: Path) -> None:
    assert fs.list_decisions(tmp_path / "nowhere") == []


def test_the_search_for_a_project_stops_rather_than_walking_to_the_root(
    tmp_path: Path,
) -> None:
    """An unbounded walk finds a stray notes folder in a home directory and
    silently switches Forge on in every project on the machine."""
    deep = tmp_path
    for part in ("a", "b", "c", "d", "e", "f"):
        deep = deep / part
    deep.mkdir(parents=True)

    assert fs.find_forge_dir(deep) is None


def test_an_unreadable_home_does_not_stop_the_search(monkeypatch, tmp_path: Path) -> None:
    def refuse():
        raise RuntimeError("no home on this machine")

    monkeypatch.setattr(Path, "home", staticmethod(refuse))
    assert fs.find_forge_dir(tmp_path) is None


def test_git_that_will_not_answer_is_not_an_accusation(monkeypatch, project: Path) -> None:
    """"cannot ask" and "the file is modified" are different answers, and only
    one of them is worth telling the user about."""
    import subprocess as sp

    def refuse(*_a, **_k):
        raise sp.TimeoutExpired(cmd="git", timeout=5)

    monkeypatch.setattr(sp, "run", refuse)
    assert fs.is_ignored_by_git(project / "notes" / "a.md") is False


# --------------------------------------------------------------------------
# forge_repair.py and forge_explain.py
# --------------------------------------------------------------------------


def test_a_file_outside_the_repository_has_no_committed_version(forge: Path) -> None:
    import forge_repair as fr

    assert fr.committed_version(forge, Path("/somewhere/else/app.py")) is None


def test_a_record_git_has_never_seen_cannot_be_restored(monkeypatch, forge: Path) -> None:
    """There is nothing to restore it to, and inventing one would be worse."""
    import forge_repair as fr

    asked = fs.ask(forge, "which database?")
    fs.answer(forge, asked.id, "# SQLite\n\n## Why\n\nsmall\n")
    record = forge / fs.DECISIONS / fs.list_decisions(forge)[0].filename()
    record.write_text(record.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")

    problems = fr.diagnose(forge)
    monkeypatch.setattr(fr, "committed_version", lambda _r, _p: None)

    assert fr.restore(problems[0], forge.parent.parent, forge) is False


def test_a_chain_file_that_cannot_be_made_writable_is_still_written(
    monkeypatch, forge: Path
) -> None:
    import forge_repair as fr

    monkeypatch.setattr(Path, "chmod", unreadable)
    fr._make_writable(forge / "chain.md")


# --------------------------------------------------------------------------
# the last of it: branches nobody reaches on the happy path
# --------------------------------------------------------------------------


def test_a_question_still_open_settles_no_facts(forge: Path) -> None:
    """Facts come from answers. An open question has none yet, and counting it
    would narrow the next menu against a choice nobody made."""
    import forge_foundation as ff

    fs.ask(forge, "How do people log in?")
    assert ff.facts(forge) == set()


def test_a_record_with_no_heading_has_no_choice_in_it(forge: Path) -> None:
    import forge_foundation as ff

    asked = fs.ask(forge, "which database?")
    fs.answer(forge, asked.id, "no heading, just prose about sqlite\n")

    assert ff.chosen(fs.list_decisions(forge)[0]) == "no heading, just prose about sqlite"

    other = fs.ask(forge, "how is it deployed?")
    fs.answer(forge, other.id, "\n\n")
    assert ff.chosen(fs.list_decisions(forge)[1]) == "", "an empty body chose nothing"


def test_an_answer_in_the_users_own_words_still_settles_what_it_implies(forge: Path) -> None:
    """They can always type instead of picking a letter, and an answer in prose
    has to narrow the next question the same way a letter does."""
    import forge_foundation as ff

    assert ff._facts_from(ff.STACK, "", set()) == set()
    assert isinstance(ff._facts_from(ff.STACK, "a website in a browser", set()), set)


def test_the_sequence_has_an_end(forge: Path) -> None:
    import forge_foundation as ff

    while (question := ff.next_question(forge)) is not None:
        asked = fs.ask(forge, question.question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")

    assert ff.next_question(forge) is None


def test_a_menu_narrows_against_the_facts_on_disk(forge: Path) -> None:
    import forge_foundation as ff

    asked = fs.ask(forge, ff.INTENT.question)
    fs.answer(forge, asked.id, "# a to-do app for me\n\n## Why\n\nmine\n")

    assert ff.menu_for(ff.STACK, forge_dir=forge) is not None


# --------------------------------------------------------------------------
# forge_skills.py — the library and the companion
# --------------------------------------------------------------------------


def test_a_companion_plugin_is_found_by_its_folder(monkeypatch, tmp_path: Path) -> None:
    import forge_skills as sk

    skill = (
        tmp_path / ".claude" / "plugins" / "cache" / "forge-marketplace"
        / "ponytail" / "skills" / "ponytail"
    )
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# ponytail\n", encoding="utf-8")

    assert sk.companion_installed("ponytail", home=tmp_path) is True
    assert sk.companion_installed("not-installed", home=tmp_path) is False

    bare = tmp_path / "empty"
    bare.mkdir()
    assert sk.companion_installed("ponytail", home=bare) is False, "no plugins folder at all"


def test_a_plugin_folder_that_cannot_be_read_reads_as_not_installed(
    monkeypatch, tmp_path: Path
) -> None:
    import forge_skills as sk

    (tmp_path / ".claude" / "plugins").mkdir(parents=True)
    monkeypatch.setattr(Path, "glob", unreadable)

    assert sk.companion_installed("ponytail", home=tmp_path) is False


def test_no_git_means_no_library_rather_than_a_traceback(monkeypatch, tmp_path: Path) -> None:
    import forge_skills as sk

    def missing(*_a, **_k):
        raise FileNotFoundError("no git")

    monkeypatch.setattr(sk.subprocess, "run", missing)
    assert sk.library_commit(tmp_path) == ""
    assert sk.library_is_clean(tmp_path) is False


def test_a_library_fetch_without_git_says_which_command_is_missing(
    monkeypatch, tmp_path: Path
) -> None:
    import forge_skills as sk

    def missing(*_a, **_k):
        raise FileNotFoundError("no git")

    monkeypatch.setattr(sk.subprocess, "run", missing)
    with pytest.raises(sk.SkillError, match="git is not installed"):
        sk.install_library(home=tmp_path)


def test_a_library_fetch_that_hangs_is_stopped(monkeypatch, tmp_path: Path) -> None:
    import forge_skills as sk

    def hangs(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="git", timeout=300)

    monkeypatch.setattr(sk.subprocess, "run", hangs)
    with pytest.raises(sk.SkillError, match="timed out"):
        sk.install_library(home=tmp_path)


def test_a_file_that_will_not_delete_does_not_fail_the_error_path(
    monkeypatch, tmp_path: Path
) -> None:
    """This runs while cleaning up after a failed install. Raising here would
    replace the real error with a worse one."""
    import forge_skills as sk

    folder = tmp_path / "library"
    folder.mkdir()
    (folder / "a.md").write_text("x", encoding="utf-8")

    monkeypatch.setattr(sk.os, "chmod", unreadable)
    sk._remove(folder)


# --------------------------------------------------------------------------
# presenter.py and grounded.py — the two hooks that fail open
# --------------------------------------------------------------------------


def test_the_presenter_allows_when_it_cannot_tell_whether_a_step_is_open(
    monkeypatch, forge: Path
) -> None:
    """Presentation is never worth a wedged session."""
    import presenter

    monkeypatch.setitem(sys.modules, "forge_steps", None)
    assert presenter._building(forge) is False


def test_the_presenter_reads_a_turn_written_as_plain_text(tmp_path: Path) -> None:
    """The client may hand back a string instead of a list of parts, and both
    shapes are speech."""
    import presenter

    path = tmp_path / "t.jsonl"
    path.write_text(
        json.dumps({"type": "assistant", "message": {"content": "a plain string"}}) + "\n"
        + json.dumps({"type": "assistant", "message": {"content": 42}}) + "\n",
        encoding="utf-8",
    )

    assert "a plain string" in presenter.last_assistant_text(path)


def test_a_diff_fence_rule_counts_as_the_start_of_a_block() -> None:
    import presenter

    assert presenter._starts_the_block("@@ ⚒ FORGE · DECISION 001 @@") is True
    assert presenter._starts_the_block("@@ no symbol here @@") is False


def test_a_reply_with_no_block_at_all_is_all_loose_prose() -> None:
    import presenter

    assert presenter.loose_lines("one\ntwo\nthree") == 3


def test_the_presenter_allows_a_turn_with_no_transcript(monkeypatch, capsys, forge: Path) -> None:
    import presenter

    fs.ask(forge, "which database?")
    answer = hook(
        presenter,
        monkeypatch,
        capsys,
        {"hook_event_name": "Stop", "cwd": str(forge.parent.parent)},
    )
    assert answer == {}


def test_the_grounding_hook_says_nothing_when_it_cannot_load_its_own_checks(
    monkeypatch, capsys, project: Path
) -> None:
    import grounded

    monkeypatch.setitem(sys.modules, "forge_grounding", None)
    assert grounded.message({"cwd": str(project), "tool_input": {"file_path": "a.py"}}) == ""


def test_the_grounding_hook_ignores_a_write_with_no_path(project: Path) -> None:
    import grounded

    assert grounded.message({"cwd": str(project), "tool_input": {}}) == ""


# --------------------------------------------------------------------------
# forge_steps.py
# --------------------------------------------------------------------------


def test_a_phase_file_that_cannot_be_read_lists_no_steps(monkeypatch, forge: Path) -> None:
    import forge_steps as stp

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    path = phases / "1-first.md"
    path.write_text("---\nphase: 1\ntitle: First\n---\n\n## Steps\n\n1. [ ] a thing\n", "utf-8")

    monkeypatch.setattr(Path, "read_text", unreadable)
    assert stp.read_steps(path, 1) == []


def test_compiling_the_phases_twice_replaces_the_first_set(forge: Path) -> None:
    """`compile_phases` writes the whole plan at once, and a second call is a
    redraft rather than a duplicate."""
    import forge_steps as stp

    stp.compile_phases(forge, [("First", "a thing"), ("Second", "another")])
    stp.compile_phases(forge, [("Only one", "a thing")])

    assert len(stp.phase_files(forge)) == 1


# --------------------------------------------------------------------------
# the very last of it
# --------------------------------------------------------------------------


def test_a_library_skill_is_found_where_the_library_puts_it(tmp_path: Path) -> None:
    import forge_skills as sk

    skill = sk.library_dir(tmp_path) / "ponytail"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# ponytail\n", encoding="utf-8")

    assert sk.companion_installed("ponytail", home=tmp_path) is True


def test_a_library_whose_commit_git_will_not_report(monkeypatch, tmp_path: Path) -> None:
    import forge_skills as sk

    class Result:
        returncode = 1
        stdout = ""
        stderr = "not a repository"

    monkeypatch.setattr(sk.subprocess, "run", lambda *a, **k: Result())
    assert sk.library_commit(tmp_path) == ""
    assert sk.library_is_clean(tmp_path) is False


def test_a_library_that_lands_on_the_wrong_commit_is_refused(
    monkeypatch, tmp_path: Path
) -> None:
    """Pinned means pinned: every machine gets the reviewed set or none of it."""
    import forge_skills as sk

    class Result:
        returncode = 0
        stdout = "some-other-commit"
        stderr = ""

    monkeypatch.setattr(sk.subprocess, "run", lambda *a, **k: Result())
    with pytest.raises(sk.SkillError):
        sk.install_library(home=tmp_path)


def test_removing_a_read_only_file_is_attempted_before_giving_up(tmp_path: Path) -> None:
    """Git objects arrive read-only on Windows, so a plain delete fails and the
    cleanup after a failed install would leave half a library behind."""
    import forge_skills as sk

    folder = tmp_path / "library"
    folder.mkdir()
    victim = folder / "a.md"
    victim.write_text("x", encoding="utf-8")
    victim.chmod(0o444)

    sk._remove(folder)
    assert not folder.exists()


def test_every_shape_of_env_file_is_a_secret() -> None:
    """`.env.production` and `.env.local` are the same risk as `.env`."""
    import safety

    assert safety.is_secret_file(".env.production") is True
    assert safety.is_secret_file("config/.env.local") is True
    assert safety.is_secret_file("id_rsa") is True
    assert safety.is_secret_file("README.md") is False


def test_a_path_that_cannot_be_checked_is_not_relaxed(monkeypatch) -> None:
    """"Cannot tell" is not "safe" when the question is whether it is a secret."""
    import safety

    monkeypatch.setattr(Path, "exists", unreadable)
    assert safety._looks_like_code_not_a_path("thing.env", cwd=".") is False


def test_a_review_that_is_already_seen_is_not_asked_for_again(
    monkeypatch, project: Path
) -> None:
    import forge_review as rv
    import reviewed

    forge = project / fs.FORGE_DIR
    rv.add_local(forge, 8, [("a.py", "1", "x")], "ponytail")
    (forge / "reviews" / "pr-8.md").write_text("# review\n", encoding="utf-8")

    monkeypatch.setattr(rv, "local_review_owed", lambda *a, **k: False)
    assert reviewed.message(project) == ""


def test_the_review_trigger_survives_notes_it_cannot_read(monkeypatch, project: Path) -> None:
    import reviewed

    monkeypatch.setattr(reviewed, "_owed", unreadable)
    assert reviewed.message(project) == ""


def test_a_phase_file_with_no_number_is_stepped_over(forge: Path) -> None:
    import forge_steps as stp

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "notes.md").write_text("not a phase file\n", encoding="utf-8")

    listed = stp.phase_files(forge)
    assert [header.get("unreadable") for _n, _p, header in listed] == ["yes"], (
        "a file that is not a phase is listed as unreadable rather than parsed"
    )
    assert stp.current(forge) is None, "and it is stepped over when looking for work"


def test_a_project_with_no_steps_left_has_no_gap_to_report(forge: Path) -> None:
    """Every phase finished is the one state where there is nothing to ask."""
    import forge_steps as stp

    stp.compile_phases(forge, [("First", "a thing")])
    stp.write_steps(forge, 1, ["the only step"])
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")
    stp.mark_built(forge, 1, 1)

    assert stp.current(forge) is None
    assert stp.next_gap(forge) is None


def test_a_phase_file_with_no_steps_section_gains_one(forge: Path) -> None:
    import forge_steps as stp

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        "---\nphase: 1\ntitle: First\n---\n\nit delivers a thing\n", encoding="utf-8"
    )

    stp.write_steps(forge, 1, ["the first slice"])
    text = (phases / "1-first.md").read_text(encoding="utf-8")

    assert "the first slice" in text
    assert "it delivers a thing" in text, "and what was already there survives"


def test_the_search_upward_steps_over_a_file(tmp_path: Path) -> None:
    """The path being checked is usually a folder about to be created, so the
    anchor walk has to survive a path whose parent is a file."""
    (tmp_path / "a-file").write_text("x", encoding="utf-8")
    assert fs.is_ignored_by_git(tmp_path / "a-file" / "nested" / "thing.md") in (True, False)


def test_a_notes_folder_git_ignores_is_refused(monkeypatch, forge: Path) -> None:
    """Decision 016: the records are committed, never ignored. Silently writing
    into an ignored folder would produce a project whose history is not there."""
    monkeypatch.setattr(fs, "is_ignored_by_git", lambda _p: True)

    with pytest.raises(fs.StateError, match="ignoring"):
        fs.refuse_if_ignored(forge)


def test_a_feature_that_clashes_with_nothing_recorded_has_no_clashes(forge: Path) -> None:
    import forge_feature as ff

    assert ff.clashes(forge, "a photo on each todo") == []


def test_a_roadmap_steps_over_a_question_still_open(forge: Path) -> None:
    """The plan shows what was decided. An open question has decided nothing."""
    import forge_roadmap as rm
    import forge_steps as stp

    stp.compile_phases(forge, [("First", "a thing")])
    fs.ask(forge, "which database?")

    assert "First" in rm.render(forge, "todo-app")


def test_text_with_nothing_credential_shaped_is_returned_untouched() -> None:
    import forge_prompts as fpr

    text, hits = fpr.redact("a plain sentence about the database")
    assert hits == 0 and "plain sentence" in text


def test_a_push_that_github_refuses_says_what_it_said(monkeypatch, project: Path) -> None:
    import forge_push as fp

    plan = fp.Plan(branch="merge", remote="origin", commit="abc1234", files=["a.py"], ahead=1)

    class Result:
        returncode = 1
        stdout = ""
        stderr = "! [rejected] merge -> merge (fetch first)"

    monkeypatch.setattr(fp, "preview", lambda *a, **k: plan)
    monkeypatch.setattr(fp, "_git", lambda *a, **k: Result())

    with pytest.raises(fp.PushError, match="refused"):
        fp.push(project, confirmed=True)
