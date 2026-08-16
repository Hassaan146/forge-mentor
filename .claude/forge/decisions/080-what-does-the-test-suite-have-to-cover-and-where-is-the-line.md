---
id: 080
question: What does the test suite have to cover, and where is the line drawn?
status: decided
date: 2026-08-16
decided_by: user
affects: phase-10
content_sha: d3e7cb8eb3e42fc9a1f4513458b07953ddb6fde1666298b905ec3e5af39eac6b
prev_sha: d0103679c8b46b28d1d191ecc47baffce1b89863785af9255bc95971677437e4
---

# 100 percent, measured across the libraries, the hooks and the engine, and gated at 100 in CI

**Options considered**

- Leave it at 89.68 percent of scripts/ and say why the rest is not worth covering
- Real tests wherever a test can run, pragma only for process entry points, engine included, gate raised to 100
- Reach 100 quickly by excluding whatever is awkward

**Recommended:** Real tests, engine included - **Decided:** Real tests, engine included

## Why

Two things were wrong with the old number. It measured scripts/ only, so the 2,506-line engine and all 49 of its tools sat outside the figure entirely, and 89.68 percent of the smaller half is a smaller claim than it sounded. And the uncovered tenth was almost entirely defensive branches: a file that cannot be read, git missing, a permission flag that will not set. Every one of those has a documented answer in a comment, and not one had ever run.

Both were fixed by writing tests rather than by excluding code. 345 new tests across five files: the tools no session path reaches, then each module's own failure rule, which differs on purpose. The governor fails closed because a blocked write costs one turn. The presenter fails open because a Stop hook that errors ends the conversation. The meter reports unavailable rather than zero, because zero is a number somebody would believe.

Twenty lines carry pragma: no cover, every one an if __name__ == "__main__" block or a CLI main, each with its reason inline. Nothing behavioural is excluded, which is a claim a reader can check with one grep.

The work paid for itself once immediately. The _says_why decorator from the audit was never being exercised: functools.wraps sets __wrapped__, the test helper followed it, and every test ran the undecorated function while production ran the wrapper. The suite was green on that for a day.

What 100 percent does not prove is worth saying in the same breath: the fifteen unreachable tools found by the audit were covered, some near 100, and callable by nobody. Coverage measures lines executed, not behaviour guaranteed. The caller-exists guard from decision 079 remains the more valuable test.

## In their words

completel the 100 percent implementation
