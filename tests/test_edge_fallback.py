"""
tests/test_edge_fallback.py — Unit tests for Latency-Aware Edge-Cloud Fallback.
"""
import pytest
from fastapi.testclient import TestClient
import rads
import server

client = TestClient(server.app)

DUMMY_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

def test_check_edge_fallback_math():
    # 0 queue depth, deadline 100ms -> predicted total ~ 26ms <= 100ms -> no fallback
    res = rads.check_edge_fallback(queue_depth=0, deadline_ms=100.0, active_workers=2, est_inference_ms=22.0)
    assert res["should_fallback"] is False
    assert res["status"] == "PROCESS_IN_CLOUD"

    # Queue depth = 10 (5 waiting per worker), est wait = 110ms + 22ms + 4ms = 136ms > 50ms deadline -> fallback!
    res_fallback = rads.check_edge_fallback(queue_depth=10, deadline_ms=50.0, active_workers=2, est_inference_ms=22.0)
    assert res_fallback["should_fallback"] is True
    assert res_fallback["status"] == "EXECUTE_AT_EDGE"
    assert res_fallback["reason"] == "deadline_unreachable"
    assert res_fallback["predicted_total_latency_ms"] >= 136.0

def test_inference_rejects_unreachable_deadline_with_edge_fallback():
    # Submit task with aggressive 12ms deadline (est inference alone is 22ms)
    resp = client.post(
        "/api/v1/inference",
        headers={"X-Robot-Token": "agv-token"},
        json={
            "robot_id": "AGV-01",
            "task_type": "object_detection",
            "criticality": "CRITICAL",
            "deadline_ms": 12.0,
            "image_base64": DUMMY_B64
        }
    )
    assert resp.status_code == 429
    assert resp.headers.get("x-robonexus-action") == "EXECUTE_AT_EDGE"
    data = resp.json()
    assert data["status"] == "EXECUTE_AT_EDGE"
    assert data["reason"] == "deadline_unreachable"
    assert data["deadline_ms"] == 12.0

def test_demo_edge_fallback_endpoint():
    resp = client.post("/api/v1/cloud/demo_edge_fallback")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "EXECUTE_AT_EDGE"
    assert data["action"] == "PROTECTIVE_FALLBACK_TRIGGERED"
    assert "Onboard edge model" in data["message"]
