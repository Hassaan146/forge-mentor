---
id: 003
question: Can the user change which AI does which job?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-2, phase-5, phase-7]
content_sha: e07f1663e44f41beff712ba54690ab1911160e5cb68e00c71c522c595f185f8f
prev_sha: eb0e0e40f193f451c5c0ba978c978054c2c681eb53dec861a4760aa8c3c3a7f8
---
# Yes — through settings, with a warning, never a block

**Options considered**

- **A** — fixed inside Forge, user cannot change it
- **B** — a settings file the user edits freely
- **C** — defaults ship with Forge; a settings file overrides them

**Recommended:** C · **Decided:** C, refined with three added rules.

## The three added rules

**1. Changing is deliberate.** The user cannot change an AI by chatting. They must open
the settings file and edit it. This keeps a beginner from drifting into a bad setup by
accident.

**2. Warn, do not block.** When a change would lower quality, Forge says so plainly and
asks for confirmation — *"Teaching is being changed to Haiku 4.5. That AI is fast and
cheap, but its explanations will be shallower and its planning weaker. This is the part
of Forge that teaches you. Continue?"* It is a warning, not an error. The user may
proceed. Their choice is recorded.

**3. Fall back to the next best available.** If the preferred AI is not on the user's
plan, Forge moves down an ordered list rather than failing.

## Fallback order

| Job | Preferred | Then | Then |
|---|---|---|---|
| Teaching / asking / planning | Fable 5 | Opus 4.8 | Sonnet 5 |
| Writing code | Opus 4.8 | Sonnet 5 | Haiku 4.5 |
| Tidying answers | Haiku 4.5 | Sonnet 5 | — |
| Fixing review comments | Opus 4.8 | Sonnet 5 | — |

**Correction recorded:** the user referred to "Opus 5". No such model exists — the
strongest Opus today is **Opus 4.8**, and the most capable model overall is **Fable 5**.
Because model names change often, the fallback list is stored as an editable ordered
list, not written into the code. When Anthropic releases a newer model, one line in that
list is updated — no code change.

## Why

Defaults protect the beginner, who is the main user. The override solves the real problem
that a cheaper plan may not include Fable 5. Warning instead of blocking respects that it
is the user's project — the same principle as the rest of Forge: teach the consequence,
then let the human decide.

## Consequence accepted

A settings file needs documentation and validation, and a user can still choose a setup
that gives them worse teaching. The warning makes that an informed choice rather than an
accident.
