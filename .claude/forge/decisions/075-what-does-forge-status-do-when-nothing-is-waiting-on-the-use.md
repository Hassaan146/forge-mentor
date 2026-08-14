---
id: 075
question: What does /forge:status do when nothing is waiting on the user?
status: decided
date: 2026-08-14
decided_by: user
affects: phase-5, phase-8
content_sha: 394dab70d7915ea7cc0a7bfbb5fcf21eaee11162964c3ed4307a6dbbdf519fbc
prev_sha: f95852d707dabc5bca107ac83b8dcad7342e35f437102d1da6fc14b38a80cee9
---

# It carries on. An empty next block means the next move is Forge's, not that there is nothing to do

**Options considered**

- Leave it: the summary is a report, and the user runs the next command themselves
- Carry straight on into the build loop in the same turn when nothing is waiting on the user
- Ask "shall I continue?" and wait for yes

**Recommended:** Carry on - **Decided:** Carry on

## Why

catch_up returns two blocks, the story so far and whatever comes next, and its instruction was to paste both and stop. The second block is empty whenever nothing is waiting on the user, which is exactly the state a decided step is in. So a session reopened on a decided step got a summary, the line "No question is open; nothing is blocking you", and the turn ended: "good but didnt asked me the next question". The report was accurate and the loop had quietly forgotten to take its turn.

Empty is not "nothing to do", it is "nothing to do that is theirs". The instruction is now conditional on which of the two endings applies, and the empty one says to keep going in the same turn and names the calls: current_step, plan_files, build it. This is decision 013 (one continuous flow) applied to the one command that was contradicting it, and it is safe to continue without asking because the build loop announces itself now (decision 073) rather than arriving as finished files.

## In their words

good but didnt asked me the next question
