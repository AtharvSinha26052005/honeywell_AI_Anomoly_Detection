"""
Synthetic Access-Log Data Generator
====================================
Generates realistic synthetic cybersecurity access logs with injected attack patterns.
Follows the Honeywell hackathon schema specification.

Behaviour patterns simulated:
  - Normal baseline (benign)
  - Brute force (anomaly)
  - Impossible travel (anomaly)
  - Credential stuffing (anomaly)
  - Lateral movement (anomaly)
  - Device spoofing (anomaly)
  - Low-and-slow exfiltration (anomaly)
  - Insider drift (edge case)
"""

import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
import random
import os
import hashlib
import json

fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

NUM_USERS = 200
NUM_SERVICE_ACCOUNTS = 30
NUM_EDGE_DEVICES = 50
TOTAL_ENTITIES = NUM_USERS + NUM_SERVICE_ACCOUNTS + NUM_EDGE_DEVICES

NORMAL_EVENTS = 45000
BRUTE_FORCE_EVENTS = 800
IMPOSSIBLE_TRAVEL_EVENTS = 400
CREDENTIAL_STUFFING_EVENTS = 600
LATERAL_MOVEMENT_EVENTS = 500
DEVICE_SPOOFING_EVENTS = 300
LOW_AND_SLOW_EVENTS = 700
INSIDER_DRIFT_EVENTS = 400

START_DATE = datetime(2026, 6, 1)
END_DATE = datetime(2026, 7, 25)

RESOURCES = [
    "/api/v1/users", "/api/v1/admin", "/api/v1/data/export",
    "/api/v1/config", "/api/v1/logs", "/api/v1/billing",
    "/api/v1/auth/tokens", "/api/v1/devices/register",
    "/api/v1/network/scan", "/api/v1/firewall/rules",
    "/internal/db/query", "/internal/db/admin",
    "/internal/storage/read", "/internal/storage/write",
    "/internal/keys/rotate", "/internal/deploy/trigger",
    "port:22", "port:3389", "port:443", "port:8080",
    "port:3306", "port:5432", "port:27017", "port:6379",
    "file:/etc/passwd", "file:/var/log/syslog",
    "file:/opt/app/config.yml", "file:/home/admin/.ssh/id_rsa",
    "device:sensor_read", "device:actuator_write",
    "device:firmware_update", "device:config_change",
]

AUTH_METHODS = ["password", "token", "certificate", "biometric", "mfa"]
OS_LIST = ["Windows 11", "Ubuntu 22.04", "macOS 14", "RHEL 9", "IoT-FW-v3.1", "IoT-FW-v2.8"]
PROTOCOLS = ["HTTPS", "SSH", "RDP", "MQTT", "CoAP", "gRPC"]

GEO_LOCATIONS = [
    {"city": "Mumbai", "lat": 19.076, "lon": 72.877, "ip_prefix": "103.21"},
    {"city": "Delhi", "lat": 28.644, "lon": 77.216, "ip_prefix": "103.22"},
    {"city": "Bangalore", "lat": 12.972, "lon": 77.595, "ip_prefix": "103.23"},
    {"city": "New York", "lat": 40.713, "lon": -74.006, "ip_prefix": "198.51"},
    {"city": "London", "lat": 51.507, "lon": -0.128, "ip_prefix": "203.0"},
    {"city": "Tokyo", "lat": 35.682, "lon": 139.692, "ip_prefix": "192.0"},
    {"city": "Singapore", "lat": 1.352, "lon": 103.820, "ip_prefix": "175.45"},
    {"city": "Sydney", "lat": -33.868, "lon": 151.209, "ip_prefix": "202.14"},
    {"city": "Frankfurt", "lat": 50.110, "lon": 8.682, "ip_prefix": "185.12"},
    {"city": "São Paulo", "lat": -23.550, "lon": -46.633, "ip_prefix": "200.17"},
]


# ---------------------------------------------------------------------------
# Entity Generation
# ---------------------------------------------------------------------------

