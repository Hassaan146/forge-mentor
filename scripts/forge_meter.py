"""Forge Mentor — what this build has cost so far.

Decision 008 promised a usage meter and warnings before the user hits a wall.
Decision 024 settled where the numbers come from, and the answer is unusual
enough to be worth stating at the top:

**Forge does not call any model.** Claude Code does. Forge is a plugin inside
the thing doing the spending, so it has no request of its own to count. What it
has instead is Claude Code's own session log — every assistant turn is appended
to `~/.claude/projects/<project>/<session>.jsonl` with the real token counts
attached, including the cache columns. Those are measured numbers, not
estimates, and the cache column is the one that shows whether the cache-stable
assembly is earning its keep.

**Tokens are the headline, money is optional.** Most users are on a
subscription, where a dollar figure is fiction. So the meter reports tokens
always, and converts to money only when a price list has been configured. It
never invents a price to fill the column — decision 024's rule was that a wrong
number is worse than a missing one, because a wrong number gets believed.

**Nothing blocks on this.** The meter is a display. If Claude Code changes its
log format tomorrow, `available` goes false, the banner says usage is
unavailable, and every other part of Forge carries on.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import forge_state as fs
import forge_ui as ui

USAGE_FILE = "usage.md"

# Decision 008: warn at roughly half, three-quarters, and nearly full.
THRESHOLDS: tuple[tuple[int, str], ...] = (
    (50, "about half"),
    (75, "three quarters"),
    (90, "nearly full"),
)


class MeterError(Exception):
    """Usage could not be read. Never fatal — the caller reports and moves on."""


# --------------------------------------------------------------------------
# finding Claude Code's own logs
# --------------------------------------------------------------------------


def transcript_root() -> Path:
    """Where Claude Code keeps its session logs."""
    # Honoured by Claude Code itself, so a user with a relocated config is not
    # silently reported as having no usage.
    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    base = Path(configured) if configured else Path.home() / ".claude"
    return base / "projects"


def encode_project(project: Path) -> str:
    """The folder name Claude Code derives from a working directory.

    Every character that is not a letter or digit becomes a hyphen, so
    `H:\\Skills\\Project` becomes `H--Skills-Project`. The rule is inferred
    rather than documented, which is why `session_files` confirms the result
    against the `cwd` recorded inside the files instead of trusting the name.
    """
    return re.sub(r"[^a-zA-Z0-9]", "-", str(project))


def session_files(project: Path) -> list[Path]:
    """Every session log belonging to this project.

    Tries the derived folder name first because it is one stat call. Falls back
    to reading the `cwd` field out of each candidate folder, so a change to the
    naming rule degrades to "slower" rather than "reports zero".
    """
    root = transcript_root()
    if not root.is_dir():
        return []

    direct = root / encode_project(project)
    if direct.is_dir():
        return sorted(direct.glob("*.jsonl"))

    wanted = str(project).replace("/", "\\").lower()
    found: list[Path] = []
    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.jsonl")):
            if _first_cwd(path) == wanted:
                found.extend(sorted(folder.glob("*.jsonl")))
                break
    return found


def _first_cwd(path: Path) -> str | None:
    """The working directory a session ran in, from its first record."""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cwd = record.get("cwd")
                if cwd:
                    return str(cwd).replace("/", "\\").lower()
    except OSError:
        return None
    return None


# --------------------------------------------------------------------------
# reading the turns
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Turn:
    """One model response, and what it cost in tokens."""

    message_id: str
    model: str
    fresh_input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    sidechain: bool = False

    @property
    def billed_input(self) -> int:
        """Input the user is charged for. Cache reads are cheap but not free."""
        return self.fresh_input + self.cache_write + self.cache_read

    @property
    def total(self) -> int:
        return self.billed_input + self.output


def read_turns(project: Path) -> list[Turn]:
    """Every distinct model response for this project.

    **Deduplicated by `message.id`, and that is the whole trick.** One assistant
    message containing several tool calls is written to the log as several
    records, each carrying an identical copy of the same usage block. Summing
    the records instead of the responses over-counted by a factor of three on
    the first session tested. The API response id is the real unit of spend.
    """
    seen: dict[str, Turn] = {}

    for path in session_files(project):
        try:
            handle = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue  # a log we cannot read is not a reason to report nothing
        with handle:
            for line in handle:
                turn = _turn_from(line)
                if turn is not None:
                    seen.setdefault(turn.message_id, turn)

    return list(seen.values())


def _turn_from(line: str) -> Turn | None:
    line = line.strip()
    if not line:
        return None
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None  # a partially written last line is normal, not an error

    if record.get("type") != "assistant":
        return None

    message = record.get("message")
    if not isinstance(message, dict):
        return None
    usage = message.get("usage")
    if not isinstance(usage, dict):
        return None

    message_id = message.get("id")
    if not message_id:
        return None

    return Turn(
        message_id=str(message_id),
        model=str(message.get("model") or "unknown"),
        fresh_input=_count(usage, "input_tokens"),
        output=_count(usage, "output_tokens"),
        cache_read=_count(usage, "cache_read_input_tokens"),
        cache_write=_count(usage, "cache_creation_input_tokens"),
        sidechain=bool(record.get("isSidechain")),
    )


def _count(usage: dict, key: str) -> int:
    value = usage.get(key)
    return value if isinstance(value, int) and value >= 0 else 0


# --------------------------------------------------------------------------
# adding it up
# --------------------------------------------------------------------------


@dataclass
class Usage:
    """What this project has spent, in tokens."""

    turns: int = 0
    fresh_input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    by_model: dict[str, int] = field(default_factory=dict)
    subagent_turns: int = 0
    available: bool = True
    reason: str = ""

    @property
    def total(self) -> int:
        return self.fresh_input + self.cache_write + self.cache_read + self.output

    @property
    def cache_saving(self) -> float:
        """Share of input served from cache, 0.0–1.0.

        The number the cache-stable assembly exists to move. Reported rather
        than converted to money, because the discount differs per plan.
        """
        billed_input = self.fresh_input + self.cache_write + self.cache_read
        return self.cache_read / billed_input if billed_input else 0.0


def summarise(turns: list[Turn]) -> Usage:
    usage = Usage(turns=len(turns))
    for turn in turns:
        usage.fresh_input += turn.fresh_input
        usage.output += turn.output
        usage.cache_read += turn.cache_read
        usage.cache_write += turn.cache_write
        usage.by_model[turn.model] = usage.by_model.get(turn.model, 0) + turn.total
        if turn.sidechain:
            usage.subagent_turns += 1
    return usage


def measure(project: Path) -> Usage:
    """Read and total this project's usage. Never raises."""
    try:
        root = transcript_root()
        if not root.is_dir():
            return Usage(
                available=False,
                reason="Claude Code keeps no session logs on this machine.",
            )
        turns = read_turns(project)
    except OSError as exc:
        return Usage(available=False, reason=f"Could not read the session logs: {exc}")

    if not turns:
        return Usage(
            available=False,
            reason="No sessions recorded for this project yet.",
        )
    return summarise(turns)


