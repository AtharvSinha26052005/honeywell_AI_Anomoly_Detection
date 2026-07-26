"""
Anomaly Classifier
===================
Multi-class Random Forest classifier that categorizes anomalies into
specific attack types (brute force, impossible travel, credential stuffing,
lateral movement, device spoofing, low-and-slow, insider drift).
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib
import json
import os


class AnomalyClassifier:
    """Multi-class anomaly type classifier."""

    ATTACK_TYPES = [
        "normal", "brute_force", "impossible_travel", "credential_stuffing",
        "lateral_movement", "device_spoofing", "low_and_slow", "insider_drift"
    ]

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = []

    def engineer_features(self, df):
        """Engineer features for classification."""
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        df["is_night"] = ((df["hour"] < 6) | (df["hour"] > 22)).astype(int)

        # Geo parsing
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

        # Session duration
        df["session_duration"] = pd.to_numeric(df["session_duration"], errors="coerce").fillna(0)

        # Command count and complexity
        df["cmd_count"] = df["command_sequence"].apply(
            lambda x: len(json.loads(x)) if isinstance(x, str) else 0
        )

        # Check for suspicious commands
        suspicious_cmds = {"sudo", "ssh", "scp", "rsync", "wget", "chmod", "download", "compress", "encrypt", "transfer"}
        df["has_suspicious_cmd"] = df["command_sequence"].apply(
            lambda x: int(bool(set(json.loads(x)) & suspicious_cmds)) if isinstance(x, str) else 0
        )

        # Auth-related features
        df["is_password_auth"] = (df["auth_method"] == "password").astype(int)
        df["is_failed_auth"] = df["command_sequence"].apply(
            lambda x: int("auth_attempt_failed" in x) if isinstance(x, str) else 0
        )

        # Resource-related features
        df["is_sensitive_resource"] = df["resource_accessed"].apply(
            lambda x: int(any(s in str(x) for s in ["admin", "keys", "passwd", "ssh", "config", "export", "deploy"]))
        )

        # Device fingerprint mismatch (simplified)
        df["fp_os"] = df["device_fingerprint"].apply(
            lambda x: json.loads(x).get("os", "Unknown") if isinstance(x, str) else "Unknown"
        )
        df["is_iot_device"] = df["fp_os"].apply(
            lambda x: int("IoT" in str(x) or "FW" in str(x))
        )

        # Entity type encoding
        entity_type_map = {"user": 0, "service_account": 1, "edge_device": 2}
        df["entity_type_enc"] = df["entity_type"].map(entity_type_map).fillna(0)

        # IP frequency (simplified as hash-based feature)
        df["ip_hash"] = df["source_ip"].apply(lambda x: hash(x) % 1000)

        self.feature_names = [
            "hour", "day_of_week", "is_weekend", "is_night",
            "lat", "lon", "session_duration", "cmd_count",
            "has_suspicious_cmd", "is_password_auth", "is_failed_auth",
            "is_sensitive_resource", "is_iot_device", "entity_type_enc",
            "ip_hash"
        ]

        return df, self.feature_names

    def train(self, df):
        """Train the multi-class classifier."""
        print("  [Anomaly Classifier] Engineering features...")
        df_feat, feature_cols = self.engineer_features(df)

        X = df_feat[feature_cols].values
        X = np.nan_to_num(X)

        # Encode labels
        y = self.label_encoder.fit_transform(df_feat["label"])

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Scale
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        print("  [Anomaly Classifier] Training Random Forest...")
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        accuracy = (y_pred == y_test).mean()

        print(f"\n  [Anomaly Classifier] Test Accuracy: {accuracy:.4f}")
        print("\n  Classification Report:")
        report = classification_report(
            y_test, y_pred,
            target_names=self.label_encoder.classes_,
            zero_division=0
        )
        print(report)

        # Feature importance
        importances = self.model.feature_importances_
        importance_df = pd.DataFrame({
            "feature": feature_cols,
            "importance": importances
        }).sort_values("importance", ascending=False)
        print("  Top Features:")
        for _, row in importance_df.head(5).iterrows():
            print(f"    {row['feature']:25s}: {row['importance']:.4f}")

        return accuracy, report

    def predict(self, df):
        """Predict anomaly types and probabilities."""
        df_feat, feature_cols = self.engineer_features(df)
        X = df_feat[feature_cols].values
        X = np.nan_to_num(X)
        X_scaled = self.scaler.transform(X)

        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)
        pred_labels = self.label_encoder.inverse_transform(predictions)

        # Confidence = max probability
        confidence = probabilities.max(axis=1)

        return pred_labels, confidence, probabilities

    def save(self, path="saved_models"):
        os.makedirs(path, exist_ok=True)
        joblib.dump(self.model, os.path.join(path, "anomaly_classifier.joblib"))
        joblib.dump(self.scaler, os.path.join(path, "classifier_scaler.joblib"))
        joblib.dump(self.label_encoder, os.path.join(path, "label_encoder.joblib"))
        joblib.dump(self.feature_names, os.path.join(path, "feature_names.joblib"))
        print(f"  [Anomaly Classifier] Models saved to {path}/")

    def load(self, path="saved_models"):
        self.model = joblib.load(os.path.join(path, "anomaly_classifier.joblib"))
        self.scaler = joblib.load(os.path.join(path, "classifier_scaler.joblib"))
        self.label_encoder = joblib.load(os.path.join(path, "label_encoder.joblib"))
        self.feature_names = joblib.load(os.path.join(path, "feature_names.joblib"))
