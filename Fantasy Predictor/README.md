---
title: Start here
date: 2026-10-25
tags: [pitwall, index]
aliases: [Start here, Fantasy Predictor]
---

# Start here

These are my notes for PitWall, the F1 Fantasy predictor. They're for two readers:
me in a few months trying to remember how something works, and a new Claude chat
that needs catching up. If you're a new chat, read this page first, then whichever
notes below the task needs. Everything here was checked against the code on
2026-10-25, so if a note and the code disagree, the code wins and the note needs fixing.

## What PitWall is

A website that builds F1 Fantasy teams before the deadline (the start of qualifying,
or the start of the sprint race on sprint weekends, so sprint qualifying has already run). It looks at practice pace, turns that into
expected fantasy points, and finds the best 3 teams under budget, plus a 2x pick and
chip advice. Each weekend gets locked once, after the last practice session, and
saved as a snapshot so the answer never changes after that.

- Site: https://formula-1-fantasy-predictor.vercel.app (Vercel, React)
- Backend: https://formula-1-fantasy-predictor.onrender.com (Render free tier, FastAPI in Docker)
- Repo: https://github.com/pyyroo-a/Formula-1-Fantasy-Predictor
- Everything has to stay free. I can't pay for hosting or data.

## The notes

How it works:
- [Race weekend flow](Race%20weekend%20flow.md): what happens from FP1 to Monday, the one to read first
- [Model](Model.md): how a finishing order gets predicted, and why it's basically the practice order right now
- [Fantasy scoring](Fantasy%20scoring.md): turning a predicted finish into fantasy points, constructors, picking the 3 teams, the 2x pick
- [Chips](Chips.md): how each chip gets a PLAY / CONSIDER / HOLD
- [Planner](Planner.md): my own 3 teams and the transfer ladder, keep or swap and what each one is worth
- [Prices](Prices.md): where prices come from and the duplicate driver trap
- [Snapshots](Snapshots.md): locking a weekend, the GitHub Action, the setup steps
- [API](API.md): every endpoint and which file it lives in
- [Frontend](Frontend.md): how the site's files fit together

Why it is the way it is:
- [Decisions and evidence](Decisions%20and%20evidence.md): every measured number behind a decision, so nobody undoes one by feel
- [Scorecard](Scorecard.md): every 2026 race graded with the game's own points, PitWall against simple picks anyone could make
- [Gotchas](Gotchas.md): things that have bitten us before

Doing things:
- [How-tos](How-tos.md): lock a weekend by hand, re-record the tests, run it locally, start a new season
- [Working rules](Working%20rules.md): how I like to work with Claude on this

Where it's going:
- [Roadmap](Roadmap.md): the 7 projects from the post Austin brainstorm, open tasks, banked ideas, closed questions
- [Future plans](Future%20plans.md): the bigger career picture PitWall sits in

## Where things stand (2026-10-28)

- 2026 season, US GP (round 18) was locked automatically on FP3 by the GitHub Action.
  Mexico (round 19) is next, and its lock is the first to save ownership.
- Projects 1, 2 and 3 on the [Roadmap](Roadmap.md) are done. PitWall gets graded with
  the game's own points: 203.9 pts/race on the replay vs 190.6 for copying the FP3
  order, see the [Scorecard](Scorecard.md). The [Planner](Planner.md) is live under My
  Team: using free transfers its way beat keeping the team by 25 pts/race. Plans and
  designs are in [`docs/superpowers/`](../docs/superpowers/). Next is project 4, better
  practice data.
- 154 tests, all passing, including a test that fails if an em dash sneaks in anywhere.
- F1 put its live timing behind an F1TV login in October 2026. Practice comes from
  OpenF1 now, race results still come through FastF1 and that's fine (the 2026-10-26
  Monday job worked). See [Gotchas](Gotchas.md).

Related: [Race weekend flow](Race%20weekend%20flow.md), [Working rules](Working%20rules.md), [Roadmap](Roadmap.md)
