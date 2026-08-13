---
id: 069
question: How does the code reach the user: all at once, or a file at a time?
status: decided
date: 2026-08-14
decided_by: user
affects: 
content_sha: 320108543a4b6205d1820a6a16ade1160626162f22d60be91ca22e3e60bf2792
prev_sha: 3281dae950b8acb470c32625c1b7d8b55f5212b196a47ce042febcad62f4a548
---

# The step names its files first, skeleton before detail, and the governor allows one at a time: what it is, why it exists, how it works, then the file, then the next

**Options considered**

- As the builder produces it, which is a step's worth of files in one turn
- One file at a time, in a planned order, each explained before the next
- All at once, with an explanation written afterwards
- One file at a time, with the explanation optional

**Recommended:** One file at a time, each explained before the next · **Decided:** The step names its files first, skeleton before detail, and the governor allows one at a time: what it is, why it exists, how it works, then the file, then the next

## Why

A decided step came back as four finished files. Every one was permitted and covered by the decision, and the user watched an application appear: they could defend the decision because they made it, and not the code, because they met it finished and all at once. That is the problem this product exists to solve, moved one level down. So the unit is the file and the price of the next one is explaining the last, which is what stops the explanation being a note somebody meant to add at the end. Three questions and not one sentence three ways: what it is without why leaves somebody who can read the code and not question it, and why without how leaves somebody who agrees with a thing they could not maintain. Skeleton first, so what arrives is a project taking form rather than a pile in alphabetical order. The ledger is opt-in per step and can be extended with `add_file`, because a list with no way to grow is a list somebody works around, and working around it means writing files nobody announced.

## In their words

Update all the code so that it should have an incremental approach in coding. Ponytail should ensure at least an incremental approach so that the user can understand each and every concept of the code: why we are using a certain thing, how we are using it, what it is.
