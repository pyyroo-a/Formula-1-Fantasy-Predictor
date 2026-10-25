---
title: Working rules
date: 2026-10-25
tags: [pitwall, process]
---

# Working rules

How I work on PitWall, with Claude or without. A new chat should follow these.

- **Ask before writing or changing code.** Explain what and why, then wait for a yes or
  no. Reading, investigating and measuring are fine without asking.
- **I commit and push, never Claude.** At each milestone: the files to tick in GitHub
  Desktop, a Summary and a Description, then wait for me to say "committed".
- **Measure before shipping.** Every model or scoring change gets tested on past
  weekends first. If it measures worse, it gets switched off and the number goes in a
  comment next to the switch. See [Decisions and evidence](Decisions%20and%20evidence.md).
- **Data true always.** Numbers follow the real data. Never tune or fake a result to
  look better.
- **Tests pass before a push**, and files that belong together go in one commit.
- **No backend pushes from FP1 Friday until the race is over.**
- **Free hosting and free data only.** Already ruled out: Hugging Face Spaces (went
  paid), DigitalOcean credits (expired), Oracle Always Free (too much setup), F1TV (paid).
- **No em dashes or en dashes**, anywhere. There's a test for it.
- **Comments, notes and commit messages in my voice**: plain and casual, "we",
  "basically", short explanations of why. Things I found myself get written as mine.
- **Never ask for or handle the `SNAPSHOT_SECRET` value.**
- If I say "let's come back to that later", don't bring it back up unless I do.
- Big pieces of work: brainstorm first, a short design, a plan, then build it in steps
  with a commit each. Designs and plans live in [`docs/superpowers/`](../docs/superpowers/).

Related: [README](README.md), [How-tos](How-tos.md)
