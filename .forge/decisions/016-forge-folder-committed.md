---
id: 016
question: Is the .forge/ folder committed or ignored?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-2, phase-3]
content_sha: fcc1c1d158f63018f0dca309a8c6c7c6dc8870523006719c9a77ba460401864e
prev_sha: 5de3153bc9fc3662a766163d8f38d29e2f6c7f8df33911efdf01128ae823b410
---
# Committed to the project repository and pushed to GitHub

**Decision:** `.forge/` is committed inside the project repository, and every decision is
pushed to GitHub along with the code.

## Why this is required, not optional

Three earlier decisions depend on it:

- **001** — the notes must be readable by the user and by Claude. Ignored files are invisible
  to anyone who clones the project.
- **011** — switching accounts works by pulling the repository. If `.forge/` is not in the
  repository, nothing arrives, and the new session starts blind.
- **005** — the decision and the code it produced travel together in the same commit, so the
  reason a line exists is stored beside the line itself.

An ignored `.forge/` would break all three at once.

## What follows from it

- Decision records are public whenever the repository is public, so they must never contain
  secrets — they hold reasoning, not configuration values.
- Anyone who clones the project inherits its full decision history, and can read why the
  project is shaped the way it is.
- The commit history becomes a readable record of the project's thinking, not only its code.
