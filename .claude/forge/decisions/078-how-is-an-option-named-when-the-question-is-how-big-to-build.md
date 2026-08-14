---
id: 078
question: How is an option named when the question is how big to build something?
status: decided
date: 2026-08-14
decided_by: user
affects: phase-5
content_sha: e903a148609550cbfc45e715a76fa9badba062c4e13985a99fe5b837e87ce45e
prev_sha: f11ce9375817991174d5297d752fc95f799f3c7781b49f7946411049c9d72861
---

# By what the project gets. A label that counts files is refused in code

**Options considered**

- Leave it to the brief: tell the model to name options by capability
- Refuse a label that is only a count of files, in forge_options, like every other menu rule
- Drop file counts from the block entirely, including the consequence lines

**Recommended:** Refuse it in code - **Decided:** Refuse it in code

## Why

The size question reached a user as "A Three files / B Five files / C Let SQLAlchemy build the table / D Skip it". Two of those four are layouts for code nobody has seen yet, and picking between them is picking a directory structure, not a capability. Their words: "Dont tell me how many files to add, just tell for each option what functionality will be added."

The invitation was in the tool. lean_check told the model to "offer at least three sizes", and a size is answered in a model's head as a number of files. It now says to name each option by what the project gets and to put the count in the consequence line, where it reads as a cost. And because rule R13 makes a brief advice, forge_options refuses a label that is nothing but a count, alongside the rules that already refuse a two-option menu and an option with no consequence line.

The check is deliberately narrow: plural only, and only when the label is nothing else. "One table, one model, one migration" names the thing and happens to count it. "A file" is a real answer to where data is stored, sitting next to SQLite and Postgres, and catching it cost a test the first time this rule was written.

## In their words

Dont tell me how many files to add, just tell for each option what fucntioanlity will be added
