# LLM Master Prompt: RoboNexus Advanced Architecture Implementation

**System Context & Persona:**
You are an expert Cloud & Software Architecture AI assistant. You are working on "RoboNexus," a private AI control plane for robot fleets. 
RoboNexus is NOT a simple YOLO inference API. It is a highly resilient, robotics-aware cloud environment where multiple robot fleets (AGVs, Drones, Sweepers) compete for limited AI compute. 

The core architecture uses a FastAPI gateway, Redis sorted-set queues for scheduling (RADS), isolated Python worker pools, MinIO for incident storage, and a Streamlit dashboard for mission control.

**Your Task:**
Implement three advanced architectural features designed to prove enterprise-grade scalability, edge-cloud intelligence, and data lakehouse readiness. Ensure structural design patterns (like Strategy or Adapter) are used to keep the API routing decoupled from the ML pipelines and batch processes.

Read the feature requirements below and provide the Python implementation, Redis queries, and integration tests for each.

---

## Feature 1: Predictive Compute Provisioning

**Objective:**
Shift autoscaling from reactive (queue-depth based) to proactive (mission-aware). Fleets should be able to announce high-intensity workloads ahead of time so the control plane can pre-warm worker containers before the queue spikes.

**Implementation Requirements:**
1. Create a new FastAPI endpoint: `POST /api/v1/mission/announce`
2. Accept a payload containing: `fleet_id`, `expected_critical_tasks`, `start_time` (ISO 8601 timestamp), and `duration_seconds`.
3. Update the `autoscaler.py` daemon to evaluate active and upcoming missions alongside the current Redis queue depth.
4. If an upcoming mission requires high compute, scale the worker pool up to the predicted capacity at least 30 seconds prior to `start_time`.
5. Implement a cooldown mechanism to safely scale down after the mission `duration_seconds` expires, provided the Redis queue is empty.
6. Push a `PREDICTIVE_SCALE_UP` event to the Redis event stream for the dashboard.
7. Provide Pytest unit tests simulating a mission announcement and verifying the scaling trigger timeline.

---

## Feature 2: Latency-Aware Edge-Cloud Fallback

**Objective:**
Act as a smart circuit breaker. If the scheduler determines that the requested cloud inference cannot mathematically meet the robot's strict control deadline, it must reject the request instantly rather than wasting compute.

**Implementation Requirements:**
1. Inside the `rads.py` scheduling logic, calculate `predicted_total_latency` = `current_queue_wait_time` + `estimated_inference_time`.
2. Compare this against the `deadline_ms` provided in the robot's request.
3. If `predicted_total_latency` > `deadline_ms`, immediately drop the task from the scheduling queue.
4. Return an HTTP 429 or 503 response with the exact payload: `{"status": "EXECUTE_AT_EDGE", "reason": "deadline_unreachable"}`.
5. Increment an `edge_fallback_count` metric in Redis.
6. Ensure this is logged as a protective system action, not a crash or unhandled exception.
7. Provide a test simulating an overloaded Redis queue that verifies the API immediately returns the fallback instruction.

---

## Feature 3: Data Lakehouse Export for Fleet Analytics

**Objective:**
Create an offline analytics ETL pipeline. We need to export daily system metrics and incident logs into a scalable, batch-processable format to support future predictive demand modeling and analytics.

**Implementation Requirements:**
1. Create a standalone `batch_exporter.py` ETL utility.
2. The script must query Redis for all recorded time-series events (e.g., `TASK_FAILOVER`, `SCALE_UP`, `DEADLINE_MISSED`, `PREDICTIVE_SCALE_UP`).
3. Extract the metadata of all incident images stored in MinIO for the current day.
4. Transform this data into a structured columnar schema. You may use Pandas (or configure it to be PySpark-ready for distributed execution).
5. Save the output as a `.parquet` file.
6. Upload the generated Parquet file back into a dedicated `robonexus-analytics` bucket in MinIO.
7. Ensure the script can be triggered manually via CLI or via a simple cron job for demonstration purposes.

---

**Output Instructions:**
*   Provide the code organized by file (e.g., `server.py` additions, `autoscaler.py`, `rads.py`, `batch_exporter.py`).
*   Include the required Pytest functions.
*   Do not break existing core functionality. Assume the basic Redis queue and MinIO client connections already exist.
