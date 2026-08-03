"""Forge Mentor — tamper-evident decision records.

Implements decisions 020 and 021.

The governor's job is to check that a decision was recorded. If it trusts any
file that merely *looks* like a record, insecure code can be walked straight
past the block carrying a document that makes it appear reviewed. That was the
forged-record attack found in the challenge (finding C2).

**This is tamper-evidence, not authentication.** No secret is involved, and
that is deliberate: a secret in the repository proves nothing because anyone
who clones it can use it, and a secret in the machine's keychain stops working
the moment the user switches accounts — which would break decision 011, the
promise the user cared most about.

So instead of proving *who* wrote a record, this proves whether a record has
*changed since it was written*, and whether the history around it is intact.
Authorship is answered by git, which already records who committed what.

    verified      fingerprint matches, chain link is intact
    modified      the text changed after it was written
    chain_broken  a record was inserted, removed, or reordered
    unsigned      no fingerprint — hand-written, allowed but not trusted

What this does not stop, stated plainly: someone who knows the format can
append a *new* record with a correct fingerprint and chain link, because the
fingerprints are computed openly. It converts the attack from invisible to
visible — a forgery now has to arrive as a commit, from a named author, in a
reviewable pull request.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import forge_state as fs

CONTENT_SHA = "content_sha"
PREV_SHA = "prev_sha"

# The fingerprint covers the question, the outcome, and the prose — everything
# that carries meaning. Fields Forge maintains itself (the fingerprints, and
# the date it was written) are excluded, or the hash could never be stable.
SIGNED_FIELDS = ("id", "question", "status", "decided_by", "affects")
EXCLUDED_FROM_HASH = {CONTENT_SHA, PREV_SHA, "date"}

GENESIS = "genesis"  # what the first record points back to


class Integrity(str, Enum):
    VERIFIED = "verified"
    MODIFIED = "modified"
    CHAIN_BROKEN = "chain_broken"
    UNSIGNED = "unsigned"

    @property
    def trusted(self) -> bool:
        """Only a verified record counts as an approval (decision 020)."""
        return self is Integrity.VERIFIED

    @property
    def explanation(self) -> str:
        return {
            Integrity.VERIFIED: "written by Forge and unchanged since",
            Integrity.MODIFIED: "the text changed after it was written",
            Integrity.CHAIN_BROKEN: "a record was inserted, removed, or reordered",
            Integrity.UNSIGNED: "hand-written — readable, but not treated as an approval",
        }[self]


@dataclass(frozen=True)
class Checked:
    """A decision plus what verification concluded about it."""

    decision: fs.Decision
    integrity: Integrity

    @property
    def trusted(self) -> bool:
        return self.integrity.trusted


def fingerprint(decision: fs.Decision) -> str:
    """A stable fingerprint of a record's meaningful content.

    Built from an explicit field list rather than the raw file bytes, so that
    a reformat — line endings, trailing whitespace, key order — does not look
    like tampering. Meaning is what is protected, not byte layout.
    """
    parts = [
        f"{field}={_normalise(getattr(decision, field, ''))}" for field in SIGNED_FIELDS
    ]
    parts.append(f"body={_normalise(decision.body)}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _normalise(value: object) -> str:
    """Collapse formatting differences that carry no meaning."""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    return "\n".join(line.rstrip() for line in text.splitlines())


def sign(decision: fs.Decision, previous: fs.Decision | None) -> dict[str, str]:
    """The two header fields that make a record verifiable."""
    return {
        CONTENT_SHA: fingerprint(decision),
        PREV_SHA: fingerprint(previous) if previous is not None else GENESIS,
    }


def check_all(forge_dir: Path) -> list[Checked]:
    """Verify every record in order, and report what each one is.

    A break in the chain does not stop the walk. Later records are still
    checked and reported, because a single damaged old record must not hide
    the state of everything after it.
    """
    decisions = fs.list_decisions(forge_dir)
    signatures = _read_signatures(forge_dir)

    results: list[Checked] = []
    previous: fs.Decision | None = None

    for decision in decisions:
        stored = signatures.get(decision.id, {})
        results.append(Checked(decision, _classify(decision, previous, stored)))
        previous = decision

    return results


def _classify(
    decision: fs.Decision, previous: fs.Decision | None, stored: dict[str, str]
) -> Integrity:
    content = stored.get(CONTENT_SHA, "").strip()
    if not content:
        return Integrity.UNSIGNED

    if content != fingerprint(decision):
        return Integrity.MODIFIED

    expected_prev = fingerprint(previous) if previous is not None else GENESIS
    if stored.get(PREV_SHA, "").strip() != expected_prev:
        return Integrity.CHAIN_BROKEN

    return Integrity.VERIFIED


def _read_signatures(forge_dir: Path) -> dict[int, dict[str, str]]:
    """Pull the fingerprint fields straight from each file's header.

    Read separately because `fs.Decision` deliberately models only the fields a
    person cares about; the fingerprints are bookkeeping.
    """
    folder = forge_dir / fs.DECISIONS
    if not folder.is_dir():
        return {}

    out: dict[int, dict[str, str]] = {}
    for path in sorted(folder.glob("*.md")):
        try:
            header, _ = fs.parse_header(
                path.read_text(encoding="utf-8", errors="replace"), path
            )
        except fs.StateError:
            continue  # a broken file is reported by the state layer, not here
        try:
            out[int(header.get("id", "0"))] = header
        except ValueError:
            continue
    return out


def verify_decision(forge_dir: Path, decision_id: int) -> Checked | None:
    """Verify one record, in the context of the chain it sits in."""
    for checked in check_all(forge_dir):
        if checked.decision.id == decision_id:
            return checked
    return None


def untrusted(forge_dir: Path) -> list[Checked]:
    """Every record that does not count as an approval."""
    return [c for c in check_all(forge_dir) if not c.trusted]


def is_approved(forge_dir: Path, decision_id: int) -> bool:
    """The question the governor actually asks before allowing a write."""
    checked = verify_decision(forge_dir, decision_id)
    return bool(checked and checked.trusted and checked.decision.status == fs.STATUS_DECIDED)