# --------------------------------------------------------------------------
# thresholds — warned once each, never repeated (decision 008)
# --------------------------------------------------------------------------


def budget(forge_dir: Path) -> int:
    """The token budget the user set, or 0 for none.

    Absent by default and never inferred. A subscription has no token budget
    Forge can know, and decision 024 forbids inventing one to make the meter
    look busy — a threshold crossed against a made-up ceiling is a false alarm.
    """
    path = forge_dir / fs.SETTINGS
    if not path.is_file():
        return 0
    try:
        header, _ = fs.parse_header(path.read_text(encoding="utf-8"), path)
    except (fs.StateError, OSError):
        return 0
    raw = str(header.get("token_budget", "")).replace("_", "").replace(",", "").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _already_warned(forge_dir: Path) -> set[int]:
    path = forge_dir / USAGE_FILE
    if not path.is_file():
        return set()
    try:
        header, _ = fs.parse_header(path.read_text(encoding="utf-8"), path)
    except (fs.StateError, OSError):
        return set()
    out: set[int] = set()
    for piece in str(header.get("warned_at", "")).split(","):
        piece = piece.strip()
        if piece.isdigit():
            out.add(int(piece))
    return out


def _remember_warning(forge_dir: Path, marks: set[int]) -> None:
    path = forge_dir / USAGE_FILE
    header = {
        "type": "usage",
        "warned_at": ",".join(str(m) for m in sorted(marks)),
    }
    body = (
        "# Usage warnings already given\n\n"
        "Bookkeeping only. Decision 008: each threshold is stated once, not repeated,\n"
        "so a warning informs rather than nags. Delete this file to hear them again.\n"
    )
    try:
        forge_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(fs.render_header(header) + body, encoding="utf-8")
    except OSError:
        pass  # a meter that cannot write its notes still reports correctly