def generate_entities():
    """Create a pool of entities with stable profiles."""
    entities = []

    for i in range(NUM_USERS):
        home_geo = random.choice(GEO_LOCATIONS)
        entities.append({
            "entity_id": f"user_{i:04d}",
            "entity_type": "user",
            "home_geo": home_geo,
            "typical_hours": (random.randint(7, 10), random.randint(17, 20)),
            "typical_resources": random.sample(RESOURCES, k=random.randint(3, 8)),
            "auth_method": random.choice(AUTH_METHODS[:4]),
            "device_fp": {
                "os": random.choice(OS_LIST[:4]),
                "mac": fake.mac_address(),
                "protocol": random.choice(PROTOCOLS[:3]),
            },
        })

    for i in range(NUM_SERVICE_ACCOUNTS):
        home_geo = random.choice(GEO_LOCATIONS)
        entities.append({
            "entity_id": f"svc_{i:04d}",
            "entity_type": "service_account",
            "home_geo": home_geo,
            "typical_hours": (0, 23),  # service accounts run 24/7
            "typical_resources": random.sample(RESOURCES, k=random.randint(2, 5)),
            "auth_method": "certificate",
            "device_fp": {
                "os": random.choice(OS_LIST[:4]),
                "mac": fake.mac_address(),
                "protocol": "gRPC",
            },
        })

    for i in range(NUM_EDGE_DEVICES):
        home_geo = random.choice(GEO_LOCATIONS)
        entities.append({
            "entity_id": f"device_{i:04d}",
            "entity_type": "edge_device",
            "home_geo": home_geo,
            "typical_hours": (0, 23),
            "typical_resources": random.sample(
                [r for r in RESOURCES if r.startswith("device:")], k=min(3, len([r for r in RESOURCES if r.startswith("device:")]))
            ),
            "auth_method": "certificate",
            "device_fp": {
                "os": random.choice(OS_LIST[4:]),
                "mac": fake.mac_address(),
                "protocol": random.choice(["MQTT", "CoAP"]),
            },
        })

    return entities


def random_timestamp(start=START_DATE, end=END_DATE):
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def gen_ip(geo):
    return f"{geo['ip_prefix']}.{random.randint(1,254)}.{random.randint(1,254)}"


# ---------------------------------------------------------------------------
# Normal Baseline Events
# ---------------------------------------------------------------------------

def generate_normal_events(entities, n=NORMAL_EVENTS):
    """Generate benign access events following per-entity habitual patterns."""
    records = []
    for _ in range(n):
        entity = random.choice(entities)
        ts = random_timestamp()
        # Bias timestamp toward typical hours
        hour_start, hour_end = entity["typical_hours"]
        if entity["entity_type"] == "user":
            hour = random.gauss((hour_start + hour_end) / 2, 2)
            hour = int(max(0, min(23, hour)))
            ts = ts.replace(hour=hour, minute=random.randint(0, 59))

        geo = entity["home_geo"]
        # Small chance of travel (legitimate)
        if random.random() < 0.05:
            nearby = [g for g in GEO_LOCATIONS if g != geo]
            geo = random.choice(nearby)

        records.append({
            "entity_id": entity["entity_id"],
            "entity_type": entity["entity_type"],
            "timestamp": ts.isoformat(),
            "source_ip": gen_ip(geo),
            "geo_location": f"{geo['city']}({geo['lat']},{geo['lon']})",
            "resource_accessed": random.choice(entity["typical_resources"]),
            "auth_method": entity["auth_method"],
            "session_duration": max(10, int(random.gauss(300, 120))),
            "command_sequence": json.dumps(random.sample(
                ["ls", "cat", "grep", "curl", "read", "write", "query", "list"], k=random.randint(1, 3)
            )),
            "device_fingerprint": json.dumps(entity["device_fp"]),
            "label": "normal",
        })
    return records


# ---------------------------------------------------------------------------
# Brute Force Events
# ---------------------------------------------------------------------------

