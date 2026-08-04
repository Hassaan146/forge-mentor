---
id: 024
question: Where do the usage numbers come from?
status: decided
date: 2026-08-04
decided_by: user
implements: 008
affects: [phase-6]
---

# Read Claude Code's own transcripts

**Options considered**

- **A** — read Claude Code's session transcripts
- **B** — estimate from the text Forge sends
- **C** — count only when Forge calls a model directly
- **D** — drop the meter from v1

**Recommended:** A · **Decided:** A

## The problem this had to solve

Decision 008 promised a usage meter and warnings at thresholds. But Forge does not call any
model. Claude Code does. Forge is a plugin *inside* the thing doing the spending, so it has
no request of its own to count — which means the obvious implementation does not exist.

Three of the four options fail on that:

- **B** guesses. Cache reads are invisible to a character count, and a cached prefix is the
  single largest saving in the whole design. A meter that cannot see the saving would warn
  the user at the wrong moment — worse than no meter, because it is believed.
- **C** is exact but blank. The default path is the subscription, where Forge makes no direct
  calls, so the meter would read zero for almost every user.
- **D** gives up a stated Phase 6 deliverable.

## The mechanism

Claude Code already writes what is needed. Every assistant turn is appended to a session
file under `~/.claude/projects/<project>/<session>.jsonl`, and each carries the real counts:

| Field | What it is |
|---|---|
| `input_tokens` | fresh input |
| `output_tokens` | what came back |
| `cache_read_input_tokens` | input served from cache — the saving |
| `cache_creation_input_tokens` | input written into cache |
| `model` | which model was billed |

Forge reads those files. The numbers are measured, not estimated, and they include the cache
columns — so the meter can show what the cache-stable assembly is actually saving.

The project folder is the working directory with every non-alphanumeric character replaced by
a hyphen (`H:\Skills\Project` becomes `H--Skills-Project`). That is a guessable rule, so Forge
uses it only to find the folder quickly and then confirms against the `cwd` field recorded
inside the files. If the name rule ever changes, the confirmation still holds.

## Consequence accepted

**This reads a file format Anthropic never promised to keep.** A future Claude Code release
could rename the folder, move the field, or drop the file.

Accepted because the failure is soft and the alternative is worse. The meter is a display, not
a gate — nothing in the pipeline blocks on it. If the format changes, Forge reports that usage
is unavailable and everything else keeps working. It never guesses a number to fill the gap,
because a wrong number is the one outcome decision 008's warnings cannot survive.

Related: [[008-cost-and-usage]] · [[002-which-ai-does-which-job]]
