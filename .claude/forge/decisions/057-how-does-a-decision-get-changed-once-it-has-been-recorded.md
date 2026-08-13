---
id: 057
question: How does a decision get changed once it has been recorded?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: c3b2b5870f4507769e29adc77bfe696ad99c5d6351f562a43479c20b31a2a20b
prev_sha: b4783aaf728c6206d95523ee270b6e26f9ba04ede15b6c1abdca004012f8bd52
---

# A new record that names the old one with `supersedes`, and the old one stays readable

**Options considered**

- Edit the record
- A new record naming the old one with supersedes, and the old one stays
- Delete the old record and write a new one
- Keep a separate list of what is no longer true

**Recommended:** A new record naming the old one · **Decided:** A new record that names the old one with `supersedes`, and the old one stays readable

## Why

This is the shape decision 042 already used when Opus 5 replaced Opus 4.8 in 002, now enforced by the tool rather than done by hand. An edit destroys the only thing the record was for: what was believed, when, and why it changed. It also breaks the chain, since the fingerprint covers the body. It matters most on the incremental path, where a new feature meets a decision made months earlier: the clash is named, the user chooses between changing the feature and changing the decision, and changing the decision leaves a trace either way.

## In their words

By adding one feature we are not disturbing the other feature.
