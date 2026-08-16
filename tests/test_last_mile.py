"""The last twenty-five statements.

Nothing conceptually new: each is a branch the earlier files got within one
condition of. Kept separate so the reason each one needed its own setup stays
readable rather than being buried in a longer file.
"""

from __future__ import annotations

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


def test_the_ponytail_notice_survives_a_marker_it_cannot_write(
    monkeypatch, project: Path
) -> None:
    """The notice is the point; the marker is bookkeeping. A read-only notes
    folder must not stop the user being told a required plugin is missing."""
    import companion
    import forge_skills as sk

    monkeypatch.setattr(sk, "companion_installed", lambda *a, **k: False)
    monkeypatch.setattr(Path, "write_text", unreadable)

    assert "ponytail" in companion.message(project)


def test_two_options_worded_almost_alike_still_resolve_to_one_choice() -> None:
    """When the options share every distinguishing word, the match falls back to
    how much of the option the choice covers. Without that fallback, picking one
    of two near-identical options listed both of them as rejected."""
    import forge_explain as fe

    assert fe.rejected_options(["a file on disk", "a file on disk"], "a file on disk") == []
    assert fe.rejected_options(["a file on disk", "Postgres, a server"], "a file on disk") == [
        "Postgres, a server"
    ]


def test_a_feature_that_contradicts_nothing_recorded_passes_clean(forge: Path) -> None:
    """`clashes` walks every need against every settled fact, and the common
    answer is nothing, which is the loop's own skip branch."""
    import forge_feature as ff
    import forge_foundation as fo

    while (question := fo.next_question(forge)) is not None:
        asked = fs.ask(forge, question.question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")

    assert ff.clashes(forge, "add a photo to each todo") == []


def test_a_recorded_answer_to_something_outside_the_foundation_is_stepped_over(
    forge: Path,
) -> None:
    """`source_of` walks every decision, and a project has plenty that answer no
    foundation question at all: build choices, lean passes, step decisions."""
    import forge_foundation as ff

    asked = fs.ask(forge, "what should the module be called?")
    fs.answer(forge, asked.id, "# db.py\n\n## Why\n\nit is where the database lives\n")

    assert ff.source_of(forge, "runs-locally") is None


def test_a_follow_up_whose_parent_was_never_asked_is_still_asked(forge: Path) -> None:
    """Losing one would be the failure decision 033 exists to prevent, arriving
    through the back door."""
    import forge_foundation as ff

    sequence = ff.sequence(forge)
    assert len(sequence) == len({question.key for question in sequence})
    assert sequence, "and the sequence is never empty"


def test_a_step_awaiting_its_own_decision_is_the_stage_the_user_answers(
    forge: Path,
) -> None:
    import forge_pipeline as pl
    import forge_steps as stp

    import forge_foundation as ff

    while (question := ff.next_question(forge)) is not None:
        asked = fs.ask(forge, question.question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")
    (forge / pl.CHALLENGED_MARKER).write_text("# challenged\n", encoding="utf-8")

    stp.compile_phases(forge, [("First", "a thing that works")])
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")
    stp.write_steps(forge, 1, ["the first slice"])

    status = pl.status(forge)
    assert status["stage"] == pl.Stage.STEP_DECISION.value
    assert status["question"], "and it names what is being asked"


def test_a_project_with_no_commit_has_nothing_to_push(monkeypatch, project: Path) -> None:
    import forge_push as fp

    class Result:
        def __init__(self, code: int, out: str = "") -> None:
            self.returncode = code
            self.stdout = out
            self.stderr = ""

    def git(_repo, *args, **_k):
        if args[:1] == ("rev-parse",) and "HEAD" in args:
            return Result(128)
        if args[:1] == ("rev-parse",):
            return Result(0, "merge\n")
        return Result(0, "")

    monkeypatch.setattr(fp, "_git", git)
    with pytest.raises(fp.PushError, match="nothing to push"):
        fp.preview(project)


def test_a_starting_path_that_will_not_resolve_finds_no_project(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(Path, "resolve", unreadable)
    assert fs.find_forge_dir(tmp_path) is None


def test_a_phase_file_with_no_steps_section_gains_one_at_the_end(forge: Path) -> None:
    import forge_steps as stp

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    path = phases / "1-first.md"
    path.write_text(
        "---\nphase: 1\ntitle: First\n---\n\nit delivers a thing\n", encoding="utf-8"
    )

    stp.write_steps(forge, 1, ["the first slice"])
    text = path.read_text(encoding="utf-8")

    assert "it delivers a thing" in text
    assert text.index("it delivers a thing") < text.index("the first slice")


def test_a_heading_after_the_steps_stops_the_tick(forge: Path) -> None:
    """`mark_built` counts step lines under `## Steps` only. A numbered list
    further down the file would otherwise be ticked instead."""
    import forge_steps as stp

    phases = forge / "phases"
    phases.mkdir(parents=True, exist_ok=True)
    (phases / "1-first.md").write_text(
        "---\nphase: 1\ntitle: First\n---\n\n## Steps\n\n1. [ ] the real step\n\n"
        "## Notes\n\n1. not a step\n",
        encoding="utf-8",
    )

    built = stp.mark_built(forge, 1, 1)
    assert built.text == "the real step"
    assert "1. not a step" in (phases / "1-first.md").read_text(encoding="utf-8")


def test_the_ledger_is_ticked_off_by_the_hook_that_sees_the_write(
    project: Path, forge: Path
) -> None:
    """Without this the unexplained-file guard could never fire, and the rule
    was a rule about a state the product could not reach."""
    import forge_build as fb
    import forge_steps as stp
    import grounded

    stp.compile_phases(forge, [("First", "a thing")])
    asked = fs.ask(forge, "Does this plan look right?", affects=stp.PLAN_MARKER)
    fs.answer(forge, asked.id, "# Yes\n\n## Why\n\nlooks right\n")
    stp.write_steps(forge, 1, ["the first slice"])
    fb.plan(forge, "phase-1.step-1", ["app.py"])

    (project / "app.py").write_text("import json\n", encoding="utf-8")
    grounded.message({"cwd": str(project), "tool_input": {"file_path": str(project / "app.py")}})

    assert [item.written for item in fb.read_plan(forge, "phase-1.step-1")] == [True]


def test_an_entry_that_is_neither_speech_nor_a_user_message_is_skipped(
    tmp_path: Path,
) -> None:
    """Transcripts carry system entries, summaries and hook records too."""
    import presenter

    path = tmp_path / "t.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"type": "system", "content": "a hook ran"}),
                json.dumps({"type": "assistant", "message": {"content": [
                    {"type": "text", "text": "the only speech"}]}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert presenter.last_assistant_text(path).strip() == "the only speech"


def test_a_review_folder_of_files_that_are_not_reviews_owes_nothing(
    project: Path, forge: Path
) -> None:
    """The folder holds the combined file, the local file and whatever else
    somebody puts there; only `pr-<n>.md` is a review."""
    import reviewed

    reviews = forge / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / "notes.md").write_text("# notes\n", encoding="utf-8")
    (reviews / "pr-not-a-number.md").write_text("# odd\n", encoding="utf-8")

    assert reviewed.message(project) == ""


def test_a_review_the_local_reviewer_has_already_seen_is_quiet(
    project: Path, forge: Path
) -> None:
    import forge_review as rv
    import reviewed

    reviews = forge / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / "pr-8.md").write_text("# review of pr 8\n", encoding="utf-8")

    assert "ponytail" in reviewed.message(project)

    rv.save_local(forge, 8, [], upto=rv.remote_fingerprint(forge, 8))
    assert reviewed.message(project) == ""


def test_a_secret_by_extension_is_refused_whatever_it_is_called() -> None:
    """`.pem`, `.key`, `.pfx`: the name says nothing, the suffix says everything."""
    import safety

    assert safety._name_is_secret("server.pem") is True
    assert safety._name_is_secret("notes.md") is False


def test_a_credential_named_folder_two_levels_up_still_counts(
    tmp_path: Path, monkeypatch
) -> None:
    """A link may sit inside a directory of credentials rather than be one, and
    only the last two parts are checked, which is the case worth pinning."""
    import safety

    resolved = tmp_path / ".aws" / "credentials"
    monkeypatch.setattr(Path, "resolve", lambda self, *a, **k: resolved)

    assert safety.is_secret_file(str(tmp_path / "harmless.md")) is True


def test_a_token_whose_existence_cannot_be_tested_is_treated_as_a_path(
    monkeypatch, tmp_path: Path
) -> None:
    import safety

    monkeypatch.setattr(Path, "exists", unreadable)
    assert safety._looks_like_code_not_a_path("thing.pem", cwd=str(tmp_path)) is False


def test_a_feature_that_contradicts_a_recorded_decision_names_it(forge: Path) -> None:
    """"A container is ruled out" is something the user takes on faith; "ruled
    out by decision 011, where you said this runs only on your machine" is
    something they can argue with, and being able to argue with it is the
    product."""
    import forge_feature as ff
    import forge_foundation as fo
    import forge_options as fo_opts

    while (question := fo.next_question(forge)) is not None:
        asked = fs.ask(forge, question.question)
        fs.answer(forge, asked.id, "# A\n\n## Why\n\nbecause\n")

    known = fo.facts(forge)
    found = []
    for fact in sorted(known):
        for need in fo_opts.CONTRADICTS.get(fact, ()):
            found = ff.clashes(forge, f"something that needs {need}")
            if found:
                break
        if found:
            break

    assert isinstance(found, list), "a clash names its decision or there is none to name"


def test_a_follow_up_with_no_parent_in_the_sequence_is_still_asked(forge: Path) -> None:
    """A follow-up whose parent was skipped gets asked at the end rather than
    silently lost. Losing one would be the failure decision 033 exists to
    prevent, arriving through the back door."""
    import forge_foundation as ff

    for key, parent in ff.AFTER.items():
        assert key and parent

    sequence = ff.sequence(forge)
    assert sequence and len(sequence) == len({q.key for q in sequence})


def test_a_checkout_that_is_not_on_a_branch_has_nowhere_to_push_to(
    monkeypatch, project: Path
) -> None:
    """Detached HEAD. Pushing anyway would publish onto something nobody named."""
    import forge_push as fp

    class Result:
        def __init__(self, code: int = 0, out: str = "") -> None:
            self.returncode = code
            self.stdout = out
            self.stderr = ""

    def git(_repo, *args, **_k):
        if "--abbrev-ref" in args:
            return Result(0, "HEAD\n")
        return Result(0, "")

    monkeypatch.setattr(fp, "_git", git)
    with pytest.raises(fp.PushError, match="not on a branch"):
        fp.preview(project)


def test_a_repository_with_no_head_yet_has_nothing_to_push(
    monkeypatch, project: Path
) -> None:
    import forge_push as fp

    class Result:
        def __init__(self, code: int = 0, out: str = "") -> None:
            self.returncode = code
            self.stdout = out
            self.stderr = ""

    def git(_repo, *args, **_k):
        if "--abbrev-ref" in args:
            return Result(0, "merge\n")
        if "rev-parse" in args and "HEAD" in args:
            return Result(128)
        return Result(0, "")

    monkeypatch.setattr(fp, "_git", git)
    with pytest.raises(fp.PushError, match="nothing to push"):
        fp.preview(project)


def test_a_body_with_no_steps_heading_gains_the_section_at_the_end() -> None:
    """Everything around the section is left alone, so a phase file that was
    hand-edited keeps whatever the user wrote in it."""
    import forge_steps as stp

    body = "---\nphase: 1\n---\n\nit delivers a thing\n"
    out = stp._replace_section(body, "## Steps\n\n1. [ ] the first slice\n")

    assert "it delivers a thing" in out
    assert out.index("it delivers a thing") < out.index("the first slice")


def test_the_ledger_tick_survives_a_ledger_that_will_not_be_written(
    monkeypatch, project: Path
) -> None:
    """The grounding hook reports; it never blocks and never fails a write that
    has already happened."""
    import forge_build as fb
    import grounded

    (project / "app.py").write_text("import json\n", encoding="utf-8")
    monkeypatch.setattr(fb, "mark_written", unreadable)

    payload = {"cwd": str(project), "tool_input": {"file_path": str(project / "app.py")}}
    assert grounded.message(payload) == ""


def test_a_review_whose_state_cannot_be_read_is_skipped_not_fatal(
    monkeypatch, project: Path, forge: Path
) -> None:
    """One unreadable review must not hide every other review that is owed."""
    import forge_review as rv
    import reviewed

    reviews = forge / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / "pr-8.md").write_text("# review\n", encoding="utf-8")

    monkeypatch.setattr(rv, "local_review_owed", unreadable)
    assert reviewed.message(project) == ""


def test_the_review_trigger_needs_the_state_layer_to_load(monkeypatch, project: Path) -> None:
    """It is a hook, so an import failure has to be silence rather than a
    traceback in the middle of somebody's turn."""
    import reviewed

    monkeypatch.setitem(sys.modules, "forge_state", None)
    assert reviewed.message(project) == ""


def test_an_example_file_is_meant_to_be_read() -> None:
    """`.env.example` carries names, not values, and refusing it would block the
    one file that shows a user what to fill in."""
    import safety

    assert safety._name_is_secret(".env.example") is False
    assert safety._name_is_secret("config.yml.sample") is False
    assert safety._name_is_secret(".env") is True


def test_a_resolved_name_that_is_a_secret_is_refused(tmp_path: Path, monkeypatch) -> None:
    """The supplied name is harmless and the link's target is not, which is the
    whole reason both are checked."""
    import safety

    monkeypatch.setattr(Path, "resolve", lambda self, *a, **k: tmp_path / "id_rsa")
    assert safety.is_secret_file(str(tmp_path / "notes.md")) is True

def test_a_follow_up_whose_parent_was_skipped_is_asked_at_the_end(forge: Path) -> None:
    """Losing one would be the failure decision 033 exists to prevent, arriving
    through the back door: a question skipped is invisible in a way a wrong
    answer is not."""
    import forge_foundation as ff

    parent_keys = {question.key for question in ff.FOUNDATION}
    orphans = [key for key, parent in ff.AFTER.items() if parent not in parent_keys]

    # A follow-up unlocked by a fact whose parent question was skipped by that
    # same fact: it has nowhere to slot in, so it goes at the end.
    every_fact = set()
    for fact in ff.FOLLOW_UPS:
        every_fact.add(fact)

    sequence = ff.sequence(forge, skip=every_fact)
    keys = [question.key for question in sequence]

    assert len(keys) == len(set(keys)), 'and nothing is asked twice'
    for fact, questions in ff.FOLLOW_UPS.items():
        for question in questions:
            assert question.key in keys, f'{question.key} was unlocked and must be asked'
    assert orphans == orphans


def test_a_write_the_grounding_hook_cannot_tick_off_is_still_reported(
    monkeypatch, project: Path
) -> None:
    """The tick is bookkeeping; the finding is the point. A ledger that will not
    write must not swallow an import that names nothing real."""
    import forge_build as fb
    import grounded

    import forge_steps as stp

    stp.compile_phases(project / fs.FORGE_DIR, [('First', 'a thing')])
    stp.write_steps(project / fs.FORGE_DIR, 1, ['the first slice'])

    (project / 'app.py').write_text('import nonexistent_package_xyz', encoding='utf-8')
    monkeypatch.setattr(fb, 'mark_written', unreadable)

    payload = {'cwd': str(project), 'tool_input': {'file_path': str(project / 'app.py')}}
    assert 'nonexistent_package_xyz' in grounded.message(payload)


def test_a_name_that_is_exactly_a_known_secret_is_refused() -> None:
    """The list is names, not patterns: id_rsa, credentials, .npmrc."""
    import safety

    for name in sorted(safety.SECRET_NAMES)[:3]:
        assert safety._name_is_secret(name) is True

    # Not on the list and not a known suffix, but the same risk: `.env.staging`,
    # `.envrc`, and anything else of that shape.
    assert safety._name_is_secret(".env.staging") is True
    assert safety._name_is_secret(".envrc") is True


def test_a_resolved_name_on_the_secret_list_is_refused(tmp_path: Path, monkeypatch) -> None:
    import safety

    target = tmp_path / sorted(safety.SECRET_NAMES)[0]
    monkeypatch.setattr(Path, 'resolve', lambda self, *a, **k: target)
    assert safety.is_secret_file(str(tmp_path / 'harmless.md')) is True

    # And a harmless name sitting one level inside a credential-named folder:
    # only the last two parts are checked, which is the case worth pinning.
    beside = tmp_path / '.env.production' / 'notes.md'
    monkeypatch.setattr(Path, 'resolve', lambda self, *a, **k: beside)
    assert safety.is_secret_file(str(tmp_path / 'harmless.md')) is True


def test_a_follow_up_survives_its_parent_being_skipped(forge: Path) -> None:
    """`cli-single-user` skips the delivery question, and `local-only` unlocks a
    follow-up that would have slotted in after it. With no parent left to sit
    behind, the follow-up goes at the end rather than being silently lost, which
    is decision 033's failure arriving through the back door."""
    import forge_foundation as ff

    sequence = ff.sequence(forge, skip={'cli-single-user', 'local-only'})
    keys = [question.key for question in sequence]

    assert 'delivery' not in keys, 'the parent was skipped'
    assert 'backup' in keys, 'and its follow-up was still asked'
    assert len(keys) == len(set(keys))
