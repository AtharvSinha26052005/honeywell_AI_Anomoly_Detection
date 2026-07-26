"""
Explainability Layer
=====================
Provides human-readable explanations for each anomaly alert using
feature attribution (tree-based feature importance and rule extraction).
"""

import numpy as np
import pandas as pd
import json
import os


class ExplainabilityEngine:
    """Generate human-readable explanations for anomaly alerts."""

    FEATURE_DESCRIPTIONS = {
        "hour": "Access time (hour of day)",
        "day_of_week": "Day of the week",
        "is_weekend": "Weekend access",
        "is_night": "Night-time access",
        "lat": "Geographic latitude",
        "lon": "Geographic longitude",
        "session_duration": "Session duration",
        "cmd_count": "Number of commands executed",
        "has_suspicious_cmd": "Suspicious commands detected",
        "is_password_auth": "Password-based authentication",
        "is_failed_auth": "Failed authentication attempt",
        "is_sensitive_resource": "Sensitive resource accessed",
        "is_iot_device": "IoT device fingerprint",
        "entity_type_enc": "Entity type",
        "ip_hash": "Source IP pattern",
    }

    ANOMALY_EXPLANATIONS = {
        "brute_force": {
            "description": "Rapid repeated authentication attempts detected",
            "key_indicators": ["Multiple failed login attempts", "Short time window", "Same source IP"],
            "risk_factors": ["Credential compromise", "Account lockout potential"],
        },
        "impossible_travel": {
            "description": "Login from geographically distant locations in impossibly short time",
            "key_indicators": ["Large geographic distance", "Short time gap between logins", "Different source IPs"],
            "risk_factors": ["Credential sharing", "VPN abuse", "Account compromise"],
        },
        "credential_stuffing": {
            "description": "Many accounts targeted from few source IPs with high failure rate",
            "key_indicators": ["Multiple target accounts", "Few source IPs", "High failure rate"],
            "risk_factors": ["Leaked credential database", "Automated attack tools"],
        },
        "lateral_movement": {
            "description": "Entity accessing unusual breadth of resources not in baseline profile",
            "key_indicators": ["Unusual resource access pattern", "Privilege escalation commands", "Broad resource sweep"],
            "risk_factors": ["Compromised credentials", "Internal threat actor", "Malware propagation"],
        },
        "device_spoofing": {
            "description": "Device reappearing with mismatched fingerprint (OS/MAC changed)",
            "key_indicators": ["Device fingerprint mismatch", "OS version change", "MAC address change"],
            "risk_factors": ["Cloned device identity", "Man-in-the-middle attack"],
        },
        "low_and_slow": {
            "description": "Gradual off-hours data access building up over time",
            "key_indicators": ["Off-hours access", "Data export resources", "Gradual increase pattern"],
            "risk_factors": ["Data exfiltration", "Insider threat", "APT activity"],
        },
        "insider_drift": {
            "description": "Entity gradually expanding resource access beyond baseline",
            "key_indicators": ["Slowly expanding resource footprint", "New resource categories", "Privilege creep"],
            "risk_factors": ["Insider threat", "Role creep", "Potential policy violation"],
        },
    }

    def __init__(self, classifier=None):
        self.classifier = classifier

    def explain_alert(self, row, predicted_label, confidence, feature_values=None, feature_names=None):
        """Generate a human-readable explanation for a single alert."""
        explanation = {
            "entity_id": row.get("entity_id", "unknown"),
            "timestamp": str(row.get("timestamp", "")),
            "predicted_anomaly_type": predicted_label,
            "confidence": float(confidence),
            "risk_score": self._calculate_risk_score(predicted_label, confidence, row),
        }

        # Get anomaly-specific explanation
        if predicted_label in self.ANOMALY_EXPLANATIONS:
            anomaly_info = self.ANOMALY_EXPLANATIONS[predicted_label]
            explanation["description"] = anomaly_info["description"]
            explanation["key_indicators"] = anomaly_info["key_indicators"]
            explanation["risk_factors"] = anomaly_info["risk_factors"]
        else:
            explanation["description"] = "Normal access pattern"
            explanation["key_indicators"] = []
            explanation["risk_factors"] = []

        # Generate feature-based contributing factors
        explanation["contributing_factors"] = self._get_contributing_factors(row, predicted_label)

        # Human-readable summary
        explanation["summary"] = self._generate_summary(explanation, row)

        return explanation

    def _calculate_risk_score(self, predicted_label, confidence, row):
        """Calculate a 0-100 risk score based on anomaly type and confidence."""
        base_scores = {
            "normal": 5,
            "brute_force": 85,
            "impossible_travel": 80,
            "credential_stuffing": 90,
            "lateral_movement": 88,
            "device_spoofing": 75,
            "low_and_slow": 70,
            "insider_drift": 45,
        }
        base = base_scores.get(predicted_label, 50)

        # Adjust by confidence
        score = base * confidence

        # Bonus for sensitive resources
        resource = str(row.get("resource_accessed", ""))
        if any(s in resource for s in ["admin", "keys", "passwd", "ssh", "config", "export"]):
            score = min(100, score + 10)

        # Bonus for night-time
        try:
            ts = pd.to_datetime(row.get("timestamp", ""))
            if ts.hour < 6 or ts.hour > 22:
                score = min(100, score + 5)
        except:
            pass

        return round(min(100, max(0, score)), 1)

    def _get_contributing_factors(self, row, predicted_label):
        """Extract contributing factors from the event data."""
        factors = []

        # Time-based
        try:
            ts = pd.to_datetime(row.get("timestamp", ""))
            if ts.hour < 6 or ts.hour > 22:
                factors.append("🕐 Access during off-hours (unusual time)")
            if ts.weekday() >= 5:
                factors.append("📅 Weekend access detected")
        except:
            pass

        # Auth-based
        if row.get("auth_method") == "password":
            factors.append("🔑 Password-based authentication (less secure)")

        cmd_seq = str(row.get("command_sequence", ""))
        if "auth_attempt_failed" in cmd_seq:
            factors.append("❌ Failed authentication attempt")

        # Resource-based
        resource = str(row.get("resource_accessed", ""))
        if "admin" in resource or "keys" in resource:
            factors.append(f"⚠️ Sensitive resource accessed: {resource}")
        if "export" in resource or "download" in cmd_seq:
            factors.append("📤 Data export/download activity")

        # Geo-based
        if predicted_label == "impossible_travel":
            factors.append(f"🌍 Geographic anomaly: {row.get('geo_location', 'N/A')}")

        # Command-based
        suspicious = {"sudo", "ssh", "scp", "rsync", "wget", "chmod"}
        try:
            cmds = json.loads(cmd_seq) if isinstance(cmd_seq, str) and cmd_seq.startswith("[") else []
            found = set(cmds) & suspicious
            if found:
                factors.append(f"🔧 Suspicious commands: {', '.join(found)}")
        except:
            pass

        # Session duration
        duration = float(row.get("session_duration", 0))
        if duration < 5:
            factors.append("⚡ Very short session (possible automated attack)")
        elif duration > 600:
            factors.append("⏱️ Unusually long session duration")

        # Device fingerprint
        if predicted_label == "device_spoofing":
            factors.append("🖥️ Device fingerprint mismatch detected")

        if not factors:
            factors.append("✅ No significant risk factors identified")

        return factors

    def _generate_summary(self, explanation, row):
        """Generate a one-line human-readable summary."""
        entity = explanation["entity_id"]
        anomaly = explanation["predicted_anomaly_type"]
        risk = explanation["risk_score"]
        conf = explanation["confidence"]

        if anomaly == "normal":
            return f"Entity {entity}: Normal access pattern (Risk: {risk}/100)"

        return (
            f"🚨 Entity {entity}: {explanation['description']} "
            f"(Type: {anomaly}, Risk: {risk}/100, Confidence: {conf:.0%})"
        )

    def batch_explain(self, df, pred_labels, confidences):
        """Generate explanations for a batch of events."""
        explanations = []
        for i in range(len(df)):
            row = df.iloc[i].to_dict()
            exp = self.explain_alert(row, pred_labels[i], confidences[i])
            explanations.append(exp)
        return explanations
