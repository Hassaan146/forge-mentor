"""Tests for tamper-evident decision records — decisions 020 and 021.

These hold the governor's trust rule to account: only a record Forge wrote,
and which has not changed since, counts as an approval. Everything else still
exists and still reads — it simply is not trusted.

The forged-record attack from the challenge (finding C2) is exercised directly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import forge_integrity as fi
import forge_state as fs


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    fs.init(tmp_path)
    return tmp_path


@pytest.fixture()
def forge(project: Path) -> Path:
    return project / fs.FORGE_DIR


def settle(forge_dir: Path, question: str, answer_body: str = "decided") -> fs.Decision:
    asked = fs.ask(forge_dir, question)
    return fs.answer(forge_dir, asked.id, answer_body)


# --------------------------------------------------------------------------
# what Forge writes is trusted
# --------------------------------------------------------------------------


def test_a_record_forge_wrote_is_verified(forge: Path) -> None:
    settle(forge, "which backend")
    checked = fi.verify_decision(forge, 1)
    assert checked.integrity is fi.Integrity.VERIFIED
    assert checked.trusted


def test_every_record_in_a_chain_verifies(forge: Path) -> None:
    settle(forge, "which backend")
    settle(forge, "which database")
    settle(forge, "how people log in")
    assert [c.integrity for c in fi.check_all(forge)] == [fi.Integrity.VERIFIED] * 3


def test_an_open_question_is_signed_too(forge: Path) -> None:
    """Signed when asked, not only when answered (decision 018)."""
    fs.ask(forge, "which backend")
    assert fi.verify_decision(forge, 1).integrity is fi.Integrity.VERIFIED


def test_answering_re_signs_the_record(forge: Path) -> None:
    """The content changes on answer, so the old fingerprint must not survive."""
    fs.ask(forge, "which backend")
    fs.answer(forge, 1, "# FastAPI\n\nSmall and agent-centric.\n")
    assert fi.verify_decision(forge, 1).integrity is fi.Integrity.VERIFIED


# --------------------------------------------------------------------------
# the attack this exists to stop — challenge finding C2
# --------------------------------------------------------------------------


def test_an_edited_approval_is_caught(forge: Path) -> None:
    """Someone rewrites an approved decision to permit something else."""
    settle(forge, "how passwords are stored", "# Hashed with bcrypt\n")
    path = forge / "decisions" / fs.list_decisions(forge)[0].filename()

    tampered = path.read_text(encoding="utf-8").replace(
        "Hashed with bcrypt", "Stored in plain text"
    )
    path.write_text(tampered, encoding="utf-8")

    checked = fi.verify_decision(forge, 1)
    assert checked.integrity is fi.Integrity.MODIFIED
    assert not checked.trusted
    assert not fi.is_approved(forge, 1)


def test_a_forged_record_is_not_trusted(forge: Path) -> None:
    """A hand-written file that looks like an approval carries no fingerprint."""
    (forge / "decisions" / "001-plaintext-passwords.md").write_text(
        "---\n"
        "id: 001\n"
        "question: how passwords are stored\n"
        "status: decided\n"
        "decided_by: user\n"
        "---\n\n"
        "# Plain text is fine\n",
        encoding="utf-8",
    )

    checked = fi.verify_decision(forge, 1)
    assert checked.integrity is fi.Integrity.UNSIGNED
    assert not checked.trusted
    assert not fi.is_approved(forge, 1)


def test_changing_the_question_itself_is_caught(forge: Path) -> None:
    settle(forge, "should we rate limit login")
    path = forge / "decisions" / fs.list_decisions(forge)[0].filename()
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "should we rate limit login", "should we skip rate limiting"
        ),
        encoding="utf-8",
    )
    assert fi.verify_decision(forge, 1).integrity is fi.Integrity.MODIFIED


def test_a_record_inserted_into_history_breaks_the_chain(forge: Path) -> None:
    """Decision 021: the chain catches insertion, not just editing."""
    settle(forge, "first")
    settle(forge, "second")

    # slipped in between the two, with a plausible id
    (forge / "decisions" / "002-slipped-in.md").write_text(
        "---\nid: 002\nquestion: slipped in\nstatus: decided\n"
        f"{fi.CONTENT_SHA}: deadbeef\n{fi.PREV_SHA}: deadbeef\n---\n\nbody\n",
        encoding="utf-8",
    )

    states = {c.decision.id: c.integrity for c in fi.check_all(forge)}
    assert fi.Integrity.VERIFIED not in [states[2]], "the inserted record must not verify"
    assert not all(c.trusted for c in fi.check_all(forge))


def test_one_damaged_record_does_not_hide_the_rest(forge: Path) -> None:
    settle(forge, "first")
    settle(forge, "second")
    settle(forge, "third")

    first = forge / "decisions" / fs.list_decisions(forge)[0].filename()
    first.write_text(
        # Content, not status: an unrecognised status is refused by the reader
        # now, which is a stronger check that fires before this one.
        first.read_text(encoding="utf-8") + "\nquietly appended\n", encoding="utf-8"
    )

    results = fi.check_all(forge)
    assert len(results) == 3, "the walk must continue past a damaged record"


# --------------------------------------------------------------------------
# formatting is not tampering
# --------------------------------------------------------------------------


def test_reformatting_does_not_look_like_tampering(forge: Path) -> None:
    """Line endings and trailing spaces carry no meaning, so they must not fail."""
    settle(forge, "which backend")
    path = forge / "decisions" / fs.list_decisions(forge)[0].filename()

    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("\n", "\r\n") + "   \n\n", encoding="utf-8")

    assert fi.verify_decision(forge, 1).integrity is fi.Integrity.VERIFIED


def test_moving_the_date_on_an_approval_is_detected(forge: Path) -> None:
    """This asserted the opposite, and the reasoning behind it was wrong.

    The date was excluded because re-signing rewrites it — but `Decision.write`
    persists it, so it was a field someone could change while verification kept
    passing. The date on an approval is not decoration; it is when the user
    agreed to the thing. Re-signing recomputes the whole chain anyway, so there
    was never a stability problem being bought.
    """
    settle(forge, "which backend")
    path = forge / "decisions" / fs.list_decisions(forge)[0].filename()
    path.write_text(
        path.read_text(encoding="utf-8").replace("date: ", "date: 1999-01-01 #"),
        encoding="utf-8",
    )
    assert fi.verify_decision(forge, 1).integrity is fi.Integrity.MODIFIED


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------


def test_untrusted_lists_only_the_problems(forge: Path) -> None:
    settle(forge, "good one")
    (forge / "decisions" / "002-hand-written.md").write_text(
        "---\nid: 002\nquestion: hand written\nstatus: decided\n---\n\nbody\n",
        encoding="utf-8",
    )

    problems = fi.untrusted(forge)
    assert [c.decision.id for c in problems] == [2]
    assert problems[0].integrity is fi.Integrity.UNSIGNED


def test_every_state_explains_itself_in_plain_words(forge: Path) -> None:
    """Rule R1 — a user must understand what the tool is telling them."""
    for state in fi.Integrity:
        assert state.explanation and state.explanation[0].islower()


def test_only_verified_counts_as_trusted() -> None:
    assert fi.Integrity.VERIFIED.trusted
    for state in (fi.Integrity.MODIFIED, fi.Integrity.CHAIN_BROKEN, fi.Integrity.UNSIGNED):
        assert not state.trusted


def test_an_open_question_is_never_an_approval(forge: Path) -> None:
    fs.ask(forge, "still deciding")
    assert not fi.is_approved(forge, 1), "asked is not the same as decided"


def test_verifying_an_unknown_id_returns_nothing(forge: Path) -> None:
    assert fi.verify_decision(forge, 99) is None
    assert not fi.is_approved(forge, 99)


def test_no_decisions_at_all_is_not_an_error(project: Path) -> None:
    assert fi.check_all(project / fs.FORGE_DIR) == []
    assert fi.untrusted(project / fs.FORGE_DIR) == []


# --------------------------------------------------------------------------
# the fingerprint is a denylist, so new fields are covered by default
# --------------------------------------------------------------------------


def test_a_new_field_is_protected_without_anyone_remembering(forge: Path) -> None:
    """The reason it is a denylist.

    With a list of fields to hash, a field added later silently escapes the
    fingerprint and can then be altered undetected. Deriving from the record
    minus the exclusions closes that by default.
    """
    settle(forge, "which backend")
    decision = fs.list_decisions(forge)[0]

    before = fi.fingerprint(decision)
    decision.affects = "phase-9"  # a field that carries meaning
    assert fi.fingerprint(decision) != before, "meaningful fields must move the hash"


def test_only_the_fingerprints_themselves_are_left_out(forge: Path) -> None:
    """Everything a record persists is covered, including the date.

    This used to assert `date` was excluded, on the reasoning that Forge
    rewrites it when re-signing. But `Decision.write` persists it, so anything
    excluded is a field someone can change while verification keeps passing —
    and re-signing recomputes the chain anyway.
    """
    settle(forge, "which backend")
    decision = fs.list_decisions(forge)[0]

    covered = fi.signed_fields(decision)
    for field in ("question", "status", "date", "decided_by", "id", "affects"):
        assert field in covered, f"{field} is persisted, so it must be signed"

    for field in (fi.CONTENT_SHA, fi.PREV_SHA, "body"):
        assert field not in covered, "the fingerprints cannot hash themselves"


def test_the_body_is_always_hashed(forge: Path) -> None:
    """It carries most of the meaning, so it is hashed explicitly."""
    settle(forge, "which backend", "# Original\n")
    decision = fs.list_decisions(forge)[0]

    before = fi.fingerprint(decision)
    decision.body = "# Something else entirely\n"
    assert fi.fingerprint(decision) != before

def test_a_header_forge_does_not_model_is_still_signed(forge: Path) -> None:
    """`Decision.read` used to discard anything it did not recognise.

    A header added later would then carry meaning from outside the fingerprint
    — changeable without the hash moving, which is the whole thing this file
    exists to prevent.
    """
    settle(forge, "which backend")
    path = forge / "decisions" / fs.list_decisions(forge)[0].filename()

    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("status:", "approved_by: the-cto\nstatus:", 1), encoding="utf-8")

    decision = fs.Decision.read(path)
    assert decision.extra.get("approved_by") == "the-cto", "the header is kept, not dropped"

    # And it is inside the fingerprint: changing it changes the hash, so the
    # record no longer verifies against the one stored when it was written.
    assert fi.verify_decision(forge, 1).integrity is fi.Integrity.MODIFIED
