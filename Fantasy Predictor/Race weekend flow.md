---
title: Race weekend flow
date: 2026-10-25
tags: [pitwall, weekend, snapshots]
---

# Race weekend flow

What happens across a race weekend, start to finish. Most things that have ever gone
wrong on the site went wrong somewhere in this flow, so it's worth knowing well.

## The one rule behind everything

You pick your fantasy team before qualifying (normal weekend) or before the sprint
race (sprint weekend). Nobody knows the grid yet. So PitWall uses the last practice
session that runs before the deadline as its best guess of the order:

| Weekend | Session we lock on | Why |
|---|---|---|
| Normal | FP3 | last thing before quali. Hungary R11 proved it, see [Decisions and evidence](Decisions%20and%20evidence.md) |
| Sprint | SQ (sprint qualifying) | the deadline is the sprint race, so sprint quali has already run. Worth about +30 pts a race over FP1 |

`final_practice_session()` in `src/weekend.py` picks which one.

## Step by step

1. **More than 5 days out.** `/weekend-team` says the next race is X days away and
   the site keeps showing the last snapshot as the HELD team.
2. **Practice starts (FP1, FP2).** Once a session is over (plus a 30 minute buffer so
   all the laps are in), `/weekend-team` builds a live PROVISIONAL team from the best
   session so far. It's worked out fresh on every request and can still change.
   Practice laps come from OpenF1 first, FastF1 second, see [Model](Model.md).
3. **The lock session finishes (FP3 or SQ).** Two things race to lock it, whichever
   gets there first wins:
   - **The GitHub Action** (`.github/workflows/lock-snapshot.yml`) calls
     `POST /snapshot/auto` every 30 minutes on Fridays and Saturdays, plus Sunday
     morning UTC. That checks the session is finished AND OpenF1 has it, then builds
     the snapshot in the background and commits it to GitHub.
   - **The self lock.** If someone opens the site and the provisional was built from
     the lock session, the page view kicks off the same build (`should_self_lock` in
     `src/api/weekend_lock.py`).
4. **Locked.** The snapshot is saved in `data/snapshots/` and committed to GitHub
   (Render has no disk, so that's the only way it survives a restart). The site says
   LOCKED and that weekend never changes again. See [Snapshots](Snapshots.md).
5. **The race starts.** "The next race" moves on to the following weekend, but
   `/last-team` and `/weekend-finishes` keep showing the newest snapshot, so the team
   doesn't disappear mid race. This is exactly what broke at Bahrain and Singapore
   before the self lock existed: nothing had saved a snapshot, so the site fell back
   to an older race.
6. **Monday 06:00 UTC.** `.github/workflows/update-race-data.yml` runs
   `scripts/update_data.py`: adds the new race and sprint results to
   `data/processed/`, refreshes prices for the next round, then
   `scripts/track_record.py` rebuilds `data/track_record_2026.json` for the track
   record page, `scripts/chip_history.py` rebuilds `data/chip_history.json` for the
   CHIPS tab, and it all gets committed. Render redeploys
   and retrains on the new data. Predicted finishes now show the real results next
   to them, with how many places off we were.
7. **Once results are in the data**, nothing will ever build a snapshot for that race
   again (`results_already_in_data`), because the model would have seen the answers.
   If a weekend got missed, it has to be recovered BEFORE Monday, see [How-tos](How-tos.md).

## The times worth remembering

All UTC. My clock is UTC+3.
- Lock session ends, then 30 minutes buffer, then the next Action run picks it up.
  US GP 2026: FP3 ended 18:30, locked 19:18.
- Monday job: 06:00 UTC (09:00 for me).

Related: [Snapshots](Snapshots.md), [Model](Model.md), [Gotchas](Gotchas.md), [How-tos](How-tos.md)