def generate_brute_force(entities, n=BRUTE_FORCE_EVENTS):
    """Rapid repeated failed auth attempts from one source in a short window."""
    records = []
    num_attacks = n // 20  # ~20 attempts per attack burst
    for _ in range(num_attacks):
        target = random.choice([e for e in entities if e["entity_type"] == "user"])
        attacker_geo = random.choice(GEO_LOCATIONS)
        attacker_ip = gen_ip(attacker_geo)
        base_ts = random_timestamp()

        for attempt in range(20):
            ts = base_ts + timedelta(seconds=random.randint(1, 60))
            records.append({
                "entity_id": target["entity_id"],
                "entity_type": target["entity_type"],
                "timestamp": ts.isoformat(),
                "source_ip": attacker_ip,
                "geo_location": f"{attacker_geo['city']}({attacker_geo['lat']},{attacker_geo['lon']})",
                "resource_accessed": "/api/v1/auth/tokens",
                "auth_method": "password",
                "session_duration": random.randint(1, 5),
                "command_sequence": json.dumps(["auth_attempt_failed"]),
                "device_fingerprint": json.dumps({
                    "os": random.choice(OS_LIST),
                    "mac": fake.mac_address(),
                    "protocol": "HTTPS",
                }),
                "label": "brute_force",
            })
            if len(records) >= n:
                return records
    return records


# ---------------------------------------------------------------------------
# Impossible Travel Events
# ---------------------------------------------------------------------------

def generate_impossible_travel(entities, n=IMPOSSIBLE_TRAVEL_EVENTS):
    """Same entity logging in from geographically distant locations within implausible time gap."""
    records = []
    num_attacks = n // 2  # pairs
    for _ in range(num_attacks):
        entity = random.choice([e for e in entities if e["entity_type"] == "user"])
        geo1, geo2 = random.sample(GEO_LOCATIONS, 2)
        ts1 = random_timestamp()
        ts2 = ts1 + timedelta(minutes=random.randint(5, 30))  # impossibly fast

        for ts, geo in [(ts1, geo1), (ts2, geo2)]:
            records.append({
                "entity_id": entity["entity_id"],
                "entity_type": entity["entity_type"],
                "timestamp": ts.isoformat(),
                "source_ip": gen_ip(geo),
                "geo_location": f"{geo['city']}({geo['lat']},{geo['lon']})",
                "resource_accessed": random.choice(entity["typical_resources"]),
                "auth_method": entity["auth_method"],
                "session_duration": max(10, int(random.gauss(200, 80))),
                "command_sequence": json.dumps(random.sample(
                    ["ls", "cat", "read", "download"], k=2
                )),
                "device_fingerprint": json.dumps(entity["device_fp"]),
                "label": "impossible_travel",
            })
            if len(records) >= n:
                return records
    return records


# ---------------------------------------------------------------------------
# Credential Stuffing Events
# ---------------------------------------------------------------------------

def generate_credential_stuffing(entities, n=CREDENTIAL_STUFFING_EVENTS):
    """Many entity_ids, few source_ips, high failure rate."""
    records = []
    attacker_ips = [gen_ip(random.choice(GEO_LOCATIONS)) for _ in range(3)]
    attacker_geo = random.choice(GEO_LOCATIONS)
    targets = random.sample([e for e in entities if e["entity_type"] == "user"],
                            k=min(50, len([e for e in entities if e["entity_type"] == "user"])))
    base_ts = random_timestamp()

    for i in range(n):
        target = random.choice(targets)
        ts = base_ts + timedelta(seconds=random.randint(0, 600))
        records.append({
            "entity_id": target["entity_id"],
            "entity_type": target["entity_type"],
            "timestamp": ts.isoformat(),
            "source_ip": random.choice(attacker_ips),
            "geo_location": f"{attacker_geo['city']}({attacker_geo['lat']},{attacker_geo['lon']})",
            "resource_accessed": "/api/v1/auth/tokens",
            "auth_method": "password",
            "session_duration": random.randint(1, 3),
            "command_sequence": json.dumps(["auth_attempt_failed"]),
            "device_fingerprint": json.dumps({
                "os": "Unknown",
                "mac": random.choice(attacker_ips),
                "protocol": "HTTPS",
            }),
            "label": "credential_stuffing",
        })
    return records


# ---------------------------------------------------------------------------
# Lateral Movement Events
# ---------------------------------------------------------------------------

