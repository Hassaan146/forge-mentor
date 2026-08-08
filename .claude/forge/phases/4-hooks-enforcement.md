---
phase: 4
title: Hooks & Enforcement
status: planned
effort: M
depends_on: phase-3
branch: phase-4-hooks-enforcement
base: phase-3-state-layer
---

# Phase 4 — Hooks & Enforcement

**Deliverables**

Gate hooks (no commit until tests pass) · safety hooks (secret files, prompt-injection) · the override flow · signed decision records (challenge C2)

**Done when**

A write with no recorded decision is blocked · a commit is blocked until tests pass · secret files are unreadable · a forged decision record is not trusted

**Chain:** this branch builds on `phase-3-state-layer`, so its pull request shows only
Phase 4's own commits. Each phase reviews independently while the work stays
in order.
