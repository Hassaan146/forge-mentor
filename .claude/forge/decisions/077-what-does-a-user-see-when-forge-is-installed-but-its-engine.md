---
id: 077
question: What does a user see when Forge is installed but its engine is not running?
status: decided
date: 2026-08-14
decided_by: user
affects: phase-2, phase-4
content_sha: f11ce9375817991174d5297d752fc95f799f3c7781b49f7946411049c9d72861
prev_sha: 6bdb21381aa9d101a58f6dbfda5cde9d4c255eac727eaaa4f43e7037f8158da5
---

# One box, two commands. The engine is checked before the banner and the explanation is deleted

**Options considered**

- Leave it: the model explains the situation in its own words each time
- One block from forge_ui, printed before the banner, and nothing else said
- Put the two commands in the readiness table as a seventh row

**Recommended:** One block - **Decided:** One block

## Why

A user installed both plugins inside a session and ran /forge:start. The slash command was found, because commands are files on disk, and the MCP engine was not running, because a plugin's server is spawned at session start from a list read before either plugin existed. What reached the screen was a banner, six green readiness ticks, a stop sign, and eleven paragraphs: which parts of a plugin load when, why the command worked while the tools did not, and what would happen to the record if the questions were asked by hand. Every line true and none of it the answer, which is one command long. Their words: "just do a few things, like go and reload the plugins or exit Claude, and all that, encapsulated in a box which would look good, not this thing with so much theory."

Two fixes, and the smaller one matters more. The block is drawn by forge_ui like everything else, so there is one copy of it and no version living in a command file to drift. And it is printed before the banner rather than after the readiness check, because six green ticks above a stop sign is worse than no check at all: the check tests Python, mcp, git, sign-in and ponytail, and not one of those can tell whether Forge's own engine is loaded in this session. color_legend can, because calling it is the question.

## In their words

when someone should start the forge project, you should ask him to just do a few things, like go and reload the plugins or exit Claude, and all that, encapsulated in a box which would look good, not this thing with so much theory.
