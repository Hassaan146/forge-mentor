"""Tests for the readiness check — the "does it run on this laptop" question.

There is nothing to deploy, but there are prerequisites, and the failure they
cause is the nastiest state Forge has: the hooks are stdlib-only so they keep
blocking writes, while the engine that records decisions is missing. Forge
stops a write and is then unable to record the decision that unblocks it.

So the check has to run on a machine where nothing is installed — which is why
it is stdlib-only itself. A readiness check that needs a dependency in order to
report a missing dependency is no check at all.
"""

from __future__ import annotations

import forge_preflight as pf


def test_the_check_needs_nothing_but_the_standard_library() -> None:
    """Otherwise it cannot run on the machine it exists to diagnose."""
    source = (pf.__file__)
    with open(source, encoding="utf-8") as handle:
        text = handle.read()

    for line in text.splitlines():
        if line.startswith(("import ", "from ")) and "__future__" not in line:
            module = line.split()[1].split(".")[0]
            assert module in {
                "importlib", "shutil", "subprocess", "sys", "dataclasses",
            }, f"{module} is not in the standard library"


def test_a_missing_engine_package_is_fatal() -> None:
    """It is the one that stops Forge working, and nothing installs it."""
    checks = {c.name: c for c in pf.run()}
    assert checks["the mcp package"].fatal is True
    assert checks["git"].fatal is True


def test_a_missing_github_sign_in_is_not_fatal() -> None:
    """Everything except reading reviews works without it."""
    assert {c.name: c for c in pf.run()}["GitHub sign-in"].fatal is False


def test_every_failure_carries_the_command_that_fixes_it() -> None:
    """Rule R1: the user may not be able to work out the fix themselves."""
    for check in pf.run():
        assert check.fix, f"{check.name} has no fix line"


def test_the_report_explains_why_a_half_install_is_dangerous() -> None:
    """A user told only "missing package" would reasonably carry on regardless."""
    broken = [
        pf.Check("the mcp package", False, "gone", fix="pip install mcp", fatal=True),
    ]
    text = pf.report(broken)

    # Collapsed first: the explanation is wrapped for a terminal, so asserting
    # on the raw string would be testing where the line breaks fall.
    flat = " ".join(text.split())
    assert "MISSING" in flat
    assert "unable to record the decision that unblocks it" in flat


def test_a_ready_machine_says_so_plainly() -> None:
    ready = [pf.Check("Python 3.12 or newer", True, "", fix="x")]
    assert "Ready." in pf.report(ready)


def test_only_an_optional_gap_still_counts_as_ready() -> None:
    checks = [
        pf.Check("the mcp package", True, "", fix="x"),
        pf.Check("GitHub sign-in", False, "not signed in", fix="gh auth login"),
    ]
    text = pf.report(checks)
    assert "only affects reading reviews" in text
    assert "cannot run yet" not in text


# --------------------------------------------------------------------------
# running outside a terminal — the desktop app, an IDE panel
# --------------------------------------------------------------------------


def test_the_hooks_own_python_is_checked_separately(monkeypatch) -> None:
    """The interpreter you typed and the one the hooks get are different things.

    `hooks.json` invokes a bare `python`. Outside a terminal that word resolves
    against whatever PATH the app was launched with, which is often not the
    shell's — so "Python is installed" and "Forge's hooks can run Python" can
    disagree, and only the second one matters.
    """
    import shutil

    real = shutil.which
    monkeypatch.setattr(shutil, "which", lambda n: None if n == "python" else real(n))

    checks = {c.name: c for c in pf.run()}
    hooks_python = checks["the `python` command Forge's hooks use"]

    assert hooks_python.ok is False
    assert hooks_python.fatal is True
    assert "not on PATH" in hooks_python.detail


def test_the_store_stub_is_not_mistaken_for_python(monkeypatch) -> None:
    """On Windows a bare `python` can be the Microsoft Store placeholder.

    It exits without running anything, so the hook does nothing at all and says
    nothing about it — the quietest possible failure.
    """
    class Stub:
        returncode = 0
        stdout = ""      # the placeholder prints nothing
        stderr = ""

    monkeypatch.setattr(pf.shutil, "which", lambda n: r"C:\...\WindowsApps\python.exe")
    monkeypatch.setattr(pf.subprocess, "run", lambda *a, **k: Stub())

    ok, detail = pf._plugin_python_works()
    assert ok is False
    assert "Microsoft Store" in detail
