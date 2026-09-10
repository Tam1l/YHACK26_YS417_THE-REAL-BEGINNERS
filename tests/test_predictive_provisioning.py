import time
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from server import app, redis_client
import autoscaler
from autoscaler import ElasticAutoscaler, parse_mission_time

client = TestClient(app)

def test_parse_mission_time():
    # Numeric epoch
    ts = 1789093800.0
    assert parse_mission_time(ts) == ts
    assert parse_mission_time("1789093800.0") == ts

    # ISO 8601 UTC
    iso_str = "2026-09-11T02:30:00Z"
    parsed = parse_mission_time(iso_str)
    assert isinstance(parsed, float)
    assert parsed > 0

    # With offset
    iso_offset = "2026-09-11T02:30:00+00:00"
    assert parse_mission_time(iso_offset) == parsed

    # Invalid
    with pytest.raises(ValueError):
        parse_mission_time("invalid-date-string")

def test_mission_announcement_endpoint():
    future_time = time.time() + 60.0 # Starts in 60s
    payload = {
        "fleet_id": "FLEET-AGV-LOGISTICS",
        "expected_critical_tasks": 16,
        "start_time": str(future_time),
        "duration_seconds": 90.0
    }
    
    headers = {"X-Robot-Token": "agv-token"}
    response = client.post("/api/v1/mission/announce", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    
    assert data["status"] == "ANNOUNCED"
    assert data["fleet_id"] == "FLEET-AGV-LOGISTICS"
    assert data["target_prewarmed_workers"] == 5
    assert data["expected_critical_tasks"] == 16
    assert "mission_id" in data
    
    # Check stored in Redis
    mission_id = data["mission_id"]
    stored = redis_client.hgetall(f"mission:{mission_id}")
    assert stored["fleet_id"] == "FLEET-AGV-LOGISTICS"
    assert stored["expected_critical_tasks"] == "16"
    assert redis_client.sismember("missions:active", mission_id)

def test_mission_active_list_endpoint():
    res = client.get("/api/v1/mission/active")
    assert res.status_code == 200
    data = res.json()
    assert "active_missions" in data
    assert isinstance(data["active_missions"], list)

def test_proactive_scaling_trigger_30s_window():
    """
    Verifies that when a mission start time is within 30 seconds,
    the autoscaler pre-warms workers to the target capacity.
    """
    now = time.time()
    # Announce mission starting in 15 seconds (within 30s pre-warm window)
    start_ts = now + 15.0
    payload = {
        "fleet_id": "FLEET-DRONE-PATROL",
        "expected_critical_tasks": 8,
        "start_time": str(start_ts),
        "duration_seconds": 30.0
    }
    headers = {"X-Robot-Token": "drone-token"}
    res = client.post("/api/v1/mission/announce", json=payload, headers=headers)
    assert res.status_code == 201
    m_data = res.json()
    mission_id = m_data["mission_id"]

    # Target workers for 8 tasks is 4
    assert m_data["target_prewarmed_workers"] == 4

    # Run check_scheduled_missions on autoscaler
    scaler = ElasticAutoscaler()
    active = scaler.check_scheduled_missions(now)
    
    # Assert mission was detected in the pre-warming window
    matched = [m for m in active if m.get("mission_id") == mission_id]
    assert len(matched) == 1
    
    # Check that workers were pre-warmed up to target
    current_workers = autoscaler.MIN_WORKERS + len(scaler.active_scaled_workers)
    assert current_workers >= 4

    # Check that PREDICTIVE_SCALE_UP was logged
    events = redis_client.lrange("cloud:autoscaler:events", 0, 10)
    predictive_events = [e for e in events if "PREDICTIVE_SCALE_UP" in e]
    assert len(predictive_events) > 0

    # Clean up test mission
    redis_client.srem("missions:active", mission_id)
    redis_client.delete(f"mission:{mission_id}")
