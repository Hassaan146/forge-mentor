"""Forge Mentor, putting a request together so the cache can do its job.

A model caches a request by its *prefix*. Everything up to the first byte that
differs from last time is reused cheaply; from that byte onward it is paid for
again. So the order of the pieces decides the bill: stable things first,
changing things last. Get it backwards and the cache never hits once.

The failure this module exists to catch is quiet. Nothing errors, nothing looks
wrong, a timestamp, a session id, or a re-sorted dictionary slips into the
frozen part of the prompt, the prefix changes on every call, and the cache
silently stops working. The only symptom is the bill, and on a subscription
there is no bill to notice.

So the prefix is fingerprinted and the fingerprint is remembered. When it moves,
Forge says so and names the block that moved. And blocks declared frozen are
scanned for the things that are known to move, a date, a clock time, a uuid, a
run of digits long enough to be an id, because the cheapest time to catch a
cache killer is before it is sent.

Ordering here, measurement in `forge_meter`. The meter's `cache_saving` figure
is how you tell whether any of this is working.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

import forge_state as fs

ASSEMBLY_FILE = "assembly.md"

# Roughly four characters to a token. Used only to say "about this big" in a
# report — never for billing, which comes from measured counts in forge_meter.
CHARS_PER_TOKEN = 4


class Tier(IntEnum):
    """How often a block changes. Lower goes earlier in the request."""

    FROZEN = 0  # the contract and the skills, identical every call
    SLOW = 1  # decisions already recorded; grows, never rewrites
    VOLATILE = 2  # this step, this file, this question

    @property
    def label(self) -> str:
        return {Tier.FROZEN: "frozen", Tier.SLOW: "slow", Tier.VOLATILE: "volatile"}[self]


# Things that must never appear in a frozen block. Each one changes per call,
# and one of them is enough to cost the whole cached prefix.
_CACHE_KILLERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a date", re.compile(r"\b\d{4}-\d{2}-\d{2}\b")),
    ("a clock time", re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b")),
    (
        "a uuid",
        re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            re.IGNORECASE,
        ),
    ),
    ("an id-like number", re.compile(r"\b\d{9,}\b")),
    # No leading \b here: a slash is not a word character, so a boundary never
    # matches before "/tmp/" and the pattern silently found nothing.
    ("a temporary path", re.compile(r"(?i)(?:/tmp/|[A-Z]:\\+Users\\+[^\\\s]+\\+AppData)")),
)


class AssemblyError(Exception):
    """A request could not be assembled safely."""


@dataclass(frozen=True)
class Block:
    """One labelled piece of a request."""

    name: str
    text: str
    tier: Tier = Tier.VOLATILE

    @property
    def size(self) -> int:
        return len(self.text)


@dataclass
class Assembly:
    """An assembled request, and what can be said about its cacheability."""

    text: str = ""
    prefix: str = ""
    prefix_sha: str = ""
    order: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    @property
    def prefix_tokens(self) -> int:
        """About how many tokens sit in the cacheable prefix."""
        return len(self.prefix) // CHARS_PER_TOKEN

    @property
    def cacheable_share(self) -> float:
        return len(self.prefix) / len(self.text) if self.text else 0.0


def _kill_risks(block: Block) -> list[str]:
    """Anything in a cached block that will move between calls.

    Both frozen *and* slow blocks are scanned. Only the volatile tier sits
    outside the prefix, so a date in a slow block costs exactly as much as a
    date in a frozen one, the first draft checked frozen alone and would have
    missed half the cases it exists to catch.
    """
    if block.tier is Tier.VOLATILE:
        return []
    found = []
    for what, pattern in _CACHE_KILLERS:
        match = pattern.search(block.text)
        if match:
            found.append(f"{block.name}: contains {what} ({match.group(0)!r})")
    return found


def assemble(blocks: list[Block]) -> Assembly:
    """Order the blocks so the stable part comes first, and report the risks.

    Sorting is stable within a tier, so the caller's declared order is kept.
    That matters more than it looks: a set or a plain dict comprehension
    upstream will reorder blocks between runs and break the prefix without ever
    touching a byte of their content.
    """
    if not blocks:
        return Assembly()

    seen: set[str] = set()
    for block in blocks:
        if block.name in seen:
            raise AssemblyError(
                f"Two blocks are both called {block.name!r}. "
                "Names identify a block across calls, so they have to be unique."
            )
        seen.add(block.name)

    ordered = sorted(blocks, key=lambda b: b.tier)
    prefix_blocks = [b for b in ordered if b.tier is not Tier.VOLATILE]

    joined = "\n\n".join(b.text for b in ordered)
    prefix = "\n\n".join(b.text for b in prefix_blocks)

    risks: list[str] = []
    for block in blocks:
        risks.extend(_kill_risks(block))
    if not prefix_blocks:
        risks.append("nothing is cacheable: every block is volatile")

    return Assembly(
        text=joined,
        prefix=prefix,
        prefix_sha=hashlib.sha256(prefix.encode("utf-8")).hexdigest()[:16],
        order=[f"{b.name} ({b.tier.label})" for b in ordered],
        risks=risks,
    )


# --------------------------------------------------------------------------
# remembering the prefix, so drift is visible
# --------------------------------------------------------------------------


def last_prefix(forge_dir: Path) -> str:
    path = forge_dir / ASSEMBLY_FILE
    if not path.is_file():
        return ""
    try:
        header, _ = fs.parse_header(path.read_text(encoding="utf-8"), path)
    except (fs.StateError, OSError):
        return ""
    return str(header.get("prefix_sha", "")).strip()


def remember_prefix(forge_dir: Path, assembly: Assembly) -> None:
    path = forge_dir / ASSEMBLY_FILE
    header = {
        "type": "assembly",
        "prefix_sha": assembly.prefix_sha,
        "prefix_tokens": str(assembly.prefix_tokens),
    }
    body = (
        "# The cached part of each request\n\n"
        "The fingerprint above covers everything sent before the changing part of a\n"
        "request. While it holds still, the model reuses that text instead of reading\n"
        "it again. When it moves, Forge says so, a moving prefix means the cache is\n"
        "not working, and nothing else reports that.\n"
    )
    try:
        forge_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(fs.render_header(header) + body, encoding="utf-8")
    except OSError:
        pass  # failing to record the fingerprint must not fail the request


def check(forge_dir: Path, assembly: Assembly) -> dict[str, object]:
    """Assemble-time report: did the cacheable prefix move since last time?"""
    previous = last_prefix(forge_dir)
    drifted = bool(previous) and previous != assembly.prefix_sha
    remember_prefix(forge_dir, assembly)

    return {
        "prefix_sha": assembly.prefix_sha,
        "prefix_tokens": assembly.prefix_tokens,
        "cacheable_share": round(assembly.cacheable_share, 4),
        "order": assembly.order,
        "risks": assembly.risks,
        "drifted": drifted,
        "previous_sha": previous,
        "note": (
            "The cached part of the request changed since the last call, so it was "
            "paid for again. Something in a frozen or slow block moved."
            if drifted
            else "The cached part of the request is unchanged."
        ),
    }