def generate_lateral_movement(entities, n=LATERAL_MOVEMENT_EVENTS):
    """Compromised entity accessing unusual sequence or breadth of resources."""
    records = []
    compromised = random.sample([e for e in entities if e["entity_type"] == "user"], k=5)

    for entity in compromised:
        unusual_resources = [r for r in RESOURCES if r not in entity["typical_resources"]]
        num_events = n // len(compromised)
        base_ts = random_timestamp()

        for i in range(num_events):
            ts = base_ts + timedelta(minutes=random.randint(1, 120))
            records.append({
                "entity_id": entity["entity_id"],
                "entity_type": entity["entity_type"],
                "timestamp": ts.isoformat(),
                "source_ip": gen_ip(entity["home_geo"]),
                "geo_location": f"{entity['home_geo']['city']}({entity['home_geo']['lat']},{entity['home_geo']['lon']})",
                "resource_accessed": random.choice(unusual_resources),
                "auth_method": entity["auth_method"],
                "session_duration": max(5, int(random.gauss(150, 60))),
                "command_sequence": json.dumps(random.sample(
                    ["ls", "cat", "find", "scp", "rsync", "wget", "chmod", "sudo", "ssh"], k=random.randint(3, 6)
                )),
                "device_fingerprint": json.dumps(entity["device_fp"]),
                "label": "lateral_movement",
            })
    return records[:n]


# ---------------------------------------------------------------------------
# Device Spoofing Events
# ---------------------------------------------------------------------------

def generate_device_spoofing(entities, n=DEVICE_SPOOFING_EVENTS):
    """Device reappearing with mismatched fingerprint."""
    records = []
    devices = [e for e in entities if e["entity_type"] == "edge_device"]
    spoofed_devices = random.sample(devices, k=min(10, len(devices)))

    for device in spoofed_devices:
        num_events = n // len(spoofed_devices)
        for i in range(num_events):
            ts = random_timestamp()
            fake_fp = {
                "os": random.choice([o for o in OS_LIST if o != device["device_fp"]["os"]]),
                "mac": fake.mac_address(),
                "protocol": device["device_fp"]["protocol"],
            }
            records.append({
                "entity_id": device["entity_id"],
                "entity_type": device["entity_type"],
                "timestamp": ts.isoformat(),
                "source_ip": gen_ip(random.choice(GEO_LOCATIONS)),
                "geo_location": f"{device['home_geo']['city']}({device['home_geo']['lat']},{device['home_geo']['lon']})",
                "resource_accessed": random.choice(RESOURCES),
                "auth_method": "certificate",
                "session_duration": max(5, int(random.gauss(100, 40))),
                "command_sequence": json.dumps(["device_connect", "firmware_check"]),
                "device_fingerprint": json.dumps(fake_fp),
                "label": "device_spoofing",
            })
    return records[:n]


# ---------------------------------------------------------------------------
# Low-and-Slow Exfiltration Events
# ---------------------------------------------------------------------------

def generate_low_and_slow(entities, n=LOW_AND_SLOW_EVENTS):
    """Gradual, small, off-hours resource access building up over days."""
    records = []
    attackers = random.sample([e for e in entities if e["entity_type"] == "user"], k=5)

    for entity in attackers:
        num_events = n // len(attackers)
        for i in range(num_events):
            # Off-hours: late night / early morning
            ts = random_timestamp()
            hour = random.choice([0, 1, 2, 3, 4, 22, 23])
            ts = ts.replace(hour=hour, minute=random.randint(0, 59))

            records.append({
                "entity_id": entity["entity_id"],
                "entity_type": entity["entity_type"],
                "timestamp": ts.isoformat(),
                "source_ip": gen_ip(entity["home_geo"]),
                "geo_location": f"{entity['home_geo']['city']}({entity['home_geo']['lat']},{entity['home_geo']['lon']})",
                "resource_accessed": random.choice([
                    "/api/v1/data/export", "/internal/storage/read",
                    "/internal/db/query", "file:/opt/app/config.yml"
                ]),
                "auth_method": entity["auth_method"],
                "session_duration": random.randint(30, 180),
                "command_sequence": json.dumps(random.sample(
                    ["read", "download", "compress", "transfer", "encrypt"], k=random.randint(2, 4)
                )),
                "device_fingerprint": json.dumps(entity["device_fp"]),
                "label": "low_and_slow",
            })
    return records[:n]


# ---------------------------------------------------------------------------
# Insider Drift Events (Edge Case)
# ---------------------------------------------------------------------------

