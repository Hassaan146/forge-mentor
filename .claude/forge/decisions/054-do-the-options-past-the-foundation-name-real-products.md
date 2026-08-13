---
id: 054
question: Do the options past the foundation name real products?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: d7df7878dddeb4d495c074be7b542f29aaccb7c6560944e108e83830fcdd4228
prev_sha: ad219a2be2e753527be84699e0a72b9cc4d4743e455c5318d096e4392db39c29
---

# The stack question keeps naming shapes; every question after it names the actual products, with what each one costs

**Options considered**

- No. Shapes only, everywhere, as decision 041 has it for the stack
- Yes, from the first question onwards
- Shapes for the stack question, named products for every question after it
- Let the planner decide per question

**Recommended:** Shapes for the stack, named products after it · **Decided:** The stack question keeps naming shapes; every question after it names the actual products, with what each one costs

## Why

Decision 041 made the stack options name shapes rather than technologies, and that was right for the first question: naming a product there assumes the shape nobody has chosen yet. It is wrong for everything after it. By the time a step is storing something the shape is decided, and 'a relational database' is no help to anyone. So the database question offers Postgres you run yourself, Supabase, Neon, SQLite, MySQL and MongoDB, each with the thing that is actually wrong with it, and the orchestration question offers nothing, a service manager, Docker Compose, a platform and Kubernetes, and says out loud that Kubernetes is the answer at a scale you are not at. This amends 041 rather than editing it, in the shape decision 042 used.

## In their words

I want to figure out whether I have to use Supabase or other databases or something else.
