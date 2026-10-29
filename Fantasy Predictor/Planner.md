---
title: Planner
date: 2026-10-28
tags: [pitwall, planner, transfers]
---

# Planner

The "my team" transfer planner, project 3 on the [Roadmap](Roadmap.md). It's the call I
had to make by myself at the US GP: my main team had 2 free transfers, the big swaps
were obvious, and the hard part was the cheap picks and the second constructor. Is
this swap actually worth it, and is a 3rd one worth the -10?

## What it does

My Team > GARAGE (the PLANNER tab until the redesign, the chips for the same team sit next to it now). I save up to 3 of my real teams in the browser (5 drivers, 2
constructors, my budget, free transfers this week), pick a race, and get the ladder:

| Row | What it is |
|---|---|
| Keep your team | my team as it is, with its 2x |
| 1 transfer (free) | the best team with exactly 1 swap |
| 2 transfers (both free) | the best team with exactly 2 swaps |
| 3 transfers (all 3 free) | only when I saved one last week |

Each row shows what that team is expected to score (with the 2x counted), the
difference from keeping, the practice reason behind every swap ("Haas F1 Team P14 and
P17 to Audi P8 and P13 in FP3") and the 2x pick. Under it, facts only, never "do this":

- "The highest expected total is with 2 transfers (201)."
- "Transfer 2 adds +7."
- "Skip transfer 2 and you'd have 3 free transfers next week."
- "Transfer 3 costs -10."

Each row is worked out on its own. With budgets, the best 2 transfers often don't
include the best single one, so a row lists all of its swaps against my current team.

## The rules it follows

- **Free transfers:** 2 a race, ONE unused one carries over, so 3 at most, and every one
  past the free ones is -10. Checked 2026-10-28 against the 2026 rules write ups
  (motorsport.com, fanamp), the official rules page only loads in a browser. 2026 counts
  transfers as the net change from your last team, which is how the ladder counts them.
- **Same numbers as the Manual Team page.** Each driver's and constructor's points come
  from the same pool (`get_race_pool`). The ladder's total adds the 2x on top (Manual
  Team's MY SCORE doesn't), and the 2x pick is the main page's rule.
- **Budget** is what I type in, my total in the game (team value plus bank). Every row
  fits inside it. The keep row is whatever I have.
- **Forecast:** worked out live from practice like the Manual Team page. On a locked
  weekend it uses the session the lock used, before that it's a preview from the
  latest practice (sprint quali on sprint weekends).
- A pick that isn't in this weekend's field scores 0 and gets named in the facts.
- Rows and facts round the same way (.5 goes up), so a row and its fact always agree.

## Proven on real points

Before it shipped, `python scripts/planner_grade.py` replayed R3 to R18 of 2026 walk
forward from PitWall's R3 team at $100M (Antonelli, Russell, Hulkenberg, Bortoleto,
Lawson, Ferrari, Audi), graded with official points, -10 per paid transfer:

| Way to play | Real pts/race | Transfers | Hits |
|---|---:|---:|---:|
| Keep the team | 193.4 | 0 | 0 |
| Free transfers only | **218.6** | 29 | 0 |
| With hits | 214.6 | 32 | 3 |

- **Bar 1, free only has to beat keep:** +25.2 pts/race, better on 10, worse on 5. Passed,
  so the planner shipped.
- **Bar 2, with hits has to beat free only:** -4.0 pts/race. The 3 hits went Miami +15,
  Bahrain -30, Austin -28. Failed, so the paid row is off (`SHOW_PAID_ROW = False` in
  `src/planner.py`) and the page just says what a paid transfer costs. Our expected
  points aren't on the game's exact scale (no pit stops, retirements charged at 0), so
  "+X but -10" can't be trusted yet. Worth re-running after more races, it's one switch.

The usual caveat: 16 races, and a hit was only taken 3 times.

## Where the code is

- `src/planner.py`: the ladder, the facts, the rollover rule, `SHOW_PAID_ROW`
- `src/planner_replay.py` and `scripts/planner_grade.py`: the real points grade
- `src/api/planner.py`: `POST /transfer-ladder`, see [API](API.md)
- `frontend/src/components/myteam/TransferPlanner.jsx` and `frontend/src/plannerTeams.js`
  (`pitwall_planner_teams` in localStorage), see [Frontend](Frontend.md)

## For the redesign

The page works but it's plain. At first glance labels like "2 (free)" confused me in the
mockup, so the wording got spelled out ("2 transfers (both free)"), but the look is for
the one redesign at the end of the roadmap.

Related: [Roadmap](Roadmap.md), [Fantasy scoring](Fantasy%20scoring.md), [Decisions and evidence](Decisions%20and%20evidence.md), [Chips](Chips.md)
