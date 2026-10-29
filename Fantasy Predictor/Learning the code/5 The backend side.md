---
title: 5 The backend side
date: 2026-10-30
tags: [pitwall, learning, backend]
---

# 5. The backend side

This half is Python, so it'll feel more familiar. It uses **FastAPI**, which is a library
that turns normal Python functions into endpoints the website can ask.

## `main.py`: opening the kitchen

When Render starts the backend, `main.py` runs. Three things:

**1. Get ready before the first order** (the `lifespan` part):

```python
added = update_season_results(SEASON, results_path())
state.fantasy_table = run_pipeline()
...
state.current_prices = fetch_prices(target)
...
state.race_schedule = fastf1.get_event_schedule(SEASON, include_testing=False)
```

Download any race results we don't have yet, run the model once (`run_pipeline`), load
this round's prices and the calendar. All of that gets kept in `src/api/state.py`, which
is basically a shelf of things every endpoint can grab without redoing the work. That's
why the very first request after Render wakes up is slow: it's doing all this first.

**2. Say who's allowed to ask** (CORS):

```python
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, ...)
```

A browser only lets a website read answers from another address if that address says
it's allowed. Like a guest list at the paddock gate. On Render the list is our Vercel
site, which is why my laptop preview on a random port got turned away and we used the
local backend instead.

**3. Plug in all the endpoint files**:

```python
for module in (races, prices, teams, race_weekend, finishes, weekend_lock, planner, track_record, chip_history, dev):
    app.include_router(module.router)
```

Each group of endpoints lives in its own file in `src/api/` (see [API](../API.md) for the
full list). This loop just plugs them all into the app.

## What an endpoint looks like

The simplest one we have, `src/api/chip_history.py`:

```python
@router.get("/chip-history")
def get_chip_history():
    path = os.getenv("CHIP_HISTORY_PATH", DEFAULT_PATH)
    if not os.path.exists(path):
        # nothing built yet, that's an empty history, not an error
        return EMPTY
    with open(path, encoding="utf-8") as f:
        return json.load(f)
```

- `@router.get("/chip-history")` is the label on the counter: "when someone does GET
  `/chip-history`, run this function".
- The function returns a normal Python dict, and FastAPI turns it into JSON for the
  website by itself.
- This one just reads a saved file, because the real maths (`scripts/chip_history.py`)
  is too slow to do every time someone opens the page. The Monday GitHub Action re-runs
  the script and saves the file.

A **POST** endpoint gets information sent to it. FastAPI checks it's the right shape
first using a little class (in `src/api/schemas.py`):

```python
class PracticeRequest(BaseModel):
    race_name: str
    session: str = ""  # empty = auto-pick the final practice session that exists
```

So `/practice-results` expects a `race_name` (must be text) and maybe a `session`. If the
website sends something wrong, FastAPI answers with an error before our code even runs.

## Where the real thinking lives: `src/`

`src/api/` is just the counters. The kitchen itself is the rest of `src/`, the files from
[Code tour](../Code%20tour.md). The ones that matter most:

| File | Job |
|---|---|
| `src/fetch_practice.py`, `src/openf1.py` | get practice laps and turn them into a pace order |
| `src/models.py`, `src/pipeline.py` | the model: practice order into a predicted finish |
| `src/fantasy.py` | predicted finish into fantasy points, and the best teams under budget |
| `src/confidence.py` | high, medium, low for each pick |
| `src/weekend.py` | locking the weekend and saving the snapshot |
| `src/planner.py` | the transfer ladder |
| `src/track_record.py`, `src/chip_history.py` | the Insights numbers |

## A worked example: the practice fix

This is a real change from the redesign, and it shows how the pieces fit.

**The problem:** RACE DATA > Practice answered 500 (a crash) for every race. The
endpoint still asked FastF1 for laps, and F1 put that behind an F1TV login in October.

**The fix, in three parts:**

1. **A new function that builds the page's rows from OpenF1** (`src/openf1.py`):

   ```python
   def practice_table(laps: list, drivers: list) -> list[dict]:
       ...
       best = laps.groupby("driver_number")["lap_duration"].min().reset_index()
       ...
       rows.append({
           "Position": int(i) + 1,
           "Abbreviation": r["name_acronym"],
           "FullName": f"{r['first_name']} {r['last_name']}" if named else r["name_acronym"],
           "TeamName": r["TeamName"],
           "LapTime": _lap_text(r["lap_duration"]),
           "GapToPole": round(float(r["lap_duration"] - pole), 3),
       })
   ```

   Take everyone's fastest lap, sort fastest first, and build the exact rows the page
   already expected (so the website didn't need to change for it). If you know pandas
   from Python, `groupby(...).min()` is "the smallest lap time per driver".

2. **The endpoint tries OpenF1 first** (`src/api/races.py`):

   ```python
   try:
       output = openf1.openf1_practice(year, request.race_name, session_name, start)
   except openf1.NotPublishedYet as e:
       raise HTTPException(status_code=404, detail=str(e))
   except openf1.OpenF1Unavailable:
       output = _fastf1_practice_rows(year, request.race_name, session_name)
   ```

   Three outcomes, like a pit stop plan A, B, C: OpenF1 has it (great), the session isn't
   over yet (say so), or OpenF1 can't help (fall back to the old FastF1 way, which still
   works for old sessions saved on disk).

3. **Don't download the same laps twice.** The model and the practice page both need the
   same laps, and OpenF1's free tier is rate limited, so the laps get kept in memory per
   session (`_laps_cache`). The reviewer then spotted a trap: an **empty** answer was kept
   too, which could have stopped the automatic lock all weekend. Now it only keeps a
   session once it really has lap times:

   ```python
   if any(lap.get("lap_duration") is not None for lap in laps or []):
       _laps_cache[key] = (laps, drivers)
   ```

That's the backend in a nutshell: a counter (`src/api/`), a cook (`src/`), and saved
answers (`data/`) for anything too slow to do live.

## Little word list

- **FastAPI**: the Python library that makes functions into endpoints.
- **Router**: a group of endpoints in one file.
- **Status code**: the number on an answer. 200 = fine, 400/404 = your question had a
  problem (like "no practice yet"), 500 = the backend crashed.
- **CORS**: the guest list of websites allowed to read the answers.
- **Cache**: keeping an answer in memory so you don't fetch it again.

Next: [Tests and checking](6%20Tests%20and%20checking.md)
