---
title: Chips
date: 2026-10-28
tags: [pitwall, chips]
---

# Chips

How PitWall grades the 6 F1 Fantasy chips. It all happens in `evaluate_team_chips`
in `src/weekend.py`, which runs in two places:

- **Automatically, for each of the 3 locked teams.** The verdicts are saved in the
  snapshot and shown on the Overview (`AutoChipAdvisor.jsx`).
- **For your own team**, on the My Team > Chip Advisor page (`POST /chip-advisor` in
  `src/api/teams.py`). That one also shows the full Limitless and Wildcard teams.

## The verdicts

| Chip | What we measure | PLAY at | CONSIDER at |
|---|---|---|---|
| Limitless | best team with no budget cap minus your team | +40 | +20 |
| Wildcard | best legal team minus your team | +25 | +12 |
| 3x Boost | the best driver in YOUR team (it boosts someone you own) | 30 pts | 15 pts |
| No Negative | points at risk: expected retirements x 20 (your drivers plus both cars of your constructors) + 5 per driver predicted P16 or worse (our forecast's old quali rule, it drops out if `REAL_QUALI_RULES` ever goes on) | 30 at risk (HEDGE at 18) | |
| Final Fix | always POST-QUALI, and names your riskiest driver | | |
| Autopilot | always SAVE, the 2x pick already does its job | | |

Anything under CONSIDER is HOLD. No Negative uses the real retirement chances from
`src/dnf.py` instead of a list of crashy tracks, though the high attrition list
(Baku, Singapore, Monaco, Vegas, Saudi, Miami) is still shown with it.

## Things to know

- **The pool and the builder agree on the bonus now.** Your team used to be scored from
  the pool with no constructor bonus while the best team had it, so Wildcard and
  Limitless gains were inflated (part of why the US GP showed Limitless at +112). When
  the real bonus (up to +10 per constructor) went on, the best team's own chips told it
  to Wildcard into itself. Since 2026-10-28 the pool adds the same bonus. What's left
  is the Avoid quirk: a constructor with an Avoid driver is still added up differently
  (see [Fantasy scoring](Fantasy%20scoring.md)).
- **Sprint weekends aren't treated differently yet.** A sprint weekend pays out twice,
  so the score driven chips (Limitless, 3x, Wildcard) are worth more there, but the
  thresholds are the same every weekend. Idea from before the Dutch GP, still open.
- The Chip Advisor page always uses FP3 (falling back to FP2, FP1), even on sprint
  weekends where the locked teams use sprint quali.
- I have no chips left for the rest of 2026 (joined mid season), so this all really
  matters from 2027.

## Chip history by track (project 6, done 2026-10-28)

INSIGHTS > CHIPS. What each chip would really have been worth at every track, from the
game's own official points, best possible picks. Facts to weigh up before a race, not a
plan and never "play this now". Built by `scripts/chip_history.py` with
`src/chip_history.py`, rebuilt by the Monday job into `data/chip_history.json`, served
by `/chip-history`.

- **3x:** the top scorer's points that weekend (what a 3x adds over the 2x), and who,
  e.g. "93, ANT P19 to P1".
- **Limitless:** the best team with no budget cap minus the best $100M team.
- **No Negative:** what an average team would have got back, 7 x the mean of the points
  every driver and constructor lost below zero.
- **Wildcard, Final Fix, Autopilot:** one plain line each. They're about your team, not
  the track, so the live chip advisor above handles them.

2026 says (one season, so one weekend per track):

| Chip | Best | Worst |
|---|---|---|
| 3x | Monza 93 (Antonelli P19 to P1, a one-off), China 68, Canada 62 | Madrid 38 |
| Limitless | Miami +167, Madrid +127, Suzuka +119 | Monaco +15 |
| No Negative | Singapore 37.8, Baku 31.2, Melbourne 31.0 | Silverstone 4.9 |

My hunches, checked: 3x on a sprint only adds about 6 points on average (58.0 vs 51.6),
picking the right driver matters way more. No Negative: Singapore and Baku top it this
season, which fits my street track hunch, but it's one weekend each so far (Melbourne is
right behind them).

**Only official seasons, growing every year.** We tried 2025 with our own scoring of the
results, but our maths only counts the basics: a pole to win weekend came out at 35
almost everywhere, the real game gave 45 to 93 in 2026. It made every track look the
same and the "does 2025 predict 2026" check came out at 0.05 because of that, not
because of the tracks. 2025 still trains the model. The honest check (does last
season's ranking predict this one's) runs by itself once 2027 is raced (the script picks
up every `data/official_points_YYYY.json`), and the page says "1 season so far" until
then. Tracks are matched by place, not race name, so
2027's Sakhir and Jeddah won't mix with 2026's "Bahrain GP" in Kuala Lumpur, and
Monte Carlo = Monaco.

Related: [Fantasy scoring](Fantasy%20scoring.md), [Model](Model.md), [Roadmap](Roadmap.md)
