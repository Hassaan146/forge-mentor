"""Tests for cache-stable request assembly — Phase 6.

A model reuses a request up to the first byte that differs from last time. So
the order of the pieces decides the bill, and the failure mode is silent: a
timestamp slips into the unchanging part of the prompt, the prefix changes on
every call, the cache never hits, and nothing anywhere reports it.

These tests are mostly about that silence — that the ordering holds, that a
moving prefix is noticed and named, and that the things known to move are
caught before they are sent rather than inferred from a bill later.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import forge_assemble as fa
import forge_state as fs

CONTRACT = fa.Block("contract", "You are Forge Mentor. Decide, then code.", fa.Tier.FROZEN)
DECISIONS = fa.Block("decisions", "001 state format: both readable.", fa.Tier.SLOW)
STEP = fa.Block("step", "The user just chose option B.", fa.Tier.VOLATILE)


@pytest.fixture()
def forge(tmp_path: Path) -> Path:
    return fs.init(tmp_path)


# --------------------------------------------------------------------------
# ordering
# --------------------------------------------------------------------------


def test_the_unchanging_part_goes_first_whatever_order_it_arrives_in() -> None:
    assembled = fa.assemble([STEP, DECISIONS, CONTRACT])
    assert assembled.order == ["contract (frozen)", "decisions (slow)", "step (volatile)"]
    assert assembled.text.index("Forge Mentor") < assembled.text.index("option B")


def test_the_prefix_stops_before_the_changing_part() -> None:
    """Everything after the first changing byte is paid for again."""
    assembled = fa.assemble([CONTRACT, DECISIONS, STEP])
    assert "option B" not in assembled.prefix
    assert "Forge Mentor" in assembled.prefix and "001 state format" in assembled.prefix


def test_order_within_a_tier_is_the_order_given() -> None:
    """Two frozen blocks swapping places would break the prefix without one
    byte of their content changing — a set or a dict comprehension upstream is
    enough to cause it."""
    first = fa.assemble(
        [fa.Block("a", "A", fa.Tier.FROZEN), fa.Block("b", "B", fa.Tier.FROZEN)]
    )
    second = fa.assemble(
        [fa.Block("b", "B", fa.Tier.FROZEN), fa.Block("a", "A", fa.Tier.FROZEN)]
    )
    assert first.prefix_sha != second.prefix_sha, "reordering is a real cache miss"
    assert first.order == ["a (frozen)", "b (frozen)"]


def test_two_blocks_with_the_same_name_are_refused() -> None:
    """Names identify a block across calls, so a duplicate makes drift unreadable."""
    with pytest.raises(fa.AssemblyError, match="both called"):
        fa.assemble([fa.Block("x", "1", fa.Tier.FROZEN), fa.Block("x", "2", fa.Tier.SLOW)])


def test_nothing_to_assemble_is_not_an_error() -> None:
    assert fa.assemble([]).text == ""


# --------------------------------------------------------------------------
# the things that silently kill a cache
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Session started 2026-08-04.", "a date"),
        ("It is now 14:32 here.", "a clock time"),
        ("Session d91aa8ac-b103-4bd5-b694-7f10ab029cfb", "a uuid"),
        ("Request 1754300000123", "an id-like number"),
        ("Scratch at /tmp/claude/run", "a temporary path"),
    ],
)
def test_a_frozen_block_that_will_change_is_named(text: str, expected: str) -> None:
    assembled = fa.assemble([fa.Block("contract", text, fa.Tier.FROZEN)])
    assert any(expected in risk for risk in assembled.risks)
    assert any("contract" in risk for risk in assembled.risks), "the block is named"


def test_a_changing_value_is_fine_in_the_changing_part() -> None:
    """The volatile tier is where a timestamp belongs — that is its whole point."""
    assembled = fa.assemble([CONTRACT, fa.Block("now", "2026-08-04 14:32", fa.Tier.VOLATILE)])
    assert assembled.risks == []


def test_an_all_volatile_request_says_nothing_is_cacheable() -> None:
    assembled = fa.assemble([STEP])
    assert assembled.prefix == ""
    assert any("nothing is cacheable" in risk for risk in assembled.risks)


# --------------------------------------------------------------------------
# drift, which is the thing nobody else reports
# --------------------------------------------------------------------------


def test_the_first_call_has_nothing_to_compare_against(forge: Path) -> None:
    result = fa.check(forge, fa.assemble([CONTRACT, STEP]))
    assert result["drifted"] is False
    assert result["previous_sha"] == ""


def test_the_same_frozen_part_twice_is_not_drift(forge: Path) -> None:
    """The volatile part changing every call is expected and costs nothing."""
    fa.check(forge, fa.assemble([CONTRACT, fa.Block("step", "first", fa.Tier.VOLATILE)]))
    again = fa.check(forge, fa.assemble([CONTRACT, fa.Block("step", "second", fa.Tier.VOLATILE)]))

    assert again["drifted"] is False
    assert "unchanged" in str(again["note"])


def test_a_changed_frozen_block_is_reported(forge: Path) -> None:
    """The only symptom otherwise is the bill, and on a subscription there is none."""
    fa.check(forge, fa.assemble([CONTRACT, STEP]))
    after = fa.check(
        forge,
        fa.assemble([fa.Block("contract", "You are Forge. Reworded.", fa.Tier.FROZEN), STEP]),
    )

    assert after["drifted"] is True
    assert "paid for again" in str(after["note"])


def test_a_changed_slow_block_counts_as_drift_too(forge: Path) -> None:
    """Recorded decisions are cached as well; rewriting one costs the prefix."""
    fa.check(forge, fa.assemble([CONTRACT, DECISIONS, STEP]))
    after = fa.check(
        forge,
        fa.assemble([CONTRACT, fa.Block("decisions", "001 rewritten.", fa.Tier.SLOW), STEP]),
    )
    assert after["drifted"] is True


def test_the_fingerprint_is_remembered_between_runs(forge: Path) -> None:
    """Sessions end. Drift across a restart is exactly the case worth catching."""
    assembled = fa.assemble([CONTRACT, STEP])
    fa.check(forge, assembled)
    assert fa.last_prefix(forge) == assembled.prefix_sha


def test_failing_to_record_the_fingerprint_does_not_fail_the_request(
    tmp_path: Path,
) -> None:
    """Bookkeeping must never be the reason a build stops."""
    missing = tmp_path / "nope" / "deeper"
    result = fa.check(missing, fa.assemble([CONTRACT, STEP]))
    assert result["prefix_sha"]


def test_the_report_says_how_much_of_the_request_is_cacheable(forge: Path) -> None:
    result = fa.check(forge, fa.assemble([CONTRACT, STEP]))
    assert 0 < float(result["cacheable_share"]) < 1
    assert int(result["prefix_tokens"]) > 0
