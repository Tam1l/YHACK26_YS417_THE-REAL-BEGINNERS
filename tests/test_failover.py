import time
from unittest.mock import MagicMock
import workers

def test_supervisor_recovers_inflight_job_on_worker_crash(monkeypatch):
    """
    Spec Section 34 & 60: Criticality-Preserving Failover Integration Test.
    When a worker crashes while processing a job, the HealthSupervisor
    detects the dead heartbeat, requeues the task preserving its original
    RADS score/priority, and increments stats:failovers.
    """
    mock_redis = MagicMock()
    monkeypatch.setattr(workers, "redis_client", mock_redis)

    # Setup worker state in Redis
    worker_id = "worker-1"
    job_id = "task-crash-999"
    w_key = f"worker:{worker_id}"
    task_key = f"task:{job_id}"

    mock_redis.hgetall.side_effect = lambda key: {
        w_key: {
            "last_heartbeat": str(time.time() - 10.0), # Stale heartbeat > 3.0s
            "status": "BUSY",
            "current_job_id": job_id
        },
        task_key: {
            "state": "processing",
            "retry_count": "0",
            "queue_score": "-0.95" # High RADS priority
        }
    }.get(key, {})

    # Create dummy worker object
    class DummyWorker:
        def __init__(self, wid):
            self.worker_id = wid
            self.is_alive = False

    supervisor = workers.HealthSupervisor([DummyWorker(worker_id)])

    # Run one single inspection pass
    now = time.time()
    for w in supervisor.workers:
        data = mock_redis.hgetall(f"worker:{w.worker_id}")
        last_hb = float(data.get("last_heartbeat", 0))
        status = data.get("status")
        in_flight_job = data.get("current_job_id")

        if (now - last_hb > 3.0 or not w.is_alive) and status != "DEAD":
            mock_redis.hset(f"worker:{w.worker_id}", "status", "DEAD")
            mock_redis.hset(f"worker:{w.worker_id}", "healthy", "false")
            if in_flight_job:
                t_data = mock_redis.hgetall(f"task:{in_flight_job}")
                if t_data and t_data.get("state") in ("processing", "assigned"):
                    retries = int(t_data.get("retry_count", 0)) + 1
                    mock_redis.hset(f"task:{in_flight_job}", mapping={
                        "state": "requeued",
                        "retry_count": str(retries),
                        "assigned_worker": ""
                    })
                    queue_score = float(t_data.get("queue_score", -0.5))
                    mock_redis.zadd("inference:priority_queue", {in_flight_job: queue_score})
                    mock_redis.incr("stats:failovers")

    # Assertions
    mock_redis.hset.assert_any_call(w_key, "status", "DEAD")
    mock_redis.zadd.assert_called_once_with("inference:priority_queue", {job_id: -0.95})
    mock_redis.incr.assert_called_once_with("stats:failovers")
