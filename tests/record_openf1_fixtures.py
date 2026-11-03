"""
Saves real OpenF1 answers for the tests, so they never have to call OpenF1 themselves.

Basically on Mexico weekend we found out OpenF1 answers in ways our code didn't expect
("No results found." comes back as a dict, the driver list can be empty or out of date),
so the tests for the backup use what OpenF1 really sent instead of answers we made up.

You only run this once (or if you deliberately want to refresh them):
    python tests/record_openf1_fixtures.py
"""
import json
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "fixtures" / "openf1"
BASE = "https://api.openf1.org/v1"


def get(path, **params):
    r = httpx.get(f"{BASE}/{path}", params=params, timeout=60)
    time.sleep(1)  # the free tier is rate limited, no rush
    return r.json()


def session_key(sessions, location, name):
    return next(s["session_key"] for s in sessions if s["location"] == location and s["session_name"] == name)


def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    print(name, "list of" if isinstance(data, list) else "dict:", len(data) if isinstance(data, list) else data)


def best_laps_only(laps):
    """Each driver's timed laps are a lot of json, so keep their best lap and a few untimed ones."""
    best = {}
    for lap in laps:
        t = lap.get("lap_duration")
        if t is not None and (lap["driver_number"] not in best or t < best[lap["driver_number"]]["lap_duration"]):
            best[lap["driver_number"]] = lap
    untimed = [lap for lap in laps if lap.get("lap_duration") is None][:3]
    return sorted(best.values(), key=lambda lap: lap["driver_number"]) + untimed


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    sessions = get("sessions", year=2026)
    mex_fp3 = session_key(sessions, "Mexico City", "Practice 3")
    mex_fp2 = session_key(sessions, "Mexico City", "Practice 2")
    sq = session_key(sessions, "Miami Gardens", "Sprint Qualifying")
    madrid_fp1 = session_key(sessions, "Madrid", "Practice 1")
    monaco_fp2 = session_key(sessions, "Monte Carlo", "Practice 2")

    save("mexico_fp3_session_result.json", get("session_result", session_key=mex_fp3))
    save("mexico_fp3_drivers.json", get("drivers", session_key=mex_fp3))
    save("mexico_fp2_drivers.json", get("drivers", session_key=mex_fp2))
    save("mexico_fp3_laps_best.json", best_laps_only(get("laps", session_key=mex_fp3)))
    save("sq_session_result.json", get("session_result", session_key=sq))
    save("madrid_fp1_session_result.json", get("session_result", session_key=madrid_fp1))
    save("monaco_fp2_drivers.json", get("drivers", session_key=monaco_fp2))
