# PitWall

An ML-powered F1 Fantasy assistant that predicts race outcomes, builds optimal teams within budget, and gives you the intel to make smarter picks before qualifying locks in.

## Motivation

F1 Fantasy is deceptively hard. The sport is chaotic — a consistent midfield driver can suddenly shine at a specific circuit, or a front-runner can qualify on pole and finish P8. Plain statistics aren't enough. PitWall combines historical rolling form, grid position analysis, and live practice session data to capture both the predictable and the unpredictable sides of F1.

## What It Does

| Tab | Description |
|-----|-------------|
| **Race Results** | Actual finishing order for any completed 2026 race with position changes (P5 → P2, +3) |
| **Qualifying** | Full qualifying session results with Q1 / Q2 / Q3 times |
| **Budget Team** | ML-optimised 5 drivers + 2 constructors within a $100M budget, based on race predictions |
| **Manual Team** | Build your own team for an upcoming race using live practice session data, scored against the optimal |

The **Weekend Team Widget** auto-activates within 5 days of a race — it detects the current weekend, fetches the best available practice session (FP3 → FP2 → FP1), and shows the optimal team without you having to do anything.

## How Predictions Work

1. Historical race results (2024 + 2025 + completed 2026 rounds) are used to train an XGBoost model
2. For upcoming races, live practice session data is fetched from FastF1 to estimate grid positions
3. Each driver's recent rolling form (last 3 races) is merged with their practice pace
4. The model predicts finishing positions, which are converted into a FantasyValue score
5. Budget optimisation then searches all valid 5-driver + 2-constructor combinations to find the highest-scoring team under $100M

Practice session availability is shown directly in the Manual Team tab — green dot means data is ready, otherwise the expected session time is displayed so you know exactly when to come back.

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
| FantasyValue | Weighted score: position gain + top finish bonuses |

## Model

- **Algorithm**: XGBoost Regressor (`n_estimators=200, learning_rate=0.05, max_depth=4`)
- **Training data**: 2024 + 2025 seasons, updated with completed 2026 rounds automatically on startup
- **Target**: Finishing position
- **Pick categories**: Safe (top 3 predicted) / Value / Risk / Avoid — based on FantasyValue quartiles

## Tech Stack

**Backend**
- Python, FastAPI, Uvicorn
- XGBoost, scikit-learn, Pandas, NumPy
- FastF1 — live race schedule, practice session data, qualifying results

**Frontend**
- React + Vite
- Tailwind CSS
- Driver headshots per driver card, team colour accents

## Project Structure

```
pitwall/
├── frontend/
│   ├── public/
│   │   └── drivers/          # Driver headshot images (ABBR.avif)
│   └── src/
│       └── App.jsx
├── src/
│   ├── data_loader.py
│   ├── features.py
│   ├── fantasy.py
│   ├── models.py
│   ├── pipeline.py
│   ├── fetch_practice.py
│   ├── fetch_prices.py
│   └── fetch_results.py
├── data/
│   ├── cache/                # FastF1 HTTP cache
│   └── processed/
│       ├── race_results_2024.csv
│       ├── race_results_2025.csv
│       └── race_results_2026.csv
├── main.py
├── requirements.txt
└── .env.example
```

## Running Locally

**Backend**
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt

# Copy .env.example to .env (optional for local dev)
cp .env.example .env

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

In production, set `CORS_ORIGINS` to your deployed frontend URL (e.g. `https://pitwall.vercel.app`).

## Deployment

- **Frontend** → Vercel (set root directory to `frontend/`)
- **Backend** → Railway (start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`)
- Set `CORS_ORIGINS` environment variable on Railway to the Vercel deployment URL

## Planned

- Reddit r/FantasyF1 community sentiment layer
- Weather integration per circuit
- Tyre degradation analysis
- UI redesign with Figma mockups
