# PitWall — Feature Roadmap

All planned improvements discussed but not yet built. Update this file as things get done.

---

## 1. Three-Team Generator
**What:** F1 Fantasy allows up to 3 separate teams. Instead of recommending one optimal team, generate 3 distinct high-scoring lineups so the user can enter all three and maximise coverage across different race outcomes.

**How it works:**
- Run `build_budget_team()` once to get the best team
- Force diversity on the second and third teams — e.g. exclude the top 2 drivers from team 1 when solving team 2, exclude top 2 from team 2 when solving team 3
- Each team still respects the $100M budget and min 1 safe pick constraint
- Show all 3 side by side in the Budget Team tab with a team switcher

**Why it helps:** One team might be aggressive (value/midfield picks), another safe (top 3 + two constructors), another balanced. If one team has a bad race the others cover it.

---

## 2. Betting Odds as Prediction Signal
**What:** Blend bookmaker race odds into the model's prediction before the FP3 deadline.

**How it works:**
- Fetch pre-race win/points odds from a free API (e.g. The Odds API — free tier, 500 req/month)
- Convert odds to implied finishing position (lower odds = expected to finish higher)
- Blend as an extra signal in `predict_upcoming_race()` alongside FP3 pace and circuit history
- Suggested weight: 15–20% of the final blended score

**Why it helps:** Market odds already price in car upgrades, circuit suitability, tyre strategy expectations, and driver form — things the ML model can't see from raw lap times. Last race: Perez at long odds would have flagged him as a bad pick before deadline.

**Key constraint:** Must be available before qualifying (our deadline). Race outright odds are typically live from Thursday.

---

## 3. Session Health Signal (Practice Car Issues)

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

## 4. Weather as ML Feature
**What:** The weather widget shows the forecast but weather data is not currently fed into the prediction model.

**Why it helps:** Wet races completely scramble grid position predictions — position changes are larger, DNFs spike, midfield drivers outperform front-runners. The model currently has no way to adjust for this.

**How it works:**
- Pull rain probability and temperature for race day from Open-Meteo (already used in the widget)
- Add `RainProbability` and `Temp` as features in `build_features()`
- Historically tag each past race with its weather conditions (can be done retroactively with Open-Meteo historical API)
- In wet conditions: increase DNF weight, reduce confidence on grid position as predictor

---

## 5. APScheduler Auto-Fetch
**What:** Practice data currently requires a manual trigger (user clicks "Load Driver Pool"). A background scheduler should poll FastF1 automatically after each session ends so the prediction is ready without any manual action.

**How it works:**
- APScheduler runs inside the FastAPI app
- Schedule polls based on the race calendar (session end times from FastF1 schedule)
- After FP3 ends: wait 30 mins (FastF1 typical delay), fetch practice data, run prediction, cache result
- Frontend just loads the cached result — no waiting

**Note:** FastF1 typically has a 15–30 min delay after session ends before data is available.

---

## 6. Reddit r/FantasyF1 Sentiment
**What:** Scrape community driver picks and sentiment from r/FantasyF1 before each race as an extra signal.

**Why it helps:** The community often has insider knowledge on upgrades, tyre strategy, and circuit-specific pace that the model doesn't capture. The Reddit-recommended team last race (Antonelli, Hadjar, Lindblad, Lawson, Hulkenberg) outperformed our model's picks.

**How it works:**
- Use PRAW (Python Reddit API Wrapper) — free
- Scrape the weekly "Who are you picking?" or team reveal threads
- Count driver mention frequency + sentiment (positive/negative context)
- Use as a soft upward/downward modifier on FantasyValue

---

## Priority Order (suggested)

| # | Feature | Impact | Complexity |
|---|---------|--------|------------|
| 1 | Three-team generator | High | Low |
| 2 | Betting odds signal | High | Medium |
| 3 | Session health (Stage 1 - FastF1) | High | Low |
| 4 | Weather as ML feature | Medium | Medium |
| 5 | APScheduler auto-fetch | Medium | Medium |
| 6 | Session health (Stage 2 - scraping) | Medium | High |
| 7 | Reddit sentiment | Low-Medium | High |

---

## Already Completed
- [x] Constructor scoring fixed (mean → sum, both cars)
- [x] Qualifying score added to FantasyValue (Q3 +1.5, Q2 +0.5, Q1 -0.5)
- [x] 2024 data dropped, 2026 weighted 3x over 2025
- [x] 2x boost pick restricted to Q3 drivers only
- [x] Team lock after FP3 (locked_team.json, survives restarts)
- [x] GitHub Actions cron — auto-fetches race results every Monday
- [x] Mobile responsive layout
- [x] Helmet favicon
