# How the Model Works

Reference for the prediction pipeline, the scoring system, and circuit profiles.

---

## Overview

Three stages turn raw race history into a recommended team:

```
1. XGBoost predicts a finishing position per driver
2. That position is converted into real F1 Fantasy points (FantasyValue)
3. A combinations solver finds the 3 best teams under $100M
```

---

## Stage 1 — Predicting Finishing Position

**Algorithm:** XGBoost Regressor — an ensemble of 200 decision trees built sequentially, where each tree corrects the errors of the previous ones. The final prediction is all 200 trees summed.

```python
XGBRegressor(
    n_estimators=200,     # 200 trees
    learning_rate=0.05,   # each tree contributes 5% of its correction
    max_depth=4,          # 4 levels of questions per tree
    subsample=0.8,        # each tree sees 80% of rows (anti-overfitting)
    colsample_bytree=0.8, # each tree sees 80% of features
)
```

**Why XGBoost:** handles mixed numeric + categorical features well, captures non-linear interactions (a driver on pole *with* a high WinRate is worth much more than either signal alone), and performs well on small datasets — we only have a few hundred driver-races.

### Features

| Feature | Meaning |
|---|---|
| `GridPosition` | Starting position |
| `PreviousPosition` | Last race finish |
| `Rolling3Average` | EWM (span=3) of recent finishes |
| `AveragePositionChange` | Typical places gained/lost |
| `Consistency` | Std deviation of position change — lower is steadier |
| `GridvsForm` | Starting better or worse than form suggests |
| `FormTrend` | Improving or declining |
| `WinRate` | Wins in the last 5 races |
| `PodiumRate` | Podiums in the last 5 races |
| `TeamAvgPosition` | Team's average finish over its last 3 races |
| `TeamName` | One-hot encoded constructor |

`WinRate`, `PodiumRate`, and `TeamAvgPosition` are all **shifted by one race** before the rolling window is applied, so a race never contributes to its own prediction. Without that shift the model leaks the answer and looks far more accurate than it is.

### Training weights

Training uses 2025 + completed 2026 races, with **2026 weighted 5×**:

```python
sample_weight = np.where(df["Year"] == 2026, 5.0, 1.0)
```

2026 is a regulation-change season — the 2025 pecking order is close to irrelevant. The 5× weight lets the model learn current form (Antonelli's dominance, Aston Martin's collapse) while still using 2025 for circuit-level and driver-baseline signal.

### The blend

The raw XGBoost output is blended with three other signals. **Weights depend on the circuit** (`src/circuit_profiles.py:get_blend_weights`):

| Circuit overtaking | Model | FP3 pace | Teammate gap | Circuit history |
|---|---|---|---|---|
| ≤ 2 — Monaco | 0.35 | 0.05 | 0.05 | **0.55** |
| ≤ 4 — Hungary, Zandvoort, Singapore | 0.45 | 0.10 | 0.05 | 0.40 |
| ≤ 6 — neutral | 0.55 | 0.20 | 0.10 | 0.15 |
| ≥ 7 — Spa, Monza, Brazil | **0.60** | 0.25 | 0.10 | 0.05 |

At Monaco, where the grid essentially *is* the result, past results at the circuit are the strongest predictor. At Spa or Brazil, current pace and form matter far more because the field reshuffles during the race.

---

## Stage 2 — Scoring (`FantasyValue`)

`FantasyValue` is the **actual F1 Fantasy points** a driver is expected to score. This is what the optimiser maximises.

```
FantasyValue = RacePoints + OvertakeBonus + QualifyingScore + DNFPenalty
```

### Race points

Championship scale for the predicted finishing position:

| P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 | P11+ |
|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 18 | 15 | 12 | 10 | 8 | 6 | 4 | 2 | 1 | 0 |

### Qualifying points

| Result | Points |
|---|---|
| Pole | +10 |
| P2 → P10 | +9 down to +1 |
| Made Q2, not Q3 | 0 |
| Knocked out in Q1 | **−5** |

### Overtake bonus

`+1` per position gained, `−1` per position lost, then **scaled by the circuit's overtaking rating**.

### DNF

**−20.** This is the single largest swing in the game and the main reason a team can post a heavily negative score.

### Excluded

Fastest Lap (+10) and Driver of the Day (+10) are omitted. Both are effectively unpredictable before a race, and guessing at them would add noise rather than signal.

### Constructors

A constructor scores the **sum of both its drivers'** FantasyValue, plus:

| Bonus | Condition |
|---|---|
| +3 | Both cars reach Q3 |
| +1 | Both cars reach Q2 (but not both Q3) |
| +1.5 | Team averaging a top-4 finish (`TeamAvgPosition ≤ 4`) |
| +0.5 | Team averaging a top-7 finish |

