---
id: 070
question: What does Forge need to know about a project that it was never asking?
status: decided
date: 2026-08-14
decided_by: user
affects: 
content_sha: 8578f393d8880ef4b29d514cae582f1fc790a77ddfa330d35b136a6606ab80f0
prev_sha: 320108543a4b6205d1820a6a16ade1160626162f22d60be91ca22e3e60bf2792
---

# A question for the name and the repository, asked straight after the idea

**Options considered**

- Nothing. The six questions cover the shape
- What it is called and where the code lives, asked second
- Ask for the repository only when a push is first attempted
- Read it from the git remote and never ask

**Recommended:** Asked second, before the stack · **Decided:** A question for the name and the repository, asked straight after the idea

## Why

The foundation asked what the project *is* and never what it is *called* or where it lives, which Forge needs to push, to open a pull request and to read reviews back. Asked second because it does not depend on the stack and everything written afterwards goes into it, and renaming a repository later breaks every link, clone and pipeline pointing at it. Left open with no menu on purpose: a menu here would be Forge naming somebody's project for them, and the answer is two facts it cannot guess. Reading it from the git remote was rejected because a remote that exists is not the same as a remote the user meant to use, and decision 006 already makes the repository theirs to create.

## In their words

There are some basic questions Claude should have, for example the repository name, and other things. There are a few fundamentals to add in the governor.
