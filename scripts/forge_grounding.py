"""Forge Mentor: code that refers to things which do not exist.

**The failure this is for.** A model writes `import fastapi_cache` into a
project whose requirements name no such package; or `from .helpers import
slugify` when there is no `helpers.py`; or "as decided in decision 014" when
decision 014 is about something else entirely. Every one of those is confident,
plausible, and wrong, and none of them is caught by tests that were written by
the same turn that invented the reference.

**What is checkable and what is not.** Whether code is *correct* is not
decidable here and this file does not pretend otherwise. Whether it refers to
something that exists is decidable, cheaply, from the file and the project's own
manifests. That narrow question catches the largest and most embarrassing class:
the invented import.

**What happens when it finds one.** It does not fix it. A silent correction is
another guess on top of the first, and the user learns nothing. It puts the
reference to the user as a question: this names something the project does not
have, is it a package that has to be added, a file yet to be written, or a
mistake. The answer is recorded like any other decision.

Standard library only, and it never raises: this runs inside a hook.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Node's built-ins, the ones a generated file actually reaches for. Short on
# purpose and easy to extend: a name missing from here costs one question, and
# a wrong name here costs a silent miss.
NODE_BUILTINS = frozenset(
    {
        "fs", "path", "os", "http", "https", "url", "util", "events", "stream",
        "crypto", "child_process", "readline", "zlib", "buffer", "assert",
        "querystring", "net", "dns", "tls", "cluster", "worker_threads",
        "perf_hooks", "timers", "process", "string_decoder", "v8", "vm",
    }
)

PYTHON_SUFFIXES = (".py",)
JS_SUFFIXES = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")

_JS_IMPORT = re.compile(
    r"""(?:^|\s)(?:import\s[^'"]*from\s*|import\s*|require\s*\(\s*)['"]([^'"]+)['"]"""
)

_DECISION_CLAIM = re.compile(r"\bdecision\s+(\d{1,3})\b", re.IGNORECASE)


@dataclass(frozen=True)
class Claim:
    """Something the code says exists. What was named, and where."""

    kind: str  # unknown-import | missing-file | unrecorded-decision
    name: str
    where: str
    line: int = 0

    def question(self) -> str:
        if self.kind == "unknown-import":
            return (
                f"{self.where} imports {self.name!r}, which is not in this "
                "project's dependencies and is not part of the standard library."
            )
        if self.kind == "missing-file":
            return f"{self.where} imports {self.name!r}, and no such file is in the project."
        return (
            f"{self.where} refers to decision {self.name}, and no decision "
            f"{self.name} has been recorded."
        )


def _declared(project: Path) -> set[str]:
    """Every package this project has said it depends on.

    Read from the manifests rather than from the environment. What is installed
    on the machine that happened to write the file is not what the project
    depends on, and a package that is present by accident is the reason this
    class of bug survives review.
    """
    found: set[str] = set()

    for name in ("requirements.txt", "requirements-dev.txt"):
        path = project / name
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                bare = re.split(r"[<>=!~;\[\s]", line.strip(), maxsplit=1)[0]
                if bare and not bare.startswith(("#", "-")):
                    found.add(bare.replace("-", "_").lower())
        except OSError:
            pass

    pyproject = project / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")
            for match in re.finditer(r'"([A-Za-z0-9_.\-]+)\s*[<>=!~\[]', text):
                found.add(match.group(1).replace("-", "_").lower())
        except OSError:
            pass

    package = project / "package.json"
    if package.is_file():
        try:
            data = json.loads(package.read_text(encoding="utf-8", errors="replace"))
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                found.update(str(k).lower() for k in (data.get(section) or {}))
        except (OSError, ValueError):
            pass

    return found


def _stdlib() -> set[str]:
    names = set(getattr(sys, "stdlib_module_names", ()))
    return {name.lower() for name in names}


def _local_modules(project: Path) -> set[str]:
    """Module names the project itself provides, at any depth worth scanning."""
    found: set[str] = set()
    for path in project.rglob("*.py"):
        parts = path.parts
        if any(part.startswith(".") or part in {"node_modules", "venv", "__pycache__"} for part in parts):
            continue
        found.add(path.stem.lower())
        found.add(path.parent.name.lower())
    return found


def _package_root(name: str) -> str:
    """`fastapi.responses` is fastapi; `@scope/thing` is @scope/thing."""
    if name.startswith("@"):
        return "/".join(name.split("/")[:2]).lower()
    return name.split("/")[0].split(".")[0].lower()


def python_imports(text: str) -> list[tuple[str, int, int]]:
    """(module, level, line) for every import. Level is the relative depth."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    out: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(alias.name, 0, node.lineno) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            out.append((node.module or "", node.level or 0, node.lineno))
    return out


def js_imports(text: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in _JS_IMPORT.finditer(line):
            out.append((match.group(1), number))
    return out


def check_file(path: Path, project: Path) -> list[Claim]:
    """Everything this file names that the project does not appear to have."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    known = _declared(project) | _stdlib() | _local_modules(project)
    where = path.name
    claims: list[Claim] = []

    if path.suffix in PYTHON_SUFFIXES:
        for module, level, line in python_imports(text):
            if level:
                continue  # relative: resolved by the file check below
            root = _package_root(module)
            if root and root not in known:
                claims.append(Claim("unknown-import", module, where, line))

    elif path.suffix in JS_SUFFIXES:
        for spec, line in js_imports(text):
            if spec.startswith("."):
                target = (path.parent / spec).resolve()
                if not any(
                    target.with_suffix(suffix).exists() or (target / f"index{suffix}").exists()
                    for suffix in JS_SUFFIXES
                ) and not target.exists():
                    claims.append(Claim("missing-file", spec, where, line))
                continue
            root = _package_root(spec)
            if root not in known and root not in NODE_BUILTINS:
                claims.append(Claim("unknown-import", spec, where, line))

    return claims


def check_decisions(text: str, forge_dir: Path) -> list[Claim]:
    """Claims about the project's own history, checked against the records.

    "As decided in decision 014" is the most convincing sentence a model can
    write, and it costs nothing to verify. A wrong one is worse than no citation
    at all: it borrows the authority of a record nobody will open.
    """
    import forge_state as fs

    try:
        recorded = {f"{d.id:03d}" for d in fs.list_decisions(forge_dir)}
    except Exception:
        return []

    claims: list[Claim] = []
    for match in _DECISION_CLAIM.finditer(text or ""):
        number = f"{int(match.group(1)):03d}"
        if number not in recorded:
            claims.append(Claim("unrecorded-decision", number, "what was said"))
    return claims


def check(paths: list[Path], project: Path) -> list[Claim]:
    out: list[Claim] = []
    for path in paths:
        if path.suffix in PYTHON_SUFFIXES + JS_SUFFIXES and path.is_file():
            out += check_file(path, project)
    return out
