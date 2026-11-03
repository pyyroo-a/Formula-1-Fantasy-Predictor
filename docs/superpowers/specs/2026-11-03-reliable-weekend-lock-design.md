# Reliable weekend lock (design)

Date: 2026-11-03. Has to be pushed before Brazil FP1, Friday 6 Nov 15:30 UTC (18:30 for me),
because there are no backend pushes from FP1 until the race is over.

## Why

Mexico weekend (round 19) nearly didn't lock. Basically three things went wrong at once:

- OpenF1 had no FP3 laps (`/laps` for session 11399 said "No results found") for hours
  after FP3. They turned up sometime after quali. Its classification (`/session_result`)
  had every driver's best lap the whole time, we just never looked there.
- OpenF1 blocks all free access, old sessions included, from about 30 minutes before a
  session until it ends ("Live F1 session in progress"). That leaves a short window
  between FP3 and quali.
- The lock Action is set to run every 30 minutes on Fridays and Saturdays, but GitHub
  actually ran it every 4 to 6 hours (31 Oct: 01:26, 07:25, 13:48, 18:17, 21:47 UTC).

On top of that, the Garage (`/transfer-ladder`, `/chip-advisor`) works its numbers out
live from practice every time, so it broke during the quali block even after the
weekend was locked. My push restarted Render too, which wiped the in-memory copy.

We hand locked Mexico from the classification with a one-off script (`source: manual`
in `data/snapshots/2026_R19_mexico_city_grand_prix.json`). When the laps came in later,
every best lap matched, but the classification had car 50, which wasn't in the session's
driver list at the time. I guessed OCO, it was HIR (a Haas stand-in), so the lock gave OCO
HIR's lap. A backup has to name drivers properly instead of guessing.

Brazil (round 20, normal weekend) is tighter than Mexico: FP3 14:30 to 15:30 UTC, laps
ready about 16:00 with our 30 minute buffer, the quali block from about 17:30, quali 18:00.
So about 90 minutes to lock, and with the Action as it is now it probably wouldn't.

## Goals

1. Brazil and every weekend after it locks by itself before quali, as long as OpenF1 has
   FP3 (or SQ) in either its laps or its classification.
2. Once a weekend is locked, the main page, the Garage ladder and the chips all read the
   lock and never need OpenF1 again for that weekend.
3. If it ever does go wrong, I can lock by hand in a couple of minutes with a proper tool.
4. The site loads straight away instead of waiting ~50s for Render to wake up.

## Non goals (this week)

- Scraping formula1.com or my F1 account. F1's legal notices say the site is for
  "personal, non-commercial use only", no extracting or distributing, and they name
  live timing and race data as protected. The F1 App terms ban using it in an automated
  manner. So both are out.
- Switching the model to the classification as its main source. The 2026 comparison
  (below) says the classification drops deleted laps, which might even be better, but
  that's a measuring job for after Brazil, not a guess.
- Saving every session's raw data into our own files (later).
- The Practice page in Race data showing the classification when laps are missing (later).
- The ladder giving BOT, ALB and STR the same 183.5 for my Team 1, and the live ladder
  saying 187.0 where the Mexico hand run said 182.0 (later, its own investigation).

## Anti goals (would make this a failure even if it runs)

- A lock built from FP2 on a normal weekend. We wait for FP3, see below.
- A driver getting someone else's lap time because a car number got guessed.
- A lock that changes after it's made. Locked weekends never change.
- Anything that costs money or makes the free tiers fall over.

## What we know (measured 2026-11-03)

OpenF1 classification vs laps over all 57 practice and sprint quali sessions of 2026
(script was one-off, read only):

- Same order on 41 of 57. Six of those had no data on either side.
- Most differences are deleted laps. `/laps` still has laps that got taken away for
  track limits, the classification only counts the ones that stood (Austin FP3: LEC
  1:34.810 in the laps, 1:35.127 classified).
- Each side has been missing on its own: laps missing for Spa FP2 (and late for Mexico
  FP3), classification missing for Madrid FP1.
- `/drivers` is sometimes empty for a session (Monaco FP2, Singapore SQ), and can be
  stale (Mexico FP3 during the weekend).
- For sprint quali, `duration` in the classification is a list (one per part) and can
  have nulls. For practice it's one number or null.
- A classification row looks like this (Mexico FP3): `position`, `driver_number`,
  `number_of_laps`, `dnf`, `dns`, `dsq`, `duration`, `gap_to_leader`, `meeting_key`,
  `session_key`. A driver with no time has `duration` null.
- "Nothing there" comes back as a dict, not an empty list:
  `{"detail": "No results found."}`. The live block is also a dict (`{"detail": "Live
  F1 session in progress..."}`). Right now `_get` turns any dict into
  `OpenF1Unavailable`, which skips to FastF1 (401s), so on Mexico day missing laps never
  looked like "no laps" and `/snapshot/auto` would have answered 502. The backup has to
  read "No results found" as "no laps" and the live block as "try again later".
- Tests use real recorded OpenF1 answers (free, read only calls are fine while building):
  Mexico FP3 (session 11399) laps and classification, one sprint quali, Madrid FP1
  (laps, no classification), Monaco FP2 (empty `/drivers`).

