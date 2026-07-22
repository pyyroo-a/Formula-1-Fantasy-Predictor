# PitWall — Feature Roadmap

All planned improvements discussed but not yet built. Update this file as things get done.

---

## 1. Betting Odds as Prediction Signal
**What:** Blend bookmaker race odds into the model's prediction before the FP3 deadline.

**How it works:**
- Fetch pre-race win/points odds from a free API (e.g. The Odds API — free tier, 500 req/month)
- Convert odds to implied finishing position (lower odds = expected to finish higher)
- Blend as an extra signal in `predict_upcoming_race()` alongside FP3 pace and circuit history
- Suggested weight: 15–20% of the final blended score

**Why it helps:** Market odds already price in car upgrades, circuit suitability, tyre strategy expectations, and driver form — things the ML model can't see from raw lap times. Last race: Perez at long odds would have flagged him as a bad pick before deadline.

**Key constraint:** Must be available before qualifying (our deadline). Race outright odds are typically live from Thursday.

---

## 2. Session Health Signal (Practice Car Issues)

### Stage 1 — FastF1 Data (build first, high value, low complexity)
**What:** Detect car problems automatically from FastF1 session data and apply a confidence penalty to affected drivers.

**Signals to use:**
- Laps completed vs teammate in FP3 — if a driver did significantly fewer laps, something is wrong
- Lap time variance — massive spread = setup issues or mechanical problems
- Whether the driver participated in FP3 at all (missed session = large penalty)

**Implementation:** Add a `session_health_score()` function in `src/features.py` that returns a modifier per driver (-1.0 to 0.0). Applied on top of `FantasyValue` before team selection.

**Teammate comparison logic:** If driver A did 8 laps and teammate B did 22 laps → A gets a -0.5 health penalty. If both did similar laps → no penalty.

### Stage 2 — Commentary/Reddit Scraping (build later, higher complexity)
**What:** Extract car issue mentions from text sources using an LLM call.

**Sources:**
- Autosport session reports (structured, scrapeable)
- r/formula1 FP megathreads (free, community catches issues fast but noisy)
- F1 journalist Twitter/X (real-time but API is expensive now)

**How it works:**
- Scrape session report text after each practice session
- Pass to a lightweight LLM call: "Extract any car problems, mechanical issues, or driver complaints mentioned. Return as JSON: {driver: issue}"
- Map extracted issues to a penalty modifier

**Big team logic:** Even with a health penalty, established drivers (Verstappen, Hamilton, Norris) retain enough base FantasyValue to stay in the team — the penalty just reduces their chance of being the 2x boost pick. Smaller drivers with issues get dropped from consideration entirely.

---

## 3. Weather as ML Feature
**What:** The weather widget shows the forecast but weather data is not currently fed into the prediction model.

**Why it helps:** Wet races completely scramble grid position predictions — position changes are larger, DNFs spike, midfield drivers outperform front-runners. The model currently has no way to adjust for this.

**How it works:**
- Pull rain probability and temperature for race day from Open-Meteo (already used in the widget)
- Add `RainProbability` and `Temp` as features in `build_features()`
- Historically tag each past race with its weather conditions (can be done retroactively with Open-Meteo historical API)
- In wet conditions: increase DNF weight, reduce confidence on grid position as predictor

---

## 4. APScheduler Auto-Fetch
**What:** Practice data currently requires a manual trigger (user clicks "Load Driver Pool"). A background scheduler should poll FastF1 automatically after each session ends so the prediction is ready without any manual action.

**How it works:**
- APScheduler runs inside the FastAPI app
- Schedule polls based on the race calendar (session end times from FastF1 schedule)
- After FP3 ends: wait 30 mins (FastF1 typical delay), fetch practice data, run prediction, cache result
- Frontend just loads the cached result — no waiting

**Note:** FastF1 typically has a 15–30 min delay after session ends before data is available.

---

## 5. Reddit r/FantasyF1 Sentiment
**What:** Scrape community driver picks and sentiment from r/FantasyF1 before each race as an extra signal.

**Why it helps:** The community often has insider knowledge on upgrades, tyre strategy, and circuit-specific pace that the model doesn't capture. The Reddit-recommended team last race (Antonelli, Hadjar, Lindblad, Lawson, Hulkenberg) outperformed our model's picks.

**How it works:**
- Use PRAW (Python Reddit API Wrapper) — free
- Scrape the weekly "Who are you picking?" or team reveal threads
- Count driver mention frequency + sentiment (positive/negative context)
- Use as a soft upward/downward modifier on FantasyValue

---

## 6. Circuit Profiles — Remaining Work
The core circuit-profile system is built (see `docs/MODEL.md`). Still outstanding:

- **Attrition is stored but unused.** Each circuit has an `attrition` rate (Baku 0.20, Japan 0.08) that doesn't yet feed scoring. Should apply as expected DNF value: `FantasyValue -= attrition * 20`, making Baku/Singapore picks appropriately riskier.
- **Sprint weekend scoring.** Sprint quali and the sprint race have their own points scales that aren't modelled.
- **Validate ratings after the season.** Once 2026 is complete, re-run `compute_historical_overtaking()` against the full season and adjust the hardcoded anchors where the data disagrees.

---

## Priority Order (suggested)

| # | Feature | Impact | Complexity |
|---|---------|--------|------------|
| 1 | Betting odds signal | High | Medium |
| 2 | Session health (Stage 1 - FastF1) | High | Low |
| 3 | Circuit attrition → DNF expected value | Medium | Low |
| 4 | Weather as ML feature | Medium | Medium |
| 5 | APScheduler auto-fetch | Medium | Medium |
| 6 | Session health (Stage 2 - scraping) | Medium | High |
| 7 | Reddit sentiment | Low-Medium | High |

---

## Already Completed
- [x] **Real F1 Fantasy scoring system** — replaced the invented FantasyValue heuristic with actual game points (race 25/18/15…, quali +10→+1 / −5, overtakes ±1, DNF −20, constructor Q2 +1 / Q3 +3). The old formula scored a DNF at −0.2 instead of −20, which is largely why the −93 race happened.
- [x] **Circuit profiles** — all 24 circuits rated 1–10 for overtaking. Drives both the prediction blend weights and the scoring multipliers (`overtaking_scale`, `quali_scale`). Monaco now favours qualifiers; Spa/Brazil favour climbers.
- [x] **Three-team generator** — `build_budget_teams()` keeps a top-50 pool and greedily selects 3 lineups differing by ≥2 drivers. Frontend has a team switcher.
- [x] WinRate / PodiumRate / TeamAvgPosition added as model features
- [x] Constructor scoring fixed (mean → sum, both cars) + top-team bonus
- [x] 2024 data dropped, 2026 weighted 5x over 2025
- [x] 2x boost pick restricted to Q3 drivers only
- [x] Team lock after FP3 (locked_team.json, survives restarts)
- [x] GitHub Actions cron — auto-fetches race results every Monday
- [x] Mobile responsive layout
- [x] Helmet favicon
