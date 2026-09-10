"""
tests/test_lakehouse_exporter.py — Unit tests for Data Lakehouse Parquet Exporter.
"""
import os
import pyarrow.parquet as pq
from fastapi.testclient import TestClient
import batch_exporter
import server

client = TestClient(server.app)

def test_export_fleet_telemetry_lakehouse_parquet(tmp_path):
    out_dir = str(tmp_path / "lakehouse")
    meta = batch_exporter.export_fleet_telemetry_lakehouse(
        redis_client=server.redis_client,
        output_dir=out_dir
    )
    assert meta["status"] == "COMPLETED"
    assert meta["format"] == "APACHE_PARQUET"
    assert meta["compression"] == "SNAPPY"
    assert os.path.exists(meta["file_path"])
    assert meta["file_size_bytes"] > 0

    # Read back parquet file using PyArrow
    table = pq.read_table(meta["file_path"])
    assert table.num_rows >= 1
    assert "event" in table.column_names
    assert "robot_id" in table.column_names
    assert "deadline_ms" in table.column_names
    assert "predicted_latency_ms" in table.column_names

def test_export_lakehouse_endpoint():
    resp = client.post("/api/v1/cloud/export/lakehouse")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["format"] == "APACHE_PARQUET"
    assert "file_name" in data

def test_get_lakehouse_export_status():
    # Trigger export first
    client.post("/api/v1/cloud/export/lakehouse")
    resp = client.get("/api/v1/cloud/export/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["latest_export"] is not None
    assert data["total_exports"] >= 1
    assert isinstance(data["export_history"], list)
