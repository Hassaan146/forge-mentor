---
id: 076
question: How much of a build reaches the screen, and in what shape?
status: decided
date: 2026-08-14
decided_by: user
affects: phase-4, phase-5
content_sha: 6bdb21381aa9d101a58f6dbfda5cde9d4c255eac727eaaa4f43e7037f8158da5
prev_sha: 394dab70d7915ea7cc0a7bfbb5fcf21eaee11162964c3ed4307a6dbbdf519fbc
---

# Two boxes a step, and nothing between them. The explanations go to the record and come back one line a file

**Options considered**

- Framed, one box a file: the same paragraphs, each in its own box
- Framed, one box for the whole step: every file on one line, plus the run and the address
- Off the screen entirely, kept only in the record

**Recommended:** One box for the whole step - **Decided:** One box for the whole step

## Why

A three-file step reached the user as two boxes and about twenty lines of loose prose: a paragraph of what/why/how a file, a sentence between each about what was happening next, a port clash narrated in four lines, then the proof and the command explanation as more prose. Their instruction was exact: "only the box info should be displayed... and not this should be displayed, this should be hidden."

Two things were wrong and only one of them was the model's. file_written told it to say all three parts on screen, so the wall was the product working as written. It now records them and says nothing; what comes back is the one-line what, in the step's box, which step_built draws from the ledger with the run and the live address under it. The depth is not lost, it is in the record, which is where decision 074's promise actually lives.

The other was the presenter, the hook that exists to stop Forge speaking as prose. It only ran when a question was open, and during a build nothing is open, so every turn of every build was allowed. It now counts a step in progress as speech, and it counts prose after and between the boxes rather than only the lead-in before the first one, which is what let a wall pass underneath two perfectly good frames.

## In their words

in our plugin only the information here should be displayed, the only box info should be displayed. and not this should be displayed, this should be hidden.
