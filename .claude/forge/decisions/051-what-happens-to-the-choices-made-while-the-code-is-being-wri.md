---
id: 051
question: What happens to the choices made while the code is being written?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: 8ed8a6a942de0ece8886397d7bd06d4cc1b41cf38a5e4049b399ab414fb0ffe2
prev_sha: 96adb78fc77b0e8e103ea6306c59cbdd84037ce9107df54ed9be022fd08ba421
---

# Every choice made while building is recorded as it is made, and it cannot open a gate

**Options considered**

- Nothing, they are implementation detail
- The builder mentions them in its reply
- Each is written to the notes as it is made, marked as Forge's and not permission
- Stop and ask the user about each one

**Recommended:** Written as they are made, marked, and never permission · **Decided:** Every choice made while building is recorded as it is made, and it cannot open a gate

## Why

A recorded step decision does not settle everything inside it. What a module is called, whether a failure raises or returns, where a helper lives, which library gets pulled in: all invisible, and invisible is how a project ends up with conventions nobody chose and the user cannot explain when asked. They are marked in the header, inside the fingerprint, and the step gate refuses to count them. Without that the builder could clear its own gate by writing down what it had decided to do, which is the governor rule inverted. A choice that would change what the project is, is refused as a build note and sent back to be asked properly.

## In their words

If you are coding, you have to record all of your decisions.
