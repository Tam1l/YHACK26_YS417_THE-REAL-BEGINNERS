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

from datetime import datetime, timezone

def parse_mission_time(time_val) -> float:
    """Parses ISO 8601 string or numeric unix epoch timestamp to float epoch seconds."""
    if isinstance(time_val, (int, float)):
        return float(time_val)
    if isinstance(time_val, str):
        try:
            return float(time_val)
        except ValueError:
            pass
        try:
            cleaned = time_val.strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            return dt.timestamp()
        except Exception as e:
            raise ValueError(f"Invalid timestamp format '{time_val}': {e}")
    raise ValueError(f"Unsupported timestamp type: {type(time_val)}")

class ElasticAutoscaler(threading.Thread):
    """
    RoboNexus Cloud Dynamic Elastic Autoscaler.
    Monitors queue depth and proactively evaluates scheduled missions
    to provision/de-provision auxiliary AI workers elastically.
    """
    def __init__(self, worker_factory=None, supervisor=None):
        super().__init__(name="ElasticAutoscaler", daemon=True)
        self.worker_factory = worker_factory
        self.supervisor = supervisor
        self.running = True
        self.active_scaled_workers: Dict[str, any] = {}
        self.idle_since: Optional[float] = None
        self.last_action_ts = time.time()
        self.active_mission_id: Optional[str] = None
        
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

    def update_state(self, scaling_state: str, queue_depth: int, mission_id: Optional[str] = None):
        if not r_client:
            return
        total_workers = MIN_WORKERS + len(self.active_scaled_workers)
        policy_str = f"Predictive Pre-Warm (Mission {mission_id})" if mission_id else "KEDA-style Queue Depth Metric"
        try:
            r_client.hset("cloud:autoscaler:status", mapping={
                "state": scaling_state,
                "current_workers": str(total_workers),
                "min_workers": str(MIN_WORKERS),
                "max_workers": str(MAX_WORKERS),
                "scaled_workers_count": str(len(self.active_scaled_workers)),
                "queue_depth": str(queue_depth),
                "active_mission_id": str(mission_id or ""),
                "last_poll_ts": str(time.time()),
                "policy": policy_str
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

    def scale_up_proactive(self, target_workers: int, mission_info: Dict):
        """Pre-warms compute 30s ahead of an announced high-compute mission."""
        total_workers = MIN_WORKERS + len(self.active_scaled_workers)
        if total_workers >= MAX_WORKERS or total_workers >= target_workers:
            return
            
        next_worker_id = f"worker-{total_workers + 1}"
        fleet_id = mission_info.get("fleet_id", "FLEET-ROBOT")
        mission_id = mission_info.get("mission_id", "MSN-UNKNOWN")
        expected_tasks = mission_info.get("expected_critical_tasks", "10")
        
        self.log_event(
            f"Proactive pre-warm for fleet '{fleet_id}' mission {mission_id} (expected {expected_tasks} tasks). Scaling {next_worker_id} ahead of load!",
            "PREDICTIVE_SCALE_UP"
        )
        
        if self.worker_factory:
            worker_instance = self.worker_factory(next_worker_id)
            worker_instance.start()
            self.active_scaled_workers[next_worker_id] = worker_instance
            if self.supervisor and hasattr(self.supervisor, "workers"):
                self.supervisor.workers.append(worker_instance)
        else:
            self.active_scaled_workers[next_worker_id] = time.time()
            if r_client:
                r_client.hset(f"worker:{next_worker_id}", mapping={
                    "worker_id": next_worker_id,
                    "status": "IDLE",
                    "healthy": "true",
                    "type": "PREDICTIVE_DYNAMIC",
                    "mission_id": mission_id,
                    "last_heartbeat": str(time.time())
                })
                
        self.last_action_ts = time.time()
        self.idle_since = None
        new_total = MIN_WORKERS + len(self.active_scaled_workers)
        self.update_state("PREDICTIVE_SCALED_UP", self.get_queue_depth(), mission_id=mission_id)
        if r_client:
            try:
                r_client.incr("stats:predictive_scale_ups")
            except Exception:
                pass

    def scale_down(self):
        if not self.active_scaled_workers:
            return
            
        # Target the highest numbered worker for de-provisioning
        target_id = sorted(self.active_scaled_workers.keys())[-1]
        worker_instance = self.active_scaled_workers.pop(target_id)
        
        self.log_event(
            f"Compute cooldown elapsed (>{SCALE_DOWN_COOLDOWN_SEC}s idle). De-provisioning {target_id} to conserve compute.",
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

    def check_scheduled_missions(self, now: float) -> List[Dict]:
        """
        Evaluates active and upcoming missions in Redis.
        Triggers proactive pre-warming 30 seconds prior to start_time.
        Returns list of currently active or pre-warming missions.
        """
        if not r_client:
            return []
            
        active_missions = []
        try:
            mission_ids = r_client.smembers("missions:active") or set()
            for m_id in list(mission_ids):
                m_data = r_client.hgetall(f"mission:{m_id}")
                if not m_data:
                    r_client.srem("missions:active", m_id)
                    continue
                    
                start_ts = float(m_data.get("start_time_ts", 0))
                end_ts = float(m_data.get("end_time_ts", 0))
                target_workers = int(m_data.get("target_workers", 4))
                
                # Check if mission has expired
                if now > end_ts:
                    r_client.hset(f"mission:{m_id}", "status", "COMPLETED")
                    r_client.srem("missions:active", m_id)
                    self.log_event(
                        f"Fleet '{m_data.get('fleet_id')}' mission {m_id} completed. Safe cooldown window initiated.",
                        "MISSION_COMPLETED"
                    )
                    if self.active_mission_id == m_id:
                        self.active_mission_id = None
                    continue
                    
                lead_time = start_ts - now
                
                # Check if we are within the 30-second pre-warming window or mission is actively running
                if lead_time <= 30.0 and now <= end_ts:
                    active_missions.append(m_data)
                    self.active_mission_id = m_id
                    
                    status_str = "ACTIVE" if now >= start_ts else "PRE_WARMING"
                    if m_data.get("status") != status_str:
                        r_client.hset(f"mission:{m_id}", "status", status_str)
                        
                    current_total = MIN_WORKERS + len(self.active_scaled_workers)
                    if current_total < target_workers:
                        needed = target_workers - current_total
                        for _ in range(needed):
                            self.scale_up_proactive(target_workers, m_data)
                            
        except Exception as e:
            print(f"[AUTOSCALER ERROR] Failed checking missions: {e}")
            
        return active_missions

    def run(self):
        print(f"[+] Elastic Autoscaler daemon started (Threshold: {SCALE_UP_THRESHOLD} tasks | Max: {MAX_WORKERS} workers | Predictive Window: 30s)")
        self.log_event("Autoscaler controller initialized and operational with Predictive Provisioning.", "INIT")
        
        while self.running:
            time.sleep(0.1)
            now = time.time()
            q_depth = self.get_queue_depth()
            total_workers = MIN_WORKERS + len(self.active_scaled_workers)
            
            # 1. Evaluate scheduled/active missions proactively
            active_missions = self.check_scheduled_missions(now)
            
            # 2. Reactive Scale-Up evaluation (queue depth surge)
            if q_depth >= SCALE_UP_THRESHOLD and total_workers < MAX_WORKERS:
                self.scale_up(q_depth)
                continue
                
            # 3. Cooldown & Scale-down evaluation:
            # ONLY scale down if queue is empty AND no active/pre-warming missions exist!
            if q_depth == 0 and len(self.active_scaled_workers) > 0 and not active_missions:
                if self.idle_since is None:
                    self.idle_since = now
                elif (now - self.idle_since) >= SCALE_DOWN_COOLDOWN_SEC:
                    self.scale_down()
                    self.idle_since = None
            else:
                if active_missions or q_depth > 0:
                    self.idle_since = None
                    
            status_label = "PREDICTIVE_ACTIVE" if active_missions else ("SCALED_UP" if len(self.active_scaled_workers) > 0 else "STABLE")
            self.update_state(status_label, q_depth, mission_id=self.active_mission_id)

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

