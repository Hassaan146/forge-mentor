---
id: 060
question: What has to happen between a step appearing on the plan and its code being written?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: d3d77a9c55b6e934a29d3ff31c376147c7fa4b98b780ab82807ca6bc34a1dcd3
prev_sha: 925da36ffbc5542b46dfb12aaf435ae75b091db776aba95533419a594906abe9
---

# Two extra gates around the step: the ladder before anybody is asked anything, and the same ladder against the approach before it is built

**Options considered**

- Its own question, and that is all (what shipped)
- A lean pass first, then its own question, then a review of the approach before it is built
- A review after the code, in the fix loop, where the reviewers already are
- Trust the builder to keep it small

**Recommended:** A lean pass first, and a review of the approach before it is built · **Decided:** Two extra gates around the step: the ladder before anybody is asked anything, and the same ladder against the approach before it is built

## Why

Forge's question has always been which decision. The one before it, does this need writing and how much of it, was never asked, so a step that arrived on a plan got built at whatever size the model first imagined. The first gate runs the ladder (does it need to exist, does the project already do it, does the standard library do it, what is the smallest useful version, what the extra size costs) and puts the findings to the user as a size question with at least three answers. The second runs the same ladder against the approach once it is settled: unchanged means one line and carry on, and smaller means the user decides, because a change to what gets built is theirs and not the reviewer's. The second gate is the one that pays, because the approach is where over-building happens and by then everybody has agreed on the goal and stopped looking. Nothing in Forge judges whether code is minimal: that is the model's job with ponytail loaded, and Forge's job is to refuse to move until the answer is on disk. Reviewing after the code was rejected because by then it is written and deleting it is a second argument.

## In their words

Ponytail will ask: is this thing important or not, will this give a benefit. Claude re-evaluates his approach, asks the user, gives the concept. Then ponytail evaluates Claude's approach and the modified approach is asked from the user.
