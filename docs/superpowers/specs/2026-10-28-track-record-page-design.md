# Track record page (design)

Project 5 of 7 on the roadmap. Written 2026-10-28. Ashen skipped the questions ("just
go ahead with the design, show me the mockup") and picked mockup A.

## Why

PitWall has to earn trust from results, not from how clever it sounds. The scorecard
(`scripts/scorecard.py`, `Fantasy Predictor/Scorecard.md`) already grades every weekend
with the game's official points, but only in a note in the repo. This puts the part
that matters for trust on the site: what the team PitWall really locked scored, against
simple picks anyone could make.

It has to be honest. Right now it shows PitWall's real locked team 1 **behind** copying
the FP3 order: 175.2 vs 187.0 pts/race over R13 to R18, beating it 3 of 6. Those locks
were made before the project 2 fixes went live on 2026-10-28 (the replay with the fixes
scores 203.9). Mexico is the first lock with them. The page shows the real number and
says that, nothing gets dressed up.

## What it is (mockup A)

A new TRACK RECORD tab under INSIGHTS (next to the predicted finishes), nothing on the
main page:

- **Tiles:** PitWall (team 1) pts per race and how many races; copy the FP3 order, with
  "PitWall beat it X of Y"; most expensive, same; best possible in hindsight (the ceiling).
  Crowd gets a tile once it has races.
- **Table, one row per locked weekend:** race, PitWall, FP3 order, most expensive, crowd,
  best possible. A simple pick's cell is green when PitWall beat it that weekend, amber
  when it lost. "-" where there's no number.
- **Notes:** what each column is, all at $100M with a 2x pick, graded with the game's
  own points, crowd starts at Mexico, the 28 Oct fixes went live after R18, updated
  every Monday after the race.

## Goals

1. The numbers are exactly the scorecard's for the same columns (same grading code).
2. Only weekends PitWall really locked (a snapshot exists) that have official points.
3. Updated automatically every Monday, no manual step.
4. The page loads instantly on the free Render instance.
5. Notes updated (Scorecard, Roadmap, README, API, Frontend).

## Non-goals and anti-goals

- No replay column. The page is about what PitWall really locked; the replay stays in
  the scorecard note.
- Teams 2 and 3 aren't graded on the page (team 1 is what the site leads with).
- No polished look, that's the redesign.
- Anti-goal: any number that differs from the official points, any cherry picking of
  races, or wording that spins a loss.

## How it gets made (my calls)

- **Precomputed, not live.** Most expensive and hindsight check every possible team
  (brute force), too slow per visit on Render. A script writes
  `data/track_record_2026.json`, the endpoint just reads it.
- **Shared grading.** The simple pick columns move out of `grade_round` in
  `scripts/scorecard.py` into a small module, `src/track_record.py`, that both use. The
  scorecard keeps its replay column on top. `deadline_grid` moves from `src/backtest.py`
  to `src/fetch_practice.py` (backtest re-exports it) so the script doesn't pull in the
  model's packages.
- **The Monday Action** (`.github/workflows/update-race-data.yml`) runs
  `python scripts/track_record.py` after `update_data.py` and commits the JSON with the
  rest. It recomputes every locked round each time (about a dozen, fine for an Action).
- **Endpoint** `GET /track-record`, its own file under `src/api/`. Missing file: an
  empty record, never an error.
- **Frontend:** INSIGHTS gets two sub tabs, PREDICTED FINISHES and TRACK RECORD, like
  MY TEAM and RACE DATA already have. New `frontend/src/components/TrackRecord.jsx`.
- **PitWall = locked team 1.** Beat counts only count races where both numbers exist.