GitHub: a job can run up to 6 hours, and Actions are free on a public repo. Render's
free tier: sleeps after 15 minutes with no inbound traffic, 750 free hours per workspace a
month (always on is 720 to 744), and if they run out ALL free services get suspended
until the 1st. PitWall is my only Render service, so always on fits. Render can still
restart a free service whenever it likes.

## The how (decided)

### 1. A lock Action that stays awake

`.github/workflows/lock-snapshot.yml` changes from "poke once" to "keep poking":

- Several starts spread over Friday, Saturday and Sunday in UTC (so Las Vegas, whose
  Saturday sessions are Friday night in UTC terms, is covered too). A late start still
  lands because each run lasts hours.
- Each run calls `POST /snapshot/auto` every 5 minutes. It stops once the answer is
  `already_locked`, `idle` (no live weekend) or `refused`, or when it's near GitHub's
  6 hour limit. `waiting`, a `locked` that's still building, a 5xx and no answer at all
  (Render waking up or restarting) mean keep going. A 401 stops it, that's a setup
  problem.
- `/snapshot/auto` should answer `waiting` (not 502) during the OpenF1 live block.
- One run at a time (a concurrency group), so starts don't pile up.
- Every answer goes in the run summary like now, so I can see what happened.
- The manual "Run workflow" button stays.

`/snapshot/auto` itself is already safe to call over and over, so it barely changes.

### 2. OpenF1 laps first, then the classification

In `src/openf1.py`, when a finished session (past the buffer) has no timed laps, we
build the same grid from `/session_result` instead: each driver's best classified time
(the smallest non null one for sprint quali), ranked, with gap to pole and teammate,
same shape as `grid_from_openf1`. Drivers with no time drop out, same as the laps route.

Driver names, in this order: the session's own `/drivers`, then `/drivers` for the other
sessions of the same meeting. A car number we still can't name gets left out and logged,
never guessed. This goes for the laps route too (Claude's call): right now an empty
`/drivers` makes `grid_from_openf1` crash with a KeyError, so the lock would 502 all
afternoon. Because `get_practice_grid` also feeds the backtests and the scorecard, re-run
the scorecard after and write the numbers down, even if they don't move.

The lock records where its order came from (`lap_source`: `laps` or `classification`),
so the scorecard and the notes can tell them apart later. If the laps turn up after the
lock, nothing changes.

The confidence checks load FP1 and FP2 through the same route, so they get the backup
for free.

### 3. The lock saves the full forecast

`build_snapshot` also saves the driver and constructor pool (each driver's predicted spot,
points, price, DNF chance, Safe/Risk and confidence), plus the optimal and Limitless
scores the chips compare against. When a weekend has a lock with a pool in it,
`/transfer-ladder` and `/chip-advisor` use that and don't touch practice data. Older
snapshots without a pool keep working the old live way.

`/chip-advisor` should also stop hard coding FP3 and follow the lock session like the
ladder does (it would currently try FP3 on a sprint weekend).

### 4. Wait for FP3, never fall back to FP2

That's mostly how it already works (the self lock and `/snapshot/auto` only lock on the
final session). Writing it down so nobody "fixes" it: on a normal weekend we keep trying
for FP3 right up to quali, and if FP3 only shows up after quali starts we still lock from
FP3, flagged `built_after_quali_start`. My call, because the classification has always
been there before quali in practice, and the formula1.com page usually is too (I can look
at that one myself).

### 5. A proper hand lock tool

We already have one: `scripts/lock_team.py` (it's in How-tos, it saved Bahrain and
Singapore). It runs the normal build, so it gets the classification backup for free once
part 2 is in. Claude's calls: no second script, `lock_team.py` gets a `--dry-run` that
prints the 3 teams, the 2x and the predicted finish without saving, and marks what it saves
`source: manual` with a short note. `--force` stays as it is, it's the human escape hatch
for a wrong lock, nothing automatic ever overwrites one. Mexico's lock stays as it is, the
results are in now so rebuilding it would see the answers.

### 6. Keep Render awake

A tiny `GET /health` on the backend that answers straight away without loading anything,
also answering `HEAD`, because some uptime checkers use HEAD by default. I set up a free
uptime checker (UptimeRobot or cron-job.org, my account, my call) to hit it every 5 to 10
minutes. I'll check the Render hours in the dashboard after the first week.

## Constraints

- Free only. No paid OpenF1 key, no F1TV.
- Backend pushes before Brazil FP1 (Fri 6 Nov 15:30 UTC).
- Tests first, all 216 backend and 48 frontend tests still pass, the no dashes test too,
  lint no worse than the 4 old errors.
- Tests never call OpenF1 for real, they use recorded answers like the existing ones.
- I commit and push, Claude never does.

## Left to the builder

- Exactly how the Action loop is written and its start times, within the rules above.
- The names of new fields and functions.
- How the endpoints spot an old snapshot without a pool.
- Whether `practice_table` (Race data) needs touching to keep working with the new route,
  as long as it doesn't break.

## Notes to update after

README "where things stand", Gotchas (the OpenF1 live block, late laps, stand-ins, GitHub
cron delays), Race weekend flow, Snapshots, API (`/health`), How-tos (hand lock), Roadmap.
