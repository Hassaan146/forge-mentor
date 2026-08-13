---
id: 047
question: How many options does a question put in front of the user?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: 6819455313d4dbc9f00519de2f972515f6d8b362c293baa4c37bec02cd42bcf0
prev_sha: 6c34bb9e5f56c794238f5ee6d0055d6a7b37f09208aaa1d5690134c9a17ada5c
---

# At least three and at most six, each carrying its cost, refused at the renderer

**Options considered**

- Whatever the model thinks of at the time (what shipped)
- Two to four, as the teaching skill asked for in prose
- At least three and at most six, checked in code, each carrying its cost
- A fixed number for every question

**Recommended:** At least three and at most six, checked in code · **Decided:** At least three and at most six, each carrying its cost, refused at the renderer

## Why

Nothing generated options. One question in the product carried a menu and every other one was improvised against no rule, so the floor could not be held by asking for it. `render_decision` now refuses a block with two options or with an option that has no consequence line, and the foundation menus are checked at the source. Three is the floor because two is a false binary: the answer has usually been chosen by whoever picked the pair. Six is the ceiling because a list nobody finishes is a list nobody chooses from. A question that genuinely has two sides passes `binary_because`, and that sentence goes on screen, so claiming a binary costs the same as arguing for one.

## In their words

It is giving very limited options. It should not give limited options in the code. For example it is only giving an option for a docker setup or data. There should be multiple options.
