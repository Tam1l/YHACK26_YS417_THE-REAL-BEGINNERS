import os
import time
import json
import threading
from typing import List, Dict, Optional
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

SCALE_UP_THRESHOLD = int(os.getenv("SCALE_UP_THRESHOLD", "3")) # Queue tasks to trigger scale-up
SCALE_DOWN_COOLDOWN_SEC = float(os.getenv("SCALE_DOWN_COOLDOWN", "6.0"))
MIN_WORKERS = 2
MAX_WORKERS = 5

try:
    r_client = redis.StrictRedis(
        host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True, socket_timeout=1.5
    )
except Exception:
    r_client = None

class ElasticAutoscaler(threading.Thread):
    """
    RoboNexus Cloud Dynamic Elastic Autoscaler.
    Monitors queue depth and latency pressure to provision/de-provision
    auxiliary AI workers elastically.
    """
    def __init__(self, worker_factory=None, supervisor=None):
        super().__init__(name="ElasticAutoscaler", daemon=True)
        self.worker_factory = worker_factory
        self.supervisor = supervisor
        self.running = True
        self.active_scaled_workers: Dict[str, any] = {}
        self.idle_since: Optional[float] = None
        self.last_action_ts = time.time()
        
    def log_event(self, message: str, event_type: str = "INFO"):
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] [{event_type}] {message}"
        print(f"[AUTOSCALER] {entry}")
        if r_client:
            try:
                r_client.lpush("cloud:autoscaler:events", entry)
                r_client.ltrim("cloud:autoscaler:events", 0, 49)
                r_client.hset("cloud:autoscaler:status", "last_event", entry)
            except Exception:
                pass

    def get_queue_depth(self) -> int:
        if not r_client:
            return 0
        try:
            return int(r_client.zcard("queue:tasks") or 0)
        except Exception:
            return 0

    def update_state(self, scaling_state: str, queue_depth: int):
        if not r_client:
            return
        total_workers = MIN_WORKERS + len(self.active_scaled_workers)
        try:
            r_client.hset("cloud:autoscaler:status", mapping={
                "state": scaling_state,
                "current_workers": str(total_workers),
                "min_workers": str(MIN_WORKERS),
                "max_workers": str(MAX_WORKERS),
                "scaled_workers_count": str(len(self.active_scaled_workers)),
                "queue_depth": str(queue_depth),
                "last_poll_ts": str(time.time()),
                "policy": "KEDA-style Queue Depth Metric"
            })
        except Exception:
            pass

    def scale_up(self, queue_depth: int):
        total_workers = MIN_WORKERS + len(self.active_scaled_workers)
        if total_workers >= MAX_WORKERS:
            return
            
        next_worker_id = f"worker-{total_workers + 1}"
        self.log_event(
            f"Queue surge ({queue_depth} tasks >= {SCALE_UP_THRESHOLD}). Provisioning elastic {next_worker_id}!",
            "SCALE_UP"
        )
        
        if self.worker_factory:
            worker_instance = self.worker_factory(next_worker_id)
            worker_instance.start()
            self.active_scaled_workers[next_worker_id] = worker_instance
            if self.supervisor and hasattr(self.supervisor, "workers"):
                self.supervisor.workers.append(worker_instance)
        else:
            # Standalone mode: record scaled worker intent in Redis
            self.active_scaled_workers[next_worker_id] = time.time()
            if r_client:
                r_client.hset(f"worker:{next_worker_id}", mapping={
                    "worker_id": next_worker_id,
                    "status": "IDLE",
                    "healthy": "true",
                    "type": "ELASTIC_DYNAMIC",
                    "last_heartbeat": str(time.time())
                })
                
        self.last_action_ts = time.time()
        self.idle_since = None
        self.update_state("SCALED_UP", queue_depth)

    def scale_down(self):
        if not self.active_scaled_workers:
            return
            
        # Target the highest numbered worker for de-provisioning
        target_id = sorted(self.active_scaled_workers.keys())[-1]
        worker_instance = self.active_scaled_workers.pop(target_id)
        
        self.log_event(
            f"Queue idle for >{SCALE_DOWN_COOLDOWN_SEC}s. De-provisioning {target_id} to conserve compute.",
            "SCALE_DOWN"
        )
        
        if hasattr(worker_instance, "stop"):
            worker_instance.stop()
        elif hasattr(worker_instance, "is_alive"):
            worker_instance.is_alive = False
            
        if self.supervisor and hasattr(self.supervisor, "workers"):
            self.supervisor.workers = [w for w in self.supervisor.workers if getattr(w, "worker_id", "") != target_id]
            
        if r_client:
            try:
                r_client.delete(f"worker:{target_id}")
            except Exception:
                pass
                
        self.last_action_ts = time.time()
        self.update_state("SCALED_DOWN", 0)

    def run(self):
        print(f"[+] Elastic Autoscaler daemon started (Threshold: {SCALE_UP_THRESHOLD} tasks | Max: {MAX_WORKERS} workers)")
        self.log_event("Autoscaler controller initialized and operational.", "INIT")
        
        while self.running:
            time.sleep(0.1)
            q_depth = self.get_queue_depth()
            total_workers = MIN_WORKERS + len(self.active_scaled_workers)
            
            # Scale-up evaluation
            if q_depth >= SCALE_UP_THRESHOLD and total_workers < MAX_WORKERS:
                self.scale_up(q_depth)
                continue
                
            # Scale-down evaluation
            if q_depth == 0 and len(self.active_scaled_workers) > 0:
                now = time.time()
                if self.idle_since is None:
                    self.idle_since = now
                elif (now - self.idle_since) >= SCALE_DOWN_COOLDOWN_SEC:
                    self.scale_down()
                    self.idle_since = None
            else:
                self.idle_since = None
                
            self.update_state("STABLE", q_depth)

def main():
    scaler = ElasticAutoscaler()
    scaler.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scaler.running = False
        print("\nStopping Elastic Autoscaler.")

if __name__ == "__main__":
    main()
