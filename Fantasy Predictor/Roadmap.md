---
title: Roadmap
date: 2026-10-28
tags: [pitwall, roadmap]
---

# Roadmap

Where PitWall is going. Update this as things get done.

## The 7 projects (post Austin brainstorm, 2026-10-25)

Agreed after the US GP: PitWall has to beat simple no-model picks over a season, or
it isn't worth trusting. One project at a time, in this order. The full write up is
in [the design doc](../docs/superpowers/specs/2026-10-25-cleanup-and-notes-design.md)
(bottom section) and the cleanup's [plan](../docs/superpowers/plans/2026-10-25-cleanup-and-notes.md).

1. **Cleanup and these notes.** One scoring path, leftovers gone, big files split, no
   dashes, this vault. Done.
2. **Accuracy bar and real constructor scoring.** Done 2026-10-28. Every race graded
   with the game's own points (the official feed, not OpenF1, which only had pit times
   for 6 races) against no-model picks, see the [Scorecard](Scorecard.md). Every rule
   fix measured behind a switch, only the winners went on (the real constructor bonus
   and the P22 clip fix): 187.5 to 203.9 pts/race, copying FP3 is 190.6. The quirks
   fix and pit stop points measured too small to ship, the real quali rule measured
   worse. Numbers in [Decisions and evidence](Decisions%20and%20evidence.md).
3. **"My team" planner.** My team saved in the browser, plus free transfers and my real
   bank balance. After the lock it shows the best move for 0, 1, 2 and 3+ transfers
   with -10 per extra transfer already taken off, plus the 2x pick. Advice only, never
   touches my F1 Fantasy account. Every weekend type, and next season too. Chips plug in
   later. This is the call I had to make by myself at the US GP.
4. **Better practice data, plus confidence and reasons.** I watched Max top sector 2 in
   FP3 at the US GP while the model only saw he was P4 on lap time. Add best sectors
   (the ideal lap), long runs vs quali runs (OpenF1 stints and tyres), all three
   sessions. Aimed at the race finish and fantasy points, not the quali order. Then each
   pick gets a real confidence level and reason.
5. **Track record page.** The real points every locked team scored vs the simple
   picks, so trust comes from results.
6. **Chips.** A season chip plan by circuit, backed by history and tested on past
   seasons. The weekly check compares against the plan. Manual what ifs. Aimed at 2027,
   I have no chips left this season. See [Chips](Chips.md).
7. **Reddit discussion feed (parked).** What people are picking and their game plans.
   Reddit's free API is limited and AI summaries would cost money, so later. Ownership %
   IS in the F1 Fantasy feed, and every snapshot saves it at the lock since project 2.

After all that: **one UI redesign** of the whole site using the frontend design plugin,
once projects 2 to 5 have added what they add. No piecemeal UI changes before then.

## Open tasks

- **Delete the cron-job.org job.** The Action locked the US GP by itself, so it's no
  longer needed.
- **Re-measure the old switches** (`SHRINK_TO_GRID`, `DNF_WEIGHT`,
  `PREDICT_SPRINT_POINTS`) on the scorecard. Their numbers came from the old backtest
  that could see real retirements, see [Decisions and evidence](Decisions%20and%20evidence.md).
- **Why the real quali rule loses.** With P11 to P20 at 0 the optimiser loves the cheap
  back row. Worth a look only if there's a simple reason, F1 is never going to be 90%
  predictable so no chasing.
- **Chip gains are inflated** by the pool vs builder constructor gap, bigger now the
  real bonus is on. `FIX_CONSTRUCTOR_QUIRKS` is ready, it just didn't win on points.
- **Copy the crowd** fills in on the scorecard from Mexico, re-run it after a few races.
- **The two step simulator.** Sample thousands of weekends (quali = pace + measured
  noise, race pulled back towards pace, plus retirements), score each, report a RANGE
  not one number. Has to beat the FP3 order baseline before it touches picks.
- **DNF calibration.** The model under-predicts retirements (50.8 expected vs 57 real),
  2026 retires more than the weighting has caught up with.
- **Per team budgets in the Team Optimizer.** I play with about $107.5M, not $100M.
  Needs the driver pool stored in snapshots. Measure first whether a bigger budget
  really changes the picks. Probably folds into the planner.
- **Disrupted practice guard.** A red flagged FP3 ranks people on 1 or 2 laps. FP3 alone
  still beats FP2 + FP3 on normal weekends, so this wants a narrow per driver guard for
  thin laps, not a different default.
- **Australian GP missing from `/races`** (round 1 has no previous form). Not decided.
- **Small stuff:** `Procfile` is dead weight (Render uses the Dockerfile),
  `allow_origin_regex` for Vercel previews, sprint weekend chip thresholds.

## Banked ideas

- **Price momentum:** predict which prices go up or down from `price_history.json`, to
  bank team value and avoid transfer penalties.
- **Betting odds** as an extra signal, if a free source exists before the deadline.
- **Session health:** spot car problems from FP3 lap counts vs the teammate.
- **Weather as a feature:** wet races scramble everything, the widget already has the
  forecast (Open-Meteo).
- **Per track trust weighting:** how much to trust practice pace per track type.
- **Strategy modes:** a "max points" vs safer toggle.
- **AI agents:** discussed and deliberately kept out of the core, which is plain
  numbers. Narrow fits only, like turning session reports or Reddit text into
  structured signals.

## Closed, don't rebuild

- Charging retirement risk against the score: lost 27 to 31 pts/race at every weight.
- Expected sprint points in forecasts: no effect alone, worse combined.
- Trusting the ML blend over the practice order: measured worse every time.
- Forecasting the real quali rule (P11 to P20 = 0): -12.2 pts/race, worse on 9 of 16.
- OpenF1 as the points or pit stop source: pit times for only 6 races, overtakes that
  count pit stops. The official F1 Fantasy feed has the real points for free.
- Discounting the overtake bonus: no consistent gain.
- FP2 + FP3 combined on normal weekends: worse than FP3 alone.
- A background scheduler inside the app to fetch practice: replaced by the snapshot
  lock and the GitHub Action.

All the numbers: [Decisions and evidence](Decisions%20and%20evidence.md).

## Done

- 2026-10-28: project 2. The points referee (official points for every round), ownership
  saved at every lock, the Monday job saving official points, the season scorecard,
  the replay leak fixed, the real constructor bonus and the P22 clip fix switched on,
  round 14 prices filled in.
- 2026-10: the cleanup started (tests frozen, one scoring path, leftovers, dashes,
  smaller files, these notes). Practice from OpenF1 after the login wall. Weekend
  self lock and the GitHub Action, after Bahrain and Singapore got lost. Price feed
  duplicate driver fix.
- 2026-09: weekend snapshots replaced the old lock file. DNF risk on every card.
  Sprint weekends lock on sprint quali.
- Earlier: real F1 Fantasy scoring, circuit profiles, the 3 team generator, WinRate /
  PodiumRate / TeamAvgPosition features, constructor scoring as a sum of both cars,
  2026 weighted 5x, the 2x pick limited to Q3 drivers, the Monday data job, mobile
  layout.

Related: [Decisions and evidence](Decisions%20and%20evidence.md), [Future plans](Future%20plans.md), [README](README.md)
