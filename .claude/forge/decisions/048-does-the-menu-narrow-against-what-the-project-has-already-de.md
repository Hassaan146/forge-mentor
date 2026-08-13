---
id: 048
question: Does the menu narrow against what the project has already decided?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: d181b9795b785669046a46f249d3292a238915bf9221b469fe6ac6865c813a18
prev_sha: 6819455313d4dbc9f00519de2f972515f6d8b362c293baa4c37bec02cd42bcf0
---

# The menu narrows against the recorded facts, and what it removes is shown with the reason

**Options considered**

- No, the same options everywhere, and the user ignores the ones that do not apply
- Yes, and the excluded ones are dropped silently
- Yes, and the excluded ones are shown struck out with the reason
- Ask the user each time whether an option still applies

**Recommended:** Shown struck out with the reason · **Decided:** The menu narrows against the recorded facts, and what it removes is shown with the reason

## Why

A project that has said it runs only on the user's machine is never offered a container again; one with a single user is never offered a second reviewer. The facts are read back out of the decision records every time, never remembered, which is decision 019 applied to menus. Shown rather than dropped, because the exclusion is the cheapest teaching in the whole interrogation: a user who reads that a container is ruled out because this runs on their laptop has learned what a container is for, at no cost in questions. Silently removing it leaves them unable to tell the difference between an option Forge weighed and one it never thought of. A question is never narrowed by the fact its own answer produces, or it would answer itself and present the result as a choice.

## In their words

Only once if the person wants to make the app locally then only SQLite. There should be no docker.
