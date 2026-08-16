"""Tests for the usage meter — decisions 008 and 024.

The meter reads Claude Code's own session logs, which is the only place the
real numbers exist: Forge is a plugin inside the thing doing the spending and
has no request of its own to count.

Two properties matter more than the arithmetic. First, that one model response
is counted once — the log writes a response with several tool calls as several
records, each carrying an identical copy of the same usage block, and summing
records instead of responses over-counted by a factor of three on the first
real session tested. Second, that every way of failing to read the log is
survivable, because a meter is a display and nothing in the pipeline waits on
it.

Nothing here reads the real `~/.claude`. Logs are built in a temp directory in
the shape the real ones have.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import forge_meter as fm
import forge_state as fs


def turn_record(
    message_id: str,
    *,
    model: str = "claude-opus-5",
    fresh: int = 100,
    output: int = 50,
    cache_read: int = 900,
    cache_write: int = 0,
    sidechain: bool = False,
    cwd: str = r"H:\project",
) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "cwd": cwd,
            "isSidechain": sidechain,
            "message": {
                "id": message_id,
                "model": model,
                "usage": {
                    "input_tokens": fresh,
                    "output_tokens": output,
                    "cache_read_input_tokens": cache_read,
                    "cache_creation_input_tokens": cache_write,
                },
            },
        }
    )


@pytest.fixture()
def logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake Claude Code config directory, honoured via CLAUDE_CONFIG_DIR."""
    config = tmp_path / "claude"
    (config / "projects").mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    return config / "projects"


