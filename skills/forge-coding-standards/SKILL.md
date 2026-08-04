---
name: forge-coding-standards
description: How Forge writes code, injected on every build step so the generated project stays coherent across phases. Use whenever writing or editing code in a Forge-governed project.
---

# Coding standards

Loaded on **every** build step. Not advice — the reason the project still looks like one
project by phase eight, when the code was written weeks apart across different sessions.

Overridable, but only by a recorded decision that says which rule and why. The security floor
is the exception; it is not overridable at all.

## Write for the person who reads it next

- Names say what a thing is, not what type it is. `pending_invoices`, not `list2`.
- A function does one thing at one level of abstraction. If the name needs "and", split it.
- Comments say **why**, never what. The code already says what. A comment restating the line
  above it is noise; a comment explaining the constraint that forced an odd shape is the most
  valuable line in the file.
- Match the surrounding code. A file with one clever idiom in it reads worse than a plain file.

## Errors

- Fail on the specific exception, never a bare catch-all.
- An error message says what failed, what was expected, and what to do next.
- Never swallow an error to make a test pass. Never log-and-continue where the caller needed
  to know.

## Structure

- One responsibility per module. When a file needs "and" to describe it, it is two files.
- Dependencies point inward: the thing that changes often depends on the thing that does not.
- No configuration in code. No magic numbers — a named constant says what the number means.

## Tests

- A test names the behaviour it protects, not the function it calls:
  `test_a_write_with_no_decision_is_blocked`, not `test_governor_2`.
- Every test must be able to fail. A trailing `or True` slipped through here once and the test
  looked green for weeks.
- Test the boundary and the failure, not only the happy path. The happy path is the case that
  was already working.
- Prefer a real filesystem or a real repository over a mock wherever it is cheap. A mock proves
  the code calls what you expected, not that it works.

## What to do when the standards and the request conflict

Say so before writing, in one sentence, and offer the version that meets them. If the user
still wants it their way, write it their way and record the decision — including the rule it
sets aside. The record is what stops the same argument happening again in phase six.
