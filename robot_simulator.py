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
PREDICT_ENDPOINT = f"{SERVER_URL}/predict"
RESULT_ENDPOINT = f"{SERVER_URL}/result"

AUTH_HEADERS = {
    "X-Robot-Token": "robot-token-secret"
}

ROBOTS = [
    {"name": "AGV-Collision-Avoidance", "robot_id": "AGV-01", "priority": 1, "color": "red", "rate": 0.8},
    {"name": "Drone-Navigation", "robot_id": "DRONE-07", "priority": 2, "color": "blue", "rate": 1.5},
    {"name": "Floor-Sweeper-Inventory", "robot_id": "SWEEPER-12", "priority": 5, "color": "green", "rate": 2.5},
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
        "priority": robot_cfg["priority"],
        "image_base64": generate_mock_sensor_frame(robot_cfg["name"], robot_cfg["color"]),
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(PREDICT_ENDPOINT, json=payload, headers=AUTH_HEADERS, timeout=4.0)
            if resp.status_code == 201:
                data = resp.json()
                task_id = data["task_id"]
                logging.info(f"Task SUBMITTED -> ID: {task_id[:8]}... (Priority: {robot_cfg['priority']})")
                return task_id
            elif resp.status_code in (500, 502, 503, 504):
                raise requests.RequestException(f"Server returned HTTP {resp.status_code}")
        except Exception as e:
            logging.warning(f"Submission failed (Attempt {attempt}/{max_retries}): {e}. Backing off {delay:.1f}s...")
            time.sleep(delay)
            delay = min(delay * 2.0, 16.0)
            
    logging.error(f"Robot local queue buffered task after {max_retries} attempts.")
    return None

def poll_for_completion(task_id: str, robot_cfg: Dict, timeout: float = 15.0):
    if not task_id:
        return
    start = time.time()
    url = f"{RESULT_ENDPOINT}/{task_id}"
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, headers=AUTH_HEADERS, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                state = data.get("state")
                if state == "completed":
                    res = data.get("result", {})
                    latency = res.get("inference_time_ms", 0.0)
                    count = res.get("detection_count", 0)
                    logging.info(f"Task RESOLVED -> ID: {task_id[:8]}... | State: COMPLETED | Latency: {latency}ms | Detections: {count}")
                    return
                elif state == "failed":
                    logging.error(f"Task RESOLVED -> ID: {task_id[:8]}... | State: FAILED: {data.get('error')}")
                    return
        except Exception:
            pass
        time.sleep(0.2)
    logging.warning(f"Task timeout reached for {task_id}")

def robot_lifecycle_loop(robot_cfg: Dict):
    logging.info(f"Robot {robot_cfg['name']} active (Priority: {robot_cfg['priority']})")
    while True:
        task_id = post_with_exponential_backoff(robot_cfg)
        if task_id:
            poll_for_completion(task_id, robot_cfg)
        time.sleep(robot_cfg["rate"] + random.uniform(0.1, 0.4))

def main():
    print("=" * 65)
    print("PRIVATE AI CLOUD - MULTI-ROBOT CONCURRENT STRESS SIMULATOR")
    print("Simulating AGV (Priority 1), Drone (Priority 2), Sweeper (Priority 5)")
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
