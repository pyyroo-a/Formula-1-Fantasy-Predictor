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

- **The gains are inflated, a bit more since 2026-10-28.** The best team gets scored
  with the team builder's constructor bonus, your team gets scored from the pool, which
  has no bonus (see [Fantasy scoring](Fantasy%20scoring.md)). The builder's bonus is
  now the game's real one, up to +10 per constructor instead of +3, so the gap grew.
  That's part of why the US GP showed Limitless at +112. `FIX_CONSTRUCTOR_QUIRKS` closes
  it, but it measured +2.8 pts/race and lost more races than it won, so it's off for now.
- **Sprint weekends aren't treated differently yet.** A sprint weekend pays out twice,
  so the score driven chips (Limitless, 3x, Wildcard) are worth more there, but the
  thresholds are the same every weekend. Idea from before the Dutch GP, still open.
- The Chip Advisor page always uses FP3 (falling back to FP2, FP1), even on sprint
  weekends where the locked teams use sprint quali.
- I have no chips left for the rest of 2026 (joined mid season), so this all really
  matters from 2027.

## Where it's going

Project 6 on the [Roadmap](Roadmap.md): a season chip plan by circuit (the Reddit
style "Limitless at China, No Negative on street circuits, 3x on sprints", but backed
by real history and tested on past seasons), the weekly check comparing against that
plan ("play it now" vs "save it, Singapore is better"), and manual what ifs.

Related: [Fantasy scoring](Fantasy%20scoring.md), [Model](Model.md), [Roadmap](Roadmap.md)
