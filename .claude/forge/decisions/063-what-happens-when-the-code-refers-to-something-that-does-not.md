---
id: 063
question: What happens when the code refers to something that does not exist?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: 0a635253108bb8713943fed1cd55079966f7c8b45d6e3fba8745fcd81d052f33
prev_sha: d5f2369adca711820bc052f010e04a1efc28b4b606a3a938711b0d07958e7fe5
---

# Every import is checked against the project's own manifests and files, every citation of a decision against the records, and anything unaccounted for goes to the user as a question

**Options considered**

- Nothing. Tests catch it, or the reviewers do
- Forge corrects it quietly
- Forge names it and puts it to the user as a question
- Forge blocks the write until it resolves

**Recommended:** Name it and put it to the user · **Decided:** Every import is checked against the project's own manifests and files, every citation of a decision against the records, and anything unaccounted for goes to the user as a question

## Why

The hallucination that costs the most here is the confident one: an import of a package that is in no manifest, a relative import with no file behind it, or 'as decided in decision 014' when 014 is about something else. All three are plausible, none is caught by tests written in the same turn that invented them, and all three are decidable from the file and the manifests without judging whether the code is right. `scripts/grounded.py` runs after the write rather than before, because a reference cannot be checked until it exists, and it never fixes anything: a silent correction is a second guess stacked on the first and the user learns nothing from a mistake they never saw. Each finding is one of three things, a dependency to add and record, a file about to be written, or something invented, and which one it is belongs to the user. Blocking the write was rejected: the check needs the file to exist, and a hook that stops work on suspicion is one people turn off.

## In their words

I want that if the AI hallucinates, Ponytail unhallucinates, or asks questions from me to improve the code, and then they ask questions from me.
