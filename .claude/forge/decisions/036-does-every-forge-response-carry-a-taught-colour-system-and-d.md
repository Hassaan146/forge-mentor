---
id: 036
question: Does every Forge response carry a taught colour system, and does the thing the user must do next get its own frame?
status: decided
date: 2026-08-09
decided_by: user
affects: phase-2, phase-8
content_sha: 7d4ab2884cd547fccb1b260b7f6f653be69a0ec75bbf9110aeabfb6ed5c39beb
prev_sha: bf1917b6c61a3a5b2a5c57eea43cefbfeaebe748f47606195f3145a82f7802ad
---

# Six colours with a key the user is taught, and a frame of its own for the ask

**Options considered**

- **A** — keep the palette as it is; the ask stays the last tinted line of the block
- **B** — six colours, one meaning each, taught at setup; the ask moves to its own double-ruled frame, and details that cannot be undone get a bar
- **C** — colour freely wherever it helps, with no fixed scheme

**Recommended:** B · **Decided:** B

## Why

Two separate faults, reported together.

**The colours had meanings and nobody was told them.** Six were already in use and each already meant one thing, but the meanings lived in a comment in `forge_ui.py`. Forge asks the user to *act* on colour — red means it stopped, yellow means the turn is theirs — and a scheme nobody was told about is a scheme nobody can read. The key is now printed at setup, beside the permissions, which is the one moment the user is reading carefully. Blue replaces cyan for information and yellow is added for "your turn, or a cost"; every span closes with the reset, because an unclosed one runs past the end of Forge's output and recolours the user's own shell prompt.

**The ask was the last line of the block it belonged to.** "Type yes to continue" and "A, B, or C?" carried the same weight as the option above them, and they were the first thing lost when a block scrolled — reading back through a session there was no way to find the place you were being asked something without reading everything. The ask now has the only double-ruled frame on the screen, in yellow, marked with the eighth symbol. It names the letters that were actually offered rather than a fixed A/B/C, and says what shape of answer is wanted.

The same reasoning covers details with a cost that cannot be undone — *this makes the repository public*, *every account will have to sign up again*. As sentence four of a paragraph they are read straight past, and those are the sentences the user most needs to have read. They get a yellow bar and their own vertical, inside the block rather than after it.

## What this amends

Decision 035 fixed seven symbols and set the test for an eighth: it must carry a meaning none of the others does. `→` earns it — "Forge has stopped and is waiting for you" is not ✅ (the opposite), not ⛔ (Forge refusing rather than waiting), and not ⚠️ (a cost inside a block still being read). That moment had no marker at all.

Rule R9's four-symbol count is superseded; its real point — colour is never the only signal — is kept and now tested: every block reads the same under `NO_COLOR`, on a monochrome terminal, and for a user who cannot tell the hues apart.

Recorded as rules R11 and R12 in `design-rules.md`.

Related: [[035-one-symbol-per-meaning]] · [[014-setup-flow]]