def write_session(logs: Path, project: Path, *records: str, name: str = "s1") -> Path:
    folder = logs / fm.encode_project(project)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.jsonl"
    path.write_text("\n".join(records) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# finding the logs
# --------------------------------------------------------------------------


def test_the_project_folder_name_matches_claude_codes_rule() -> None:
    """Checked against real folder names, including one with spaces."""
    assert fm.encode_project(Path(r"H:\Skills\Project")) == "H--Skills-Project"
    assert (
        fm.encode_project(Path(r"H:\Skills\Tashi - BitMadWall"))
        == "H--Skills-Tashi---BitMadWall"
    )


def test_a_relocated_config_directory_is_honoured(logs: Path, tmp_path: Path) -> None:
    """Otherwise a user with a moved config is silently reported as spending nothing."""
    project = tmp_path / "proj"
    write_session(logs, project, turn_record("m1"))
    assert fm.measure(project).turns == 1


def test_sessions_are_found_by_reading_cwd_when_the_name_rule_misses(
    logs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The folder-name rule is inferred, so it must degrade to slow, not to zero."""
    project = tmp_path / "proj"
    odd = logs / "a-folder-named-by-some-future-rule"
    odd.mkdir()
    (odd / "s1.jsonl").write_text(
        turn_record("m1", cwd=str(project)) + "\n", encoding="utf-8"
    )

    monkeypatch.setattr(fm, "encode_project", lambda _p: "definitely-not-there")
    assert fm.measure(project).turns == 1


# --------------------------------------------------------------------------
# counting a response once
# --------------------------------------------------------------------------


def test_one_response_written_as_several_records_is_counted_once(
    logs: Path, tmp_path: Path
) -> None:
    """The bug this guards against made the meter report three times the truth.

    A reply containing several tool calls is appended to the log once per
    content block, and every copy carries the same usage block.
    """
    project = tmp_path / "proj"
    write_session(
        logs,
        project,
        turn_record("msg_same", fresh=10, output=20, cache_read=30),
        turn_record("msg_same", fresh=10, output=20, cache_read=30),
        turn_record("msg_same", fresh=10, output=20, cache_read=30),
    )

    usage = fm.measure(project)
    assert usage.turns == 1
    assert usage.total == 60, "not 180"


def test_genuinely_different_responses_are_all_counted(logs: Path, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    write_session(
        logs,
        project,
        turn_record("m1", fresh=10, output=0, cache_read=0),
        turn_record("m2", fresh=20, output=0, cache_read=0),
    )
    assert fm.measure(project).total == 30


def test_responses_from_every_session_file_are_included(logs: Path, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    write_session(logs, project, turn_record("m1", fresh=5, output=0, cache_read=0), name="a")
    write_session(logs, project, turn_record("m2", fresh=7, output=0, cache_read=0), name="b")
    assert fm.measure(project).total == 12


def test_usage_is_split_by_model_and_subagents_are_visible(
    logs: Path, tmp_path: Path
) -> None:
    """Decision 002 routes jobs to different models; the meter has to show that."""
    project = tmp_path / "proj"
    write_session(
        logs,
        project,
        turn_record("m1", model="claude-opus-5", fresh=100, output=0, cache_read=0),
        turn_record("m2", model="claude-haiku-4-5", fresh=10, output=0, cache_read=0, sidechain=True),
    )

    usage = fm.measure(project)
    assert usage.by_model == {"claude-opus-5": 100, "claude-haiku-4-5": 10}
    assert usage.subagent_turns == 1


def test_the_cache_share_is_reported_because_it_is_what_assembly_moves(
    logs: Path, tmp_path: Path
) -> None:
    project = tmp_path / "proj"
    write_session(logs, project, turn_record("m1", fresh=250, cache_read=750, output=99))
    assert fm.measure(project).cache_saving == pytest.approx(0.75)


# --------------------------------------------------------------------------
# every failure is survivable — the meter is a display, not a gate
# --------------------------------------------------------------------------


def test_no_logs_at_all_reports_unavailable_rather_than_zero(
    logs: Path, tmp_path: Path
) -> None:
    """Zero would read as 'you have spent nothing', which is a different claim."""
    usage = fm.measure(tmp_path / "never-opened")
    assert usage.available is False
    assert usage.total == 0
    assert "No sessions" in usage.reason


def test_a_half_written_last_line_does_not_lose_the_session(
    logs: Path, tmp_path: Path
) -> None:
    """A log being appended to while it is read ends mid-line. That is normal."""
    project = tmp_path / "proj"
    folder = logs / fm.encode_project(project)
    folder.mkdir(parents=True)
    (folder / "s1.jsonl").write_text(
        turn_record("m1", fresh=5, output=0, cache_read=0) + '\n{"type": "assis',
        encoding="utf-8",
    )
    assert fm.measure(project).total == 5


def test_records_that_are_not_model_replies_are_skipped(logs: Path, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    write_session(
        logs,
        project,
        json.dumps({"type": "user", "message": {"content": "hello"}}),
        json.dumps({"type": "assistant", "message": {"id": "m0"}}),  # no usage block
        turn_record("m1", fresh=5, output=0, cache_read=0),
    )
    usage = fm.measure(project)
    assert usage.turns == 1 and usage.total == 5


def test_a_missing_field_is_treated_as_zero_not_as_a_crash(
    logs: Path, tmp_path: Path
) -> None:
    """The log format is not promised, so a renamed field must not be fatal."""
    project = tmp_path / "proj"
    write_session(
        logs,
        project,
        json.dumps(
            {
                "type": "assistant",
                "message": {"id": "m1", "model": "x", "usage": {"output_tokens": 7}},
            }
        ),
    )
    assert fm.measure(project).total == 7


# --------------------------------------------------------------------------
# thresholds — decision 008, never against an invented ceiling
# --------------------------------------------------------------------------


@pytest.fixture()
def forge(tmp_path: Path) -> Path:
    return fs.init(tmp_path)


def test_no_budget_means_no_warning(forge: Path) -> None:
    """A subscription has no token ceiling Forge can know.

    Decision 024 forbids inventing one — a threshold crossed against a made-up
    limit is a false alarm, and false alarms are how a real warning gets ignored.
    """
    usage = fm.Usage(fresh_input=10_000_000)
    assert fm.budget(forge) == 0
    assert fm.threshold_crossed(usage, 0) is None
    assert fm.warning(forge, usage) == ""


def set_budget(forge: Path, value: str) -> None:
    (forge / fs.SETTINGS).write_text(
        fs.render_header({"type": "settings", "token_budget": value}) + "# Settings\n",
        encoding="utf-8",
    )


def test_a_budget_the_user_set_is_read(forge: Path) -> None:
    set_budget(forge, "1_000_000")
    assert fm.budget(forge) == 1_000_000


def test_an_unreadable_budget_is_no_budget(forge: Path) -> None:
    set_budget(forge, "quite a lot")
    assert fm.budget(forge) == 0


@pytest.mark.parametrize(
    "used,expected",
    [(400, None), (500, "about half"), (760, "three quarters"), (999, "nearly full")],
)
def test_the_highest_threshold_passed_is_the_one_reported(
    used: int, expected: str | None
) -> None:
    crossed = fm.threshold_crossed(fm.Usage(fresh_input=used), 1000)
    assert (crossed[1] if crossed else None) == expected


def test_each_threshold_is_stated_once_and_not_repeated(forge: Path) -> None:
    """Decision 008: a warning should inform, not nag."""
    set_budget(forge, "1000")
    usage = fm.Usage(fresh_input=600)

    first = fm.warning(forge, usage)
    assert "about half" in first

    assert fm.warning(forge, usage) == "", "the same threshold does not fire twice"

    louder = fm.warning(forge, fm.Usage(fresh_input=800))
    assert "three quarters" in louder, "but a new threshold still does"


def test_the_warning_says_the_notes_are_portable(forge: Path) -> None:
    """Decision 008 ties the warning to decision 001 — you can switch accounts."""
    set_budget(forge, "1000")
    assert "switch accounts" in fm.warning(forge, fm.Usage(fresh_input=900))


# --------------------------------------------------------------------------
# what the user and the model each see
# --------------------------------------------------------------------------


def test_unavailable_usage_says_nothing_else_is_affected() -> None:
    text = fm.render(fm.Usage(available=False, reason="no logs"))
    assert "Nothing else is affected" in text


def test_the_report_never_invents_a_money_figure(logs: Path, tmp_path: Path) -> None:
    """Decision 024: tokens are measured, money would be guessed."""
    project = tmp_path / "proj"
    write_session(logs, project, turn_record("m1"))
    report = fm.report(project, None)

    assert "total" in report and "cache_saving" in report

    # An allowed set rather than a denied substring. Rejecting "cost" and "usd"
    # let "price", "dollars" and "spend_estimate" straight through, so the rule
    # this guards — the meter never invents a price — was barely guarded.
    assert set(report) <= {
        "available", "turns", "fresh_input", "cache_read", "cache_write",
        "output", "total", "cache_saving", "by_model", "subagent_turns",
        "reason", "budget", "threshold",
    }, "a new key has to be considered before it is allowed"


def test_the_report_carries_the_budget_when_one_is_set(forge: Path, logs: Path) -> None:
    project = forge.parent
    write_session(logs, project, turn_record("m1", fresh=600, output=0, cache_read=0))
    set_budget(forge, "1000")

    report = fm.report(project, forge)
    assert report["budget"] == 1000
    assert report["threshold"] == "about half"


# --------------------------------------------------------------------------
# the logs, when the logs are not where or what they should be
# --------------------------------------------------------------------------


def test_no_transcript_folder_at_all_reports_nothing_rather_than_zero(
    tmp_path: Path, monkeypatch
) -> None:
    """Zero is a number somebody would believe. "Unavailable" is the truth."""
    monkeypatch.setattr(fm, "transcript_root", lambda: tmp_path / "nowhere")
    assert fm.session_files(tmp_path) == []


def test_a_session_is_found_by_what_it_says_its_directory_was(
    tmp_path: Path, monkeypatch
) -> None:
    """The folder name is derived from the path, and the derivation has changed
    before. Reading `cwd` out of the log is the fallback that survives that."""
    root = tmp_path / "projects"
    odd = root / "some-other-name"
    odd.mkdir(parents=True)
    project = tmp_path / "work" / "todo-app"
    project.mkdir(parents=True)

    (odd / "a.jsonl").write_text(
        json.dumps({"cwd": str(project)}) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(fm, "transcript_root", lambda: root)

    assert [p.name for p in fm.session_files(project)] == ["a.jsonl"]


def test_a_stray_file_beside_the_folders_is_stepped_over(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "projects"
    root.mkdir(parents=True)
    (root / "not-a-folder.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(fm, "transcript_root", lambda: root)

    assert fm.session_files(tmp_path / "work") == []


def test_a_log_whose_first_lines_are_blank_or_broken_is_still_read(tmp_path: Path) -> None:
    """A partially written last line is normal in a live log, not an error."""
    log = tmp_path / "a.jsonl"
    log.write_text(
        "\n" + "{not json at all\n" + json.dumps({"no_cwd": 1}) + "\n"
        + json.dumps({"cwd": "C:/work"}) + "\n",
        encoding="utf-8",
    )

    assert fm._first_cwd(log) == "c:\work"


def test_a_log_that_cannot_be_opened_is_skipped_not_fatal(tmp_path: Path, monkeypatch) -> None:
    log = tmp_path / "a.jsonl"
    log.write_text("{}\n", encoding="utf-8")

    def refuse(*_a, **_k):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "open", refuse)
    assert fm._first_cwd(log) is None

    monkeypatch.setattr(fm, "session_files", lambda _p: [log])
    assert fm.read_turns(tmp_path) == []


def test_a_log_with_no_cwd_anywhere_says_it_does_not_know(tmp_path: Path) -> None:
    log = tmp_path / "a.jsonl"
    log.write_text(json.dumps({"type": "assistant"}) + "\n", encoding="utf-8")

    assert fm._first_cwd(log) is None


def test_reading_the_logs_at_all_is_wrapped(tmp_path: Path, monkeypatch) -> None:
    """The meter is a report, never a reason a session fails to start."""

    def broken(*_a, **_k):
        raise RuntimeError("the logs are unreadable")

    monkeypatch.setattr(fm, "read_turns", broken)
    usage = fm.measure(tmp_path)

    assert usage.available is False
    assert "Could not read" in usage.reason


def test_an_unreadable_budget_reads_as_no_budget(tmp_path: Path, monkeypatch) -> None:
    import forge_state as fs

    fs.init(tmp_path)
    forge = tmp_path / fs.FORGE_DIR

    def refuse(*_a, **_k):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "read_text", refuse)
    assert fm.budget(forge) == 0
    assert fm._already_warned(forge) == set()


def test_a_warning_that_cannot_be_recorded_still_warns(tmp_path: Path, monkeypatch) -> None:
    import forge_state as fs

    fs.init(tmp_path)
    forge = tmp_path / fs.FORGE_DIR

    def refuse(*_a, **_k):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "write_text", refuse)
    fm._remember_warning(forge, {80})


def test_the_usage_block_shows_the_split_and_who_spent_it() -> None:
    """Cached against fresh is the number that changes behaviour, and by-model
    is what tells you the teaching model is not writing the code."""
    usage = fm.Usage(
        available=True,
        turns=120,
        fresh_input=10_000,
        cache_read=90_000,
        cache_write=5_000,
        output=8_000,
        by_model={"claude-opus-5": 60_000, "claude-fable-5": 40_000},
        subagent_turns=42,
    )
    drawn = fm.render(usage)

    assert "120" in drawn
    assert "claude-opus-5" in drawn
    assert "42" in drawn
    assert "reused" in drawn


def test_a_line_that_is_not_a_turn_is_not_counted() -> None:
    """Every one of these shapes appears in a real log, and counting any of
    them would inflate the number the user is shown."""
    assert fm._turn_from(json.dumps({"type": "user"})) is None
    assert fm._turn_from(json.dumps({"type": "assistant", "message": "not a dict"})) is None
    assert fm._turn_from(json.dumps({"type": "assistant", "message": {}})) is None
    assert (
        fm._turn_from(json.dumps({"type": "assistant", "message": {"usage": {}}})) is None
    ), "no message id, so it cannot be told apart from its own duplicates"


def test_no_session_logs_on_this_machine_is_said_plainly(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(fm, "transcript_root", lambda: tmp_path / "nowhere")
    usage = fm.measure(tmp_path)

    assert usage.available is False
    assert "no session logs" in usage.reason.lower()


def test_a_budget_that_is_not_a_number_is_no_budget(tmp_path: Path) -> None:
    import forge_state as fs

    fs.init(tmp_path)
    forge = tmp_path / fs.FORGE_DIR
    (forge / fs.SETTINGS).write_text(
        "---\ntoken_budget: lots\n---\n\n# Settings\n", encoding="utf-8"
    )

    assert fm.budget(forge) == 0, "a budget nobody can read as a number is no budget"


def test_the_report_carries_the_budget_when_the_project_has_one(tmp_path: Path) -> None:
    import forge_state as fs

    fs.init(tmp_path)
    forge = tmp_path / fs.FORGE_DIR
    (forge / fs.SETTINGS).write_text(
        "---\ntoken_budget: 1_000_000\n---\n\n# Settings\n", encoding="utf-8"
    )

    out = fm.report(tmp_path, forge)
    assert out["budget"] == 1_000_000


def test_a_settings_file_that_will_not_parse_is_no_budget(tmp_path: Path) -> None:
    """Both readers are guarded the same way, and both are asked on every
    status report, so a malformed header must not stop one."""
    import forge_state as fs

    fs.init(tmp_path)
    forge = tmp_path / fs.FORGE_DIR

    (forge / fs.SETTINGS).write_text("no labelled section at all\n", encoding="utf-8")
    assert fm.budget(forge) == 0

    (forge / fm.USAGE_FILE).write_text("no labelled section here either\n", encoding="utf-8")
    assert fm._already_warned(forge) == set()


def test_a_line_with_no_usage_block_is_not_a_turn() -> None:
    assert fm._turn_from(json.dumps({"type": "assistant", "message": {"id": "m1"}})) is None


def test_a_blank_line_in_the_log_is_not_a_turn() -> None:
    assert fm._turn_from("   ") is None
