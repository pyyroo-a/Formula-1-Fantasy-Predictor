---
title: Fantasy scoring
date: 2026-10-28
tags: [pitwall, scoring, teams]
---

# Fantasy scoring

How a predicted finish becomes fantasy points (`FantasyValue`), how constructors get
scored, and how the 3 teams and the 2x pick get chosen. All in `src/fantasy.py`
unless it says otherwise.

## A driver's points

```
FantasyValue = RacePoints + OvertakeBonus + QualifyingScore + DNFPenalty
```

| Part | Points |
|---|---|
| Race finish | P1 25, P2 18, P3 15, P4 12, P5 10, P6 8, P7 6, P8 4, P9 2, P10 1, P11+ 0 |
| Qualifying (from the grid estimate) | P1 +10 down to P10 +1, P11 to P15 0, P16+ -5. The real game gives P11 to P20 a 0 (the -5 is only for no time), that's `REAL_QUALI_RULES`, switched off because it scored worse |
| Overtakes | +1 per place gained, -1 per place lost, times the circuit's overtaking scale |
| Retirement | -20, but charged at `DNF_WEIGHT = 0.0` for upcoming races, so 0 (see [Decisions and evidence](Decisions%20and%20evidence.md)) |

Fastest lap (+10) and driver of the day (+10) are left out on purpose, nobody can
predict them before a race.

The championship nudge (`src/championship_form.py`) moves each prediction a little
towards the standings. It used to clip everyone to P20, so in a 22 car field a P22
starter got predicted P20 and a made up +2 for overtakes. `CLIP_TO_REAL_FIELD` (on
since 2026-10-28) clips to the real field instead.

`PREDICT_SPRINT_POINTS = False`: on sprint weekends we don't add expected sprint
points to forecasts, it measured worse. Real sprint results still count when we
score a finished race (`sprint_score`).

## Circuit scaling

Every circuit has an overtaking rating from 1 to 10 in `CIRCUIT_PROFILES`
(`src/circuit_profiles.py`), plus an attrition rate:

- `overtaking_scale = rating / 5`: overtakes are worth 0.2x at Monaco, 1.8x at Monza and Brazil
- `quali_scale = 1 + (10 - rating) / 10`: quali points are worth 1.9x at Monaco, 1.1x at Brazil

Ratings: Monaco 1. Hungary, Zandvoort 3. Japan, Imola, Singapore, Barcelona 4.
Australia, Mexico, Abu Dhabi 5. Saudi, Miami, Madrid ("Spanish Grand Prix"), Vegas,
Qatar 6. Bahrain, China, Canada, Austria, Britain, Baku, USA 7. Spa 8. Monza, Brazil 9.

A race name missing from `CIRCUIT_PROFILES` silently falls back to a neutral 5, which
quietly makes the picks worse. Check it whenever the calendar changes, see [Gotchas](Gotchas.md).

## Constructors

A constructor scores both its drivers added together, plus a bonus in the team
builders: the game's qualifying bonus from the predicted grid (+10 both cars in Q3,
+5 one in Q3, +3 both in Q2, +1 one in Q2, -1 neither, `REAL_CONSTRUCTOR_QUALI_BONUS`,
on since 2026-10-28, we used to give only +3 / +1), plus +1.5 for a team averaging top
4 and +0.5 for top 7. All in `_constructor_scores`.

Two known quirks. Project 2 built the fix (`FIX_CONSTRUCTOR_QUIRKS`) and measured it:
+2.8 pts/race but it lost more races than it won, so it's still off:
- **The team builders drop Avoid drivers before adding up a constructor.** US GP
  2026: Cadillac got scored on Bottas alone (-3.7), both cars together were -8.8.
  So a constructor with a weak driver looks better than it is.
- **The driver pool skips the bonus.** So the chip check (which uses the pool) saw
  Ferrari as 67.7 while the team builder had 71.2 (US GP, old bonus). With the real
  bonus on the gap can be up to 10 points now, see [Chips](Chips.md).

There's a test pinning both (`test_constructor_scores_keep_the_avoid_quirk_for_now`).

Still missing compared to the real game: pit stop points (up to +20, +5 fastest, +15
world record). Nobody gives pit stop times out for free, so `src/constructor_extras.py`
works out what each constructor scores on top of its drivers and its bonus from the
official points, averaged over earlier rounds only. `USE_CONSTRUCTOR_EXTRAS` measured
+14.1 alone but only +0.3 on top of the two fixes that went on, so it's off and only
the backtest feeds it in.

## Picking the 3 teams

`build_budget_teams`:
1. Score every driver, tag them Safe (top 3 predicted), Value (top quarter by
   points), Avoid (bottom quarter) or Risk, and drop the Avoid ones.
2. Try every 5 drivers + 2 constructors combo under $100M with at least 1 Safe driver.
3. Keep the best 50, then pick 3 that differ by at least 2 drivers each. Loose on
   purpose: if a driver is clearly the best pick he can be in all 3 teams.

`build_budget_teams` is also what `/predict-budget` (the Team Optimizer page) uses.
`build_budget_team` (one team, only for the chip maths: the best legal team and the
best team with no budget cap) and `get_race_pool` (every driver and constructor, for
the Manual Team page and the chip checks) share the same scoring helpers, so there's
one copy of it.

## The 2x pick

`pick_boost_driver`: only drivers predicted into Q3 (P1 to P10), ranked by
`FantasyValue` plus a small bonus for starting near the front (up to +0.5 at P1, none
from P6). Doubling a P16 starter risks doubling a -5 (our forecast's rule, see above).

## How we know any of this works

Every finished race gets graded with the game's own points from the official feed
(`src/official_points.py`, saved in `data/official_points_2026.json`), never with our
version of the rules. The [Scorecard](Scorecard.md) puts PitWall next to picks with no
model at all. All the switch numbers are in [Decisions and evidence](Decisions%20and%20evidence.md).

Related: [Model](Model.md), [Chips](Chips.md), [Decisions and evidence](Decisions%20and%20evidence.md), [Scorecard](Scorecard.md), [Roadmap](Roadmap.md)
