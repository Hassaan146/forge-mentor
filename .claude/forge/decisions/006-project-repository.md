---
id: 006
question: Who creates the project repository, and is it public or private?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-2, phase-8, phase-9]
content_sha: 52fb989a9342981a51eabf5dc82d8c965f4f0c2ef9808d54d1b2b6ee4a9c00f3
prev_sha: c2c648732e2e97d802ad953387c5a8f0b61d13022796053cea5ce396d40f4ccf
---
# The user creates it; private first; public only if reviews require it

**Options considered**

- **A** — Forge creates it, public by default
- **B** — Forge creates it, private by default
- **C** — the user connects their own repository

**Recommended:** C with a guided fallback · **Decided:** C, refined.

## How it works

1. **By default the user creates the repository themselves** and connects it at setup.
2. **If the user asks Forge to create it**, the user must first sign in to GitHub through
   the plugin. Forge never acts on an account it was not given access to.
3. **The repository is private first**, always. Safe by default.
4. **If the review step needs a public repository**, Forge asks and the user can switch it.

## Why private first

A learner's early code is often rough, and some projects hold things that should not be
public. Publishing someone's work is not a decision a tool should make quietly — that
would break the principle the whole product rests on.

## The cost fork, surfaced at setup — not later

CodeRabbit is **free on public repositories** and **needs a paid plan on private ones**.
So the choice is really: *public code with free reviews*, or *private code with a paid
plan*. Forge states this plainly at setup so the user is not ambushed mid-build.

## Security consequence — flipping private to public

Making a private repository public exposes **the entire commit history**, not only the
current files. A secret committed early and removed later is still sitting in that
history and becomes readable the moment the repository is published.

**Required before any switch to public:**

1. Forge scans the full commit history for secrets, not just the latest files.
2. If anything is found, Forge refuses and explains what and where.
3. If clean, Forge asks for confirmation naming what becomes visible — all code, all
   history, all commit messages — and states that publishing is effectively one-way, since
   anything public can be copied or indexed within minutes.
4. The switch is recorded in the notes.

## Consequence accepted

Users who keep the repository private and have no paid CodeRabbit plan get the local
checks (tests, security floor, coding standards) but not the deeper review.
