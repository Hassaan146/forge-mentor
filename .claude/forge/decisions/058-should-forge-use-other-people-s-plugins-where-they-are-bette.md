---
id: 058
question: Should Forge use other people's plugins where they are better than its own?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: d87a49d9f37cd6eeb682794e5a3c38e3613aba9996e649c3afe037e1191aa489
prev_sha: c3b2b5870f4507769e29adc77bfe696ad99c5d6351f562a43479c20b31a2a20b
---

# ponytail is wired in as an optional companion at the building and review stages, used in addition to Forge's own skills and never instead of them

**Options considered**

- No. Everything Forge relies on ships with Forge
- Yes, copy the useful ones into the plugin
- Yes, as optional companions: additive, detected, never required
- Yes, and require them, so behaviour is the same everywhere

**Recommended:** Optional companions: additive, detected, never required · **Decided:** ponytail is wired in as an optional companion at the building and review stages, used in addition to Forge's own skills and never instead of them

## Why

ponytail (github.com/DietrichGebert/ponytail, MIT) teaches an agent to write the least code that works: check whether it needs writing, whether the project already does it, whether the standard library does it, before adding anything. It is aimed at the same target as Forge from the other end. Forge governs which decisions get made; ponytail governs how much code the answer turns into, which is the same token argument that produced the incremental path. It is kept out of ROUTE on purpose. ROUTE is deterministic because its skills ship with Forge or with the pinned library, and folding in a plugin installed separately and updated on someone else's schedule would turn 'the same skills every time' into 'unless the user happened to install something'. So COMPANIONS is a separate table, absence is a suggestion rather than a failure, and where the two disagree Forge wins: the security floor is not overridable, and a recorded decision is not optimised away because a shorter version exists. Copying it in was rejected despite the licence allowing it, because a vendored copy of a repository moving that fast is a fork nobody volunteered to maintain.

## In their words

I want you to also see if we can integrate or work with the ponytail plugin, which is a very good plugin for coding of AI. If we can integrate that into this plugin, our code quality is good enough.
