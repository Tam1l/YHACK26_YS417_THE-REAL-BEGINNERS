from fastapi.testclient import TestClient
import server

client = TestClient(server.app)
PAYLOAD = {"robot_id": "SWEEPER-12", "priority": 1, "image_base64": "aGVsbG8="}

def test_low_tier_robot_cannot_spoof_critical_priority():
    response = client.post("/predict", json=PAYLOAD, headers={"X-Robot-Token": "sweeper-token"})
    assert response.status_code == 403
