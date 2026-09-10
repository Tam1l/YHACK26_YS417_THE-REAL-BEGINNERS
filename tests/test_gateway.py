from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import server


def payload(robot_id="AGV-01", priority=1):
    return {"robot_id": robot_id, "priority": priority, "image_base64": "aGVsbG8="}


def test_authorized_agv_is_queued(monkeypatch):
    redis = MagicMock()
    monkeypatch.setattr(server, "redis_client", redis)
    response = TestClient(server.app).post(
        "/predict", json=payload(), headers={"X-Robot-Token": "agv-token"}
    )
    assert response.status_code == 201
    redis.hset.assert_called_once()
    redis.zadd.assert_called_once()
    redis.lpush.assert_called_once()


def test_token_cannot_impersonate_another_robot():
    response = TestClient(server.app).post(
        "/predict", json=payload(robot_id="DRONE-07", priority=1),
        headers={"X-Robot-Token": "agv-token"},
    )
    assert response.status_code == 403
    assert "Robot ID" in response.json()["detail"]


def test_unknown_token_is_rejected():
    response = TestClient(server.app).post(
        "/predict", json=payload(), headers={"X-Robot-Token": "not-a-token"}
    )
    assert response.status_code == 403
