---
id: 071
question: How many ways should there be to draw a block?
status: decided
date: 2026-08-14
decided_by: user
affects: 
content_sha: c26bc0fef0ec5d6f6ed35af4b4589fb6c7d8040a40730e4606c22339f00a7034
prev_sha: 8578f393d8880ef4b29d514cae582f1fc790a77ddfa330d35b136a6606ab80f0
---

# One. The four switch-guarded renderers are deleted, along with the tests that only they reached

**Options considered**

- Five: the one that ships, plus four kept behind switches for other clients
- One: the route decision 045 settled, and delete the rest
- Two: the fenced box and a plain-text fallback
- Keep them but document that they are unsupported

**Recommended:** One · **Decided:** One. The four switch-guarded renderers are deleted, along with the tests that only they reached

## Why

A ponytail review of the whole plugin returned net: -511 lines possible, and two thirds of it was here: _diff_block, _boxed_markdown, as_markdown and its five _md_* helpers, reachable only through FORGE_DIFF, FORGE_TABLE, FORGE_ANSI_FENCE and FORGE_NO_COLOUR, which nothing sets. yagni names it exactly: config for a value that never changes. They were kept because the rendering failure is per-client and another terminal might behave differently, and that argument does not survive the count: 361 lines of the product carried for a client nobody has, in a file where the same wrap arithmetic was already copied four times because the file was too large to see whole. The search that produced the answer is written down in decisions 044 to 046, which is where it belongs, rather than in four branches of a function. Applied with the deletions ponytail found alongside it: seven symbols nothing referenced, three copies of the same hook boilerplate, two spellings of one normalisation. Net -656 lines, and coverage rose from 88.1 to 88.9 because what went was code no test could reach honestly.

## In their words

Start making these changes as ponytail said, almost 500 lines of code will be reduced.
