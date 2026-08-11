---
id: 045
question: Which presentation does a block use where colour cannot arrive?
status: decided
date: 2026-08-12
decided_by: user
affects: phase-2, amends-044
content_sha: 5acadcc719e8da449381a616959be9706522461754359b5c77ae158ddc5903a1
prev_sha: 0805dea0c4cc9b045dbc0b57cc8142272f7d8832edde6b9875855dda7e8404c3
---

# The fenced box. Eight tried, and this is the one, and it is monochrome

**Amends 044**, which chose the table after seven attempts. The eighth attempt was to look at
the table on the actual screen, and it lost.

## Why the table lost

Two things this renderer decides, neither of them arguable:

- **A border after every row.** One block arrived as a stack of eleven boxes rather than one
  object with a boundary, which is the opposite of what decision 035 asks for.
- **`&nbsp;` printed literally.** The indentation inside cells came out as the entity itself,
  so every teaching line began with `&nbsp;&nbsp;`.

The user's verdict was one line: the previous one was much better.

## What ships

The drawn box inside a plain fence. The fence stops markdown reflowing it, reading `---` as a
rule or `*` as emphasis, and the client draws its own container around the whole thing. It
reads as one object, which is the entire requirement.

**It is monochrome, and that is now final.** Rule R11 has required from the first day that
colour is never the only signal, and this is the day that promise gets collected: the eight
symbols and the two frames carry every meaning, and nothing on screen depends on a hue.

## The eight

| | | box | colour |
|---|---|---|---|
| 1 | ANSI retyped into the reply | yes | stripped |
| 2 | ANSI printed by a command | yes | stripped |
| 3 | a block printed by a command | yes | never shown; output collapses |
| 4 | loose markdown | lost | arrives |
| 5 | an ```ansi fence | yes | codes printed raw |
| 6 | a one-column table | one box per row | arrives |
| 7 | **a plain fence** | **yes** | **none** |

`FORGE_TABLE=1` and `FORGE_ANSI_FENCE=1` keep 6 and 5 available, because these are decisions
this client makes and another may make them differently.

## What it cost, and the rule that comes out of it

Eight rounds, most of them spent guessing what a renderer would do and shipping the guess. Two
of them were worse than a wrong guess: a check that certified a block the user could not see,
and a frame test that refused a presentation it had never been told about.

**Look at the destination before changing how something is drawn, and look again at whether the
check still recognises what the code now produces.** The second half is the one that hides,
because the tests pass either way.

One more, small and expensive: the teaching cap counted rows on screen rather than sentences,
so a wrap fell mid-sentence and "Changing it in week three is not." arrived without its "not".
A cap that can invert a sentence is worse than no cap.

Related: [[044-how-does-a-block-reach-the-user-s-screen-with-both-its-box-a]] - [[035-one-symbol-per-meaning]]
