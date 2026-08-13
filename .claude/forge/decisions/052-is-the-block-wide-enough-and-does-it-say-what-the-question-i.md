---
id: 052
question: Is the block wide enough, and does it say what the question is about?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: b55001ec7e6fa454b4f95ddf22ccb2235054864fad85b8e6b030ee1ba5e74fb4
prev_sha: 8ed8a6a942de0ece8886397d7bd06d4cc1b41cf38a5e4049b399ab414fb0ffe2
---

# The box is 92 columns, narrowable by setting, and every question names its concept

**Options considered**

- Leave it at 74 columns and shorten the options
- Widen it, and name the concept the question is teaching
- Widen it only when the terminal is wide
- Drop the consequence lines so the options fit

**Recommended:** Widen it, and name the concept · **Decided:** The box is 92 columns, narrowable by setting, and every question names its concept

## Why

At 74 columns an option and the consequence that makes it a choice did not fit on one line, so a menu of four read as eight and the part that wrapped was the part that mattered. The width cannot be measured, because the block is drawn into a chat panel rather than a terminal, so it is a setting with a sensible default and `FORGE_BOX_WIDTH` for a split pane. The concept line is the other half: a user who remembers that they picked B has learned nothing, and the idea underneath is the only part of this that outlives the project being built.

## In their words

The question should be related to a concept, and it should be wide.
