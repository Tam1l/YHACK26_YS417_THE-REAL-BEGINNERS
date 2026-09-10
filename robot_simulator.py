import os
import time
import io
import base64
import random
import threading
import logging
from typing import Dict
import requests
from PIL import Image, ImageDraw

SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000")
INFERENCE_ENDPOINT = f"{SERVER_URL}/api/v1/inference"
LEGACY_PREDICT_ENDPOINT = f"{SERVER_URL}/predict"

AUTH_HEADERS = {
    "X-Robot-Token": "robot-token-secret"
}

# Spec Section 44: Distinct robot personas with different criticality & deadlines
ROBOTS = [
    {
        "name": "AGV-Collision-Avoidance",
        "robot_id": "AGV-01",
        "criticality": "CRITICAL",
        "deadline_ms": 100.0,
        "rate": 0.8,
        "color": "red"
    },
    {
        "name": "Drone-Navigation",
        "robot_id": "DRONE-07",
        "criticality": "HIGH",
        "deadline_ms": 250.0,
        "rate": 1.5,
        "color": "blue"
    },
    {
        "name": "Floor-Sweeper-Inventory",
        "robot_id": "SWEEPER-12",
        "criticality": "NORMAL",
        "deadline_ms": 800.0,
        "rate": 2.5,
        "color": "green"
    },
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
    datefmt="%H:%M:%S"
)

def generate_mock_sensor_frame(label: str, color: str) -> str:
    img = Image.new("RGB", (320, 240), color=color)
    draw = ImageDraw.Draw(img)
    for _ in range(random.randint(1, 4)):
        x0, y0 = random.randint(10, 200), random.randint(10, 160)
        x1, y1 = x0 + random.randint(30, 80), y0 + random.randint(30, 60)
        draw.rectangle([x0, y0, x1, y1], fill="yellow", outline="black")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode()

def post_with_exponential_backoff(robot_cfg: Dict, max_retries: int = 5) -> str:
    delay = 1.0
    payload = {
        "robot_id": robot_cfg["robot_id"],
        "task_type": "object_detection",
        "criticality": robot_cfg["criticality"],
        "deadline_ms": robot_cfg["deadline_ms"],
        "image_base64": generate_mock_sensor_frame(robot_cfg["name"], robot_cfg["color"]),
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(INFERENCE_ENDPOINT, json=payload, headers=AUTH_HEADERS, timeout=4.0)
            if resp.status_code == 201:
                data = resp.json()
                req_id = data["request_id"]
                score = data.get("rads_score", "-")
                logging.info(f"Task SUBMITTED -> ID: {req_id[:8]}... (Crit: {robot_cfg['criticality']} | Score: {score})")
                return req_id
            elif resp.status_code in (500, 502, 503, 504):
                raise requests.RequestException(f"HTTP {resp.status_code}")
        except Exception as e:
            logging.warning(f"Submission failed ({attempt}/{max_retries}): {e}. Backoff {delay:.1f}s...")
            time.sleep(delay)
            delay = min(delay * 2.0, 16.0)
            
    logging.error(f"Robot buffer full after {max_retries} attempts.")
    return None

def poll_for_completion(req_id: str, robot_cfg: Dict, timeout: float = 15.0):
    if not req_id:
        return
    start = time.time()
    url = f"{SERVER_URL}/api/v1/inference/{req_id}/result"
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, headers=AUTH_HEADERS, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status")
                if status == "COMPLETED":
                    worker = data.get("assigned_worker", "-")
                    lat = data.get("inference_ms", 0.0)
                    met = data.get("deadline_met", True)
                    logging.info(f"Task RESOLVED -> ID: {req_id[:8]}... | Worker: {worker} | Latency: {lat}ms | Deadline Met: {met}")
                    return
                elif status == "FAILED":
                    logging.error(f"Task FAILED -> ID: {req_id[:8]}... | {data.get('error')}")
                    return
        except Exception:
            pass
        time.sleep(0.1)

def robot_lifecycle_loop(robot_cfg: Dict):
    logging.info(f"Robot {robot_cfg['name']} active (Criticality: {robot_cfg['criticality']} | Deadline: {robot_cfg['deadline_ms']}ms)")
    while True:
        req_id = post_with_exponential_backoff(robot_cfg)
        if req_id:
            poll_for_completion(req_id, robot_cfg)
        time.sleep(robot_cfg["rate"] + random.uniform(0.1, 0.4))

def main():
    print("=" * 65)
    print("ROBONEXUS — MULTI-ROBOT CONCURRENT CLIENT SIMULATOR")
    print("Personas: AGV (CRITICAL 100ms), Drone (HIGH 250ms), Sweeper (NORMAL 800ms)")
    print("=" * 65)
    threads = []
    for cfg in ROBOTS:
        t = threading.Thread(target=robot_lifecycle_loop, args=(cfg,), name=cfg["robot_id"], daemon=True)
        t.start()
        threads.append(t)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping simulation.")

if __name__ == "__main__":
    main()
