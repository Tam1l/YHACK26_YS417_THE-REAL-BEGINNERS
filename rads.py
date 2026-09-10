"""Deterministic Robotics-Aware Deadline Scheduler scoring."""
from dataclasses import dataclass

CRITICALITY_SCORES = {"CRITICAL": 1.0, "HIGH": 0.7, "NORMAL": 0.4, "LOW": 0.1}

@dataclass(frozen=True)
class RadsWeights:
    criticality: float = 0.45
    deadline: float = 0.35
    waiting: float = 0.20
    inference: float = 0.10

def deadline_urgency(created_at_ms: float, deadline_ms: int, now_ms: float) -> float:
    return max(0.0, min(1.0, 1 - ((created_at_ms + deadline_ms - now_ms) / deadline_ms)))

def deadline_risk(created_at_ms: float, deadline_ms: int, now_ms: float, queue_delay_ms: float, inference_ms: float) -> str:
    return "HIGH" if now_ms + queue_delay_ms + inference_ms > created_at_ms + deadline_ms else "LOW"

def rads_score(criticality: str, created_at_ms: float, deadline_ms: int, now_ms: float, estimated_inference_ms: float, aging_window_ms: int = 30_000, weights: RadsWeights = RadsWeights()) -> float:
    waiting = max(0.0, min(1.0, (now_ms - created_at_ms) / aging_window_ms))
    urgency = deadline_urgency(created_at_ms, deadline_ms, now_ms)
    cost = min(1.0, estimated_inference_ms / 1_000)
    return weights.criticality * CRITICALITY_SCORES[criticality] + weights.deadline * urgency + weights.waiting * waiting - weights.inference * cost
