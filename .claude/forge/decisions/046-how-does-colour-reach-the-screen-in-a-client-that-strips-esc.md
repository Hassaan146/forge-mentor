---
id: 046
question: How does colour reach the screen in a client that strips escape codes?
status: decided
date: 2026-08-12
decided_by: user
affects: phase-2, amends-045
content_sha: 6c34bb9e5f56c794238f5ee6d0055d6a7b37f09208aaa1d5690134c9a17ada5c
prev_sha: 5acadcc719e8da449381a616959be9706522461754359b5c77ae158ddc5903a1
---

# The client colours it. Forge stops trying to carry it there.

**Amends 044 and 045**, both of which concluded colour was unreachable here. They were wrong,
and the reason is worth writing down: every attempt was about getting colour *through* the
client, and none asked whether the client would apply it on arrival.

## What was actually checked

`claude.exe` on the user's machine, 267 MB, grepped for a highlighter. It bundles
**highlight.js**: 83 references to `hljs`, and `hljs-addition`, `hljs-deletion`, `hljs-meta`,
`hljs-comment`, `hljs-section`, `hljs-string` and `hljs-strong` are all present as class names.

So a fenced block in a language highlight.js knows is tokenised and painted by the client. The
```ansi attempt failed for a mundane reason: `ansi` is not a highlight.js language, so the fence
fell through to plain text with the codes visible.

That fact took one command. It came after eight rounds of shipping guesses.

## The shape

A ```diff fence, with the markers carrying Forge's meanings rather than version control's:

| | |
|---|---|
| `@@ … @@` | Forge's chrome: the heading rule and the turn rule |
| `+` | an option, a thing the user can pick |
| `-` | what it costs, the line R11 paints yellow |
| `#` | quiet detail: the subtitle, the hint, the progress |

Every marker sits in column zero, because highlight.js anchors them with `^`. That is why the
drawn left border is gone: a `│` in front of a `+` makes it an ordinary line. The fence is the
container instead, and the two rules close the block.

## What this cost, and the rule

Nine attempts. Six were guesses about a renderer, checked only after shipping. Two were worse:
a guard that certified a block the user could not see, and a frame test that refused a
presentation nobody had told it about.

**Ask what the destination does before deciding what it cannot do.** "Colour cannot reach this
client" was stated three times, in three commits, and it was never true. It was never checked
either, and the check was one grep of a file already on disk.

`FORGE_PLAIN_FENCE=1` and `FORGE_TABLE=1` remain, for a client with no highlighter.

Related: [[044-how-does-a-block-reach-the-user-s-screen-with-both-its-box-a]] - [[045-which-presentation-does-a-block-use-where-colour-cannot-arri]]
