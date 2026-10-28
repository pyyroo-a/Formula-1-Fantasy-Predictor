---
title: Code tour
date: 2026-10-28
tags: [pitwall, code, index]
aliases: [Code tour, What each file does]
---

# Code tour

A plain walk through the files we added in projects 1 to 6 (October 2026), so I can
find my way around without reading all the code. One line per file: what it does and
why it's there. The older core (the model, the scoring, the snapshots) is in the other
notes, links at the bottom.

## The big picture first

Every race weekend goes like this, and each step has a file:

1. **Practice happens.** `src/openf1.py` and `src/fetch_practice.py` grab the laps and
   turn them into a practice order (who was fastest).
2. **PitWall builds 3 teams** from that order. `src/fantasy.py` turns finishing places
   into fantasy points and picks the best teams under $100M.
3. **Each pick gets a confidence level** (project 4), `src/confidence.py`.
4. **The weekend gets locked** after FP3 (or sprint quali) and saved in
   `data/snapshots/`, by `src/weekend.py` and the GitHub Action.
5. **The race happens. Monday morning** the Action saves the real results and the
   game's official points, then rebuilds the track record and the chip history.
6. **The site** (`frontend/`) shows all of it, reading from the backend (`src/api/`).

## Project 1: cleanup and these notes

| File | What it does |
|---|---|
| `tests/test_no_dashes.py` | fails if an em or en dash sneaks into anything |
| `src/api/` (`weekend_common.py`, `weekend_lock.py`, `finishes.py` and friends) | the backend split into one file per group of pages, instead of one giant `main.py` |
| `frontend/src/components/racedata/`, `myteam/TeamOptimizerTab.jsx`, `ManualTeamParts.jsx` | the big React files split into smaller ones |
| `frontend/src/hooks/useRaceData.js`, `styles.js`, `teamCache.js` | shared bits the pages use: fetching data, common styles, remembering the last team |
| `Fantasy Predictor/` | this vault |

## Project 2: grading with the game's real points

| File | What it does |
|---|---|
| `src/official_points.py` | reads the F1 Fantasy feed: every driver's and constructor's real points, plus ownership |
| `data/official_points_2026.json` | those real points for every 2026 round, saved by the Monday job |
| `scripts/backfill_official_points.py` | filled in the rounds from before we started saving them |
| `src/simple_picks.py` | the "anyone could do this" teams: copy the FP3 order, most expensive, copy the crowd, best in hindsight |
| `scripts/scorecard.py` | replays the season and grades everything with real points, writes [Scorecard](Scorecard.md) |
| `src/constructor_extras.py` | expected pit stop points for constructors (measured, switched off) |

## Project 3: the transfer planner

| File | What it does |
|---|---|
| `src/planner.py` | the ladder: keep your team, or the best team with 1, 2, 3 transfers, plus the plain facts |
| `src/api/planner.py` | `POST /transfer-ladder`, what the PLANNER page asks |
| `src/planner_replay.py`, `scripts/planner_grade.py` | proved on real points that using free transfers beats keeping your team |
| `frontend/src/components/myteam/TransferPlanner.jsx` | the PLANNER page under My Team |
| `frontend/src/plannerTeams.js` | remembers your 3 teams in the browser |

## Project 4: confidence and reasons

| File | What it does |
|---|---|
| `src/confidence.py` | gives every driver high / medium / low confidence plus a sentence why (teammate, moving around, tight pack) |
| `scripts/confidence_grade.py` | proved it on past weekends: high confidence picks land closer than low ones |
| `archive/results/confidence_rows_2026.csv` | the rows that proof came from |
| `frontend/src/confidence.js` | the CONSIDER rule (a Safe driver with low confidence) and the legend line |
| changes in `src/weekend.py`, `src/api/race_weekend.py`, `src/planner.py` | stick the confidence on the picks after they're built, so it never changes a pick |

## Project 5: the track record page

| File | What it does |
|---|---|
| `src/track_record.py` | grades the locked team and the simple picks, shared with the scorecard so they always agree |
| `scripts/track_record.py` | builds `data/track_record_2026.json`, the Monday job runs it |
| `src/api/track_record.py` | `GET /track-record`, just hands the file over |
| `frontend/src/components/TrackRecord.jsx` | INSIGHTS > TRACK RECORD |

## Project 6: chip history

| File | What it does |
|---|---|
| `src/chip_history.py` | what 3x, Limitless and No Negative were really worth at each track, the best tracks per chip, and the "does last season predict this one" check |
| `scripts/chip_history.py` | builds `data/chip_history.json` from every season's official points, the Monday job runs it |
| `src/api/chip_history.py` | `GET /chip-history`, just hands the file over |
| `frontend/src/components/ChipHistory.jsx` | INSIGHTS > CHIPS |

## A pattern worth knowing

Projects 5 and 6 work the same way: **a script does the slow maths once, saves a JSON
file, the Monday job keeps it fresh, and the page just reads the file.** That's because
the free Render server is too slow to try every possible team each time someone opens a
page. If I ever add another page like that, copy this pattern.

And every project followed the same rules: **test first, measure before switching
anything on, and if it measures worse it stays off** with the number next to the switch.

## Where to start if I want to...

- **understand how a pick happens:** `src/fantasy.py`, then [Fantasy scoring](Fantasy%20scoring.md)
- **see why something is switched off:** [Decisions and evidence](Decisions%20and%20evidence.md)
- **follow a weekend from FP1 to Monday:** [Race weekend flow](Race%20weekend%20flow.md)
- **find which file serves a page:** [API](API.md) and [Frontend](Frontend.md)

Related: [Start here](README.md), [Roadmap](Roadmap.md), [How-tos](How-tos.md)
