---
title: API
date: 2026-10-25
tags: [pitwall, api, backend]
---

# API

The FastAPI backend. `main.py` only does startup (load results, train, load prices
and the schedule), CORS and plugging the routers in. Every group of endpoints lives in
its own file under `src/api/`.

## Endpoints

| Method | Path | File | What it does |
|---|---|---|---|
| GET | `/races` | `races.py` | finished races this season (the race dropdowns) |
| GET | `/upcoming-races` | `races.py` | races still to come, with a sprint flag |
| GET | `/next-race` | `races.py` | next race name and date (the countdown) |
| POST | `/race-sessions` | `races.py` | FP1/FP2/FP3 times and whether each is available |
| POST | `/race-results` | `races.py` | finishing order of a finished race |
| POST | `/qualifying-results` | `races.py` | Q1/Q2/Q3 times |
| POST | `/practice-results` | `races.py` | practice pace for a session |
| GET | `/prices` | `prices.py` | current prices |
| GET | `/price-changes` | `prices.py` | prices vs last round |
| POST | `/predict-budget` | `teams.py` | 3 teams for any race (the Team Optimizer page) |
| POST | `/upcoming-race-pool` | `teams.py` | every driver and constructor with points (Manual Team page) |
| POST | `/chip-advisor` | `teams.py` | chip verdicts for your own team, see [Chips](Chips.md) |
| POST | `/predict`, `/predict-upcoming`, `/race-pool` | `teams.py` | older endpoints the site doesn't call any more, kept for now |
| GET | `/weekend-team` | `race_weekend.py` | this weekend's locked snapshot, or a provisional before the lock |
| GET | `/last-team` | `race_weekend.py` | the newest snapshot, held between races |
| GET | `/weekend-finishes` | `finishes.py` | predicted finishing order, plus real results once they're in |
| POST | `/snapshot/auto` | `weekend_lock.py` | locks the weekend, needs `X-Snapshot-Secret`, see [Snapshots](Snapshots.md) |
| GET | `/backtest` | `dev.py` | replays the season to grade the model, only with `BACKTEST_ENABLED=true` (local only, it's slow) |

The weekend files share `weekend_common.py` (schedule, next race, best practice order
right now). `state.py` holds what startup loaded, and `clock.py` has `clock.now()` so
the tests can pretend it's any time they like.

## Settings (environment variables)

| Name | Where | What |
|---|---|---|
| `CORS_ORIGINS` | Render | the Vercel URL. Vercel preview URLs aren't allowed, use the real domain |
| `SNAPSHOT_SECRET` | Render + GitHub Actions secret | guards `/snapshot/auto` |
| `GITHUB_TOKEN` | Render | lets the backend commit snapshots (`GITHUB_REPO`, `GITHUB_BRANCH` if those ever change) |
| `LOCK_ON_VIEW` | Render, optional | `0` turns the self lock off |
| `USE_OPENF1` | optional | `0` goes back to FastF1 only for practice |
| `BACKTEST_ENABLED` | local only | turns on `/backtest` |
| `SNAPSHOT_DIR`, `PROCESSED_DIR` | tests | point at test copies of the snapshots and race results |
| `VITE_API_URL` | Vercel | where the frontend finds the backend |

Related: [Snapshots](Snapshots.md), [Frontend](Frontend.md), [How-tos](How-tos.md)
