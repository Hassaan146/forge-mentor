---
id: 073
question: What does the user see between deciding a step and the code existing?
status: decided
date: 2026-08-14
decided_by: user
affects: phase-5, phase-8
content_sha: ed75b4c493b4974f38ff138523863173fe187206b20f63d86d0654ecdc756529
prev_sha: 6b26810176aa121b50e3361499b0128cce6e0b15233b16ac4b540f8336470251
---

# The ledger is required, and a step is not built until the user has watched it run

**Options considered**

- Leave the ledger opt-in and put "announce the step first" in the builder's brief
- Require plan_files before any write, and require proof and see_it before a step ticks off
- Require the ledger only for steps that write more than one file

**Recommended:** Require both - **Decided:** Require both

## Why

A decided step went from an A/B/C answer to three finished files with nothing said in between, and the user's words were "you are executing the steps directly. I don't know what is happening in this step." The mechanism for saying it already existed - decision 069's file ledger - and forge_build.allowed returned True whenever a step had no plan, on the reasoning that the ledger was opt-in per step. Opt-in is the same shape as advice: the runs that skip it are exactly the runs that were going to surprise somebody. So no plan is now a refusal that names plan_files, and plan_files takes one plain line on what the step does, because a list of filenames says what is about to appear and not what it is for.

The same run ended with the builder starting the server on a spare port, confirming it privately and shutting it down, then telling the user how to run it themselves. That is a step finished on paper. step_built now refuses without proof, what was run and what came back, and see_it, the command and address the user can use now - and the brief says to leave it running so the address is live when they read it.

## In their words

There is one problem: 1. It should run the server, which it is not running. 2. It has to ask for the change. You have just made the steps, and you are executing the steps directly. I don't know what is happening in this step. At least tell me what is happening in this.
