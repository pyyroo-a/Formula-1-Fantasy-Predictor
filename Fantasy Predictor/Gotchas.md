---
title: Gotchas
date: 2026-10-25
tags: [pitwall, gotchas]
---

# Gotchas

Things that have bitten us before. Worth a skim before touching data, deploys or the
weekend flow.

## Data

- **F1's live timing is behind an F1TV login since October 2026.** Everything on
  `livetiming.formula1.com` answers 401, old seasons too. FastF1 doesn't raise, it
  loads with 0 drivers and then `.laps` throws `DataNotLoadedError`, so the site just
  quietly said "no practice data yet" all US GP weekend. Practice now comes from OpenF1
  ([Model](Model.md)). A paid F1TV account would fix FastF1 but that's out (free only).
  **Still at risk:** results go through FastF1 in two places, the Monday job
  (`scripts/update_data.py`) and backend startup (`update_season_results` in `main.py`).
  First Monday after the wall: 2026-10-26.
- **"Can't check" must never look like "not out yet".** At Madring a broken check
  answered "not published yet" all weekend and nobody noticed the lock never happened.
  Now OpenF1 trouble raises (and `/snapshot/auto` answers 502) instead of "waiting".
- **Race names move between circuits.** "Spanish Grand Prix" was Barcelona and is now
  Madrid's Madring, "Bahrain Grand Prix" was held in Kuala Lumpur in 2026.
  `src/race_names.py` renames old history so it doesn't leak into the wrong track.
  Check whenever a new race shows up, and check `CIRCUIT_PROFILES` has it too.
- **Team names drift.** FastF1 renamed 4 teams mid 2026. `src/team_names.py` maps
  everything onto the price feed's names. A mismatch silently scores a constructor 0.
- **The price feed lists a moved driver twice.** See [Prices](Prices.md).
- **Round 1 never shows in `/races`.** `build_features` drops it (no previous form to
  build features from), so the Australian GP is missing from the race dropdowns.

## Deploys

- **Split commits break Render.** Twice now: committing a file without the module it
  imports. Commit files that belong together in one go.
- **Render free tier sleeps** after about 15 minutes, and waking takes about 53
  seconds. Anything that calls it on a schedule needs a long timeout (the Action uses
  180 seconds).
- **Render has no disk.** Anything written at runtime is gone after a restart, which is
  why snapshots get committed to GitHub.
- **No backend pushes from FP1 Friday until the race is over**, so a bad deploy can't
  break the lock on a race weekend. Frontend only commits are fine any day.
- **Vercel preview URLs aren't in `CORS_ORIGINS`**, use the real domain.
- `data/prices.json` has had git conflict markers committed in it before. It heals at
  startup, but worth knowing if it looks weird.

## Tests

- The tests use frozen copies of the race results (`tests/fixtures/processed/`) and
  snapshots, so a new race doesn't change the saved answers any more. Before that,
  the goldens went stale every Monday, and a test once quietly turned into a different
  test when Baku's results landed. If a test needs a "race that hasn't happened", use
  a made up race name like `"Test Grand Prix"`, never a real upcoming race.
- `tests/conftest.py` switches OpenF1 off so the goldens use the FastF1 cache.

## Windows

- The venv doesn't stay activated between shell commands, call
  `./venv/Scripts/python.exe -m pytest` directly.
- Files are mostly CRLF. Scripts that edit them should keep the line endings and save
  as UTF-8 without a BOM, or the site shows garbled characters.

Related: [Race weekend flow](Race%20weekend%20flow.md), [Snapshots](Snapshots.md), [How-tos](How-tos.md), [Prices](Prices.md)
