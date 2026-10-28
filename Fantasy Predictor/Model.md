---
title: Model
date: 2026-10-25
tags: [pitwall, model]
---

# Model

How PitWall predicts a finishing order for a race that hasn't happened. Short
version: there's a real ML model in here, but right now the predicted finish we
actually score IS the practice order, because every time we measured it, the model
made the picks worse. The model's own opinion is still shown on the Predicted
Finishes page so we can keep an eye on it.

## Where the practice order comes from

`src/fetch_practice.py` builds a "grid" from a session: each driver's fastest lap,
ranked, plus the gap to pole and the gap to their teammate.

- **OpenF1 first** (`src/openf1.py`, free, no login). In October 2026 F1 put its
  live timing archive behind an F1TV login, and FastF1 reads from there, so FastF1
  started "loading" new sessions with 0 drivers and no error. OpenF1 measured
  identical to FastF1 on 4 old weekends (same 22 drivers, same order, same gaps to
  the millisecond).
- **FastF1 second**, which still works for old sessions that are in our cache.
- A session only counts once it's over plus 30 minutes, so half a session never
  gets locked in. OpenF1 sessions are matched by start time, not name (the Bahrain
  GP was in Kuala Lumpur this year).
- `USE_OPENF1=0` switches OpenF1 off and goes back to FastF1 only.

Which session: FP3 on a normal weekend (falling back to FP2, then FP1 for the
provisional), sprint qualifying on a sprint weekend. See [Race weekend flow](Race%20weekend%20flow.md).

## The ML part

`src/pipeline.py`, `src/models.py`, `src/features.py`.

- **XGBoost regressor** predicting finishing position: 200 trees, learning rate
  0.05, depth 4, 80% of rows and features per tree.
- **Trained on** 2025 plus every finished 2026 race, with 2026 weighted 5x
  (`sample_weight`), because 2026 is a regulation change year and the 2025 pecking
  order barely means anything. 2023 and 2024 are out on purpose.
- **Features** (`prepare_data` in `src/models.py`): `GridPosition`, `PreviousPosition`,
  `AveragePositionChange`, `Consistency`, `GridvsForm`, `FormTrend`, `WinRate`,
  `PodiumRate`, `TeamAvgPosition`, and `TeamName` one hot encoded. `WinRate`,
  `PodiumRate` and `TeamAvgPosition` are shifted one race back so a race never
  helps predict itself.
- **For an upcoming race** (`predict_upcoming_race`), the practice order stands in
  for `GridPosition`, then the model's guess gets blended with practice pace,
  teammate gap and the driver's history at that circuit. The blend weights depend on
  how easy it is to overtake there (`get_blend_weights` in `src/circuit_profiles.py`):

| Overtaking rating | Model | Practice pace | Teammate gap | Circuit history |
|---|---|---|---|---|
| 2 or less (Monaco) | 0.35 | 0.05 | 0.05 | 0.55 |
| 4 or less (Hungary, Singapore) | 0.45 | 0.10 | 0.05 | 0.40 |
| 6 or less (neutral) | 0.55 | 0.20 | 0.10 | 0.15 |
| 7 or more (Spa, Monza, Brazil) | 0.60 | 0.25 | 0.10 | 0.05 |

## Why the practice order wins anyway

After the blend, `shrink_to_grid` pulls the prediction back towards the practice
order by `SHRINK_TO_GRID` in `src/models.py`, and that's **0.0**, so `Predicted`
ends up exactly on the practice order. The blend is kept as `ModelPredicted`, which
only feeds the "model" column on the Predicted Finishes page.

Why 0.0: the backtest gave model picks 98.5 pts a race against 113.5 for just picking
by FP3 order, and the model won 0 of 8 races. My guess at the cause: the model trains
on the real quali grid but gets served the practice order, which is about 2 places
off, and it amplifies that noise. Full numbers in [Decisions and evidence](Decisions%20and%20evidence.md).
Raise it only if the [Scorecard](Scorecard.md) shows the model beating the FP3 order.
Heads up: those numbers came from the old backtest, which could see real retirements,
and haven't been re-measured.

## Retirement risk

`src/dnf.py` gives each driver a chance of not finishing, from where they start
(front runners retire far less), the season (2026 retires way more than 2025), the
driver and the circuit, with the driver and circuit numbers pulled towards average
because there's so little data per driver. It beats a flat average on 11 of 12
races. It's shown on every card but **doesn't change any score** (`DNF_WEIGHT = 0.0`
in `src/fantasy.py`), see [Decisions and evidence](Decisions%20and%20evidence.md).
Chips use it though, see [Chips](Chips.md).

## Confidence on each pick

Project 4. The FP3 order is right on average, but some FP3 spots are solid and some are
flukes. `src/confidence.py` gives every driver a level once the lock session is in,
from three checks, each failed one is a flag:

- **Teammate doesn't back it up:** more than 2 places from them in the lock session.
- **Moved around:** the sample std of their rank across FP1, FP2 and FP3 is above 1.5.
- **Tight pack:** under 0.05s from the nearest car on lap time.

0 flags = high, 1 = medium, 2 or more = low. A check we can't do (no teammate time,
only one session) counts as passed and the reason says so. Every level comes with a
plain sentence with the real numbers, e.g. "P4 in FP3. But teammate HAD was P10, moved
around between sessions (P2 to P5) and only 0.046s from the next car." On the cards a
top 3 (Safe) driver with low confidence shows CONSIDER instead of SAFE.

It **never changes a pick**, it gets added after the teams are built. Saved in the
snapshot at the lock (the picked drivers, plus every driver's level under `confidence`,
which the planner reads once the weekend is locked so it always matches the main page). Nothing on earlier session previews, on old snapshots, or on
sprint weekends (`SHOW_ON_SPRINT_WEEKENDS = False`, it didn't hold up there). High
means "trust this spot more", never "safe": even high lands within 2 places of its
fantasy points rank only half the time. Numbers in [Decisions and evidence](Decisions%20and%20evidence.md).

## Known weak spots

- One fastest lap per driver is a noisy summary, but the obvious fixes lost: the ideal
  lap (best sectors) and FP2 long runs both did worse than the plain FP3 order on
  fantasy points, see [Decisions and evidence](Decisions%20and%20evidence.md). (Max at
  the US GP: in OpenF1's FP3 data Hamilton had the fastest sector 2, and Max's ideal lap
  was P4, same as his lap time.) Confidence tells you which FP3 spots to trust instead.
- A red flagged session ranks people on 1 or 2 laps (Madring FP3: Hamilton 2 laps P9).
- No weather, no car problem detection.

Related: [Fantasy scoring](Fantasy%20scoring.md), [Decisions and evidence](Decisions%20and%20evidence.md), [Race weekend flow](Race%20weekend%20flow.md)