The top-team bonus exists because raw FantasyValue sums can favour a cheap midfield constructor that happens to have two drivers gaining places. In practice Mercedes and Ferrari are near-mandatory picks, and this encodes that.

---

## Circuit Profiles

Defined in `src/circuit_profiles.py`. Each circuit carries an `overtaking` rating (1–10) and an `attrition` rate (DNF probability).

### Ratings

| Rating | Circuits |
|---|---|
| 1 | Monaco |
| 3 | Hungary, Zandvoort |
| 4 | Japan, Imola, Singapore, Barcelona, Spain (Madrid) |
| 5 | Australia, Mexico, Abu Dhabi |
| 6 | Saudi Arabia, Miami, Las Vegas, Qatar |
| 7 | Bahrain, China, Canada, Austria, Britain, Baku, USA |
| 8 | Spa |
| 9 | Monza, Brazil |

### How the rating is applied

Two multipliers derive from it:

```python
overtaking_scale(rating) = rating / 5.0        # Monaco 0.2×  ·  neutral 1.0×  ·  Brazil 1.8×
quali_scale(rating)      = 1 + (10 - rating)/10 # Monaco 1.9×  ·  neutral 1.5×  ·  Brazil 1.1×
```

- **`overtaking_scale`** multiplies the overtake bonus. At Monaco a predicted 5-place climb is worth ~1 point; at Brazil it's worth ~9.
- **`quali_scale`** multiplies the qualifying score. Pole at Monaco is worth ~19 points to the model, versus ~11 at Brazil — because at Monaco pole very nearly guarantees the win.

Together these change *which drivers the optimiser picks*:

| | Low overtaking (Monaco, Hungary) | High overtaking (Spa, Brazil) |
|---|---|---|
| Favours | Front-row qualifiers, top teams | Value picks starting midfield/back |
| Devalues | Position changers | Pure grid position |
| Classic case | Pole-sitter converts to a win | Verstappen P17 → win at Brazil 2024 |

### Keeping names in sync

Lookup is an exact dict match on `RaceName`. A name that isn't in `CIRCUIT_PROFILES` **silently falls back to neutral 5/10** — no error, just quietly worse picks. Worth re-checking whenever the calendar changes:

```python
import fastf1, pandas as pd
from src.circuit_profiles import CIRCUIT_PROFILES
fastf1.Cache.enable_cache('data/cache')
keys = set(CIRCUIT_PROFILES)
s = fastf1.get_event_schedule(2026, include_testing=False)
print([e['EventName'] for _, e in s.iterrows() if e['EventName'] not in keys])
```

This caught `Barcelona Grand Prix` — 2026 splits Barcelona and Madrid into separate events, with Madrid taking the "Spanish Grand Prix" name. Barcelona had been falling back to neutral.

### Validating ratings against real data

`compute_historical_overtaking(df)` derives a rating from actual results — mean absolute position change per driver per circuit, normalised to a 1–9 scale. `get_circuit_profile(race_name, historical_df)` blends that 50/50 with the hardcoded rating.

Hardcoded values are the anchor because with only ~10 races of 2026 data, a single chaotic wet race would badly distort a purely data-derived rating.

---

## Stage 3 — Team Selection

`build_budget_teams()` in `src/fantasy.py`:

1. Score every driver, drop the bottom-quartile ("Avoid") tier
2. Enumerate every valid combination of 5 drivers + 2 constructors under $100M, requiring **at least 1 Safe pick** (a top-3 predicted finisher)
3. Keep a running pool of the **top 50** lineups by total score
4. Walk that pool in score order and greedily select 3 teams that each differ from the others by **at least 2 drivers**

The diversity constraint is deliberately loose. If one driver is genuinely the best pick, they should appear in all three teams — the goal is three *good* teams that cover different outcomes, not three artificially different ones.

### 2× boost pick

`pick_boost_driver()` scores the chosen team's drivers by FantasyValue plus a small safety bonus for starting near the front, and **only considers Q3 qualifiers** (P1–P10). Doubling a driver who starts P16 risks doubling a −5 qualifying penalty on top of DNF exposure.

---

## Known Limitations

- **Small 2026 sample.** Predictions sharpen as the season progresses.
- **FP3 pace is noisy.** Teams run different fuel loads and engine modes; practice pace doesn't always carry into the race.
- **Weather is not a model feature yet.** A wet race scrambles grid-based prediction entirely — see `ROADMAP.md`.
- **No car-issue awareness.** A driver with a problem in FP3 looks identical to a healthy one — also on the roadmap.
- **Attrition is unused in scoring.** `attrition` is stored per circuit but doesn't yet feed the DNF penalty as an expected value.
