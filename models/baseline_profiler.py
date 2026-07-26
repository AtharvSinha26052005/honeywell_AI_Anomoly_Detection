"""
Baseline Profiler
==================
Builds per-entity "normal" behaviour profiles using statistical features
and Isolation Forest for baseline anomaly detection.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib
import json
import os


class BaselineProfiler:
    """Per-entity statistical profiler with Isolation Forest anomaly detection."""

    def __init__(self):
        self.entity_profiles = {}
        self.isolation_forest = None
        self.scaler = StandardScaler()
        self.le_entity_type = LabelEncoder()
        self.le_auth = LabelEncoder()
        self.le_resource = LabelEncoder()

    def extract_features(self, df):
        """Extract statistical features from access log dataframe."""
        # Parse timestamp
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        # Extract geo coordinates from geo_location string
        def parse_lat_lon(geo_str):
            try:
                coords = geo_str.split("(")[1].rstrip(")")
                lat, lon = coords.split(",")
                return float(lat), float(lon)
            except:
                return 0.0, 0.0

        df[["lat", "lon"]] = df["geo_location"].apply(
            lambda x: pd.Series(parse_lat_lon(x))
        )

        # Encode categoricals
        df["entity_type_enc"] = self.le_entity_type.fit_transform(df["entity_type"])
        df["auth_method_enc"] = self.le_auth.fit_transform(df["auth_method"])
        df["resource_enc"] = self.le_resource.fit_transform(df["resource_accessed"])

        # Session duration
        df["session_duration"] = pd.to_numeric(df["session_duration"], errors="coerce").fillna(0)

        # Command count
        df["cmd_count"] = df["command_sequence"].apply(
            lambda x: len(json.loads(x)) if isinstance(x, str) else 0
        )

        feature_cols = [
            "hour", "day_of_week", "is_weekend", "lat", "lon",
            "entity_type_enc", "auth_method_enc", "resource_enc",
            "session_duration", "cmd_count"
        ]

        return df, feature_cols

    def build_entity_profiles(self, df):
        """Build per-entity statistical profiles."""
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["hour"] = df["timestamp"].dt.hour

        for entity_id, group in df.groupby("entity_id"):
            profile = {
                "entity_id": entity_id,
                "entity_type": group["entity_type"].iloc[0],
                "event_count": len(group),
                "mean_hour": group["hour"].mean(),
                "std_hour": group["hour"].std(),
                "mean_session_duration": pd.to_numeric(group["session_duration"], errors="coerce").mean(),
                "unique_resources": group["resource_accessed"].nunique(),
                "unique_ips": group["source_ip"].nunique(),
                "most_common_resource": group["resource_accessed"].mode().iloc[0] if len(group) > 0 else "",
                "auth_method": group["auth_method"].mode().iloc[0] if len(group) > 0 else "",
            }
            self.entity_profiles[entity_id] = profile

        return self.entity_profiles

    def train(self, df):
        """Train the Isolation Forest on feature-engineered data."""
        print("  [Baseline Profiler] Extracting features...")
        df_feat, feature_cols = self.extract_features(df)

        print("  [Baseline Profiler] Building entity profiles...")
        self.build_entity_profiles(df)

        X = df_feat[feature_cols].values
        X = np.nan_to_num(X)

        print("  [Baseline Profiler] Scaling features...")
        X_scaled = self.scaler.fit_transform(X)

        print("  [Baseline Profiler] Training Isolation Forest...")
        self.isolation_forest = IsolationForest(
            n_estimators=200,
            contamination=0.1,
            random_state=42,
            n_jobs=-1
        )
        self.isolation_forest.fit(X_scaled)

        # Get anomaly scores
        scores = self.isolation_forest.decision_function(X_scaled)
        predictions = self.isolation_forest.predict(X_scaled)

        print(f"  [Baseline Profiler] Training complete.")
        print(f"    Anomalies detected: {(predictions == -1).sum()} / {len(predictions)}")

        return scores, predictions

    def predict(self, df):
        """Predict anomaly scores for new data."""
        df_feat, feature_cols = self.extract_features(df)
        X = df_feat[feature_cols].values
        X = np.nan_to_num(X)
        X_scaled = self.scaler.transform(X)
        scores = self.isolation_forest.decision_function(X_scaled)
        predictions = self.isolation_forest.predict(X_scaled)
        return scores, predictions

    def save(self, path="saved_models"):
        os.makedirs(path, exist_ok=True)
        joblib.dump(self.isolation_forest, os.path.join(path, "isolation_forest.joblib"))
        joblib.dump(self.scaler, os.path.join(path, "baseline_scaler.joblib"))
        joblib.dump(self.le_entity_type, os.path.join(path, "le_entity_type.joblib"))
        joblib.dump(self.le_auth, os.path.join(path, "le_auth.joblib"))
        joblib.dump(self.le_resource, os.path.join(path, "le_resource.joblib"))
        joblib.dump(self.entity_profiles, os.path.join(path, "entity_profiles.joblib"))
        print(f"  [Baseline Profiler] Models saved to {path}/")

    def load(self, path="saved_models"):
        self.isolation_forest = joblib.load(os.path.join(path, "isolation_forest.joblib"))
        self.scaler = joblib.load(os.path.join(path, "baseline_scaler.joblib"))
        self.le_entity_type = joblib.load(os.path.join(path, "le_entity_type.joblib"))
        self.le_auth = joblib.load(os.path.join(path, "le_auth.joblib"))
        self.le_resource = joblib.load(os.path.join(path, "le_resource.joblib"))
        self.entity_profiles = joblib.load(os.path.join(path, "entity_profiles.joblib"))
