---
id: 026
question: Who writes the review file into the repository?
status: decided
date: 2026-08-04
decided_by: user
implements: 005
affects: [phase-6]
---

# A workflow in the repository writes it, not Forge on the user's machine

**Options considered**

- **A** — a GitHub workflow fetches the review and commits the file
- **B** — Forge commits and pushes it from the user's machine after fetching
- **C** — Forge writes it locally; it rides along in the next ordinary commit

**Recommended:** A · **Decided:** A

## What was actually broken

The review file was only ever written to disk, by a tool nobody called automatically. Nothing
fired when a review was posted. So the promise — findings appear in a file, in the repository
and locally — held only if a person remembered to ask for it, and the "in the repository" half
never happened at all without a hand-written commit.

That is option C, and it is the state the code was already in.

## Why the workflow and not the plugin

Option B is the tempting one: Forge already holds GitHub access, so it could commit and push
after fetching. Two things rule it out.

**It breaks a promise.** Decision 005 and the setup flow in 014 say Forge does not push without
the user asking. A background push after every review is exactly the thing that rule exists to
prevent, and amending it to buy a convenience is a bad trade.

**It only works while someone is watching.** Reviews arrive minutes after a push, often after
the session has ended. A plugin that has exited cannot fetch anything. The workflow runs on
GitHub's side, so it does not care whether anyone is at the keyboard.

## The mechanism

A workflow ships in the repository. It wakes on a review being submitted or a review comment
being posted, runs the same fetch code the plugin runs, and commits
`.forge/reviews/pr-<n>.md` to the branch under review.

The result is the thing that was asked for: the findings are in the repository for anyone who
opens it on GitHub, and a `git pull` brings them to the machine. Both copies, one source, no
one has to remember.

## Consent, and where it lives

The workflow commits to the user's repository, which is a write. Consent is real but it moves:
the user installs the workflow into their own repository, once, knowingly — rather than
approving a push each time. That is a deliberate choice a person makes about their own repo,
not something Forge does on their behalf mid-session. Decision 005 is unchanged; nothing on the
user's machine pushes without asking.

## Consequence accepted

The workflow needs write permission on the repository, and it runs on GitHub's servers where
the user cannot see it work. Mitigations: it touches exactly one path, `.forge/reviews/`, and
it is a readable file in their own repository that they can delete. It never runs on a fork's
pull request, where an untrusted contributor could otherwise reach a token.

Related: [[005-review-and-push]] · [[014-setup-flow]] · [[025-two-reviewers-one-file]] · [[016-forge-folder-committed]]
