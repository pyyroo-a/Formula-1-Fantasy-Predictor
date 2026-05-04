# F1 Fantasy Predictor

This is a sytem powered by a machine learning model that predicts Formula 1 race outcomes and generates optimized F1 Fantasy driver selections.

## Goal
The goal of this is to predict race results and transform the predictions into **actionalble Fantasy picks** using historical and race week data.

---

## 🧠 Methodology

### Data
- Historical race data collected using FastF1
- Seasons used:
  - **2023** → training
  - **2024** → testing (real-world simulation)

---

### Feature Engineering

Key features explored:

- **GridPosition** — starting position
- **RollingAvg3** — average finishing position over last 3 races
- **PrevPosition** — previous race result

---

### Advanced Features

To reduce over-reliance on a single feature, we engineering new features:

- **GridVsForm**  
  Compares a driver's recent form with their starting position

- **FormTrend**  
  Captures improvement or decline in recent performance

- **AveragePositionChange**  
  Measures how many positions a driver typically gains or loses

- **Consistency**  
  This represents stability in driver performance acrosses races

---

### Key Insight

Initial models showed that:

- `RollingAvg3` dominated predictions (**~0.78 feature importance**)

To address this:
- RollingAvg3 was used to derive more balanced features instead of being used directly (e.g., GridVsForm, FormTrend)

---

## 📊 Results

| Model Setup | MAE |
|------------|-----|
| With RollingAvg3 | **1.45** |
| Without RollingAvg3 | 1.74 |
| + GridVsForm | 1.61 |
| + FormTrend | **1.49** |

---

## 🎯 Fantasy Pick Logic (V1)

This model is extended into a **decision-making system for F1 Fantasy**

### Strategy

Driver selection is based on:

- **Safe Picks (Top 3)**
  Drivers with the lowest predicted finishing positions

- **Midfield Picks (Top 3)**
  Selected from predicted midfield (positions 6-12) based on:
  - Average position gains
  - Consistency

---

### Evaluation Metrics

- **Top 5 Hit rate** - number of selected drivers finishing in the top 5
- **Top 10 Hit rate** - number of selected drivers finishing in the top 10
- **Average finishing position** - average position the selected driver finishes

---

## 📈 Fantasy Evaluation (V1)

This has been tested across multiple races:

- Canadian Grand Prix → **Top 5 hit rate: 0.83**
- Monaco/Singapore Grand Prix → **Strong Preformance**
- Italian Grand Prix → **Top 5 hit rate: 0.5 (weak case)**

### Observation

- Model performs well in stable races
- Performance drops when races are strategy heavy or unpredictable
- Indicates oppurtunity for improved selection logic (V2)

---

## 🔍 Learnings

- Feature dominance can negatively impact model balance
- Feature engineering is more effective than simply adding more features
- Proper evaluation (2023 → 2024 split) is critical to avoid data leakage
- Debugging and data pipeline correctness are essential for reliable results
- Prediction accuracy alone is not enough — **decision logic matters**

---

## 📁 Project Structure

- `notebooks/` → model development and experimentation
- `data/` → processed race datasets
- `results/` → stores fantasy evaluation output

---

## ⚙️ Tech Stack

- Python
- FastF1
- Pandas / NumPy
- Scikit-learn

---

## 🚀 Next Steps

- Improve fantasy selection logic (V2)
  - Introduce confidence scoring
  - Improve midfield selection
- Expand training data (2023 + 2024 → 2025)
- Incorporate regulation-era awareness (2026 changes, plus drivers and new teams)
- Build a web interface for predictions and fantasy picks

---

## 📌 Status

Active development — core prediction pipeline implemented.
Currently focused on improving the fnatasy logic and preparing for deployment
