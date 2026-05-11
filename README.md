# 🏎️ F1 Fantasy Predictor

An ML-powered Formula 1 Fantasy prediction system designed to help 
select optimal driver picks by analyzing race data and capturing 
the unpredictability of F1.

## 🎯 Motivation
F1 Fantasy is pretty difficult no matter what people think. The sport is very chaotic as anything can happen, 
a consistent midfield driver could suddenly shine in certain circuits or perform atrociously. So using plain statistics is not enough to capture it, 
thefore this project attempts to solve it.

## 🔍 Project Overview
- Trained on 2023 F1 race data, tested on 2024 season
- Evolved through 3 model versions with increasing sophistication
- Focus on both top driver prediction AND midfield chaos detection

## ⚙️ Features Engineering
| Feature | Description |
|---------|-------------|
| Rolling3Avg | 3-race rolling average performance |
| GainerScore | Heuristic scoring driver consistency and performance |
| GridGap | Starting position minus finishing position — captures race chaos |

There are more features built around Rolling3Avg to help with feature dominance.

## 📈 Model Evolution (so far)
**V1** → Basic driver ranking using 2023/2024 race data

**V2** → Introduced GainerScore to identify consistent 
midfield drivers alongside top performers

**V3** → Added GridGap feature to capture unpredictable 
circuit performance. Resulted in different midfield picks 
for chaotic circuits like Italian GP and Qatar GP compared to V2

*Will definitely try to improve the overall selection logic and have a better accuracy as well with more models if needed.*

## 📊 Results
- Mean Absolute Error: 1.49
- V2 vs V3 comparison shows meaningful difference in midfield 
picks for unpredictable circuits while top 5 predictions 
remained ~90% consistent

## 🛠️ Tech Stack
- Python
- Pandas, NumPy
- Scikit-learn (Random Forest Classifier)
- Jupyter Notebook
- Web dev soon!

## 🚀 Future Plans
- [ ] Web interface for fantasy pick recommendations
- [ ] Next race display and countdown
- [ ] Weather integration per circuit
- [ ] Season calendar and remaining races tracker
- [ ] AI assistant for weekly fantasy decisions

## 📁 Repository Structure
```
F1-Fantasy-Predictor/
├── notebooks/
│   ├── 01-data-exploration.ipynb
│   ├── 02-2023-to-2024-analysis.ipynb
│   ├── 03-analyze-v2-v3.ipynb
│   ├── model-v1-2023-2024.ipynb
    ├── model-v2-fantasy-logic.ipynb
│   └── model-v3-smarter-features.ipynb
├── results/
│   ├── fantasy_v1_results.csv
    ├── fantasy_v2_results.csv
│   └── fantasy_v3_results.csv
├── src/
│   ├── data_loader.py
    ├── features.py
│   └── models.py
├── .gitignore
├── README.md
└── requirements.txt
```
Feel free to star the repo if you find it interesting!

