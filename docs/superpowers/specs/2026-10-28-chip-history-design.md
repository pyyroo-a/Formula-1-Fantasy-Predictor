# Chip history by track (design)

Project 6 of 7 on the roadmap. Written 2026-10-28 after brainstorming with Ashen, who
picked mockup A. Aimed at 2027, he has no chips left this season.

## Why

Ashen's chips went in by instinct ("3x on a sprint"), and the results said otherwise:
a 3x sprint weekend barely got near 400, another 3x didn't break 300. He also joined a
mini league after using his chips and saw the top of it was built on well timed 3x and
Limitless weekends. What he can't work out himself before a race: **how much each chip
has really been worth at this track.** Facts to weigh, never "play this now".

He first asked for "which chip was played most at each track". Two problems: the free
F1 Fantasy feed doesn't seem to share chip usage (every guessed stats address was
refused), and what the crowd played isn't what paid off. So: what each chip WOULD have
been worth, from real points.

## The evidence so far (2026, official points, best possible picks)

| | Normal weekends (12) | Sprint weekends (6) |
|---|---:|---:|
| 3x: points of the top scorer (the extra a 3x adds over 2x) | 51.6 | 58.0 |
| Limitless: best no cap team minus best $100M team | 90.8 | 103.8 |

- Sprints add only about 6 to a 3x. The best 3x of the season was Monza, a normal
  weekend (93), and that was a one-off: Antonelli from P19 to the win (Ashen's call,
  and it's why one season per track isn't enough).
- Limitless swings by track: Miami +167, Madrid +127, Suzuka +119, Monaco only +15.
- China: best $100M team 461, a perfect Limitless team about 549.

## What it is (mockup A)

A CHIPS tab under INSIGHTS (next to predicted finishes and track record):

- **Table, one row per track:** what 3x, Limitless and No Negative have been worth
  there: the typical value (the median, with 2 seasons that's the average) and both
  values, the seasons it's based on, and a sprint marker.
- **Each value names who and how**, e.g. "93, ANT P19 to P1, 2026", so a one-off is
  visible instead of hidden in a number.
- **Best tracks per chip:** a top 3 (and the worst) for 3x, Limitless and No Negative,
  ranked by the median.
- **Wildcard, Final Fix, Autopilot:** one plain line each on how it works and when it
  helps. They depend on your team, not the track, so no track stats. The live chip
  advisor on the main page stays exactly as it is.
- A short note: best possible picks, official points in 2026, our own scoring before
  that, facts not advice.

## The three numbers (exact)

Per race weekend:

- **3x** = the highest scoring driver's points that weekend (race + quali + sprint).
- **No Negative** = what an average team would have got back: 7 x the mean, over every
  driver and constructor, of max(0, minus their points). Builder may also use the
  feed's per driver `NoNegativePoints` field for 2026 if it matches the game better,
  say which in the notes.
- **Limitless** = the best team with no budget cap (top 5 drivers, top 2
  constructors, 2x on the top driver) minus the best $100M team
  (`simple_picks.hindsight_best_team`). Needs that round's prices, so **2026 only**
  for now (prices are in `data/official_points_2026.json`), it grows every season.

**Seasons: 2025 and 2026 only** (Ashen's call, same as the model: older seasons
describe old cars, a 2023/2024 heavy model once put his 2x on Perez for -48). Points:
2026 from the official feed (`data/official_points_2026.json`). 2025 from our own
scoring of `data/processed/race_results_2025.csv` (`src/fantasy.py`),
which is close to the game but not exact (no pit stop or overtake details), the page
says so. 2025 sprint results aren't in `data/processed/`; the builder gets them from the
FastF1 cache or marks those weekends' 3x as missing the sprint, never fakes it.

Tracks are matched by circuit, not race name (Madrid is new in 2026, the Bahrain GP was
run in Kuala Lumpur, names move about). `src/circuits.py` is keyed by race name, so it
can't tell the 2026 "Spanish Grand Prix" (Madrid) from the old one (Barcelona); use the
location from FastF1's event schedule (it's in the cache) as the key, with a display
name. Past seasons' quali points use the results file's `GridPosition` (the start grid,
penalties included), close enough and said so. A track with one season says "1 season".

## Proving it (before it shows on the site)

The ranking only helps if a track's past says something about its future. A script
checks it the honest way: rank tracks by their 2025 value for 3x and No Negative,
compare with how they really ranked in 2026 (tracks raced in both), report the rank correlation and
how many of the predicted top 5 were really top 5. Limitless can't be checked yet (one
season).

- If a chip's history predicts better than chance, the page shows its ranking as is.
- If not, the table still shows the facts, but that chip's "best tracks" list says
  plainly that track history hasn't predicted much so far.
- The numbers go in Decisions and evidence. Re-run each season.

## Goals

1. The table, the best tracks lists and the three plain lines, as in mockup A.
2. Precomputed like the track record: a script writes a JSON, the Monday Action
   rebuilds it, an endpoint serves it, so it loads instantly on Render.
3. The proving check, run and written down before the tab ships.
4. Notes updated (Chips, Roadmap, Decisions and evidence, README, API, Frontend).

## Non-goals and anti-goals

- No "save it for later" engine or chip schedule that predicts future weekends.
- No crowd chip usage (not in the free feed). Bank it if a free source turns up.
- No change to the live chip advisor or to any pick.
- No polished look, that's the redesign.
- Anti-goal: a number that hides a one-off, a ranking presented as more certain than the
  proving check says, or anything that reads like an order.

## Constraints

Ashen's working rules: he commits and pushes, tests pass before a push
(`./venv/Scripts/python.exe -m pytest -q`, 193 now), no em or en dashes, casual voice,
data true, free only, no backend pushes from FP1 Friday until the race is over, keep it
simple, keep usage down.

## Calls I made (Ashen, check these)

- 2025 and 2026 only (Ashen). Median for "typical" so it keeps working as seasons
  are added; with 2 seasons a one-off still shows because every value names who scored it.
- No Negative as "what an average team would have got back", one number per weekend.
- Limitless 2026 only until there are more seasons of prices.
- Wildcard, Final Fix and Autopilot get explanations, not stats.
- The page is a tab under INSIGHTS, the main page stays as it is (option A).