def threshold_crossed(usage: Usage, limit: int) -> tuple[int, str] | None:
    """The highest threshold this usage has passed, if any."""
    if limit <= 0 or not usage.available:
        return None
    percent = usage.total * 100 / limit
    passed = [(mark, label) for mark, label in THRESHOLDS if percent >= mark]
    return passed[-1] if passed else None


def warning(forge_dir: Path, usage: Usage) -> str:
    """The warning to show now, or empty if there is nothing new to say."""
    limit = budget(forge_dir)
    crossed = threshold_crossed(usage, limit)
    if crossed is None:
        return ""

    mark, label = crossed
    already = _already_warned(forge_dir)
    if mark in already:
        return ""

    _remember_warning(forge_dir, already | {mark})
    return (
        f"\n  {ui.RED}{ui.BOLD}⚠  Usage is {label}{ui.RESET}"
        f"  {ui.DIM}{usage.total:,} of {limit:,} tokens{ui.RESET}\n"
        f"     {ui.DIM}Your notes live in the repository, so you can switch accounts\n"
        f"     and carry on without losing anything.{ui.RESET}\n"
    )


# --------------------------------------------------------------------------
# showing it
# --------------------------------------------------------------------------


def render(usage: Usage) -> str:
    """The meter, as a person reads it."""
    if not usage.available:
        return (
            f"\n  {ui.DIM}Usage unavailable — {usage.reason}{ui.RESET}\n"
            f"  {ui.DIM}Nothing else is affected.{ui.RESET}\n"
        )

    lines = [
        "",
        f"  {ui.AMBER}{ui.BOLD}{ui.MARK} Usage{ui.RESET}"
        f"  {ui.DIM}{usage.turns:,} model replies{ui.RESET}",
        "",
        f"     {ui.DIM}sent (new){ui.RESET}      {usage.fresh_input:>12,}",
        f"     {ui.DIM}sent (cached){ui.RESET}   {usage.cache_read:>12,}"
        f"   {ui.GREEN}{usage.cache_saving:.0%} reused{ui.RESET}",
        f"     {ui.DIM}cache written{ui.RESET}   {usage.cache_write:>12,}",
        f"     {ui.DIM}received{ui.RESET}        {usage.output:>12,}",
        f"     {ui.BOLD}total{ui.RESET}           {usage.total:>12,}",
    ]

    if usage.by_model:
        lines += ["", f"     {ui.DIM}by model{ui.RESET}"]
        for model, total in sorted(usage.by_model.items(), key=lambda kv: -kv[1]):
            lines.append(f"       {ui.PURPLE}{model:<22}{ui.RESET} {total:>12,}")

    if usage.subagent_turns:
        lines.append(
            f"\n     {ui.DIM}{usage.subagent_turns:,} of those ran in subagents{ui.RESET}"
        )

    lines.append("")
    return "\n".join(lines)


def report(project: Path, forge_dir: Path | None = None) -> dict[str, object]:
    """Usage as data, for the MCP tool and for tests."""
    usage = measure(project)
    out: dict[str, object] = {
        "available": usage.available,
        "turns": usage.turns,
        "fresh_input": usage.fresh_input,
        "cache_read": usage.cache_read,
        "cache_write": usage.cache_write,
        "output": usage.output,
        "total": usage.total,
        "cache_saving": round(usage.cache_saving, 4),
        "by_model": usage.by_model,
        "subagent_turns": usage.subagent_turns,
    }
    if not usage.available:
        out["reason"] = usage.reason
    if forge_dir is not None:
        limit = budget(forge_dir)
        out["budget"] = limit
        crossed = threshold_crossed(usage, limit)
        out["threshold"] = crossed[1] if crossed else None
    return out


if __name__ == "__main__":  # pragma: no cover - CLI surface
    import sys

    here = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    print(render(measure(here)))
