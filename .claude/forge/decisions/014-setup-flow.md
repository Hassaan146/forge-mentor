---
id: 014
question: What does /forge:start actually do?
status: decided
date: 2026-07-31
decided_by: user
affects: [phase-2, phase-8]
conflicts_with: 006
content_sha: c42dc9367b71e88d77cf35d3918a67c5f325774f0b3e8ad8df170140197ff38a
prev_sha: 1624224175b3cee3198562b528caf0819b0f47fb1812c966b5d6781257e53d9d
---
# Connect accounts, explain the workflow, request permissions — all mandatory

**Decision:** `/forge:start` runs a setup interview that connects the user's accounts,
explains plainly how Forge works, and requests permissions. **Every permission is
mandatory.** A user who declines any of them cannot use Forge.

## The setup sequence

1. **Connect accounts** — GitHub, and the review service.
2. **Explain the workflow** — a short, plain description of what Forge will do: it will ask
   before it writes, it will record every decision, it will commit and push on every step,
   and it will send code for review.
3. **Request permissions** — each one named, with what it is for stated in one line.
4. **Create `.forge/`** and print the banner.

## Credentials are never typed into the chat

The user's phrasing was "login credentials". The implementation is **delegated sign-in, not
credential collection**:

- GitHub access uses GitHub's own sign-in flow. Forge receives an access token, never a
  password.
- Tokens are stored in the operating system's secure store, never in a project file and
  never in the conversation.
- Forge requests the **narrowest permission scope** that allows the work, and says what is
  being granted.

This is not a preference. A teaching tool that asks a beginner to paste a password into a
chat window teaches the single worst habit in software.

## Why mandatory

Forge's value comes from the parts working together: the record, the block, the push, the
review. A half-connected Forge would leave the user unsure which promises still hold — the
worst possible state for a tool whose entire point is a guarantee.

## ⚠ Conflict with decision 006 — must be resolved

Decision 006 states: *"A user who does not want this does not connect a repository, and Forge
tells them plainly that review and history are then unavailable."* That describes Forge
working with reduced function. This decision says it does not work at all.

**These cannot both stand.** Resolution required — see the open question in `progress.md`.

## Consequence accepted

An all-or-nothing wall at the first screen. This raises the risk already recorded in the
challenge as **P10 — users quit at setup and never see the teaching.** Mitigation: the
workflow explanation comes *before* the permission requests, so the user understands what
they are agreeing to and why, rather than facing a bare list of demands.
