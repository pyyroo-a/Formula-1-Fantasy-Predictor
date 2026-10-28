---
title: Decisions and evidence
date: 2026-10-28
tags: [pitwall, evidence, decisions]
---

# Decisions and evidence

Every decision here was measured, not guessed. Don't undo one without new numbers
that beat these. The rule we work by: measure before shipping, and if something
measures worse, switch it off and leave the number next to the switch in the code.

Since 2026-10-28 the yardstick is the season scorecard, `python scripts/scorecard.py
--rules <names>` (see [Scorecard](Scorecard.md)). It replays every finished race with
`run_backtest` using only what was known before it, and grades every team with the
game's own points from the official feed, not our version of the rules. A
`--rules` name flips switches for that run only, e.g. `--rules bonus+clip`.

**Heads up on older numbers.** Everything measured before 2026-10-28 (the first table
below) used the old backtest, which graded with our own rule maths and, we found out,
had a leak: the replay could see which cars really retired, so it dodged them (US GP:
Bottas, Colapinto and Bearman, all DNFs). That's fixed and the replay now rebuilds the
real locked teams exactly, but those older numbers haven't been re-measured. I decided
to leave them flagged rather than redo them.

## Project 2 switches (measured 2026-10-28, rounds 3 to 18)

All in `src/fantasy.py`. Before any of them: 187.5 real pts/race, copying the FP3 order
190.6.

| Switch | Value | Real pts/race | Races better / worse |
|---|---|---|---|
| `REAL_CONSTRUCTOR_QUALI_BONUS` (game's -1/+1/+3/+5/+10) | **on** | 194.3 alone | 1 / 0 (only Monza changed) |
| `CLIP_TO_REAL_FIELD` (no made up +2 for P21/P22) | **on** | 200.4 alone | 5 / 3 |
| both together, what ships | | **203.9** | 6 / 2 |
| `USE_CONSTRUCTOR_EXTRAS` (expected pit stop points) | off | 201.6 alone, 204.2 on top of the two | 4 / 1 alone |
| `FIX_CONSTRUCTOR_QUIRKS` (every page adds constructors up the same way) | off | 190.3 | 1 / 2 |
| `REAL_QUALI_RULES` (P11 to P20 = 0, no -5 for P16+) | off | 175.3 | 5 / 9 |
| all five | | 155.5 | 3 / 12 |

Why the right quali rule scores worse: without the -5 the back of the grid costs
nothing to own, so the optimiser fills up on cheap P16+ drivers (24 of 80 picks vs 8 of
80). Extras stayed off because +0.3 on top isn't worth wiring into the live site.

## The planner's paid row (measured 2026-10-28, rounds 3 to 18)

`SHOW_PAID_ROW` in `src/planner.py`, measured with `scripts/planner_grade.py` from
PitWall's R3 team at $100M, official points, -10 per paid transfer:

| Way to play | Real pts/race | vs |
|---|---:|---|
| Keep the team | 193.4 | |
| Free transfers only | 218.6 | +25.2 on keep, better on 10, worse on 5 |
| With hits | 214.6 | -4.0 on free only, 3 hits (Miami +15, Bahrain -30, Austin -28) |

Free transfers passed, so the [Planner](Planner.md) shipped. The paid row failed, so it's
off and the page only states what a paid transfer costs.

## Project 4: better inputs and confidence (measured 2026-10-28)

First we tried to beat the FP3 order with better practice inputs. Places between a
driver's practice rank and their real rank, 2026 (quick read only checks, the scripts
are in the project 4 session notes, not the repo):

| Idea | Fantasy points, places off | vs FP3 order now | Verdict |
|---|---:|---:|---|
| Ideal lap (best S1 + S2 + S3), FP3 weekends | 4.04 | 3.90, ideal worse on 9 of 12 | dropped |
| FP2 long run pace (best stint median, 6+ clean laps), 11 FP3 weekends | 3.51 | 3.03, long runs worse on 9 | dropped |
| Half FP3 order, half long runs | 3.22 | 3.03, worse on 7 | dropped |

Long runs are patchy too (Spa: 2 of 22 did one), and fuel loads can't be seen for free.

What did work is telling solid FP3 spots from shaky ones, see [Model](Model.md). Graded
with `python scripts/confidence_grade.py` (rows in `archive/results/confidence_rows_2026.csv`):

| Normal weekends (12) | Driver weekends | Places off, fantasy points | Within 2 places | Places off, finish |
|---|---:|---:|---:|---:|
| High | 53 | 3.02 | 51% | 1.11 |
| Medium | 86 | 3.59 | 48% | 1.87 |
| Low | 122 | 4.51 | 30% | 2.09 |

High beat low on fantasy points on 11 of 12 weekends. Sprint weekends (6, locked on
sprint quali): high 4.81, medium 4.30, low 4.78, high beat low on only 3 of 6, so
`SHOW_ON_SPRINT_WEEKENDS` is off. Heads up: the cutoffs (2 places, 1.5, 0.05s) were
picked near the middle of this same data, so Mexico onwards is the honest test. It
doesn't change picks, so there's no points scorecard number for it.

## Switched off earlier (old backtest, see the heads up)

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
- **The P10/P11 line:** 14.2% of picks land on the wrong side of it (14.6% normal
  weekends, 13.8% sprint), where quali points go from something to nothing. Monza
  2026: practice had Gasly 9th, he took pole. (This used to say 25.8%, but that also
  counted a P15/P16 "cliff" that isn't in the real game. Same rounds 1 to 12 data,
  `archive/results/grid_error_2026.csv`.)
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

## The accuracy bar

From the post Austin brainstorm: PitWall has to beat simple ways of picking that need
no model, over a whole season, scored with the game's real points, or it isn't
earning its place. Project 2 built that. Rounds 3 to 18 of 2026, real pts/race:

| | Before the fixes | Now |
|---|---|---|
| PitWall (replay) | 187.5 | **203.9** |
| Copy the FP3 order | 190.6 | 190.6 |
| Most expensive that fit (average of every max spend team) | 135.2 | 135.2 |
| Best possible in hindsight | 292.2 | 292.2 |
| PitWall's real locked teams (R13 to R18) | 175.2 | |

So it went from level with guessing to about 13 points a race ahead, winning 8 of 16
races against FP3 order and 14 of 16 against most expensive. Not perfect and it never
will be, F1's too random for that. The catch: the switches were picked on these same 16 races, so part of that lead
could be luck in the choosing (the bonus's +6.8 is all from Monza). Mexico onwards is
the real test, re-run the scorecard after a few races.

"Most expensive" used to be one team picked by the alphabet (about 2,000 teams cost
exactly $100.0M every round), which made it look like 168.4. Now it's the average of
all of them. Found in the final review.
"Copy the crowd" starts filling in from Mexico, when the first ownership gets saved.
The track record page (project 5) will show this on the site.

Related: [Model](Model.md), [Fantasy scoring](Fantasy%20scoring.md), [Scorecard](Scorecard.md), [Roadmap](Roadmap.md)
