---
id: 016
question: Is the .forge/ folder committed or ignored?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-2, phase-3]
content_sha: 93d4bddc5a5fc1d0f1c24d85ffe0338f6092fc06a505068b9703ab0098da7c7e
prev_sha: 5786ec0e2ca22c667fe1f8b99526494d0b1e556cf22e0e6a9e9097a244f176fa
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
