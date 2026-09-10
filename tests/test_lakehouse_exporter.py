"""
tests/test_lakehouse_exporter.py — Unit tests for Data Lakehouse Parquet Exporter (Feature 3).
"""
import os
import pandas as pd
import pyarrow.parquet as pq
from fastapi.testclient import TestClient
import batch_exporter
import server

client = TestClient(server.app)

def test_extract_incident_image_metadata():
    records = batch_exporter.extract_incident_image_metadata()
    assert isinstance(records, list)
    if records:
        r = records[0]
        assert "incident_id" in r
        assert "robot_id" in r
        assert "criticality" in r
        assert "has_sensor_frame" in r
        assert "image_size_bytes" in r
        assert "s3_uri" in r

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
    assert meta["s3_analytics_uri"].startswith("s3://robonexus-analytics/")
    assert os.path.exists(meta["minio_storage_path"])

    # Read back parquet file using PyArrow
    table = pq.read_table(meta["file_path"])
    assert table.num_rows >= 1
    assert "event" in table.column_names
    assert "robot_id" in table.column_names
    assert "tenant_id" in table.column_names
    assert "criticality" in table.column_names
    assert "deadline_ms" in table.column_names
    assert "predicted_latency_ms" in table.column_names
    assert "queue_depth" in table.column_names
    assert "incident_id" in table.column_names
    assert "s3_uri" in table.column_names
    assert "has_sensor_frame" in table.column_names
    assert "image_size_bytes" in table.column_names

    # Read back using pandas to ensure PySpark/DataFrame compatibility
    df = pd.read_parquet(meta["file_path"])
    assert len(df) == table.num_rows
    assert not df.empty

def test_export_lakehouse_endpoint():
    resp = client.post("/api/v1/cloud/export/lakehouse")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["format"] == "APACHE_PARQUET"
    assert "file_name" in data
    assert "s3_analytics_uri" in data
    assert data["s3_analytics_uri"].startswith("s3://robonexus-analytics/")

def test_get_lakehouse_export_status():
    client.post("/api/v1/cloud/export/lakehouse")
    resp = client.get("/api/v1/cloud/export/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["latest_export"] is not None
    assert data["total_exports"] >= 1
    assert isinstance(data["export_history"], list)
    assert data["latest_export"]["bucket"] == "robonexus-analytics"
