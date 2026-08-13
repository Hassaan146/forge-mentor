---
type: local-review
reviewer: ponytail 4.9.0 (/ponytail-review, skill loaded)
scope: the whole plugin
version: forge 1.22.0
date: 2026-08-14
status: nothing applied, awaiting your read
---

# ponytail-review: forge-mentor

Ponytail was enabled and the session restarted, so this is the skill's own run,
not the hand-applied approximation from the earlier file. Scope is
over-engineering only: correctness, security and performance are out by the
skill's own boundary rules.

---

## Dead rendering routes

The largest single find. `render_from` keeps four ways to draw a block. Decision
045 settled the fenced box as final and shipping; the other three survive behind
environment switches nobody sets.

```
forge_ui.py:L1849: delete: FORGE_DIFF switch guarding _diff_block. Nothing replaces it.
forge_ui.py:L1498-1625: delete: _diff_block, 128 lines, reachable only by that switch.
forge_ui.py:L1840: delete: FORGE_TABLE switch guarding _boxed_markdown. Nothing replaces it.
forge_ui.py:L1628-1745: delete: _boxed_markdown, 118 lines, same.
forge_ui.py:L1825: delete: FORGE_ANSI_FENCE switch. Attempt 5 of 6, recorded as failed in its own comment.
forge_ui.py:L1854: delete: FORGE_NO_COLOUR switch, a second spelling of FORGE_NO_COLOR at L81.
forge_ui.py:L1748-1773: yagni: as_markdown, no caller outside its own tests.
forge_ui.py:L1107-1203: yagni: _md_decision/_md_note/_md_action/_md_legend/_md_roadmap, 89 lines,
  reachable only through as_markdown. Delete with it.
```

`yagni:` names this exactly: config for a value that never changes. The comments
above those switches read as a search log for a question that has been answered,
and the answer is one route.

**-361 lines.**

## Defined, referenced nowhere

Every one has a single mention in the repository: the line defining it.

```
presenter.py:L70: delete: rendered_by_command(), a transcript scan with no caller. Nothing replaces it.
presenter.py:L67: delete: RENDER_HINT, a command string nothing prints. Nothing replaces it.
gates.py:L44: delete: COMMIT_PATTERN, compiled and never matched. Nothing replaces it.
forge_update.py:L372: delete: PANEL_ROUTE, a string for a panel nothing routes to. Nothing replaces it.
forge_pipeline.py:L76: delete: BUILD, the build-loop tuple no caller reads. Nothing replaces it.
forge_state.py:L66: delete: _NONE, a set of empty spellings nothing tests against. Nothing replaces it.
forge_meter.py:L47: yagni: MeterError, never raised, never caught. Add it back when something raises it.
```

`rendered_by_command` is the pattern in miniature: a whole function answering a
question decision 044 stopped asking. It outlived the decision that killed it.

**-45 lines.**

## Same logic, more than once

```
companion.py:L96, reviewed.py:L88, grounded.py:L60: shrink: three hook mains, identical
  but for one string. One emit(event, text) in a shared module. 3x18 -> 12 + 3x2.
forge_review.py:L131: shrink: text normalisation copied from forge_integrity._normalise. Import it.
forge_ui.py:L361, L406, L1341, L1463: shrink: lead/room hanging-indent arithmetic four times.
  One hanging(text, lead, mark) helper.
tests/test_server.py:L23, tests/test_presenter.py: shrink: call(tool) unwrap defined twice.
  conftest.py.
```

The `_normalise` one is worth more than its six lines: both copies decide
whether a file counts as *changed*, and one strips `\r\n` while the other does
not.

**-55 lines.**

## Reachable only from tests

```
forge_state.py:L758-780: yagni: init(), 23 lines. start.md tells the model to create the
  notes by hand instead of calling it. Wire it or delete it; two ways to make a project
  is one way that drifts.
forge_ui.py:L178-188: yagni: paint(), 11 lines, no production caller.
forge_integrity.py:L219-222: yagni: is_approved(), 4 lines, no production caller.
safety.py:L250-255: yagni: find_injection(), 6 lines, wrapped by a caller that inlines the same check.
forge_skills.py:L244-246: yagni: missing_required(), 3 lines, added this session and never called.
forge_build.py:L161-166: yagni: mark_written(), superseded by mark_explained in the same file.
```

**-50 lines.**

---

## Not flagged, deliberately

- **The comment volume.** This repository carries more prose per statement than
  any normal codebase. It is out of scope: ponytail cuts code that runs, and the
  comments are the reasoning the decision records index.
- **The four hook scripts as separate files.** They must be stdlib-only
  subprocesses. Only their shared boilerplate is duplication.
- **Tests.** A smoke test is the ponytail minimum, never flagged.

## Score

```
net: -511 lines possible.
```

Against ~3,600 statements of core logic, so ~14%. Two thirds of it is one
finding: a rendering search that was won and never cleaned up after.

Nothing applied. Does not apply the fixes, only lists them.
