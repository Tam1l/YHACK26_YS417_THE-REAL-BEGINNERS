"""Deterministic Robotics-Aware Deadline Scheduler (RADS) scoring and policies."""
from dataclasses import dataclass
import time

CRITICALITY_SCORES = {
    "CRITICAL": 1.0,
    "HIGH": 0.7,
    "NORMAL": 0.4,
    "LOW": 0.1
}

CRITICALITY_WEIGHTS = {
    "LOW": 1,
    "NORMAL": 2,
    "HIGH": 3,
    "CRITICAL": 4,
    1: 4,
    2: 3,
    5: 2,
    9: 1
}

@dataclass(frozen=True)
class RadsWeights:
    criticality: float = 0.45
    deadline: float = 0.35
    waiting: float = 0.20
    inference: float = 0.10

Wc = 0.45
Wd = 0.35
Ww = 0.20
Wi = 0.10
AGING_WINDOW_MS = 30_000.0

def deadline_urgency(created_at_ms: float, deadline_ms: float, now_ms: float) -> float:
    """Calculates deadline urgency normalized from 0.0 to 1.0."""
    return max(0.0, min(1.0, 1.0 - ((created_at_ms + deadline_ms - now_ms) / max(1.0, deadline_ms))))

def deadline_risk(created_at_ms: float, deadline_ms: float, now_ms: float, queue_delay_ms: float, inference_ms: float) -> str:
    """Predictive Deadline Risk flag (Spec Section 36)."""
    return "HIGH" if (now_ms + queue_delay_ms + inference_ms) > (created_at_ms + deadline_ms) else "LOW"

def rads_score(
    criticality: str,
    created_at_ms: float,
    deadline_ms: float,
    now_ms: float,
    estimated_inference_ms: float,
    aging_window_ms: float = 30_000.0,
    weights: RadsWeights = RadsWeights()
) -> float:
    """Computes pure RADS score for unit tests and deterministic scoring."""
    waiting = max(0.0, min(1.0, (now_ms - created_at_ms) / max(1.0, aging_window_ms)))
    urgency = deadline_urgency(created_at_ms, deadline_ms, now_ms)
    cost = min(1.0, estimated_inference_ms / 1_000.0)
    c_score = CRITICALITY_SCORES.get(criticality.upper(), 0.4)
    return weights.criticality * c_score + weights.deadline * urgency + weights.waiting * waiting - weights.inference * cost

def compute_rads_score(criticality, deadline_ms: float, created_ts: float, now_ts: float = None, est_inference_ms: float = 20.0) -> float:
    """
    Adapter for runtime scheduling in seconds/milliseconds.
    Higher score = higher execution priority.
    """
    if now_ts is None:
        now_ts = time.time()
    
    crit_str = "CRITICAL" if criticality in ("CRITICAL", 1, "1") else ("HIGH" if criticality in ("HIGH", 2, "2") else ("NORMAL" if criticality in ("NORMAL", 5, "5") else "LOW"))
    score = rads_score(
        criticality=crit_str,
        created_at_ms=created_ts * 1000.0,
        deadline_ms=deadline_ms,
        now_ms=now_ts * 1000.0,
        estimated_inference_ms=est_inference_ms
    )
    return round(float(score), 4)

def calculate_redis_queue_score(criticality, deadline_ms: float, created_ts: float, scheduler_mode: str = "RADS") -> float:
    if scheduler_mode == "FIFO":
        return float(created_ts)
    else:
        rads_val = compute_rads_score(criticality, deadline_ms, created_ts)
        return -rads_val
