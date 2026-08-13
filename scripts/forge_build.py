"""Forge Mentor: the code arrives one file at a time, and each one is explained.

**What this replaces.** A decided step went to the builder and came back as
four files. Every one of them was permitted, every one was covered by the
decision, and the user watched an application appear. They can defend the
decision, because they made it. They cannot defend the code, because they met
it all at once and in a finished state, which is the same problem the product
exists to solve moved one level down.

**So the unit is the file, and the price of the next one is explaining the
last.** Before a file is written the builder says what it is, why it exists and
how it works. Those three, in that order, and none of them optional: what it is
without why leaves somebody who can read the code and not question it; why
without how leaves somebody who agrees with a thing they could not maintain.

**Skeleton first.** The order is not the order the builder finds convenient. A
file that is the shape of the thing comes before a file that fills it in, so
what the user sees is a project taking form rather than a pile arriving
alphabetically.

The ledger is a file in the notes, so the sequence survives the session ending
in the middle of it, like everything else here (decision 019).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import forge_state as fs

PLANS = "builds"

_ROW = re.compile(
    r"^(?P<state>\[[ x]\])\s+(?P<path>\S+)(?:\s+·\s+(?P<explained>explained))?\s*$"
)


@dataclass
class Planned:
    """One file this step will touch, and whether it has been met yet."""

    path: str
    written: bool = False
    explained: bool = False

    def row(self) -> str:
        mark = "[x]" if self.written else "[ ]"
        return f"{mark} {self.path}" + (" · explained" if self.explained else "")


def plan_path(forge_dir: Path, marker: str) -> Path:
    safe = marker.replace(":", "-").replace("/", "-")
    return forge_dir / PLANS / f"{safe}.md"


def read_plan(forge_dir: Path, marker: str) -> list[Planned]:
    path = plan_path(forge_dir, marker)
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    out: list[Planned] = []
    for line in text.splitlines():
        match = _ROW.match(line.strip())
        if match:
            out.append(
                Planned(
                    path=match.group("path"),
                    written=match.group("state") == "[x]",
                    explained=bool(match.group("explained")),
                )
            )
    return out


def write_plan(forge_dir: Path, marker: str, files: list[Planned]) -> Path:
    path = plan_path(forge_dir, marker)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        fs.render_header(
            {
                "type": "build-plan",
                "step": marker,
                "files": str(len(files)),
                "written": str(sum(1 for f in files if f.written)),
            }
        ),
        "",
        "# The files this step touches, in the order they are written",
        "",
        "Skeleton first: the shape of the thing before the detail that fills it in.",
        "Each one is explained before the next is written.",
        "",
    ]
    body += [item.row() for item in files]
    body.append("")
    path.write_text("\n".join(body), encoding="utf-8")
    return path


def plan(forge_dir: Path, marker: str, paths: list[str]) -> list[Planned]:
    """Set the order for a step. Refuses to reorder work already done.

    Rewriting a list whose files are written would renumber history: the file
    somebody was shown as the first of four becomes the third of six, and the
    explanation they were given no longer matches the sequence they saw.
    """
    existing = read_plan(forge_dir, marker)
    if any(item.written for item in existing):
        raise fs.StateError(
            "This step has already started writing files, so its order cannot be "
            "rewritten. Add to the end instead.",
            plan_path(forge_dir, marker),
            repair="use add_file to extend the list",
        )

    wanted = [Planned(path=str(p).strip()) for p in paths if str(p).strip()]
    if not wanted:
        raise fs.StateError("A build plan needs at least one file.", plan_path(forge_dir, marker))

    write_plan(forge_dir, marker, wanted)
    return wanted


def add_file(forge_dir: Path, marker: str, path: str) -> list[Planned]:
    """Extend the list. The escape hatch, and it leaves a trace.

    A ledger with no way to grow is a ledger somebody works around, and working
    around it means writing files nobody announced. Appending is visible in the
    file, which is the point.
    """
    files = read_plan(forge_dir, marker)
    if any(item.path == path for item in files):
        return files
    files.append(Planned(path=str(path).strip()))
    write_plan(forge_dir, marker, files)
    return files


def next_file(forge_dir: Path, marker: str) -> Planned | None:
    """The one file that may be written now, or None when the step is done."""
    for item in read_plan(forge_dir, marker):
        if not item.written:
            return item
    return None


def owed_explanation(forge_dir: Path, marker: str) -> Planned | None:
    """A file that was written and never explained. Nothing else may be written."""
    for item in read_plan(forge_dir, marker):
        if item.written and not item.explained:
            return item
    return None


def mark_written(forge_dir: Path, marker: str, path: str) -> None:
    files = read_plan(forge_dir, marker)
    for item in files:
        if item.path == path:
            item.written = True
    write_plan(forge_dir, marker, files)


def mark_explained(forge_dir: Path, marker: str, path: str) -> None:
    files = read_plan(forge_dir, marker)
    for item in files:
        if item.path == path:
            item.written = True
            item.explained = True
    write_plan(forge_dir, marker, files)


def allowed(forge_dir: Path, marker: str, target: Path, project: Path) -> tuple[bool, str]:
    """May this write happen right now?

    Three answers, and the middle one is the whole feature:

    * No plan for this step: allowed. The ledger is opt-in per step, and a step
      that never planned its files is governed by the gates that came before.
    * A file written but not explained: refused, whatever the target is. This is
      what makes the explanation the price of the next file rather than a note
      somebody meant to add at the end.
    * Anything other than the next file in the list: refused, and it names the
      file that was expected.
    """
    files = read_plan(forge_dir, marker)
    if not files:
        return True, ""

    owed = owed_explanation(forge_dir, marker)
    if owed is not None:
        return False, (
            f"{owed.path} was written and has not been explained yet. Say what it "
            "is, why it exists and how it works, then the next file can be written."
        )

    expected = next_file(forge_dir, marker)
    if expected is None:
        return True, ""  # every planned file is done; the step's own gates apply

    try:
        wanted = (project / expected.path).resolve()
    except OSError:
        return True, ""

    if target.resolve() == wanted:
        return True, ""

    return False, (
        f"This step writes {expected.path} next. {target.name} is not on its list: "
        "add it with add_file if it belongs, or write the planned one first."
    )
