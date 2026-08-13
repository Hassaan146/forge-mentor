---
id: 064
question: How does a reviewer that runs in the session join the two that run on GitHub?
status: decided
date: 2026-08-13
decided_by: user
affects: 
content_sha: e2442fce145d6df6b3d0049037e3e655429cb5c8e4bb8fed7f9b33fdc2ac0ccc
prev_sha: 0a635253108bb8713943fed1cd55079966f7c8b45d6e3fba8745fcd81d052f33
---

# ponytail's findings are filed in pr-<n>.local.md, merged into pr-<n>.md on every fetch, and gated exactly like CodeRabbit's and Sourcery's

**Options considered**

- It does not. ponytail advises the builder and never files a finding
- Its findings go in their own file, merged into the combined one on every fetch
- Write them straight into pr-<n>.md
- Post them to the pull request from the user's account so the fetch picks them up
- Run ponytail in CI so it posts like the other two

**Recommended:** Its own file, merged on every fetch · **Decided:** ponytail's findings are filed in pr-<n>.local.md, merged into pr-<n>.md on every fetch, and gated exactly like CodeRabbit's and Sourcery's

## Why

CodeRabbit and Sourcery are GitHub apps: they post to the pull request and a workflow reads them (decisions 025, 026). ponytail is a plugin in the user's session, on the machine that wrote the code, and it has no account to post from. Writing straight into pr-<n>.md was rejected because the workflow rewrites that file on every review, so the local findings would vanish at the next fetch and nobody would see them go. Posting from the user's account was rejected because the reviewer table is anchored to the two bot logins on purpose: the repository is public, and any account whose name contains the right word could otherwise raise findings and satisfy the reviewed check on its own. Running it in CI would need Claude Code and credentials in Actions to review a diff that was already reviewed here for free. So the local findings get their own committed file, and `fetch_and_save` assembles the combined view from both every time: decision 026 stays true, nothing is overwritten, the anchored check stays as strict as it was, and `is_clean` counts all three so a step is not finished while any of them is open. Closing one routes on its id, since a local finding has no GitHub thread behind it.

## In their words

After each PR I want the code reviews of Sourcery and CodeRabbit to come, combine with the ponytail reviews, and then Claude fixes all of those problems.
