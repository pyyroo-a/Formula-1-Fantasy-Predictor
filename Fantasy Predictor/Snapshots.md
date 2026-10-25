---
title: Snapshots
date: 2026-10-25
tags: [pitwall, snapshots, automation]
---

# Snapshots

The one saved copy of what PitWall predicted for a race weekend.

## Why they exist

The site used to work the team out again every time someone opened it, so the answer
depended on the time, on whether Render had just restarted, and on whether FastF1
downloaded properly on that request. At Madring that meant the team changed during
the race and the predicted finishes vanished.

Now each weekend gets worked out ONCE, after the lock session, and saved as a file in
`data/snapshots/`, e.g. `2026_R18_united_states_grand_prix.json`. The site only reads
those files. They get committed to GitHub because Render's free tier has no disk, so
the snapshots have to ship with the code to survive a restart. Old ones are kept, so
predicted vs actual works for every race.

A snapshot holds: year, race name, round, `session_used` (FP3 or SQ), `locked_at`,
`source` (`auto` or `manual`), `built_after_quali_start`, the 3 `teams` (with their 2x
pick and chip verdicts) and the predicted `finishes`.

Code: `src/snapshots.py` (reading, saving, committing to GitHub), `build_snapshot` in
`src/weekend.py` (what goes in one), `src/api/weekend_lock.py` (the automatic lock).
One build function is shared by the automatic lock, the self lock and the laptop
script, so they can never build different things.

## How a weekend gets locked

Two independent ways, see [Race weekend flow](Race%20weekend%20flow.md) for the timeline:

1. **`POST /snapshot/auto`, called by the GitHub Action** (`.github/workflows/lock-snapshot.yml`)
   every 30 minutes on Fridays and Saturdays plus Sunday morning UTC. `--max-time 180`
   on purpose: Render takes about 53 seconds to wake up, and cron-job.org (which we used
   before) gave up after 30, which is how Bahrain and Singapore got lost.
2. **The self lock.** When `/weekend-team` or `/weekend-finishes` builds a provisional
   from the lock session, it starts the same build in the background. Only the FINAL
   session counts, never if a snapshot exists, never once results are in the data.
   `LOCK_ON_VIEW=0` on Render switches it off without a redeploy.

What `/snapshot/auto` answers:

| Answer | Means |
|---|---|
| `idle` | no race weekend on (more than 5 days out, or season over) |
| `waiting` | the lock session isn't finished, or OpenF1 doesn't have it yet. Normal, just wait |
| `started` / `building` | the build is running in the background |
| `already_locked` | done. It still re-checks the snapshot made it to GitHub |
| `refused` | the race results are already in our data, a snapshot now would have seen the answers |
| `dry_run` | `?dry_run=true`: builds and shows the teams, saves and commits nothing |
| 401 / 503 | wrong secret / `SNAPSHOT_SECRET` not set on Render |
| 502 | couldn't check OpenF1. A real problem, not a wait (see the Madring lesson in [Gotchas](Gotchas.md)) |

Most answers include `last_result`, the last build attempt and its error if it failed.

## One time setup (already done, here in case it needs redoing)

1. **The secret.** Make one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
   Add it on Render (backend service > Environment) as `SNAPSHOT_SECRET`, AND on GitHub
   (repo > Settings > Secrets and variables > Actions > New repository secret) as
   `SNAPSHOT_SECRET`. Same value in both. Never paste it into a chat.
2. **A GitHub token so Render can commit snapshots.** GitHub > Settings > Developer
   settings > Fine grained tokens: only this repo, Repository permissions > Contents >
   Read and write, nothing else. Add it on Render as `GITHUB_TOKEN`. It expires, so
   keep a calendar reminder.
3. **Check it:** run the Action by hand (Actions > Lock Weekend Snapshot > Run workflow),
   or `curl -X POST "https://formula-1-fantasy-predictor.onrender.com/snapshot/auto?dry_run=true" -H "X-Snapshot-Secret: ..."`.

cron-job.org still has an old job pointing at this. It keeps failing and is safe to
delete now the Action has locked a real weekend (US GP 2026).

## If a weekend didn't lock

Check `/weekend-team` on the backend. `"locked": true` means fine. If not, look at the
Action's runs on GitHub, or the dry run's `last_result`. Then lock it from the laptop,
see [How-tos](How-tos.md). It has to happen before the Monday job adds the results.

Related: [Race weekend flow](Race%20weekend%20flow.md), [API](API.md), [How-tos](How-tos.md), [Gotchas](Gotchas.md)
