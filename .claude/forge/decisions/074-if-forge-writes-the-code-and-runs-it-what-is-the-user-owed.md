---
id: 074
question: If Forge writes the code and runs it, what is the user owed?
status: decided
date: 2026-08-14
decided_by: user
affects: phase-5, phase-7
content_sha: f95852d707dabc5bca107ac83b8dcad7342e35f437102d1da6fc14b38a80cee9
prev_sha: ed75b4c493b4974f38ff138523863173fe187206b20f63d86d0654ecdc756529
---

# Forge writes the code, and the user is owed every concept in it plus the command that runs it

**Options considered**

- The user types the code, Forge dictates
- Forge writes all but the load-bearing line, the user writes that one
- Forge writes it, and owes the concepts, the functionality and the run command in plain words

**Recommended:** Forge writes and owes the explanation - **Decided:** Forge writes and owes the explanation

## Why

Stated as the standing test for everything in this product: "The main aim is learning so it should be kept in mind, if ai does all the work itself then no purpose of making a plugin." Asked how far it goes, the user kept Forge writing the code and kept Forge starting the server, and drew the line at understanding: know every concept, and at minimum know what feature or functionality each piece of code provides. So the arrangement is not going to change, and the whole weight falls on what is said around the code. Two gaps followed from that. The per-file what/why/how was being written in the code's own terms, which teaches nobody: "app = FastAPI() creates the application object" says what the line says. The builder now names every idea the user has not met, in plain words, before the line that uses it. And the run command was being executed on their behalf and never explained, which is the one command they need first on the day Forge is not in the room, so it is now said part by part.

This is the counterweight to decision 073. That decision made Forge start the server so the user sees the thing working; without this one, the same convenience quietly removes the two moments where they would have learned what the thing is.

## In their words

The main aim is learning so it should be kept in mind, if ai does all the work itself then no purpose of making a plugin. as i am a builder so i want to learn things conceptually. Forge writes it but ik all the concept and all the code that is written atleast know what feature or functionality is written.
