import os
import time
import json
import base64
import io
import random
import requests
import redis
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Private AI Cloud | Robotics Mission Control",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Connect to Redis with RESP2 protocol
try:
    r = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
        protocol=2,
        socket_timeout=1.0
    )
    r.ping()
    redis_ok = True
except Exception as e:
    redis_ok = False
    redis_err = str(e)

# Check FastAPI Gateway
try:
    gw_resp = requests.get(f"{SERVER_URL}/", timeout=1.0)
    gateway_ok = (gw_resp.status_code == 200)
except Exception:
    gateway_ok = False

# Custom CSS for Cyberpunk / Enterprise Robotics Theme
st.markdown("""
<style>
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    .metric-container {
        background: linear-gradient(145deg, #111827, #1f2937);
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .step-box {
        background: #111827;
        border: 1px solid #2563eb;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }
    .badge-p1 {
        background-color: #ef4444; color: white; padding: 3px 8px; border-radius: 6px; font-weight: bold;
    }
    .badge-p2 {
        background-color: #f59e0b; color: black; padding: 3px 8px; border-radius: 6px; font-weight: bold;
    }
    .badge-p5 {
        background-color: #10b981; color: white; padding: 3px 8px; border-radius: 6px; font-weight: bold;
    }
    .badge-p9 {
        background-color: #6b7280; color: white; padding: 3px 8px; border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Helper Functions -----------------
def generate_synthetic_scene(scene_type: str) -> str:
    """Generates synthetic RGB frames representing various warehouse robotics camera feeds."""
    img = Image.new("RGB", (320, 240), color=(20, 24, 33))
    draw = ImageDraw.Draw(img)
    
    # Grid background (warehouse floor)
    for x in range(0, 320, 40):
        draw.line([(x, 0), (x, 240)], fill=(35, 42, 56), width=1)
    for y in range(0, 240, 40):
        draw.line([(0, y), (320, y)], fill=(35, 42, 56), width=1)

    if scene_type == "🚨 Emergency: Human in AGV Path":
        draw.rectangle([110, 40, 190, 190], fill=(239, 68, 68), outline=(255, 255, 255), width=2)
        draw.ellipse([135, 15, 165, 45], fill=(254, 202, 202))
        draw.text((115, 95), "HUMAN DETECT", fill="white")
    elif scene_type == "📦 Warehouse Pallet Obstacle":
        draw.rectangle([80, 80, 240, 180], fill=(245, 158, 11), outline=(255, 255, 255), width=2)
        draw.line([(80, 130), (240, 130)], fill=(180, 83, 9), width=3)
        draw.text((105, 105), "CARGO PALLET", fill="black")
    elif scene_type == "🔌 Auto-Docking Station":
        draw.rectangle([120, 70, 200, 170], fill=(16, 185, 129), outline=(255, 255, 255), width=2)
        draw.polygon([(140, 110), (180, 110), (160, 140)], fill="yellow")
        draw.text((130, 80), "DOCK PORT", fill="white")
    else:  # Clear navigation corridor
        draw.polygon([(130, 240), (190, 240), (165, 120), (155, 120)], fill=(59, 130, 246))
        draw.text((120, 160), "CLEAR PATH", fill="white")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()

def send_task(robot_id: str, priority: int, scene_type: str):
    """Submits task through FastAPI Gateway."""
    payload = {
        "robot_id": robot_id,
        "priority": priority,
        "image_base64": generate_synthetic_scene(scene_type)
    }
    try:
        resp = requests.post(f"{SERVER_URL}/predict", json=payload, headers={"X-Robot-Token": "robot-token-secret"}, timeout=2.0)
        if resp.status_code == 201:
            return resp.json()["task_id"]
    except Exception as e:
        st.sidebar.error(f"Gateway Submission Error: {e}")
    return None

# ----------------- SIDEBAR: Synthetic Robot Dispatcher -----------------
st.sidebar.title("🎮 Robot Fleet Dispatcher")
st.sidebar.caption("Synthetically inject tasks into the Private AI Cloud")

ROBOT_PRESETS = {
    "🚨 AGV-01: Collision Avoidance (Priority 1)": {"id": "AGV-COLLISION-01", "p": 1, "scene": "🚨 Emergency: Human in AGV Path"},
    "🚁 DRONE-04: Aerial Navigation (Priority 2)": {"id": "DRONE-NAV-04", "p": 2, "scene": "📦 Warehouse Pallet Obstacle"},
    "🤖 SWEEPER-09: Floor Cleaner (Priority 5)": {"id": "SWEEPER-09", "p": 5, "scene": "🔌 Auto-Docking Station"},
    "📦 SCANNER-12: Bulk Inventory (Priority 9)": {"id": "SCANNER-BATCH-12", "p": 9, "scene": "Clear Navigation Corridor"}
}

chosen_robot = st.sidebar.selectbox("Select Synthetic Robot:", list(ROBOT_PRESETS.keys()))
preset = ROBOT_PRESETS[chosen_robot]

custom_scene = st.sidebar.selectbox(
    "Simulated Camera Sensor Feed:",
    [
        "🚨 Emergency: Human in AGV Path",
        "📦 Warehouse Pallet Obstacle",
        "🔌 Auto-Docking Station",
        "Clear Navigation Corridor"
    ],
    index=0 if preset["p"] == 1 else (1 if preset["p"] == 2 else 2)
)

if st.sidebar.button("🚀 Dispatch Robot Task", width="stretch"):
    tid = send_task(preset["id"], preset["p"], custom_scene)
    if tid:
        st.sidebar.success(f"Dispatched: {tid[:8]}... (Priority {preset['p']})")

st.sidebar.markdown("---")
st.sidebar.subheader("⚡ Hackathon Live Demo")
st.sidebar.caption("Demonstrate Strict Priority Preemption:")

if st.sidebar.button("💥 Flood 5 Batch Tasks + 1 Critical AGV", width="stretch"):
    # Flood low-priority tasks
    for i in range(1, 6):
        send_task(f"SCANNER-BATCH-0{i}", 9, "Clear Navigation Corridor")
    # Immediately send critical task
    time.sleep(0.05)
    send_task("AGV-COLLISION-CRITICAL", 1, "🚨 Emergency: Human in AGV Path")
    st.sidebar.warning("Injected 5 Low (P9) + 1 Critical (P1)! Observe P1 jumped the queue!")

if st.sidebar.button("🧹 Clear Queue & Reset Telemetry", width="stretch"):
    if redis_ok:
        r.delete("queue:tasks", "history:tasks")
        r.set("stats:processed", "0")
        r.set("stats:latency_sum", "0")
        st.sidebar.info("Queue cleared.")

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("🔄 Auto-Refresh UI (500ms)", value=True)

# ----------------- MAIN VIEW -----------------
st.title("🤖 Private AI Cloud for Robotics")
st.markdown("**Strict Priority Queue Scheduling & AI Vision Inference Pipeline**")

# System Status Bar
c1, c2, c3, c4 = st.columns(4)
c1.metric("FastAPI Gateway", "ONLINE 🟢" if gateway_ok else "OFFLINE 🔴", f"{SERVER_URL}")
c2.metric("Redis Priority Queue", "ONLINE 🟢" if redis_ok else "OFFLINE 🔴", f"{REDIS_HOST}:{REDIS_PORT}")

if redis_ok:
    processed = int(r.get("stats:processed") or 0)
    q_depth = int(r.zcard("queue:tasks") or 0)
    lat_sum = float(r.get("stats:latency_sum") or 0.0)
    avg_lat = round(lat_sum / processed, 2) if processed > 0 else 0.0
else:
    processed, q_depth, avg_lat = 0, 0, 0.0

c3.metric("Tasks Processed", f"{processed:,}")
c4.metric("Average Inference Latency", f"{avg_lat} ms")

st.markdown("---")

# Visual Pipeline Diagram
st.subheader("🔍 End-to-End Processing Pipeline")
step_col1, step_col2, step_col3, step_col4 = st.columns(4)

with step_col1:
    st.markdown("""
    <div class="step-box">
        <h4>1. Robot Egress</h4>
        <p style="font-size: 13px; color: #9ca3af;">
            Robots transmit base64 sensor frames with pre-shared tokens and priority ratings (1 to 9).
        </p>
        <span class="badge-p1">P1 = Collision</span>
        <span class="badge-p5">P5 = Sweep</span>
    </div>
    """, unsafe_allow_html=True)

with step_col2:
    st.markdown(f"""
    <div class="step-box">
        <h4>2. Redis Sorted Set Queue</h4>
        <p style="font-size: 13px; color: #9ca3af;">
            <b>Score = Priority</b>. P1 tasks jump directly to front of queue.
        </p>
        <b style="color: #60a5fa;">Pending in Queue: {q_depth}</b>
    </div>
    """, unsafe_allow_html=True)

with step_col3:
    st.markdown("""
    <div class="step-box">
        <h4>3. AI Worker Daemon</h4>
        <p style="font-size: 13px; color: #9ca3af;">
            Pops lowest score via atomic <code>ZPOPMIN</code>. Runs YOLOv8 edge vision model.
        </p>
        <b style="color: #34d399;">Model: YOLOv8 Engine</b>
    </div>
    """, unsafe_allow_html=True)

with step_col4:
    st.markdown("""
    <div class="step-box">
        <h4>4. Robot Actuation</h4>
        <p style="font-size: 13px; color: #9ca3af;">
            Bounding boxes & object classes saved back to Redis. Robot polls result & avoids obstacle.
        </p>
        <b style="color: #f472b6;">Latency: &lt; 25ms</b>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Main Content Split: Active Queue vs Latest Processed Feed
view_col1, view_col2 = st.columns([1, 1])

with view_col1:
    st.subheader(f"⏳ Live Redis Priority Queue ({q_depth} waiting)")
    if redis_ok and q_depth > 0:
        # Fetch items sorted by priority score
        queue_items = r.zrange("queue:tasks", 0, 10, withscores=True)
        q_rows = []
        for rank, (tid, score) in enumerate(queue_items, 1):
            tdata = r.hgetall(f"task:{tid}") or {}
            p_int = int(score)
            p_badge = f"🚨 P1 [CRITICAL]" if p_int == 1 else (f"🚁 P2 [HIGH]" if p_int == 2 else f"📦 P{p_int} [STANDARD]")
            q_rows.append({
                "Queue Pos": f"#{rank}",
                "Priority Score": p_badge,
                "Robot ID": tdata.get("robot_id", "Unknown"),
                "Task ID": tid[:8] + "...",
                "State": tdata.get("state", "queued").upper()
            })
        st.dataframe(pd.DataFrame(q_rows), width="stretch", hide_index=True)
        st.caption("Notice: Lower Priority Score is popped FIRST by the AI worker.")
    else:
        st.info("✅ Queue is currently empty! All tasks have been processed by the AI worker.")

with view_col2:
    st.subheader("👁️ Latest Processed Robot Camera Feed")
    if redis_ok:
        recent_ids = r.lrange("history:tasks", 0, 5)
        latest_task = None
        for tid in recent_ids:
            tdata = r.hgetall(f"task:{tid}")
            if tdata and tdata.get("state") == "completed" and tdata.get("image_base64"):
                latest_task = tdata
                break
        
        if latest_task:
            try:
                img_bytes = base64.b64decode(latest_task["image_base64"])
                pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                draw = ImageDraw.Draw(pil_img)
                
                boxes_raw = latest_task.get("boxes", "[]")
                classes_raw = latest_task.get("classes", "[]")
                boxes = json.loads(boxes_raw)
                classes = json.loads(classes_raw)
                
                for b, c in zip(boxes, classes):
                    draw.rectangle(b, outline="cyan", width=3)
                    draw.text((b[0] + 4, max(4, b[1] - 12)), str(c).upper(), fill="yellow")
                
                st.image(
                    pil_img,
                    caption=f"Robot: {latest_task.get('robot_id')} | Latency: {latest_task.get('inference_time_ms')}ms | Objects Detected: {len(boxes)}"
                )
            except Exception as e:
                st.warning(f"Preview rendering: {e}")
        else:
            st.info("No completed image feed to display yet. Use the sidebar to dispatch a synthetic robot.")

st.markdown("---")

# Telemetry Execution Table
st.subheader("📋 Real-Time Execution Log (Last 25 Tasks)")
if redis_ok:
    history_ids = r.lrange("history:tasks", 0, 25)
    hist_rows = []
    for tid in history_ids:
        d = r.hgetall(f"task:{tid}")
        if d:
            p = int(d.get("priority", 9))
            p_str = "P1 [CRITICAL]" if p == 1 else ("P2 [HIGH]" if p == 2 else f"P{p}")
            hist_rows.append({
                "Timestamp": time.strftime("%H:%M:%S", time.localtime(float(d.get("created_ts", time.time())))),
                "Task ID": tid[:8] + "...",
                "Robot ID": d.get("robot_id", "Unknown"),
                "Priority": p_str,
                "State": d.get("state", "queued").upper(),
                "Detections": d.get("detection_count", "-"),
                "Latency (ms)": f"{float(d.get('inference_time_ms', 0)):.1f}" if d.get("inference_time_ms") else "-",
            })
    if hist_rows:
        st.dataframe(pd.DataFrame(hist_rows), width="stretch", hide_index=True)
    else:
        st.info("Awaiting robot activity.")

# Auto-refresh loop
if auto_refresh:
    time.sleep(0.5)
    st.rerun()
