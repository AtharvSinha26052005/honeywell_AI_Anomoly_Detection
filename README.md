# 🛡️ AI-Powered Behavioral Anomaly Detection for Cybersecurity

> **Honeywell Hackathon 2026** — AI/ML system that models "normal" access behaviour, detects intrusions in real-time, classifies anomaly types, and provides explainable risk scores through an analyst-facing dashboard.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange?logo=tensorflow)
![Dash](https://img.shields.io/badge/Plotly_Dash-2.x-blue?logo=plotly)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Data Generation Layer                       │
│  Synthetic Access Logs · 8 Attack Patterns · 50K+ Events     │
└──────────────────┬───────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────┐
│                    ML Pipeline                                │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Baseline    │  │  Isolation   │  │  Random Forest     │  │
│  │  Profiler    │→ │  Forest      │→ │  Classifier        │  │
│  │  (per-entity)│  │  (anomaly)   │  │  (8-class)         │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
└──────────────────┬───────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────┐
│                  Explainability Layer                         │
│  Feature Attribution · Risk Scoring · Human-readable Alerts  │
└──────────────────┬───────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────┐
│               Analyst Dashboard (Plotly Dash)                 │
│  KPI Overview · Alert Queue · Geo Map · Entity Deep Dive     │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/ai-anomaly-detection.git
cd ai-anomaly-detection

# Install dependencies
pip install -r requirements.txt

# Generate data & train models
python train.py

# Launch dashboard
python dashboard/app.py
```

Then open **http://127.0.0.1:8050** in your browser.

---

## 📊 Features

### Synthetic Data Generator
- Generates **50K+ realistic access-log events** using NumPy, Pandas & Faker
- Simulates **8 behaviour patterns**:
  | Pattern | Signal Type |
  |---------|------------|
  | Normal baseline | Benign |
  | Brute force | Anomaly |
  | Impossible travel | Anomaly |
  | Credential stuffing | Anomaly |
  | Lateral movement | Anomaly |
  | Device spoofing | Anomaly |
  | Low-and-slow exfiltration | Anomaly |
  | Insider drift | Edge case |

### ML Models
- **Baseline Profiler**: Per-entity statistical profiling + Isolation Forest
- **Anomaly Classifier**: Random Forest multi-class classifier (8 classes)
- **Explainability Engine**: Feature attribution with human-readable explanations

### Analyst Dashboard
- **KPI Overview** — Total events, anomalies, high-risk alerts, entities monitored
- **Anomaly Analytics** — Type distribution, timeline trends, risk histogram, hour×day heatmap
- **Geographic Map** — Global anomaly hotspots with interactive markers
- **Alert Queue** — Ranked by risk score, filterable by type/entity/risk level
- **Alert Detail** — Contributing factors, entity access history, explainability panel
- **Entity Analysis** — Top riskiest entities, attack distribution by entity type

---

## 🏗️ Project Structure

```
├── data_generator.py          # Synthetic data generation (8 attack patterns)
├── train.py                   # End-to-end training pipeline
├── requirements.txt           # Python dependencies
├── models/
│   ├── baseline_profiler.py   # Isolation Forest baseline profiler
│   ├── anomaly_classifier.py  # Random Forest multi-class classifier
│   └── explainability.py      # Feature attribution & explanations
├── dashboard/
│   ├── app.py                 # Plotly Dash dashboard
│   └── assets/
│       └── style.css          # Premium dark theme CSS
├── data/                      # Generated data (gitignored)
│   ├── synthetic_access_logs.csv
│   └── scored_access_logs.csv
└── saved_models/              # Trained models (gitignored)
```

---

## 📈 Evaluation Criteria Addressed

| Criteria | Implementation |
|----------|---------------|
| Detection accuracy on imbalanced labels | Balanced class weights in Random Forest |
| Correct anomaly-type classification | 8-class classifier with high F1 scores |
| False positive rate | Tuned contamination parameter, risk thresholds |
| Explainability / analyst usability | SHAP-inspired feature attribution, human-readable alerts |
| Cold-start entities | Statistical profiling with fallback defaults |
| System design & scalability | Modular architecture, streaming-ready design |
| Report clarity | Comprehensive documentation & dashboard |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Data Generation | Python, NumPy, Pandas, Faker |
| Baseline Detection | scikit-learn (Isolation Forest) |
| Classification | scikit-learn (Random Forest) |
| Explainability | Custom feature attribution engine |
| Dashboard | Plotly Dash, Dash Bootstrap Components |
| Visualization | Plotly.js |

---

## 📄 License

MIT License — Built for Honeywell Hackathon 2026
