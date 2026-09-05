# PitWall

An ML-powered F1 Fantasy assistant that predicts race outcomes, builds optimal teams within budget, advises on chip timing, and gives you the intel to make smarter picks before qualifying locks in.

**Live:** [formula-1-fantasy-predictor.vercel.app](https://formula-1-fantasy-predictor.vercel.app)

## Motivation

F1 Fantasy is deceptively hard. The sport is chaotic — a consistent midfield driver can suddenly shine at a specific circuit, or a front-runner can qualify on pole and finish P8. Plain statistics aren't enough. PitWall combines historical rolling form, grid position analysis, live practice session data, and F1 Fantasy pricing to capture both the predictable and the unpredictable sides of F1.

## What It Does

| Tab | Description |
|-----|-------------|
| **Race Results** | Actual finishing order for any completed 2026 race with position changes (P5 → P2, +3) |
| **Qualifying** | Full qualifying session results with Q1 / Q2 / Q3 times |
| **Budget Team** | Three ML-optimised lineups (5 drivers + 2 constructors) within a $100M budget, with a team switcher — F1 Fantasy allows up to 3 entries |
| **Manual Team** | Build your own team for an upcoming race using live practice session data, scored against the optimal |
| **Chip Advisor** | Enter your current F1 Fantasy squad and get a PLAY / CONSIDER / HOLD recommendation for each chip |

The **Weekend Team Widget** auto-activates within 5 days of a race — it detects the current weekend, fetches the best available practice session (FP3 → FP2 → FP1), and shows the optimal team without you having to do anything.

The **Prices Sidebar** is always visible on the right — it shows current F1 Fantasy prices for every driver and constructor, with arrows indicating whether each price went up or down compared to last round.

## How Predictions Work

1. Historical race results (2025 + completed 2026 rounds, 2026 weighted 5×) train an XGBoost model
2. For upcoming races, live practice session data is fetched from FastF1 to estimate grid positions
3. Each driver's recent rolling form is merged with their practice pace
4. The raw prediction is blended with FP3 pace, teammate gap, and circuit history — **the blend weights change per circuit** (see below)
5. Predicted finishing positions are converted into **real F1 Fantasy points** (FantasyValue)
6. Budget optimisation searches all valid 5-driver + 2-constructor combinations and returns the 3 best mutually-distinct teams under $100M

Full detail on the scoring system and circuit profiles: **[`docs/MODEL.md`](docs/MODEL.md)**

### Circuit-Aware Predictions

Every circuit is rated 1–10 for overtaking difficulty, which changes both the blend and the scoring:

| Circuit type | Example | Blend shifts toward | Scoring effect |
|---|---|---|---|
| Low overtaking | Monaco (1), Hungary (3) | Circuit history / grid | Qualifying points weighted up to **1.9×**, overtake bonus down to **0.2×** |
| Neutral | Australia (5), Abu Dhabi (5) | Balanced | 1.0× / 1.0× |
| High overtaking | Spa (8), Monza & Brazil (9) | Model + FP3 pace | Overtake bonus up to **1.8×** |

This means at Monaco the optimiser naturally prefers front-row qualifiers, and at Spa or Brazil it favours value picks starting further back who can climb.

Practice session availability is shown directly in the Manual Team tab — green dot means data is ready, otherwise the expected session time is displayed so you know exactly when to come back. The session picker auto-fallbacks FP3 → FP2 → FP1 and always shows which session the predictions are based on.

## Handling Uncertainty

**You have to pick your F1 Fantasy team before qualifying happens.**

That one rule shapes everything. When the deadline hits, nobody knows the starting
grid yet. So PitWall does the only thing available: it looks at who was fastest in
practice and assumes the race will start roughly in that order.

That assumption is the biggest source of error in the whole system. `scripts/measure_grid_error.py`
checks how often it is wrong, by replaying all of 2026 and comparing what practice
predicted against where drivers actually lined up.

```
python scripts/measure_grid_error.py --year 2026
```

### How good is practice, really?

Across 12 races and 260 driver performances:

| | |
|---|---|
| Typical miss | **about 2 places** |
| Half the time | within 1 place |
| Worst 5% of the time | off by 6 or more |
| Picked the actual pole-sitter | **7 races out of 12** |

Practice is decent. It is not close to reliable.

Importantly, it is not *biased*. It does not flatter one team or drag another down.
It is simply noisy, and it misses in both directions about equally. That matters,
because it means you cannot fix this by tweaking a number somewhere. The wobble is
real and it is not going away.

### Why "off by 2 places" is worse than it sounds

F1 Fantasy does not award points smoothly. It awards them in **jumps**:

- Qualify in the **top 10** and you score up to +10
- Qualify **11th to 15th** and you score nothing
- Qualify **16th or worse** and you *lose* 5 points

So the gap between 10th and 11th is not one place. It is the difference between
points and nothing. And the gap between 15th and 16th swings you from zero to minus five.

Now put those two facts together. Practice is normally off by about two places, and
the scoring has sudden drops at exactly those boundaries.

> **One pick in four (25.8%) ends up on the wrong side of one of these jumps.**
> PitWall scores the driver for a grid slot he never actually started from.

**Monza 2026 is the perfect example.** Practice had Gasly down in 9th, so PitWall
gave him a small qualifying score. He then went out and took pole, worth the full
+10. The prediction was not slightly off. It was looking at a completely different
race.

### Sprint weekends are noticeably shakier

Normal weekends have three practice sessions. Sprint weekends have **one**, and it
runs on a green, dusty track before anyone has properly dialled the car in.

| | Normal weekend | Sprint weekend |
|---|---|---|
| Typical miss | 1.9 places | **2.5 places** |
| Landed on the wrong side of a scoring jump | 23% | **29%** |
| Found the actual pole-sitter | **7 out of 7** | **0 out of 5** |

Practice correctly identified the pole-sitter at every single normal weekend, and at
none of the sprint weekends. Sprint weekends are not a different problem needing a
different model. They are the same problem with **less information**, so the sensible
response is for PitWall to be visibly less confident on those weekends.

### Cars that do not finish

About **3 cars per race retire**. PitWall's scoring has always applied a −20 point
penalty for a retirement, but for upcoming races it quietly set that penalty to zero
and assumed all 20 cars would finish. So the riskiest picks looked exactly as safe as
the reliable ones.

`src/dnf.py` estimates how likely each driver is to retire. It does **not** try to
call who will crash, which is not possible. It prices the risk so the expected points
stop being quietly optimistic.

What the data says, over 2025 and 2026:

- **Where you start matters most.** Front-runners retire far less than backmarkers:
  roughly 8% from the first two rows, rising past 20% at the back. Slower cars are
  less reliable and more exposed to first-lap trouble.
- **The season matters a lot.** 2025 ran at 12.5%, 2026 at 21.6%, almost double.
  Recent races are weighted more heavily as a result.
- **Who is driving matters less than it looks.** One driver retiring nine times in 36
  races and another retiring twice looks like a huge gap, but a perfectly average
  driver would produce that spread by luck reasonably often. So individual rates get
  pulled toward the field average, by an amount measured from the data rather than
  picked by hand. Tracks get pulled even harder, since each one has only been raced
  once or twice.

Roughly what it produces for a typical driver:

| Starting slot | Chance of retiring | Average points cost |
|---|---|---|
| P1 | 7.5% | −1.5 |
| P5 | 9.8% | −2.0 |
| P10 | 13.8% | −2.8 |
| P15 | 18.9% | −3.8 |
| P20 | 25.4% | −5.1 |

**Was it tested?** Yes. `scripts/measure_dnf.py` replays 2026 race by race, training
only on races that had already happened and then predicting the next one. It is graded
against the simplest sensible forecast: give every driver the same average chance.

| | Model | Flat average |
|---|---|---|
| Brier score (lower is better) | **0.1652** | 0.1750 |
| Log loss (lower is better) | **0.5126** | 0.5429 |
| Races predicted better | **11 of 12** | |

An improvement of about 5.6%. Real, and consistent across the season, but modest. Worth
being honest that the big win here is not the fancy part, it is simply no longer
pretending that every car finishes.

### What we are doing about it

The instinct is "make the prediction better." That is the wrong target, and we have
the evidence: PitWall's machine-learning adjustments are currently switched off
(`SHRINK_TO_GRID = 0.0` in `src/models.py`) because testing showed they made results
*worse*, not better.

The actual problem is that PitWall commits to **one guess** and then treats it as
fact, even though we now know that guess is off by two places on a typical weekend.

So instead of predicting one weekend, PitWall will simulate **thousands** of them.

Each simulated weekend rolls a slightly different grid, drawn from the real spread of
errors measured above. Some drivers retire, based on how often they actually retire
(**15.3%** of the time across 2025 and 2026, roughly 3 cars per race, a number PitWall
currently ignores completely by assuming everyone finishes). Then every simulated
weekend gets scored with the normal scoring rules.

Run that a few thousand times and you learn things a single guess can never tell you:

- What a driver scores **on average**, rather than in one lucky version of events
- How **reliable** that number is, since a driver who scores 20 every time is a very
  different pick from one who scores 40 or 0
- The chance a pick **backfires**

That last point is what actually wins fantasy leagues. You get three teams, so the
right move is one safe team and one that swings for the fences, and you cannot make
that call without knowing which picks are risky.

Nothing ships on vibes. Every change is tested against `run_backtest`, which replays
completed races. The bar to beat is the embarrassingly simple strategy of just picking
drivers in practice order, which currently beats PitWall's model **8 races to 0**.

## Chip Advisor

PitWall analyses all 6 F1 Fantasy chips against your squad and the upcoming race predictions:

| Chip | Logic |
|------|-------|
| **Limitless** | Removes budget cap — compares uncapped optimal team vs your squad |
| **Wildcard** | Scores if a full squad rebuild would gain significantly over your current team |
| **3× Boost** | Scores if your best predicted driver is significantly ahead of the field (2× → 3×) |
| **Final Fix** | Flags your weakest scorer as a swap candidate after qualifying |
| **No Negative** | Recommends for high-attrition circuits (Monaco, Singapore, Baku, etc.) |
| **Auto Pilot** | Always SAVE — PitWall already does this better |

Each chip gets a **PLAY / CONSIDER / HOLD / SAVE** verdict with an expected xP gain.

## Feature Engineering

| Feature | Description |
|---------|-------------|
| Rolling3Average | 3-race rolling average finish position |
| PreviousPosition | Last race finish |
| PositionChange | Positions gained/lost per race |
| AveragePositionChange | Rolling 3-race average of position gains |
| Consistency | Std deviation of position change — lower = more consistent |
| GridvsForm | Starting position vs recent average — detects overperformance potential |
| FormTrend | Rolling average vs previous race — captures momentum |
| Top10Finish | Binary: points finish |
| Top5Finish | Binary: strong finish |
| WinRate | Wins over the last 5 races — captures in-season dominance |
| PodiumRate | Podiums over the last 5 races |
| TeamAvgPosition | Team's average finish over its last 3 races |
| FantasyValue | **Real F1 Fantasy points** for the predicted result (see below) |

## Scoring

`FantasyValue` is the actual F1 Fantasy points a driver is expected to score, not an invented heuristic:

```
FantasyValue = RacePoints + OvertakeBonus + QualifyingScore + DNFPenalty
```

| Component | Value |
|---|---|
| Race position | P1 = 25, P2 = 18, P3 = 15, P4 = 12, P5 = 10, P6 = 8, P7 = 6, P8 = 4, P9 = 2, P10 = 1 |
| Qualifying | P1 = +10 down to P10 = +1 · Q2-only = 0 · Q1 knockout = **−5** |
| Overtakes | +1 per position gained, −1 per position lost (scaled by circuit) |
| DNF | **−20** |

Constructors score the sum of both their drivers, plus **+3 if both cars reach Q3** (or +1 for Q2), plus a top-team bonus so Mercedes/Ferrari are correctly favoured.

Fastest Lap (+10) and Driver of the Day (+10) are deliberately excluded — they can't be predicted reliably before a race.

## Model

- **Algorithm**: XGBoost Regressor (`n_estimators=200, learning_rate=0.05, max_depth=4`)
- **Training data**: 2025 season + completed 2026 rounds, with **2026 weighted 5×** so current car pace dominates. Updated automatically on startup.
- **Target**: Finishing position
- **Blend**: model / FP3 pace / teammate gap / circuit history — weights vary per circuit
- **Pick categories**: Safe (top 3 predicted) / Value / Risk / Avoid — based on FantasyValue quartiles

## Tech Stack

**Backend**
- Python, FastAPI, Uvicorn
- XGBoost, scikit-learn, Pandas, NumPy
- FastF1 — live race schedule, practice session data, qualifying results
- Public F1 Fantasy API — driver and constructor prices

**Frontend**
- React + Vite
- Tailwind CSS
- Component-based architecture — each feature in its own file under `frontend/src/components/`
- Driver headshots per card (`.avif`), team colour accents on every card

## Project Structure

```
pitwall/
├── frontend/
│   ├── public/
│   │   └── drivers/              # Driver headshots (ABBR.avif, one per driver)
│   └── src/
│       ├── App.jsx               # Thin shell: layout, top-level state, tab switching
│       ├── constants.js          # DRIVER_NAMES, TEAM_COLORS, CHIP_META, REC_STYLE, etc.
│       └── components/
│           ├── DriverAvatar.jsx       # Headshot with abbreviation fallback
│           ├── CountdownWidget.jsx    # Race name + live countdown
│           ├── SessionSchedule.jsx    # FP1/FP2/FP3 availability dots
│           ├── WeekendTeamWidget.jsx  # Auto-shows optimal team near race weekend
│           ├── RaceResultsTable.jsx   # Completed race results with position change
│           ├── QualifyingTable.jsx    # Q1/Q2/Q3 results with Q3 highlight
│           ├── BudgetTeam.jsx         # BudgetBar, BudgetDriverCard, ConstructorCard
│           ├── ManualTeamBuilder.jsx  # Pick-your-own team with scoring vs optimal
│           ├── ChipAdvisor.jsx        # Chip PLAY/CONSIDER/HOLD recommendations
│           └── PricesSidebar.jsx      # Sticky sidebar: prices + vs-last-round changes
├── src/
│   ├── data_loader.py
│   ├── features.py
│   ├── fantasy.py                 # Real F1 Fantasy scoring + budget team solver
│   ├── circuit_profiles.py        # Per-circuit overtaking ratings + blend weights
│   ├── dnf.py                     # P(retirement) per driver, used to price risk
│   ├── championship_form.py
│   ├── models.py
│   ├── pipeline.py
│   ├── fetch_practice.py
│   ├── fetch_prices.py            # Fetches current + previous round prices, diffs them
│   └── fetch_results.py
├── scripts/
│   ├── update_data.py             # Called by the GitHub Actions cron
│   ├── measure_grid_error.py      # Practice-order vs real-grid error (see Handling Uncertainty)
│   └── measure_dnf.py             # Walk-forward validation of the DNF model
├── .github/workflows/
│   └── update-race-data.yml       # Auto-fetches new race results every Monday
├── docs/
│   └── MODEL.md                   # Scoring system + circuit profiles in detail
├── data/
│   ├── cache/                     # FastF1 HTTP cache
│   ├── locked_team.json           # Weekend team lock (survives restarts)
│   └── processed/
│       ├── race_results_2025.csv
│       └── race_results_2026.csv
├── main.py
├── ROADMAP.md
├── requirements.txt
└── .env.example
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/races` | List of completed 2026 races |
| GET | `/upcoming-races` | Upcoming races with sprint flag |
| GET | `/next-race` | Next race name + date |
| GET | `/weekend-team` | Auto optimal team if within 5 days of a race |
| GET | `/price-changes` | All driver + constructor prices vs last round |
| POST | `/race-results` | Completed race finishing order |
| POST | `/qualifying-results` | Q1/Q2/Q3 times for a race |
| POST | `/race-sessions` | FP1/FP2/FP3 schedule + availability for a race |
| POST | `/predict` | ML prediction for an upcoming race |
| POST | `/predict-budget` | Three optimal teams within $100M budget — returns `{ "teams": [...] }` |
| POST | `/unlock-team` | Clears the weekend team lock so it regenerates |
| POST | `/upcoming-race-pool` | Driver + constructor pool for manual team builder |
| POST | `/chip-advisor` | Chip recommendations for a given squad |

## Running Locally

**Backend**
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt

uvicorn main:app --reload
```

Wait for `Pipeline loaded with X rows` in the terminal before using the app. Startup takes ~10–20 seconds as it fetches any new race results and trains the model.

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins | `*` (all) |

In production, set `CORS_ORIGINS` to your deployed frontend URL.

## Deployment

- **Frontend** → Vercel (set root directory to `frontend/`)
- **Backend** → Render (Docker runtime, builds the root `Dockerfile`, binds `$PORT`)
- Set `CORS_ORIGINS` in the Render dashboard to the Vercel deployment URL
- Set `VITE_API_URL` on Vercel to the Render URL, then redeploy — Vite bakes env vars in at build time

The free instance sleeps after 15 minutes idle, so the first request after a quiet spell pays a cold start.

## Automation

A GitHub Actions cron (`.github/workflows/update-race-data.yml`) runs every Monday at 06:00 UTC, fetches any newly completed races via FastF1, and commits the updated CSV. Render auto-deploys on push, so the model retrains on fresh data without any manual step.

## Planned

See **[`ROADMAP.md`](ROADMAP.md)** for the full list. Next up:

- Sports betting odds integration — market-implied finishing order as an extra signal
- Session health signal — detect car issues from FP3 lap counts vs teammate
- Weather as an ML feature
- APScheduler background job to auto-fetch practice data as sessions finish
