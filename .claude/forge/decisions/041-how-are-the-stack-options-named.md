---
id: 041
question: How are the stack options named?
status: decided
date: 2026-08-10
decided_by: user
affects: phase-8
content_sha: 070c7ca6109478cb5ae0384ae4fa3519d2b56756995b18e4c4e8469a1a91001f
prev_sha: 99ca02c4a7e549a3ed6d6cfddb8d72181d47890be5b2b0f20f4ae7ecdd8bc126
---

# By the shape you end up with, not the technology you would type

**Options considered**

- **A** - keep the technology names: "Browser only", "Browser + small API", "Python service"
- **B** - name the shape: front end only, back end only, both together, command line
- **C** - ask the shape first, then a second question for the technology

## Why

**A hid an answer in plain sight.** A user reading the list said the options were missing the
case where you build the API and database first and add the screens later. It was there. It was
option B, called "Browser + small API", and the name described what they would type rather than
what they would have, so they could not see it.

That is the same failure as leaving it out. A menu is read for what it appears to offer, and
nobody audits a menu against the thing they were about to ask for.

**C is the split that decision 033 already refused**, one question up. Language, framework and
runtime do not separate cleanly, and asking the shape and then the technology lets an answer to
the first quietly rule out most answers to the second without anyone noticing.

**B keeps them together and names the outcome.** "Back end only, an API and a database now,
screens added later" is a sentence someone can recognise their own plan in. Rule R2 still holds:
the consequence line names the real thing, so the label can be plain without the option being
vague.

## The set

| | | |
|---|---|---|
| A | Front end only | screens in the browser, no server, data on this machine |
| B | Back end only | an API and a database now, screens added later |
| C | Both together | screens plus your own API and database |
| D | Command line | you type commands, nothing to host, no screens |

The teaching above them changed to match: you are choosing the shape, and the language and
framework follow from it.

Related: [[033-the-stack-is-the-first-question]]
