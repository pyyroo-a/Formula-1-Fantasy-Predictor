---
title: How-tos
date: 2026-10-25
tags: [pitwall, howto]
---

# How-tos

## Lock a weekend from my laptop

When the Action and the self lock both missed it (check `/weekend-team` says
`"locked": true` first):

```bash
python scripts/lock_team.py                          # the next race weekend
python scripts/lock_team.py --race "Singapore Grand Prix"
python scripts/lock_team.py --race "..." --force     # replace an existing snapshot
```

Then commit the new file in `data/snapshots/` and push. It builds exactly what the
automatic lock would. It refuses once the race results are in our data, so a missed
weekend has to be recovered before Monday's job runs. That's how Bahrain R16 and
Singapore R17 got saved.

## Run the tests

```bash
./venv/Scripts/python.exe -m pytest -q
```

All 79 should pass before anything gets pushed. The golden tests compare every
endpoint's answer against `tests/golden/`. If an answer changed because you MEANT it to:

```bash
UPDATE_GOLDEN=1 ./venv/Scripts/python.exe -m pytest -q
```

then read the diff of `tests/golden/` and make sure only what you meant moved.

The tests read frozen race results from `tests/fixtures/processed/`. To move them on
to newer data on purpose: copy `data/processed/*.csv` over them, check the golden diff
is only race data (new races, slightly shifted predictions), then re-record.

## Run it locally

```bash
# backend, from the repo root
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload        # wait for "Pipeline loaded with X rows", about 10 to 20s

# frontend
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

`.env.example` lists the settings. Set `BACKTEST_ENABLED=true` locally to get the
Backtest tab.

## Check the deploy after a push

Render rebuilds the backend on every push (watch for green), Vercel the frontend. Then:
`curl -s https://formula-1-fantasy-predictor.onrender.com/weekend-team` should answer
like before. The first call after a quiet spell takes about a minute while Render wakes up.

## Start a new season

`src/config.py` has `SEASON`. Change it to the new year, make sure the finished
season's results are in `data/processed/` as last season's data, check every race
name exists in `CIRCUIT_PROFILES` and `src/race_names.py` (see [Gotchas](Gotchas.md)),
and check the team names still match the price feed.

## Re-check the circuit list

```python
import fastf1
from src.circuit_profiles import CIRCUIT_PROFILES
fastf1.Cache.enable_cache("data/cache")
s = fastf1.get_event_schedule(2026, include_testing=False)
print([e["EventName"] for _, e in s.iterrows() if e["EventName"] not in CIRCUIT_PROFILES])
```

Anything printed falls back to a neutral rating of 5.

## Catch Claude up in a new chat

"Read `Fantasy Predictor/README.md` and the notes it points to for whatever we're doing."

Related: [Snapshots](Snapshots.md), [Gotchas](Gotchas.md), [Working rules](Working%20rules.md), [API](API.md)
