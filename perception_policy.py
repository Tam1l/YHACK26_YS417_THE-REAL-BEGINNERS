"""Warehouse perception policy for converting YOLO detections into robot actions."""

import json
import os
from typing import Dict, List, Sequence, Tuple


ACTION_RANK = {
    "PATH_CLEAR": 0,
    "SLOW_AND_MONITOR": 1,
    "CONTROLLED_STOP": 2,
    "REROUTE": 3,
    "STOP_AND_REROUTE": 4,
    "EMERGENCY_BRAKE": 5,
}

VEHICLE_CLASSES = {"car", "bus", "truck", "motorcycle", "bicycle", "forklift"}
ROUTE_OBSTACLE_CLASSES = {"pallet", "safety_cone", "agv", "agv_robot", "robot", "docking_station"}


def _normalise(class_name: str) -> str:
    return str(class_name).strip().lower().replace(" ", "_").replace("-", "_")


def _custom_policies() -> Dict[str, Dict]:
    """Optional JSON override, e.g. {""pallet"": {""action"": ""REROUTE""}}."""
    try:
        value = json.loads(os.getenv("ROBONEXUS_CLASS_POLICIES", "{}"))
        return {_normalise(name): data for name, data in value.items() if isinstance(data, dict)}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _in_agv_safety_zone(box: Sequence[float], image_size: Tuple[int, int]) -> bool:
    """Front corridor: central width and lower half of the robot camera frame."""
    if len(box) != 4:
        return False
    width, height = image_size
    if width <= 0 or height <= 0:
        return False
    x1, y1, x2, y2 = (float(v) for v in box)
    center_x = (x1 + x2) / 2 / width
    bottom_y = y2 / height
    area_ratio = max(0.0, x2 - x1) * max(0.0, y2 - y1) / (width * height)
    return 0.25 <= center_x <= 0.75 and (bottom_y >= 0.52 or area_ratio >= 0.08)


def evaluate_detections(
    boxes: Sequence[Sequence[float]],
    classes: Sequence[str],
    confidences: Sequence[float],
    image_size: Tuple[int, int],
) -> Dict:
    """Return the highest-priority operational action for a completed YOLO frame."""
    best = {
        "action": "PATH_CLEAR",
        "severity": "NONE",
        "hazard_detected": False,
        "hazard_class": "",
        "hazard_confidence": 0.0,
        "hazard_zone": "CLEAR",
        "reason": "No configured warehouse hazard detected.",
    }
    custom = _custom_policies()

    for box, raw_class, raw_confidence in zip(boxes, classes, confidences):
        class_name = _normalise(raw_class)
        confidence = float(raw_confidence)
        in_zone = _in_agv_safety_zone(box, image_size)
        zone = "AGV_PATH" if in_zone else "OUTER_ZONE"
        policy = custom.get(class_name, {})

        if policy:
            action = str(policy.get("action", "REROUTE")).upper()
            severity = str(policy.get("severity", "HIGH")).upper()
            reason = str(policy.get("reason", f"Custom class {class_name} detected."))
        elif class_name == "person":
            action = "EMERGENCY_BRAKE" if in_zone else "SLOW_AND_MONITOR"
            severity = "CRITICAL" if in_zone else "HIGH"
            reason = "Person detected in the AGV travel corridor." if in_zone else "Person detected outside the AGV travel corridor."
        elif class_name in VEHICLE_CLASSES:
            action = "STOP_AND_REROUTE" if in_zone else "SLOW_AND_MONITOR"
            severity = "HIGH" if in_zone else "MEDIUM"
            reason = f"{class_name.replace('_', ' ').title()} obstructs the AGV travel corridor." if in_zone else f"{class_name.replace('_', ' ').title()} detected near the route."
        elif class_name == "stop_sign":
            action, severity, reason = "CONTROLLED_STOP", "HIGH", "Stop sign detected; wait for route clearance."
        elif class_name == "damaged_package":
            action, severity, reason = "CONTROLLED_STOP", "HIGH", "Damaged package detected; request inspection."
        elif class_name in ROUTE_OBSTACLE_CLASSES:
            action, severity, reason = "REROUTE", "MEDIUM", f"{class_name.replace('_', ' ').title()} obstructs the planned route."
        else:
            continue

        candidate = {
            "action": action,
            "severity": severity,
            "hazard_detected": True,
            "hazard_class": class_name,
            "hazard_confidence": round(confidence, 4),
            "hazard_zone": zone,
            "reason": reason,
        }
        if ACTION_RANK.get(candidate["action"], 0) > ACTION_RANK.get(best["action"], 0):
            best = candidate

    return best
