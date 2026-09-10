import time

CRITICALITY_WEIGHTS = {
    "LOW": 1,
    "NORMAL": 2,
    "HIGH": 3,
    "CRITICAL": 4,
    1: 4, # numerical compatibility (1 is critical in legacy)
    2: 3,
    5: 2,
    9: 1
}

# Spec Section 14: Configurable weights
Wc = 0.45  # Criticality weight
Wd = 0.35  # Deadline urgency weight
Ww = 0.20  # Waiting time aging weight
Wi = 0.10  # Inference cost penalty weight

AGING_WINDOW_MS = 10000.0  # 10s aging window for starvation prevention

def compute_rads_score(criticality, deadline_ms: float, created_ts: float, now_ts: float = None, est_inference_ms: float = 20.0) -> float:
    """
    Computes the normalized RADS (Robotics-Aware Deadline Scheduler) priority score.
    Higher score = higher execution priority.
    """
    if now_ts is None:
        now_ts = time.time()
        
    # 1. Mission Criticality (normalized 0.25 to 1.0)
    raw_c = CRITICALITY_WEIGHTS.get(criticality, 2)
    c_score = raw_c / 4.0
    
    # 2. Deadline Urgency (clamps from 0.0 to 1.0 as deadline approaches 0ms)
    deadline_at = created_ts + (deadline_ms / 1000.0)
    remaining_ms = (deadline_at - now_ts) * 1000.0
    deadline_urgency = max(0.0, min(1.0, 1.0 - (remaining_ms / max(10.0, deadline_ms))))
    
    # 3. Anti-Starvation Aging (longer wait = higher score boost)
    waiting_ms = max(0.0, (now_ts - created_ts) * 1000.0)
    waiting_score = min(1.0, waiting_ms / AGING_WINDOW_MS)
    
    # 4. Inference Cost penalty
    cost_penalty = min(1.0, est_inference_ms / 100.0)
    
    # Combined RADS Formula (Spec Section 14)
    final_score = (Wc * c_score) + (Wd * deadline_urgency) + (Ww * waiting_score) - (Wi * cost_penalty)
    return round(float(final_score), 4)

def calculate_redis_queue_score(criticality, deadline_ms: float, created_ts: float, scheduler_mode: str = "RADS") -> float:
    """
    Computes score for Redis Sorted Set.
    Using ZPOPMIN: lower score pops first.
    For RADS: score = -rads_score (highest score pops first).
    For FIFO: score = created_ts (oldest request pops first).
    """
    if scheduler_mode == "FIFO":
        return float(created_ts)
    else:
        rads_val = compute_rads_score(criticality, deadline_ms, created_ts)
        return -rads_val
