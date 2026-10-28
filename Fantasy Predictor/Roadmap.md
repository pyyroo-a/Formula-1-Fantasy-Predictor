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
3. **"My team" planner.** Done 2026-10-28, see [Planner](Planner.md). My 3 teams saved in
   the browser, and a transfer ladder for any of them (keep, then each free transfer)
   with expected points, the practice reason for every swap and facts instead of
   orders. Free transfers its way beat keeping the team by 25.2 pts/race on real points.
   The paid (-10) row lost to free only, so it's switched off. Chips plug in later.
4. **Better practice data, plus confidence and reasons.** Done 2026-10-28. Started from
   Max topping sector 2 in Austin FP3 while the model saw P4. Measured first: the ideal
   lap and FP2 long runs both lost to the plain FP3 order on fantasy points, so they're
   out. Every pick now gets a confidence level (high, medium, low) and a plain reason,
   from 3 checks (teammate, moving around, tight pack), and a low confidence SAFE driver
   shows CONSIDER. High beat low on 11 of 12 weekends. Never changes a pick. Off on
   sprint weekends, it didn't hold up there. See [Model](Model.md).
5. **Track record page.** Done 2026-10-28. INSIGHTS > TRACK RECORD shows what the real
   locked team 1 scored every locked weekend vs copy the FP3 order, most expensive, copy
   the crowd and the best possible, in official points. Same grading code as the
   scorecard (`src/track_record.py`), rebuilt every Monday by the Action. Honest
   start: R13 to R18 PitWall 175.2 vs 187.0 for copying FP3 (beat it 3 of 6), all
   locked before the 28 Oct fixes, Mexico is the first real test.
6. **Chips.** Done 2026-10-28. INSIGHTS > CHIPS: what 3x, Limitless and No Negative were
   really worth at every track, best tracks per chip, plain lines for the other three.
   Official points only (2026, growing every season), our 2025 maths was on a smaller
   scale. No "save it for later" engine, facts only. See [Chips](Chips.md).
7. **Reddit discussion feed (parked).** What people are picking and their game plans.
   Reddit's free API is limited and AI summaries would cost money, so later. Ownership %
   IS in the F1 Fantasy feed, and every snapshot saves it at the lock since project 2.

After all that: **one UI redesign** of the whole site using the frontend design plugin,
once projects 2 to 5 have added what they add. No piecemeal UI changes before then.

## Open tasks

- **Re-run `scripts/confidence_grade.py` after a few races from Mexico.** The cutoffs
  were picked on R1 to R18, the new races are the honest test. Same for sprint weekends
  if we ever want them on.
- **A simple code tour note in this vault** (I asked for it 2026-10-28): every file
  added in projects 1 to 6 and what it does, in plain words, not all the code.
- **After the first 2027 races:** check the CHIPS tab's "does last season predict this
  one" line has filled in, and write the numbers in Decisions and evidence.
- **Re-test the paid transfer row** after a few more races (`scripts/planner_grade.py`).
  It lost by 4 pts/race over 3 hits, a small sample.

- **Delete the cron-job.org job.** The Action locked the US GP by itself, so it's no
  longer needed.
- **Re-measure the old switches** (`SHRINK_TO_GRID`, `DNF_WEIGHT`,
  `PREDICT_SPRINT_POINTS`) on the scorecard. Their numbers came from the old backtest
  that could see real retirements, see [Decisions and evidence](Decisions%20and%20evidence.md).
- **Why the real quali rule loses.** With P11 to P20 at 0 the optimiser loves the cheap
  back row. Worth a look only if there's a simple reason, F1 is never going to be 90%
  predictable so no chasing.
- **The Avoid quirk** still adds a constructor with an Avoid driver up differently in the
  builders than in the pool. `FIX_CONSTRUCTOR_QUIRKS` is ready, it just didn't win on points.
- **Re-run the scorecard after a few races from Mexico.** The switches were picked on
  R3 to R18, so the new races are the honest test. Copy the crowd fills in from then too.
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
- **Let confidence steer something,** like keeping the 2x off a low confidence driver.
  Its own switch, off until it wins on the scorecard in official points.
- **A 2x card on the main page.** The main page never shows the 2x pick, only the Team
  Optimizer does. For the redesign.
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
- The ideal lap (best sectors) instead of fastest lap: worse on fantasy points, 9 of 12.
- FP2 long run pace instead of, or mixed with, the FP3 order: worse on 9 of 11.
- A background scheduler inside the app to fetch practice: replaced by the snapshot
  lock and the GitHub Action.

All the numbers: [Decisions and evidence](Decisions%20and%20evidence.md).

## Done

- 2026-10-28: project 6. Chip history by track (`src/chip_history.py`,
  `scripts/chip_history.py`, `/chip-history`, the CHIPS tab), in the Monday job.
- 2026-10-28: project 5. The track record page, `scripts/track_record.py` in the Monday
  job, `/track-record`, the scorecard's grading shared in `src/track_record.py`.
- 2026-10-28: project 4. Ideal lap and long runs measured and dropped, confidence levels
  with reasons on the main page teams and the planner's swaps, CONSIDER for a shaky
  Safe driver, `scripts/confidence_grade.py`.
- 2026-10-28: project 3. The transfer planner: the ladder maths, the real points grade,
  `/transfer-ladder`, and the PLANNER page with 3 saved teams.
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
