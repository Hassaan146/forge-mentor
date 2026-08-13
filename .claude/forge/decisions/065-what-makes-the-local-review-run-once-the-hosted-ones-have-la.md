---
id: 065
question: What makes the local review run once the hosted ones have landed?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: a410e08d990600e889729bdf87c26c0dc97f0d151c838f5a1f62b853dee72917
prev_sha: e2442fce145d6df6b3d0049037e3e655429cb5c8e4bb8fed7f9b33fdc2ac0ccc
---

# Every pull request's review carries a fingerprint, the local review file records which version it was written against, and anything else is owed until they match

**Options considered**

- Nothing. The model calls the tool when it remembers to
- A hook on the moment the review file is written
- A state check: the review on disk against the version the local reviewer last saw
- Run it on a schedule

**Recommended:** A state check · **Decided:** Every pull request's review carries a fingerprint, the local review file records which version it was written against, and anything else is owed until they match

## Why

Filing ponytail's findings was a tool somebody had to remember, which is the shape of every rule this repository has watched get skipped. Hooking the write was the obvious fix and it is the wrong one: the usual way a review arrives is a workflow committing it on GitHub's side and the user pulling in a terminal (decision 026), and no hook in the session sees that happen. So the question asked is not 'did the file just arrive' but 'has ponytail seen this version', which is answerable from disk however the file got there, including a fetch three sessions ago that nobody followed up. `clean` now means all three reviewers have looked, not merely that no finding is open: the old bar read as passed while one of the reviewers had never run. Filing nothing counts as having looked, because 'found nothing' and 'has not run' are different states and only the second should hold a step up. The hook runs after the fetch tool, after Bash, and at the start of a session, so a pull in another window is noticed at the top of the next turn.

## In their words

Whenever the two apps' md files for the PRs are downloaded locally, then the ponytail review runs. When it runs we have all of the reviews and all of the improvements, and after that everything runs.
