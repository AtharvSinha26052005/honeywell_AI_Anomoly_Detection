"""
Train Pipeline
===============
End-to-end training pipeline:
  1. Generate synthetic data
  2. Train baseline profiler (Isolation Forest)
  3. Train anomaly classifier (Random Forest)
  4. Generate scored dataset for dashboard
  5. Save all models and results
"""

import os
import sys
import json
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_generator import generate_dataset
from models.baseline_profiler import BaselineProfiler
from models.anomaly_classifier import AnomalyClassifier
from models.explainability import ExplainabilityEngine


def main():
    print("=" * 70)
    print("  AI-Powered Behavioral Anomaly Detection — Training Pipeline")
    print("=" * 70)

    # ---------------------------------------------------------------
    # Step 1: Generate synthetic data
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  STEP 1: Generating Synthetic Data")
    print("=" * 70)

    data_path = os.path.join("data", "synthetic_access_logs.csv")
    if os.path.exists(data_path):
        print(f"  Loading existing data from {data_path}...")
        df = pd.read_csv(data_path)
    else:
        df, entities = generate_dataset()

    print(f"  Dataset shape: {df.shape}")
    print(f"  Labels: {df['label'].value_counts().to_dict()}")

    # ---------------------------------------------------------------
    # Step 2: Train Baseline Profiler
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  STEP 2: Training Baseline Profiler (Isolation Forest)")
    print("=" * 70)

    profiler = BaselineProfiler()
    baseline_scores, baseline_preds = profiler.train(df)
    profiler.save()

    # ---------------------------------------------------------------
    # Step 3: Train Anomaly Classifier
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  STEP 3: Training Anomaly Classifier (Random Forest)")
    print("=" * 70)

    classifier = AnomalyClassifier()
    accuracy, report = classifier.train(df)
    classifier.save()

    # ---------------------------------------------------------------
    # Step 4: Generate scored dataset for dashboard
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  STEP 4: Generating Scored Dataset for Dashboard")
    print("=" * 70)

    print("  Predicting anomaly types...")
    pred_labels, confidences, probabilities = classifier.predict(df)

    print("  Generating explanations...")
    explainer = ExplainabilityEngine(classifier)

    # Add predictions to dataframe
    df_scored = df.copy()
    df_scored["predicted_label"] = pred_labels
    df_scored["confidence"] = confidences
    df_scored["baseline_score"] = baseline_scores

    # Calculate risk scores
    risk_scores = []
    contributing_factors_list = []
    summaries = []

    for i in range(len(df_scored)):
        row = df_scored.iloc[i].to_dict()
        exp = explainer.explain_alert(row, pred_labels[i], confidences[i])
        risk_scores.append(exp["risk_score"])
        contributing_factors_list.append(json.dumps(exp["contributing_factors"]))
        summaries.append(exp["summary"])

    df_scored["risk_score"] = risk_scores
    df_scored["contributing_factors"] = contributing_factors_list
    df_scored["explanation_summary"] = summaries

    # Save scored dataset
    scored_path = os.path.join("data", "scored_access_logs.csv")
    df_scored.to_csv(scored_path, index=False)
    print(f"  Scored dataset saved to: {scored_path}")
    print(f"  Shape: {df_scored.shape}")

    # ---------------------------------------------------------------
    # Step 5: Summary Statistics
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  STEP 5: Summary")
    print("=" * 70)

    print(f"\n  Total Events:           {len(df_scored)}")
    print(f"  Classifier Accuracy:    {accuracy:.4f}")

    print(f"\n  Prediction Distribution:")
    for label, count in df_scored["predicted_label"].value_counts().items():
        pct = count / len(df_scored) * 100
        print(f"    {label:25s}: {count:6d}  ({pct:5.1f}%)")

    print(f"\n  Risk Score Stats:")
    print(f"    Mean:   {df_scored['risk_score'].mean():.1f}")
    print(f"    Median: {df_scored['risk_score'].median():.1f}")
    print(f"    Max:    {df_scored['risk_score'].max():.1f}")
    print(f"    Min:    {df_scored['risk_score'].min():.1f}")

    high_risk = df_scored[df_scored["risk_score"] >= 70]
    print(f"\n  High-Risk Alerts (≥70): {len(high_risk)}")

    print("\n" + "=" * 70)
    print("  ✅ Training pipeline complete!")
    print(f"  Models saved to: saved_models/")
    print(f"  Scored data saved to: {scored_path}")
    print(f"  Run 'python dashboard/app.py' to launch the dashboard")
    print("=" * 70)


if __name__ == "__main__":
    main()