def generate_insider_drift(entities, n=INSIDER_DRIFT_EVENTS):
    """Legitimate entity slowly expanding privilege or resource footprint."""
    records = []
    insiders = random.sample([e for e in entities if e["entity_type"] == "user"], k=4)

    for entity in insiders:
        num_events = n // len(insiders)
        all_resources = list(RESOURCES)
        # Gradually expand resource access
        expanding_resources = entity["typical_resources"].copy()

        for i in range(num_events):
            ts = random_timestamp()
            hour_start, hour_end = entity["typical_hours"]
            hour = random.randint(hour_start, hour_end)
            ts = ts.replace(hour=hour)

            # Every few events, add a new resource
            if i % 5 == 0 and len(expanding_resources) < len(all_resources):
                new_res = random.choice([r for r in all_resources if r not in expanding_resources])
                expanding_resources.append(new_res)

            records.append({
                "entity_id": entity["entity_id"],
                "entity_type": entity["entity_type"],
                "timestamp": ts.isoformat(),
                "source_ip": gen_ip(entity["home_geo"]),
                "geo_location": f"{entity['home_geo']['city']}({entity['home_geo']['lat']},{entity['home_geo']['lon']})",
                "resource_accessed": random.choice(expanding_resources),
                "auth_method": entity["auth_method"],
                "session_duration": max(10, int(random.gauss(300, 100))),
                "command_sequence": json.dumps(random.sample(
                    ["ls", "cat", "read", "write", "sudo", "admin_panel"], k=random.randint(2, 4)
                )),
                "device_fingerprint": json.dumps(entity["device_fp"]),
                "label": "insider_drift",
            })
    return records[:n]


# ---------------------------------------------------------------------------
# Main Generator
# ---------------------------------------------------------------------------

def generate_dataset():
    """Generate the full synthetic dataset."""
    print("=" * 60)
    print("  Synthetic Access-Log Data Generator")
    print("=" * 60)

    print("\n[1/9] Generating entity profiles...")
    entities = generate_entities()
    print(f"  -> {len(entities)} entities created "
          f"({NUM_USERS} users, {NUM_SERVICE_ACCOUNTS} service accounts, {NUM_EDGE_DEVICES} edge devices)")

    print("[2/9] Generating normal baseline events...")
    normal = generate_normal_events(entities)
    print(f"  -> {len(normal)} normal events")

    print("[3/9] Generating brute force attacks...")
    brute = generate_brute_force(entities)
    print(f"  -> {len(brute)} brute force events")

    print("[4/9] Generating impossible travel events...")
    travel = generate_impossible_travel(entities)
    print(f"  -> {len(travel)} impossible travel events")

    print("[5/9] Generating credential stuffing events...")
    cred = generate_credential_stuffing(entities)
    print(f"  -> {len(cred)} credential stuffing events")

    print("[6/9] Generating lateral movement events...")
    lateral = generate_lateral_movement(entities)
    print(f"  -> {len(lateral)} lateral movement events")

    print("[7/9] Generating device spoofing events...")
    spoof = generate_device_spoofing(entities)
    print(f"  -> {len(spoof)} device spoofing events")

    print("[8/9] Generating low-and-slow exfiltration events...")
    slow = generate_low_and_slow(entities)
    print(f"  -> {len(slow)} low-and-slow events")

    print("[9/9] Generating insider drift events...")
    drift = generate_insider_drift(entities)
    print(f"  -> {len(drift)} insider drift events")

    # Combine all events
    all_events = normal + brute + travel + cred + lateral + spoof + slow + drift
    df = pd.DataFrame(all_events)

    # Shuffle and sort by timestamp
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Save
    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", "synthetic_access_logs.csv")
    df.to_csv(output_path, index=False)

    # Save entity profiles for dashboard reference
    entity_profiles_path = os.path.join("data", "entity_profiles.json")
    # Convert entity profiles (remove non-serializable items)
    serializable_entities = []
    for e in entities:
        se = e.copy()
        se["home_geo"] = e["home_geo"]["city"]
        serializable_entities.append(se)
    with open(entity_profiles_path, "w") as f:
        json.dump(serializable_entities, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  Dataset saved to: {output_path}")
    print(f"  Entity profiles saved to: {entity_profiles_path}")
    print(f"  Total records: {len(df)}")
    print(f"\n  Label Distribution:")
    for label, count in df["label"].value_counts().items():
        pct = count / len(df) * 100
        print(f"    {label:25s}: {count:6d}  ({pct:5.1f}%)")
    print(f"{'=' * 60}")

    return df, entities


if __name__ == "__main__":
    generate_dataset()
