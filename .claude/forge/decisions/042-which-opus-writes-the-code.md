---
id: 042
question: Which Opus writes the code?
status: decided
date: 2026-08-10
decided_by: user
affects: phase-5, phase-7
content_sha: bc10f99a79b923a7675f0d0e5d24a9003287b7949e4163a0b3be6e904caf5adf
prev_sha: 070c7ca6109478cb5ae0384ae4fa3519d2b56756995b18e4c4e8469a1a91001f
---

# Opus 5, and decision 002 is amended rather than edited

**Options considered**

- **A** - leave `claude-opus-4-8` in place
- **B** - move every building and fixing job to `claude-opus-5`

## Why

Decision 002 chose "the strongest coding model" and then wrote down the name of the model that
was strongest when it was written. The name aged; the reasoning did not. Opus 5 is the current
one, so B is what 002 actually asked for.

The user caught it in the demo output, where the live line read "Opus 4.8 is now writing it".
That line exists to make the multi-model design visible, which means it is also the line that
shows when the routing is wrong.

## What moved

`builder` and `review-fixer` now declare `claude-opus-5` in their own files, which is what
Claude Code reads at dispatch (decision 029), and the server's fallback lists follow. The
planner stays on Fable 5 and the structurer on Haiku 4.5: nothing about those changed.

## Why a new record and not an edit

Decision 002 is signed and chained. Editing it would either break the chain or, worse, quietly
rewrite what a user was told at the time they agreed to it. A record is what was decided then;
this is what is decided now, and both stay readable.

The general form, worth keeping: a decision should name the reason in a way that survives its
own example. "The strongest coding model, currently Opus 5" ages better than a bare version
number, because the next reader can tell whether the name or the rule went stale.

Related: [[002-which-ai-does-which-job]] - [[029-which-model-runs-a-job]]
