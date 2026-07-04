# 🏎️ F1 Fantasy Predictor

An ML-powered Formula 1 Fantasy prediction system designed to help 
select optimal driver picks by analyzing race data and capturing 
the unpredictability of F1.

## 🎯 Motivation
F1 Fantasy is pretty difficult no matter what people think. The sport is very chaotic as anything can happen, 
a consistent midfield driver could suddenly shine in certain circuits or perform atrociously. So using plain statistics is not enough to capture it, 
therefore this project attempts to solve it.

## 🔍 Project Overview
- Trained on 2024 + 2025 F1 race data, with completed 2026 races included in training
- Evolved through 5 model versions with increasing sophistication
- Focus on both top driver prediction AND midfield chaos detection
- Fantasy value layer on top of position prediction for practical recommendations
- Full stack web application with completed race analysis and live upcoming race predictions
- Practice session data (FP1/FP2/FP3) used to predict upcoming race weekends before results are known
- Sprint weekend detection — automatically selects FP1 for sprint weekends where FP2/FP3 don't exist

## ⚙️ Feature Engineering
| Feature | Description |
|---------|-------------|
| Rolling3Avg | 3-race rolling average performance |
| PositionChange | Positions gained or lost per race |
| AveragePositionChange | Rolling 3-race average of position gains |
| Consistency | Standard deviation of position change over 3 races |
| GridvsForm | Starting position vs recent average finish — detects overperformance potential |
| FormTrend | Rolling average vs previous race — captures momentum |
| GridGap | Starting position minus predicted finish — captures upside potential |
| Top10Finish | Binary flag for points finish |
| Top5Finish | Binary flag for strong finish |
| FantasyValue | Weighted score combining position gain, top finish bonuses |

## 📈 Model Evolution
**V1** → Basic driver ranking using 2023/2024 race data

**V2** → Introduced GainerScore to identify consistent 
midfield drivers alongside top performers

**V3** → Added GridGap feature to capture unpredictable 
circuit performance. Resulted in different midfield picks 
for chaotic circuits like Italian GP and Qatar GP compared to V2

**V4** → Refactored entire codebase into reusable src modules, 
defined proper FantasyValueScore, introduced formal pick categories 
(Safe/Value/Risk/Avoid), auto-tuned GainerScore weights using 
historical race data, and added explanation text per pick

**V5** → Added circuit profiling with manual labels (street/permanent/semi-permanent, DRS zones) 
combined with data driven stats per circuit

**V6 (Web App)** → Built a full stack web interface — FastAPI backend serving the ML pipeline 
as an API, React + Tailwind frontend with race selector, driver cards, pick category badges, 
and explanation text per pick

**V7 (Live 2026 Predictions)** → Upgraded pipeline to train on 2024+2025+completed 2026 races 
and predict upcoming race weekends using practice session data fetched live from FastF1. 
Added sprint weekend detection, dynamic upcoming race list, and FP1/FP2/FP3 session selector

## 📊 Results
- Mean Absolute Error: 0.59 on 2025 test data (trained on 2024+2025)
- Top 5 Hit Rate: 0.61 across 2024 season
- Top 10 Hit Rate: 0.95 across 2024 season
- Average Finish: 4.68
- Predictions validated against actual 2025 and 2026 race results

## 🛠️ Tech Stack

**Machine Learning**
- Python, Pandas, NumPy
- Scikit-learn (Random Forest Regressor)
- FastF1 for race data and live practice session fetching
- Jupyter Notebook

**Web Application**
- FastAPI (backend API)
- React + Vite (frontend)
- Tailwind CSS (styling)

## 🚀 Future Plans
- [ ] Budget cap constraints ($100M) for realistic team building
- [ ] Constructor picks (2 constructors per fantasy team)
- [ ] V6 — Upgrade ML model (XGBoost, LightGBM)
- [ ] Weather integration per circuit
- [ ] Tyre degradation analysis using FastF1 lap data
- [ ] Next race display and countdown
- [ ] AI assistant for weekly fantasy decisions
- [ ] Production deployment (Vercel + Railway)

## 📁 Repository Structure
```
F1-Fantasy-Predictor/
├── frontend/
│   └── src/
│       └── App.jsx
├── notebooks/
│   ├── 01-data-exploration.ipynb
│   ├── 02-2023-to-2024-analysis.ipynb
│   ├── 03-analyze-v2-v3.ipynb
│   ├── model-v1-2023-2024.ipynb
│   ├── model-v2-fantasy-logic.ipynb
│   ├── model-v3-smarter-features.ipynb
│   ├── model-v4-fantasy-logic.ipynb
│   └── model-v5-track-profiles.ipynb
├── src/
│   ├── data_loader.py
│   ├── features.py
│   ├── fantasy.py
│   ├── models.py
│   ├── circuits.py
│   ├── pipeline.py
│   └── fetch_practice.py
├── data/
│   └── processed/
│       ├── race_results_2024.csv
│       ├── race_results_2025.csv
│       └── race_results_2026.csv
├── main.py
├── .gitignore
├── README.md
└── requirements.txt
```

## 🏃 Running the App

**Backend**
```bash
# Activate virtual environment first
venv\Scripts\activate

uvicorn main:app --reload
```
Server starts at `http://127.0.0.1:8000`. Wait for "Pipeline loaded with X rows" before using the app.

**Frontend**
```bash
cd frontend
npm run dev
```
Opens at `http://localhost:5173`

## 🔮 How Upcoming Race Predictions Work

1. Select the **Upcoming Race** tab in the UI
2. Choose the next race from the dynamic list (automatically excludes completed rounds)
3. For normal weekends — select FP2 or FP3 (FP3 recommended)
4. For sprint weekends (Dutch GP, Singapore GP) — FP1 is used automatically
5. The system fetches live practice lap times from FastF1, ranks drivers by fastest lap as estimated grid positions, combines with each driver's historical rolling form, and predicts finishing positions
6. Pick your fantasy team before the race locks in

Feel free to star the repo if you find it interesting!
