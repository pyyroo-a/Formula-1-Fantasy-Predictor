---
title: Decisions and evidence
date: 2026-10-25
tags: [pitwall, evidence, decisions]
---

# Decisions and evidence

Every decision here was measured, not guessed. Don't undo one without new numbers
that beat these. The rule we work by: measure before shipping, and if something
measures worse, switch it off and leave the number next to the switch in the code.

The backtest is `run_backtest(use_practice=True)` in `src/backtest.py` (or `/backtest`
locally). It replays finished races using only what was known before each one, and
the bar is "just pick by FP3 order".

## Switched off, and why

| Switch | Value | Evidence |
|---|---|---|
| `SHRINK_TO_GRID` (`src/models.py`) | 0.0 | model picks 98.5 pts/race vs 113.5 for FP3 order, won 0 of 8 races. With the real quali grid: 1.0 gave -35.9/race, 0.6 -22.9, 0.4 -12.6, 0.0 exactly the baseline |
| `DNF_WEIGHT` (`src/fantasy.py`) | 0.0 | over 10 races: 113.9 pts/race with no charge, 83.2 at 15%, 30% and 50%, 87.0 at 100%. Charging retirement risk pushes the picks off the cheap deep field drivers, which is exactly where a budget team earns its points |
| `PREDICT_SPRINT_POINTS` (`src/fantasy.py`) | False | 4 sprint weekends: baseline 113.0, + sprint points 113.0 (changed nothing), + sprint quali input 143.2, both 135.8 |

Also tried and dropped: discounting the overtake bonus (no consistent gain), and FP2 +
FP3 combined on normal weekends (grid error 2.26 vs 2.07 for FP3 alone).

## Kept, and why

- **Lock normal weekends on FP3.** Hungary R11 2026 was the first weekend with picks
  locked on FP3: the 3 teams scored 131, 217 and 182 once everything settled, and the
  2x pick turned out to be the best possible captain.
- **Lock sprint weekends on sprint qualifying, not FP1.** The fantasy deadline is the
  sprint race, so sprint quali has already happened. About +30 pts a race, and the
  grid it gives matches the real sprint grid exactly 72% of the time.
- **Practice comes from OpenF1.** Identical to FastF1 on Monza, Madring, Baku and
  Bahrain FP3: same 22 drivers, same order, same gap to pole to the millisecond.
- **The DNF model is good, just not as a points charge.** Beats a flat average on 11
  of 12 races (Brier 0.1652 vs 0.1750). Its ranking works (the over 30% band really
  retires 43%) but the raw numbers run low (17.9% predicted vs 20.1% real), so treat it
  as a ranking, not exact odds.

## How good the predictions are

- **Practice order vs the real grid:** about 2 places off on average (2.15), within 1
  place half the time, 6+ places off 5% of the time. Not biased towards any team, just
  noisy. Sprint weekends are worse (2.5 places vs 1.9).
- **The scoring cliffs:** 25.8% of picks land on the wrong side of P10/P11 or P15/P16,
  where quali points jump. Monza 2026: practice had Gasly 9th, he took pole.
- **Walk forward over 13 races of 2026:** practice order beat the model column on
  everything. Winner right 6/13 vs 4/13, places off 2.05 vs 2.31, rank correlation
  0.829 vs 0.803. (Antonelli won 7 of 13, so "always pick Antonelli" also gets 7.)
- **Fantasy value vs points really scored:** rank correlation 0.815, and on average
  3.92 of our top 5 value picks really were top 5 scorers. This is the number that
  matters most for fantasy.
- **Recovered weekends, places off per classified finisher:** Baku R15 (FP3) 3.67,
  Bahrain R16 (FP3) 3.05, Singapore R17 (sprint quali) 2.39.

Measuring scripts: `scripts/measure_grid_error.py` (writes to `archive/results/`) and
`scripts/measure_dnf.py`.

## The accuracy bar going forward

From the post Austin brainstorm: PitWall has to beat simple ways of picking that need
no model ("copy the FP3 order", "most expensive drivers that fit") over a whole
season, scored with the game's real points, or it isn't earning its place. That's
project 2 on the [Roadmap](Roadmap.md), and the track record page (project 5) shows it.

Related: [Model](Model.md), [Fantasy scoring](Fantasy%20scoring.md), [Roadmap](Roadmap.md)
