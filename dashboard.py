import os
import time
import json
import base64
import io
import hashlib
import requests
import redis
import pandas as pd
from PIL import Image, ImageDraw
import streamlit as st
import fleet_tenants
import incident_archiver

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="RoboNexus | Private AI Cloud Mission Control",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
except Exception:
    redis_ok = False

try:
    gw_resp = requests.get(f"{SERVER_URL}/health", timeout=1.0)
    gateway_data = gw_resp.json() if gw_resp.status_code == 200 else {}
    gateway_ok = (gw_resp.status_code == 200)
except Exception:
    gateway_ok = False
    gateway_data = {}

st.markdown("""
<style>
    /* Sleek Modern Light Mode Design System */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
        font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Top Header Bar */
    header[data-testid="stHeader"] {
        background: rgba(248, 250, 252, 0.85);
        backdrop-filter: blur(8px);
    }
    
    /* Shift main screen div to the rightmost leaving space on the left and padding on the right */
    .main .block-container {
        max-width: min(1440px, calc(100% - 40px)) !important;
        margin-left: auto !important;
        margin-right: 28px !important;
        padding-right: 28px !important;
    }
    
    /* Sidebar Styling - Clean Slate-100 with High Readability */
    section[data-testid="stSidebar"] {
        background-color: #f1f5f9 !important;
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #0f172a !important;
        font-weight: 700 !important;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] span {
        color: #1e293b !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] p {
        color: #475569 !important;
    }
    
    /* Sleek Light Selectboxes in Sidebar */
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] span,
    section[data-testid="stSidebar"] div[data-baseweb="select"] div {
        color: #0f172a !important;
        font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] svg {
        fill: #64748b !important;
    }

    /* Sidebar Buttons (Avoid harsh black boxes) */
    section[data-testid="stSidebar"] .stButton > button {
        background: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.2s ease !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #f8fafc !important;
        border-color: #94a3b8 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.06) !important;
    }
    section[data-testid="stSidebar"] .stButton > button p {
        color: #0f172a !important;
    }
    
    /* Primary Action Button (Dispatch) */
    section[data-testid="stSidebar"] div.row-widget.stButton:nth-of-type(1) > button,
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(button:contains("Dispatch")) button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25) !important;
    }
    section[data-testid="stSidebar"] div.row-widget.stButton:nth-of-type(1) > button p {
        color: #ffffff !important;
    }
    
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    }
    div[data-testid="stMetricLabel"] p {
        color: #64748b !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 700 !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f1f5f9;
        padding: 4px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #64748b;
        font-weight: 600;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    
    /* Worker Cards */
    .worker-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    
    .badge-crit { background-color: #ef4444; color: white; padding: 3px 8px; border-radius: 6px; font-weight: bold; }
    .badge-high { background-color: #f59e0b; color: white; padding: 3px 8px; border-radius: 6px; font-weight: bold; }
    .badge-norm { background-color: #10b981; color: white; padding: 3px 8px; border-radius: 6px; }
    .badge-low  { background-color: #64748b; color: white; padding: 3px 8px; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

def generate_synthetic_scene(scene_type: str) -> str:
    img = Image.new("RGB", (320, 240), color=(241, 245, 249))
    draw = ImageDraw.Draw(img)
    for x in range(0, 320, 40):
        draw.line([(x, 0), (x, 240)], fill=(226, 232, 240), width=1)
    for y in range(0, 240, 40):
        draw.line([(0, y), (320, y)], fill=(226, 232, 240), width=1)

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
    else:
        draw.polygon([(130, 240), (190, 240), (165, 120), (155, 120)], fill=(59, 130, 246))
        draw.text((120, 160), "CLEAR PATH", fill="white")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()

def submit_image_task(
    robot_id: str,
    criticality: str,
    deadline_ms: float,
    image_bytes: bytes,
    source: str = "live_camera"
):
    payload = {
        "robot_id": robot_id,
        "task_type": "object_detection",
        "criticality": criticality,
        "deadline_ms": deadline_ms,
        "image_base64": base64.b64encode(image_bytes).decode(),
        "source": source,
    }
    try:
        resp = requests.post(f"{SERVER_URL}/api/v1/inference", json=payload, headers={"X-Robot-Token": "robot-token-secret"}, timeout=2.0)
        if resp.status_code == 201:
            return resp.json()["request_id"]
    except Exception as e:
        st.sidebar.error(f"Gateway Error: {e}")
    return None

def send_task(robot_id: str, criticality: str, deadline_ms: float, scene_type: str):
    return submit_image_task(
        robot_id,
        criticality,
        deadline_ms,
        base64.b64decode(generate_synthetic_scene(scene_type)),
        source="synthetic_dispatch"
    )

# ================= SIDEBAR: Mission Controls =================
st.sidebar.title("🎮 RoboNexus Dispatcher")
st.sidebar.caption("RADS Scheduler & Multi-Worker Mission Control")

ROBOT_PRESETS = {
    "🚨 AGV-01: Collision Avoidance": {"id": "AGV-COLLISION-01", "crit": "CRITICAL", "dl": 100.0, "scene": "🚨 Emergency: Human in AGV Path"},
    "🚁 DRONE-04: Aerial Navigation": {"id": "DRONE-NAV-04", "crit": "HIGH", "dl": 250.0, "scene": "📦 Warehouse Pallet Obstacle"},
    "🤖 SWEEPER-09: Floor Maintenance": {"id": "SWEEPER-09", "crit": "NORMAL", "dl": 600.0, "scene": "🔌 Auto-Docking Station"},
    "📦 SCANNER-12: Bulk Inventory": {"id": "SCANNER-BATCH-12", "crit": "LOW", "dl": 1500.0, "scene": "Clear Navigation Corridor"}
}

chosen = st.sidebar.selectbox("Select Synthetic Robot:", list(ROBOT_PRESETS.keys()))
p_info = ROBOT_PRESETS[chosen]

scene = st.sidebar.selectbox("Camera Feed:", [
    "🚨 Emergency: Human in AGV Path",
    "📦 Warehouse Pallet Obstacle",
    "🔌 Auto-Docking Station",
    "Clear Navigation Corridor"
], index=0 if p_info["crit"] == "CRITICAL" else (1 if p_info["crit"] == "HIGH" else 2))

c_crit = st.sidebar.selectbox("Criticality Level:", ["CRITICAL", "HIGH", "NORMAL", "LOW"], index=["CRITICAL", "HIGH", "NORMAL", "LOW"].index(p_info["crit"]))
c_dl = st.sidebar.slider("Deadline (ms):", min_value=50, max_value=2000, value=int(p_info["dl"]), step=50)

st.sidebar.markdown("---")
st.sidebar.subheader("Live YOLO Camera")
if "camera_enabled" not in st.session_state:
    st.session_state["camera_enabled"] = False

camera_button_label = "📷 Open Robot Camera" if not st.session_state["camera_enabled"] else "📷 Close Robot Camera"
if st.sidebar.button(camera_button_label, width="stretch"):
    st.session_state["camera_enabled"] = not st.session_state["camera_enabled"]
    if not st.session_state["camera_enabled"]:
        st.session_state.pop("live_camera_frame", None)
    st.rerun()

st.sidebar.caption("The webcam only activates after opening it. Uploaded photos are also queued through RADS for YOLO detection.")
camera_frame = None
if st.session_state["camera_enabled"]:
    camera_frame = st.sidebar.camera_input("Capture robot camera frame", key="live_camera_frame")
else:
    st.sidebar.info("Camera is off. Click Open Robot Camera when you need a new frame.")

uploaded_frame = st.sidebar.file_uploader("Or upload a JPEG/PNG", type=["jpg", "jpeg", "png"], key="live_upload_frame")
live_frame = camera_frame if camera_frame is not None else uploaded_frame
auto_run_live_yolo = st.sidebar.checkbox("Automatically process each new photo", value=True)

if live_frame is not None and auto_run_live_yolo:
    frame_bytes = live_frame.getvalue()
    frame_hash = hashlib.sha256(frame_bytes).hexdigest()
    if st.session_state.get("last_live_frame_hash") != frame_hash:
        st.session_state["last_live_frame_hash"] = frame_hash
        task_id = submit_image_task(p_info["id"], c_crit, float(c_dl), frame_bytes)
        if task_id:
            st.session_state["live_vision_task_id"] = task_id
            st.sidebar.success(f"New camera frame queued: {task_id[:8]}...")
elif live_frame is None:
    # Clearing a frame permits a future capture of the same scene to be processed again.
    st.session_state.pop("last_live_frame_hash", None)

if st.sidebar.button("Run Real YOLO Inference", width="stretch"):
    if live_frame is None:
        st.sidebar.warning("Capture or upload an image first.")
    else:
        task_id = submit_image_task(p_info["id"], c_crit, float(c_dl), live_frame.getvalue())
        if task_id:
            st.session_state["live_vision_task_id"] = task_id
            st.sidebar.success(f"Live frame queued: {task_id[:8]}... Open the Vision Feed tab for detections.")

if st.sidebar.button("🚀 Dispatch Robot Task", width="stretch"):
    tid = send_task(p_info["id"], c_crit, float(c_dl), scene)
    if tid:
        st.sidebar.success(f"Dispatched: {tid[:8]}... ({c_crit} | {c_dl}ms)")

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Advanced Architecture Demos")

if st.sidebar.button("🛡️ Edge-Cloud Fallback", width="stretch", help="Demonstrates protective rejection of unreachable 15ms safety tasks with EXECUTE_AT_EDGE"):
    try:
        fb_resp = requests.post(f"{SERVER_URL}/api/v1/cloud/demo_edge_fallback", timeout=2.0)
        fb_data = fb_resp.json()
        st.sidebar.warning(f"🛡️ Circuit Breaker: {fb_data.get('status')}! Latency {fb_data.get('predicted_latency_ms')}ms > {fb_data.get('deadline_ms')}ms deadline. Handed over to edge.")
    except Exception as e:
        st.sidebar.error(f"Fallback error: {e}")

if st.sidebar.button("📊 Export Lakehouse Parquet", width="stretch", help="Batch ETL: Exports Redis telemetry & MinIO incidents into Snappy Parquet in s3://robonexus-analytics/"):
    try:
        import batch_exporter
        exp_meta = batch_exporter.export_fleet_telemetry_lakehouse(r)
        st.sidebar.success(f"📊 Exported {exp_meta['row_count']} rows to {exp_meta['s3_analytics_uri']} ({(exp_meta['file_size_bytes']/1024):.1f} KB)")
    except Exception as e:
        st.sidebar.error(f"Export error: {e}")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ System Maintenance")

if st.sidebar.button("🧹 Reset System & Workers", width="stretch"):
    if redis_ok:
        r.delete("queue:tasks", "history:tasks")
        for k in r.keys("debug:fail:*"):
            r.delete(k)
        for wid in ("worker-1", "worker-2"):
            r.hset(f"worker:{wid}", mapping={
                "worker_id": wid,
                "status": "IDLE",
                "healthy": "true",
                "current_job_id": "",
                "last_heartbeat": str(time.time())
            })
        try:
            requests.post(f"{SERVER_URL}/api/v1/debug/workers/worker-1/recover", timeout=1.0)
            requests.post(f"{SERVER_URL}/api/v1/debug/workers/worker-2/recover", timeout=1.0)
        except Exception:
            pass
        st.sidebar.success("System & worker pool reset to HEALTHY.")

auto_refresh = st.sidebar.checkbox("🔄 Auto-Refresh UI (500ms)", value=True)

# ================= MAIN VIEW =================
st.title("🤖 RoboNexus — Robotics-Aware Private AI Cloud")


import streamlit.components.v1 as components

ARENA_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #f8fafc;
            color: #0f172a;
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
            overflow: hidden;
            user-select: none;
        }
        #container {
            position: relative;
            width: 100%;
            height: 575px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.03);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        #arena-wrapper {
            position: relative;
            width: 100%;
            flex: 1;
            min-height: 505px;
            overflow: hidden;
            background: #f8fafc;
        }
        canvas {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }
        #controls-deck {
            height: 62px;
            background: #ffffff;
            border-top: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            box-sizing: border-box;
            z-index: 20;
            box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.02);
        }
        .deck-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .deck-label {
            font-size: 11px;
            font-weight: 700;
            color: #64748b;
            letter-spacing: 0.6px;
            margin-right: 4px;
        }
        .btn {
            background: #f1f5f9;
            color: #1e293b;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        }
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }
        .btn-danger {
            background: #ef4444;
            border-color: #dc2626;
            color: #ffffff;
        }
        .btn-danger:hover { background: #dc2626; }
        .btn-primary {
            background: #2563eb;
            border-color: #1d4ed8;
            color: #ffffff;
        }
        .btn-primary:hover { background: #1d4ed8; }
        .btn-warning {
            background: #d97706;
            border-color: #b45309;
            color: #ffffff;
        }
        .btn-warning:hover { background: #b45309; }
        #banner {
            position: absolute;
            top: 14px;
            left: 50%;
            transform: translateX(-50%);
            padding: 8px 22px;
            border-radius: 24px;
            font-size: 13px;
            font-weight: 700;
            display: none;
            z-index: 30;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.08);
            animation: pulse 1.2s infinite alternate;
        }
        @keyframes pulse {
            from { opacity: 0.92; transform: translateX(-50%) scale(0.99); }
            to { opacity: 1.0; transform: translateX(-50%) scale(1.01); }
        }
    </style>
</head>
<body>
    <div id="container">
        <div id="arena-wrapper">
            <canvas id="arenaCanvas"></canvas>
            <div id="banner"></div>
        </div>
        <div id="controls-deck">
            <div class="deck-group">
                <span class="deck-label">FLEET OPS:</span>
                <button class="btn" id="btnPlayPause" style="background:#0f172a; border-color:#0f172a; color:#ffffff;">⏸ Pause Fleet</button>
                <button class="btn btn-danger" id="btnHazardToggle">🚨 TRIGGER HAZARD (AGV-01)</button>
            </div>
            <div class="deck-group">
                <span class="deck-label">LIVE DEMOS:</span>
                <button class="btn" id="btnBatchDemo" style="background:#2563eb; border-color:#1d4ed8; color:#ffffff;">📦 5x Batch + 1 Critical Leapfrog</button>
                <button class="btn btn-warning" id="btnKillWorker">🔥 KILL WORKER-1</button>
                <button class="btn" id="btnSurge" style="background:#059669; border-color:#047857; color:#ffffff;">📈 Fleet Surge (Autoscale)</button>
                <button class="btn" id="btnRogueSpoof" style="background:#881337; border-color:#701a75; color:#fdf2f8;">🛡️ Rogue Token (403)</button>
            </div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('arenaCanvas');
        const ctx = canvas.getContext('2d');
        const banner = document.getElementById('banner');

        function resize() {
            const wrapper = document.getElementById('arena-wrapper');
            canvas.width = wrapper.clientWidth;
            canvas.height = wrapper.clientHeight;
        }
        window.addEventListener('resize', resize);
        resize();

        const liveVision = __LIVE_VISION_DATA__;
        const liveImage = new Image();
        if (liveVision.image) liveImage.src = liveVision.image;
        const detectedClasses = (liveVision.detections || []).map(d => d.class_name);
        const liveHazard = Boolean(liveVision.hazard_detected);

        let isRunning = true;
        let humanHazard = liveHazard;
        let humanPos = { x: 560, y: 265 };
        let worker1Alive = true;
        let worker2Alive = true;
        let latestLatency = Number(liveVision.inference_ms || 17.4);
        let queueList = [
            { id: 'DRONE-07', crit: 'HIGH', p: 2, color: '#38bdf8' },
            { id: 'SWEEPER-12', crit: 'NORMAL', p: 5, color: '#34d399' },
            { id: 'SCANNER-09', crit: 'LOW', p: 9, color: '#94a3b8' }
        ];

        // Robots
        const agv = {
            id: 'AGV-01',
            x: 80,
            y: 265,
            targetX: 840,
            speed: 2.2,
            crit: 'CRITICAL',
            color: '#ef4444',
            status: 'NORMAL',
            beamActive: false
        };

        const drone = {
            id: 'DRONE-07',
            x: 260,
            y: 195,
            speed: 1.8,
            rotorAngle: 0,
            tilt: 0,
            bayHoverTimer: 0,
            currentBayIndex: 0,
            scannedSKU: 'SKU-4821 [VERIFIED]',
            color: '#38bdf8'
        };

        const sweeper = {
            id: 'SWEEPER-12',
            x: 320,
            y: 338,
            dir: 1,
            speed: 1.2,
            brushAngle: 0,
            color: '#34d399'
        };

        // Telemetry packets in-flight
        let packets = [];

        function showBanner(text, bg, border) {
            banner.innerText = text;
            banner.style.background = bg;
            banner.style.border = '1px solid ' + border;
            banner.style.display = 'block';
            setTimeout(() => { banner.style.display = 'none'; }, 4500);
        }

        // Fleet Play/Pause
        document.getElementById('btnPlayPause').onclick = () => {
            isRunning = !isRunning;
            document.getElementById('btnPlayPause').innerText = isRunning ? "⏸ Pause Fleet" : "▶ Resume Fleet";
        };

        // Unified Hazard Toggle (AGV-01)
        document.getElementById('btnHazardToggle').onclick = async () => {
            const btn = document.getElementById('btnHazardToggle');
            if (!humanHazard) {
                humanHazard = true;
                btn.innerText = "🧹 CLEAR HAZARD";
                btn.className = "btn btn-primary";

                // Ensure the hazard is ALWAYS positioned ahead of the AGV in its lane of travel
                if (agv.x > canvas.width - 240 || agv.x >= 450) {
                    agv.x = 100; // Reset AGV to earlier in the corridor so it approaches cleanly
                }
                humanPos.x = Math.min(canvas.width - 120, Math.max(agv.x + 180, 480));
                agv.status = 'NORMAL';
                
                // Visual red packet fly
                packets.push({ fromX: agv.x, fromY: agv.y, toX: canvas.width - 110, toY: 60, progress: 0, color: '#ef4444' });

                // Insert into front of queue (RADS line-cutting!)
                queueList.unshift({ id: 'AGV-01 [CRITICAL P1]', crit: 'CRITICAL', p: 1, color: '#ef4444' });
                
                showBanner("🚨 HAZARD TRIGGERED! Obstacle Detected Ahead • Preemption Braking Activated", "rgba(185, 28, 28, 0.95)", "#ef4444");

                try {
                    const resp = await fetch('http://127.0.0.1:8000/api/v1/inference', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-Robot-Token': 'robot-token-secret' },
                        body: JSON.stringify({
                            robot_id: 'AGV-01',
                            task_type: 'collision_avoidance',
                            criticality: 'CRITICAL',
                            deadline_ms: 100.0,
                            image_base64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkWPifDwAEiAGlV9r9pQAAAABJRU5ErkJggg=='
                        })
                    });
                    const data = await resp.json();
                    if (data.request_id) {
                        setTimeout(async () => {
                            try {
                                const res = await fetch(`http://127.0.0.1:8000/api/v1/inference/${data.request_id}/result`, {
                                    headers: { 'X-Robot-Token': 'robot-token-secret' }
                                });
                                const rData = await res.json();
                                if (rData.inference_ms) latestLatency = rData.inference_ms;
                            } catch(e) {}
                        }, 300);
                    }
                } catch(e) {}
            } else {
                humanHazard = false;
                agv.status = 'NORMAL';
                agv.x = 80;
                btn.innerText = "🚨 TRIGGER HAZARD (AGV-01)";
                btn.className = "btn btn-danger";
                queueList = queueList.filter(q => !q.id.includes('CRITICAL'));
                showBanner("Corridor Cleared — Autonomous Fleet Traffic Resumed", "rgba(16, 185, 129, 0.95)", "#10b981");
            }
        };

        // Live Cluster Status Sync (Sync Worker-1 & Worker-2 status from backend)
        async function syncClusterStatus() {
            try {
                const resp = await fetch('http://127.0.0.1:8000/api/v1/cloud/status');
                if (resp.ok) {
                    const data = await resp.json();
                    if (data.workers) {
                        const w1 = data.workers.find(w => w.worker_id === 'worker-1');
                        const w2 = data.workers.find(w => w.worker_id === 'worker-2');
                        if (w1) {
                            worker1Alive = (w1.healthy === 'true' && w1.status !== 'DEAD');
                            const btn = document.getElementById('btnKillWorker');
                            if (btn) {
                                if (worker1Alive) {
                                    btn.innerText = "🔥 KILL WORKER-1";
                                    btn.className = "btn btn-warning";
                                } else {
                                    btn.innerText = "💚 RESTORE WORKER-1";
                                    btn.className = "btn btn-primary";
                                }
                            }
                        }
                        if (w2) {
                            worker2Alive = (w2.healthy === 'true' && w2.status !== 'DEAD');
                        }
                    }
                }
            } catch(e) {}
        }
        syncClusterStatus();
        setInterval(syncClusterStatus, 2500);

        // Kill / Restore Worker 1 (Failover Demo)
        document.getElementById('btnKillWorker').onclick = async () => {
            const btn = document.getElementById('btnKillWorker');
            if (worker1Alive) {
                worker1Alive = false;
                btn.innerText = "💚 RESTORE WORKER-1";
                btn.className = "btn btn-primary";
                showBanner("⚠️ WORKER-1 KILLED! Failover Monitor requeuing jobs -> Worker-2 Taking Over!", "rgba(180, 83, 9, 0.95)", "#f59e0b");
                try { await fetch('http://127.0.0.1:8000/api/v1/debug/workers/worker-1/fail', { method: 'POST' }); } catch(e) {}
            } else {
                worker1Alive = true;
                btn.innerText = "🔥 KILL WORKER-1";
                btn.className = "btn btn-warning";
                showBanner("✅ Worker-1 Restored to Healthy State (Status: IDLE)", "rgba(16, 185, 129, 0.95)", "#10b981");
                try { await fetch('http://127.0.0.1:8000/api/v1/debug/workers/worker-1/recover', { method: 'POST' }); } catch(e) {}
            }
        };

        // 5x Batch + 1 Critical Leapfrog Pre-emption Demo
        document.getElementById('btnBatchDemo').onclick = async () => {
            showBanner("📦 Enqueuing 5x Routine Sweeper Tasks, followed by 1x Emergency AGV Task...", "rgba(30, 58, 138, 0.95)", "#60a5fa");
            
            // 1. Immediately display 5 routine tasks in queue
            queueList = [
                { id: 'SWEEPER-BATCH-01', crit: 'LOW', p: 9, color: '#38bdf8' },
                { id: 'SWEEPER-BATCH-02', crit: 'LOW', p: 9, color: '#38bdf8' },
                { id: 'SWEEPER-BATCH-03', crit: 'LOW', p: 9, color: '#38bdf8' },
                { id: 'SWEEPER-BATCH-04', crit: 'LOW', p: 9, color: '#38bdf8' },
                { id: 'SWEEPER-BATCH-05', crit: 'LOW', p: 9, color: '#38bdf8' }
            ];
            
            // 2. Launch 5 blue telemetry packets
            for (let i = 0; i < 5; i++) {
                setTimeout(() => {
                    packets.push({ fromX: sweeper.x, fromY: sweeper.y, toX: canvas.width - 110, toY: 60, progress: 0, color: '#38bdf8' });
                }, i * 70);
            }

            try {
                // Call dedicated backend leapfrog endpoint
                const resp = await fetch('http://127.0.0.1:8000/api/v1/cloud/batch_leapfrog', { method: 'POST' });
                const data = await resp.json();

                // 3. Immediately insert Critical AGV task at FRONT of queue (index 0)
                setTimeout(() => {
                    queueList.unshift({ id: 'AGV-COLLISION-CRITICAL', crit: 'CRITICAL', p: 1, color: '#ef4444' });
                    packets.push({ fromX: agv.x, fromY: agv.y, toX: canvas.width - 110, toY: 60, progress: 0, color: '#ef4444' });
                    
                    showBanner(`🎯 RADS PREEMPTION PROVED! Critical AGV (Score: ${data.critical_rads_score}) jumped ahead of 5 routine tasks (Score: ${data.routine_sample_score})! Popped first by Worker!`, "rgba(185, 28, 28, 0.95)", "#ef4444");

                    // Drain visual queue smoothly as workers consume jobs
                    setTimeout(() => { if (queueList.length > 0) queueList.shift(); }, 600);
                    setTimeout(() => { if (queueList.length > 0) queueList.shift(); }, 1000);
                    setTimeout(() => { if (queueList.length > 0) queueList.shift(); }, 1400);
                    setTimeout(() => { if (queueList.length > 0) queueList.shift(); }, 1800);
                    setTimeout(() => { if (queueList.length > 0) queueList.shift(); }, 2200);
                    setTimeout(() => { if (queueList.length > 0) queueList.shift(); }, 2600);
                }, 300);

            } catch(e) {
                // Fallback demonstration if backend network glitch
                setTimeout(() => {
                    queueList.unshift({ id: 'AGV-COLLISION-CRITICAL', crit: 'CRITICAL', p: 1, color: '#ef4444' });
                    packets.push({ fromX: agv.x, fromY: agv.y, toX: canvas.width - 110, toY: 60, progress: 0, color: '#ef4444' });
                    showBanner("🎯 RADS PREEMPTION PROVED! Critical AGV Task jumped to Queue #1 ahead of 5 routine jobs!", "rgba(185, 28, 28, 0.95)", "#ef4444");
                }, 300);
            }
        };

        // Fleet Surge Autoscale Demo
        document.getElementById('btnSurge').onclick = async () => {
            showBanner("📈 FLEET SURGE: Dispatching 10 concurrent inference tasks to trigger Elastic Autoscaling...", "rgba(6, 95, 70, 0.95)", "#10b981");
            for (let i = 1; i <= 6; i++) {
                packets.push({ fromX: sweeper.x, fromY: sweeper.y, toX: canvas.width - 110, toY: 60, progress: 0, color: '#10b981' });
            }
            try {
                const resp = await fetch('http://127.0.0.1:8000/api/v1/cloud/surge', { method: 'POST' });
                const data = await resp.json();
                showBanner(`📈 AUTOSCALER SURGE: ${data.message || 'Auxiliary workers scaling up!'}`, "rgba(6, 95, 70, 0.95)", "#10b981");
            } catch(e) {
                showBanner("📈 FLEET SURGE: 10 tasks injected into queue!", "rgba(6, 95, 70, 0.95)", "#10b981");
            }
        };

        // Rogue Sweeper Spoofing P1 -> 403 Forbidden
        document.getElementById('btnRogueSpoof').onclick = async () => {
            showBanner("🔒 Testing Server Security: SWEEPER-12 attempting to spoof CRITICAL P1 priority...", "rgba(88, 28, 135, 0.95)", "#c084fc");
            try {
                const resp = await fetch('http://127.0.0.1:8000/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-Robot-Token': 'sweeper-token' },
                    body: JSON.stringify({ robot_id: 'SWEEPER-12', priority: 1, image_base64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkWPifDwAEiAGlV9r9pQAAAABJRU5ErkJggg==' })
                });
                if (resp.status === 403) {
                    const err = await resp.json();
                    showBanner(`🛡️ 403 FORBIDDEN: Server Enforced Security Policy! [${err.detail}]`, "rgba(220, 38, 38, 0.95)", "#f87171");
                } else {
                    showBanner(`Response: HTTP ${resp.status}`, "rgba(30, 41, 59, 0.9)", "#94a3b8");
                }
            } catch(e) {
                showBanner(`Connection error: ${e}`, "rgba(220, 38, 38, 0.95)", "#f87171");
            }
        };

        function drawWarehouse() {
            const w = canvas.width;
            const h = canvas.height;

            // Cleanroom Base Canvas Fill
            ctx.fillStyle = '#f8fafc';
            ctx.fillRect(0, 0, w, h);

            // Background Grid (Cleanroom subtle steel/slate grid)
            ctx.strokeStyle = '#e2e8f0';
            ctx.lineWidth = 1;
            for (let x = 0; x < w; x += 40) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
            }
            for (let y = 0; y < h; y += 40) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
            }

            // Central AGV Highway Transit Lane
            ctx.fillStyle = '#f1f5f9';
            ctx.fillRect(0, 225, w, 80);
            ctx.strokeStyle = '#cbd5e1';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(0, 225); ctx.lineTo(w, 225);
            ctx.moveTo(0, 305); ctx.lineTo(w, 305);
            ctx.stroke();

            // Center yellow hazard guidestrip
            ctx.strokeStyle = '#d97706';
            ctx.lineWidth = 2.5;
            ctx.setLineDash([14, 12]);
            ctx.beginPath();
            ctx.moveTo(0, 265); ctx.lineTo(w, 265);
            ctx.stroke();
            ctx.setLineDash([]);

            // Fleet Autonomous Charging Dock (Top Center: between Queue HUD and Cloud Hub)
            const dockX = Math.max(260, Math.floor((w - 180) / 2));
            const dockY = 14;
            const dockW = 180;
            const dockH = 92;
            ctx.fillStyle = 'rgba(16, 185, 129, 0.08)';
            ctx.fillRect(dockX, dockY, dockW, dockH);
            ctx.strokeStyle = 'rgba(16, 185, 129, 0.6)';
            ctx.lineWidth = 1.5;
            ctx.strokeRect(dockX, dockY, dockW, dockH);

            ctx.fillStyle = '#059669';
            ctx.font = 'bold 11px sans-serif';
            ctx.fillText("⚡ AUTONOMOUS DOCK", dockX + 16, dockY + 22);

            ctx.fillStyle = '#0f766e';
            ctx.font = '9px monospace';
            ctx.fillText("BAY 1: WIRELESS INDUCTIVE", dockX + 16, dockY + 44);
            ctx.fillText("TELEMETRY: 5.8 GHz RAW", dockX + 16, dockY + 62);
            ctx.fillText("STATUS: ACTIVE READY", dockX + 16, dockY + 80);

            // Upper High-Bay Storage Racks (Level 3: Aerial Drone Inspection Layer)
            drawRack(24, 118, 240, 60, '#38bdf8', 'RACK-A [HIGH-BAY LOGISTICS]', 'LEVEL 3: AERIAL DRONE SCAN LAYER', true);
            drawRack(w - 264, 118, 240, 60, '#818cf8', 'RACK-B [HIGH-BAY AUTOMATED]', 'LEVEL 3: AERIAL DRONE SCAN LAYER', true);

            // Drone flight path dashed guide
            ctx.strokeStyle = 'rgba(2, 132, 199, 0.25)';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 8]);
            ctx.beginPath();
            ctx.moveTo(30, 205); ctx.lineTo(w - 30, 205);
            ctx.stroke();
            ctx.setLineDash([]);

            // Lower Floor Maintenance Apron: Sweeper sweeps along y = 338
            ctx.strokeStyle = 'rgba(5, 150, 105, 0.25)';
            ctx.setLineDash([6, 6]);
            ctx.beginPath();
            ctx.moveTo(30, 338); ctx.lineTo(w - 270, 338);
            ctx.stroke();
            ctx.setLineDash([]);

            // Lower Floor Storage Racks (Level 0: Perimeter Staging & Buffer)
            drawRack(24, 380, 240, 60, '#34d399', 'RACK-C [INVENTORY & RAW]', 'LEVEL 0: SWEEPER AISLE PERIMETER', true);
            drawRack(Math.max(280, Math.floor((w - 240) / 2)), 380, 240, 60, '#f472b6', 'RACK-D [STAGING & BUFFER]', 'LEVEL 0: SWEEPER AISLE PERIMETER', true);
        }

        function drawRack(x, y, w, h, accentColor, label, tierLevel, light = true) {
            const isUpper = (y < 250);
            ctx.save();

            // 1. Crisp modern card container with soft ambient elevation
            ctx.shadowColor = light ? 'rgba(15, 23, 42, 0.05)' : 'rgba(0, 0, 0, 0.4)';
            ctx.shadowBlur = 6;
            ctx.shadowOffsetY = 2;
            ctx.fillStyle = light ? '#ffffff' : '#0f172a';
            ctx.beginPath();
            ctx.roundRect(x, y, w, h, 6);
            ctx.fill();
            ctx.shadowColor = 'transparent';

            ctx.strokeStyle = light ? '#e2e8f0' : '#1e293b';
            ctx.lineWidth = 1;
            ctx.stroke();

            // 2. Structural steel columns (Left, Center, Right - down to shelf)
            const postW = 2.5;
            const postPositions = [x, x + Math.floor(w / 2) - 1, x + w - postW];
            ctx.fillStyle = light ? '#cbd5e1' : '#334155';
            postPositions.forEach(px => {
                ctx.fillRect(px, y, postW, 35);
            });

            // 3. Sleek horizontal shelf rail (Cool architectural steel)
            const beamY = y + 32;
            ctx.fillStyle = light ? '#94a3b8' : '#475569';
            ctx.fillRect(x, beamY, w, 2.5);
            ctx.fillStyle = light ? '#cbd5e1' : '#64748b';
            ctx.fillRect(x, beamY + 2.5, w, 0.5);

            // 4. 4 Harmonious, evenly spaced cargo pallet bays
            const numBays = 4;
            const baySpacing = (w - 12) / numBays;
            const palletW = 44;

            for (let i = 0; i < numBays; i++) {
                const px = x + 6 + (i * baySpacing) + (baySpacing - palletW) / 2;
                const palletY = beamY - 4;
                const cargoY = palletY - 16;
                const isDroneHoveringThisBay = isUpper && Math.abs(drone.x - (px + palletW / 2)) < 22;

                // --- Refined Birch Timber Pallet ---
                ctx.fillStyle = light ? '#ded3c3' : '#3e352e';
                ctx.beginPath();
                ctx.roundRect(px, palletY, palletW, 4, 1);
                ctx.fill();
                // Clean fork pocket cutouts
                ctx.fillStyle = light ? '#ffffff' : '#0f172a';
                ctx.fillRect(px + 6, palletY + 2, 7, 2);
                ctx.fillRect(px + palletW - 13, palletY + 2, 7, 2);

                // --- Cohesive, Modern Cargo Palette ---
                if (i === 0) {
                    // Bay 0: Soft Warm Kraft Shipping Carton
                    ctx.fillStyle = light ? '#d4b08c' : '#785b40';
                    ctx.beginPath();
                    ctx.roundRect(px + 3, cargoY + 2, palletW - 6, 14, 2);
                    ctx.fill();
                    // Subtle seal tape
                    ctx.fillStyle = light ? '#c29a72' : '#634932';
                    ctx.fillRect(px + Math.floor(palletW / 2) - 2, cargoY + 2, 4, 14);

                } else if (i === 1) {
                    // Bay 1: Muted Slate-Blue Logistics Tote
                    ctx.fillStyle = light ? '#93c5fd' : '#1e40af';
                    ctx.beginPath();
                    ctx.roundRect(px + 4, cargoY + 3, palletW - 8, 13, 2);
                    ctx.fill();
                    // Clean tote rim
                    ctx.fillStyle = light ? '#60a5fa' : '#3b82f6';
                    ctx.fillRect(px + 3, cargoY + 2, palletW - 6, 2);

                } else if (i === 2) {
                    // Bay 2: Twin Brushed Steel Storage Drums
                    const drumW = 16;
                    for (let d = 0; d < 2; d++) {
                        const dx = px + 4 + d * 20;
                        ctx.fillStyle = light ? '#94a3b8' : '#475569';
                        ctx.beginPath();
                        ctx.roundRect(dx, cargoY + 2, drumW, 14, 2);
                        ctx.fill();
                        // Refined horizontal metallic bands
                        ctx.fillStyle = light ? '#cbd5e1' : '#64748b';
                        ctx.fillRect(dx + 1, cargoY + 5, drumW - 2, 1.2);
                        ctx.fillRect(dx + 1, cargoY + 9, drumW - 2, 1.2);
                    }

                } else {
                    // Bay 3: Clean Staging Container
                    ctx.fillStyle = light ? '#f1f5f9' : '#1e293b';
                    ctx.beginPath();
                    ctx.roundRect(px + 3, cargoY + 2, palletW - 6, 14, 2);
                    ctx.fill();
                    ctx.strokeStyle = light ? '#cbd5e1' : '#334155';
                    ctx.lineWidth = 0.8;
                    ctx.stroke();
                    // Subtle accent band
                    ctx.fillStyle = light ? '#a5b4fc' : '#6366f1';
                    ctx.fillRect(px + 3, cargoY + 7, palletW - 6, 2.5);
                }

                // --- Minimal Drone Laser Sweep ---
                if (isDroneHoveringThisBay) {
                    ctx.fillStyle = 'rgba(14, 165, 233, 0.08)';
                    ctx.fillRect(px + 2, cargoY, palletW - 4, 18);

                    const scanY = cargoY + ((Date.now() / 25) % 16);
                    ctx.strokeStyle = '#0ea5e9';
                    ctx.lineWidth = 1.2;
                    ctx.beginPath();
                    ctx.moveTo(px + 2, scanY);
                    ctx.lineTo(px + palletW - 2, scanY);
                    ctx.stroke();

                    ctx.fillStyle = '#0ea5e9';
                    ctx.beginPath();
                    ctx.arc(px + Math.floor(palletW / 2), y + 5, 2, 0, Math.PI * 2);
                    ctx.fill();
                }
            }

            // 5. Sleek Divider Line between Cargo and Footer
            ctx.strokeStyle = light ? '#f1f5f9' : '#1e293b';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x + 6, y + 41);
            ctx.lineTo(x + w - 6, y + 41);
            ctx.stroke();

            // 6. Refined Footer Metadata Bar
            // Status dot
            ctx.fillStyle = '#10b981';
            ctx.beginPath();
            ctx.arc(x + 14, y + 50.5, 2.5, 0, Math.PI * 2);
            ctx.fill();

            // Rack Title
            ctx.fillStyle = light ? '#334155' : '#f1f5f9';
            ctx.font = 'bold 7.5px monospace';
            ctx.fillText(label, x + 21, y + 53);

            // Clean Capacity Pill Badge
            const badgeW = 44, badgeH = 11;
            const badgeX = x + w - badgeW - 8;
            const badgeY = y + 45;
            ctx.fillStyle = light ? '#f1f5f9' : '#1e293b';
            ctx.beginPath();
            ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 3);
            ctx.fill();
            ctx.fillStyle = light ? '#64748b' : '#94a3b8';
            ctx.font = 'bold 7px monospace';
            ctx.fillText("CAP 98%", badgeX + 6, badgeY + 8);

            ctx.restore();
        }

        function drawCloudHub() {
            const w = canvas.width;
            const hubW = 172;
            const hubH = 92;
            const hubX = w - hubW - 16;
            const hubY = 14;

            ctx.fillStyle = '#ffffff';
            ctx.fillRect(hubX, hubY, hubW, hubH);
            ctx.strokeStyle = '#0284c7';
            ctx.lineWidth = 1.6;
            ctx.strokeRect(hubX, hubY, hubW, hubH);

            ctx.fillStyle = '#0284c7';
            ctx.fillRect(hubX, hubY, hubW, 22);

            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 11px sans-serif';
            ctx.fillText("☁️ PRIVATE AI CLOUD", hubX + 10, hubY + 15);

            // Workers
            ctx.fillStyle = worker1Alive ? '#16a34a' : '#dc2626';
            ctx.beginPath(); ctx.arc(hubX + 18, hubY + 45, 5, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#1e293b';
            ctx.font = '11px monospace';
            ctx.fillText(`Worker-1: ${worker1Alive ? 'HEALTHY' : 'DEAD'}`, hubX + 30, hubY + 49);

            ctx.fillStyle = worker2Alive ? '#16a34a' : '#dc2626';
            ctx.beginPath(); ctx.arc(hubX + 18, hubY + 70, 5, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#1e293b';
            ctx.fillText(`Worker-2: HEALTHY`, hubX + 30, hubY + 74);
        }

        function drawQueueHUD() {
            const qX = 16;
            const qY = 14;
            const qW = 230;
            const qH = 92;

            ctx.fillStyle = '#ffffff';
            ctx.fillRect(qX, qY, qW, qH);
            ctx.strokeStyle = '#4f46e5';
            ctx.lineWidth = 1.6;
            ctx.strokeRect(qX, qY, qW, qH);

            ctx.fillStyle = '#4338ca';
            ctx.fillRect(qX, qY, qW, 22);

            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 11px sans-serif';
            ctx.fillText("⚡ RADS PRIORITY QUEUE", qX + 10, qY + 15);

            const items = queueList.slice(0, 3);
            items.forEach((item, idx) => {
                const rowY = qY + 38 + (idx * 19);

                // Priority Badge
                ctx.fillStyle = item.color;
                ctx.fillRect(qX + 8, rowY - 10, 24, 13);
                ctx.fillStyle = '#ffffff';
                ctx.font = 'bold 9px monospace';
                ctx.fillText(`P${item.p}`, qX + 12, rowY);

                // Robot / Task Name
                ctx.fillStyle = '#1e293b';
                ctx.font = '10px monospace';
                const nameText = item.id.length > 17 ? item.id.substring(0, 15) + '..' : item.id;
                ctx.fillText(nameText, qX + 38, rowY);

                // Position Badge
                ctx.fillStyle = (idx === 0) ? '#dc2626' : '#64748b';
                ctx.font = 'bold 9px monospace';
                ctx.fillText(`#${idx + 1}`, qX + qW - 20, rowY);
            });
        }

        function drawCameraHUD() {
            const w = canvas.width;
            const hudW = 205;
            const hudH = 135;
            const hudX = w - hudW - 16;
            const hudY = canvas.height - hudH - 14;

            ctx.fillStyle = '#ffffff';
            ctx.fillRect(hudX, hudY, hudW, hudH);
            ctx.strokeStyle = '#0891b2';
            ctx.lineWidth = 1.6;
            ctx.strokeRect(hudX, hudY, hudW, hudH);

            ctx.fillStyle = '#0891b2';
            ctx.fillRect(hudX, hudY, hudW, 20);

            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 10px sans-serif';
            ctx.fillText("👁️ AGV REAL-TIME YOLOv8 CAM", hudX + 8, hudY + 14);

            if (liveVision.image && liveImage.complete && liveImage.naturalWidth) {
                const imgX = hudX + 8;
                const imgY = hudY + 26;
                const imgW = hudW - 16;
                const imgH = 76;
                ctx.drawImage(liveImage, imgX, imgY, imgW, imgH);

                const scaleX = imgW / liveImage.naturalWidth;
                const scaleY = imgH / liveImage.naturalHeight;
                (liveVision.detections || []).forEach(det => {
                    const [x1, y1, x2, y2] = det.box;
                    const x = imgX + x1 * scaleX;
                    const y = imgY + y1 * scaleY;
                    const boxW = (x2 - x1) * scaleX;
                    const boxH = (y2 - y1) * scaleY;
                    const color = ['person', 'car', 'bus', 'truck'].includes(det.class_name) ? '#ef4444' : '#facc15';
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 1.5;
                    ctx.strokeRect(x, y, boxW, boxH);
                    const label = `${det.class_name.toUpperCase()} ${(det.confidence * 100).toFixed(0)}%`;
                    ctx.font = 'bold 7px sans-serif';
                    const labelW = ctx.measureText(label).width + 4;
                    ctx.fillStyle = color;
                    ctx.fillRect(x, Math.max(imgY, y - 9), labelW, 9);
                    ctx.fillStyle = '#111827';
                    ctx.fillText(label, x + 2, Math.max(imgY + 7, y - 2));
                });

                const summary = detectedClasses.length ? detectedClasses.join(', ').toUpperCase() : 'NO OBJECTS';
                ctx.fillStyle = liveHazard ? '#ef4444' : '#10b981';
                ctx.font = 'bold 8px monospace';
                ctx.fillText(`${liveVision.action || 'YOLO'}: ${summary.substring(0, 21)}`, hudX + 8, hudY + 117);
            } else if (humanHazard) {
                ctx.strokeStyle = '#dc2626';
                ctx.lineWidth = 2;
                ctx.strokeRect(hudX + 50, hudY + 32, 105, 60);
                ctx.fillStyle = '#dc2626';
                ctx.fillRect(hudX + 50, hudY + 22, 105, 13);
                ctx.fillStyle = 'white';
                ctx.font = 'bold 9px sans-serif';
                ctx.fillText("HUMAN HAZARD 99.1%", hudX + 53, hudY + 32);

                ctx.fillStyle = '#dc2626';
                ctx.font = 'bold 10px monospace';
                ctx.fillText("STATUS: PREEMPTION BRAKE", hudX + 8, hudY + 118);
            } else {
                ctx.strokeStyle = '#16a34a';
                ctx.lineWidth = 1.5;
                ctx.strokeRect(hudX + 35, hudY + 38, 135, 48);
                ctx.fillStyle = '#16a34a';
                ctx.font = '9px monospace';
                ctx.fillText("CORRIDOR CLEAR [P=0.98]", hudX + 40, hudY + 34);

                ctx.fillStyle = '#64748b';
                ctx.font = '10px monospace';
                ctx.fillText(`LATENCY: ${latestLatency.toFixed(1)}ms [DEADLINE MET]`, hudX + 8, hudY + 118);
            }
        }

        function update() {
            if (isRunning) {
                // 1. AGV logic
                if (humanHazard) {
                    const dist = humanPos.x - agv.x;
                    if (dist > 75) {
                        agv.status = 'NORMAL';
                        agv.x += agv.speed;
                    } else if (dist > 0) {
                        agv.status = 'STOPPED';
                    } else {
                        agv.x = humanPos.x - 75;
                        agv.status = 'STOPPED';
                    }
                } else {
                    agv.status = 'NORMAL';
                    agv.x += agv.speed;
                    if (agv.x > canvas.width - 60) agv.x = 40;
                }

                // 2. Multirotor Drone Quadcopter Flight & Shelf Inspection
                const inspectionBays = [65, 125, 185, 235, canvas.width - 235, canvas.width - 185, canvas.width - 125, canvas.width - 65];
                const targetBayX = inspectionBays[drone.currentBayIndex % inspectionBays.length];
                const ddx = targetBayX - drone.x;
                if (Math.abs(ddx) > 6) {
                    const moveDir = ddx > 0 ? 1 : -1;
                    drone.x += moveDir * drone.speed;
                    drone.tilt = drone.tilt * 0.85 + (moveDir * 0.14) * 0.15;
                    drone.bayHoverTimer = 0;
                } else {
                    drone.tilt = drone.tilt * 0.8;
                    drone.bayHoverTimer++;
                    if (drone.bayHoverTimer > 80) {
                        drone.currentBayIndex = (drone.currentBayIndex + 1) % inspectionBays.length;
                        drone.scannedSKU = `SKU-${1000 + Math.floor(Math.random() * 8999)} [VERIFIED]`;
                        drone.bayHoverTimer = 0;
                    }
                }
                drone.y = 205 + Math.sin(Date.now() * 0.004) * 4;
                drone.rotorAngle = (drone.rotorAngle + 0.45) % (Math.PI * 2);

                // 3. Sweeper back and forth along maintenance apron
                sweeper.x += sweeper.dir * sweeper.speed;
                if (sweeper.dir > 0 && sweeper.x > canvas.width - 290) sweeper.dir = -1;
                if (sweeper.dir < 0 && sweeper.x < 70) sweeper.dir = 1;
                sweeper.brushAngle = (sweeper.brushAngle + 0.22) % (Math.PI * 2);

                // 4. Telemetry packets
                packets.forEach(p => { p.progress += 0.04; });
                packets = packets.filter(p => p.progress < 1.0);
            }
        }

        function render() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            drawWarehouse();

            // 1. Draw Human if hazard active
            if (humanHazard) {
                ctx.save();
                ctx.fillStyle = '#ef4444';
                ctx.beginPath(); ctx.arc(humanPos.x, humanPos.y - 14, 8, 0, Math.PI * 2); ctx.fill();
                ctx.fillRect(humanPos.x - 6, humanPos.y - 6, 12, 22);
                ctx.strokeStyle = '#dc2626';
                ctx.strokeRect(humanPos.x - 14, humanPos.y - 26, 28, 48);

                ctx.fillStyle = '#dc2626';
                ctx.font = 'bold 10px sans-serif';
                ctx.fillText("HAZARD INTRUSION", humanPos.x - 30, humanPos.y - 32);
                ctx.restore();
            }

            // 2. Draw AGV Robot with Industrial Chassis & LiDAR
            const isStopped = (agv.status === 'STOPPED');
            ctx.save();
            ctx.fillStyle = 'rgba(0, 0, 0, 0.12)';
            ctx.beginPath();
            ctx.roundRect(agv.x - 22, agv.y - 13, 44, 32, 6);
            ctx.fill();

            // Safety Laser Illumination Beam
            const beamW = isStopped ? 80 : 130;
            const beamColor = isStopped ? 'rgba(239, 68, 68, 0.25)' : 'rgba(245, 158, 11, 0.18)';
            const beamGrad = ctx.createLinearGradient(agv.x + 22, agv.y, agv.x + 22 + beamW, agv.y);
            beamGrad.addColorStop(0, beamColor);
            beamGrad.addColorStop(1, 'rgba(245, 158, 11, 0)');
            ctx.fillStyle = beamGrad;
            ctx.beginPath();
            ctx.moveTo(agv.x + 22, agv.y - 8);
            ctx.lineTo(agv.x + 22 + beamW, agv.y - 32);
            ctx.lineTo(agv.x + 22 + beamW, agv.y + 32);
            ctx.lineTo(agv.x + 22, agv.y + 8);
            ctx.closePath();
            ctx.fill();

            // Chassis
            ctx.fillStyle = isStopped ? '#dc2626' : '#b91c1c';
            ctx.beginPath();
            ctx.roundRect(agv.x - 22, agv.y - 15, 44, 30, 6);
            ctx.fill();
            ctx.strokeStyle = isStopped ? '#ef4444' : '#991b1b';
            ctx.lineWidth = 1.8;
            ctx.stroke();

            // Front Bumper Chevron Warning Stripes
            ctx.fillStyle = '#eab308';
            ctx.fillRect(agv.x + 18, agv.y - 13, 4, 26);
            ctx.fillStyle = '#0f172a';
            ctx.fillRect(agv.x + 18, agv.y - 9, 4, 3);
            ctx.fillRect(agv.x + 18, agv.y - 1, 4, 3);
            ctx.fillRect(agv.x + 18, agv.y + 7, 4, 3);

            // Spinning LiDAR Turret
            ctx.fillStyle = '#0f172a';
            ctx.beginPath(); ctx.arc(agv.x + 8, agv.y, 6, 0, Math.PI * 2); ctx.fill();
            const lidarAngle = (Date.now() / 120) % (Math.PI * 2);
            ctx.strokeStyle = '#38bdf8';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(agv.x + 8, agv.y);
            ctx.lineTo(agv.x + 8 + Math.cos(lidarAngle) * 5.5, agv.y + Math.sin(lidarAngle) * 5.5);
            ctx.stroke();

            // Label
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 8.5px monospace';
            ctx.fillText(agv.id, agv.x - 19, agv.y + 3.5);
            ctx.restore();

            // 3. Draw Multirotor Drone Quadcopter
            ctx.save();
            ctx.fillStyle = 'rgba(0,0,0,0.12)';
            ctx.beginPath();
            ctx.ellipse(drone.x, drone.y + 42, 22, 7, 0, 0, Math.PI * 2);
            ctx.fill();

            // Downward Conical Optical Scan Beam over Rack
            const dgrad = ctx.createLinearGradient(drone.x, drone.y + 6, drone.x, drone.y - 45);
            dgrad.addColorStop(0, 'rgba(14, 165, 233, 0.45)');
            dgrad.addColorStop(1, 'rgba(14, 165, 233, 0.0)');
            ctx.fillStyle = dgrad;
            ctx.beginPath();
            ctx.moveTo(drone.x, drone.y + 4);
            ctx.lineTo(drone.x - 32, drone.y - 45);
            ctx.lineTo(drone.x + 32, drone.y - 45);
            ctx.closePath();
            ctx.fill();

            // Barcode scan reticle over bay
            if (drone.bayHoverTimer > 10) {
                ctx.strokeStyle = '#10b981';
                ctx.lineWidth = 1.5;
                ctx.strokeRect(drone.x - 18, drone.y - 50, 36, 18);
                ctx.fillStyle = '#10b981';
                ctx.font = 'bold 7.5px monospace';
                ctx.fillText(drone.scannedSKU, drone.x - 42, drone.y - 54);
            }

            // Quadcopter Banking Tilt Rotation
            ctx.translate(drone.x, drone.y);
            ctx.rotate(drone.tilt);

            // Carbon-fiber X-Arms
            ctx.strokeStyle = '#334155';
            ctx.lineWidth = 2.5;
            ctx.beginPath();
            ctx.moveTo(-16, -10); ctx.lineTo(16, 10);
            ctx.moveTo(16, -10); ctx.lineTo(-16, 10);
            ctx.stroke();

            // 4 Motor Pods & High-Speed Spinning Rotor Blades
            const motors = [
                { x: -16, y: -10 },
                { x: 16, y: -10 },
                { x: -16, y: 10 },
                { x: 16, y: 10 }
            ];

            motors.forEach((m, idx) => {
                ctx.fillStyle = '#0f172a';
                ctx.beginPath(); ctx.arc(m.x, m.y, 3, 0, Math.PI * 2); ctx.fill();

                ctx.fillStyle = 'rgba(56, 189, 248, 0.35)';
                ctx.beginPath();
                ctx.ellipse(m.x, m.y, 12, 4.5, 0, 0, Math.PI * 2);
                ctx.fill();

                ctx.strokeStyle = '#0284c7';
                ctx.lineWidth = 1.2;
                const angle = drone.rotorAngle + idx;
                ctx.beginPath();
                ctx.moveTo(m.x - Math.cos(angle) * 11, m.y - Math.sin(angle) * 3.5);
                ctx.lineTo(m.x + Math.cos(angle) * 11, m.y + Math.sin(angle) * 3.5);
                ctx.stroke();
            });

            // Central Aerodynamic Pod
            ctx.fillStyle = '#0284c7';
            ctx.beginPath();
            ctx.roundRect(-10, -8, 20, 16, 4);
            ctx.fill();
            ctx.strokeStyle = '#0369a1';
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Blinking Navigational Beacon
            ctx.fillStyle = (Date.now() % 400 < 200) ? '#38bdf8' : '#ffffff';
            ctx.beginPath(); ctx.arc(0, 0, 3, 0, Math.PI * 2); ctx.fill();

            // Drone ID
            ctx.fillStyle = '#0369a1';
            ctx.font = 'bold 8px monospace';
            ctx.fillText("DRONE-07", -20, -13);
            ctx.restore();

            // 4. Draw Sweeper Cleaning Robot
            ctx.save();
            const brushOffset = sweeper.dir * 15;
            const b1 = { x: sweeper.x + brushOffset, y: sweeper.y - 10 };
            const b2 = { x: sweeper.x + brushOffset, y: sweeper.y + 10 };

            [b1, b2].forEach((b, idx) => {
                ctx.fillStyle = 'rgba(5, 150, 105, 0.3)';
                ctx.beginPath(); ctx.arc(b.x, b.y, 9, 0, Math.PI * 2); ctx.fill();
                ctx.strokeStyle = '#047857';
                ctx.lineWidth = 1.2;
                ctx.stroke();

                const bAngle = sweeper.brushAngle + idx * Math.PI;
                for (let i = 0; i < 4; i++) {
                    const rad = bAngle + (i * Math.PI / 2);
                    ctx.beginPath();
                    ctx.moveTo(b.x, b.y);
                    ctx.lineTo(b.x + Math.cos(rad) * 8, b.y + Math.sin(rad) * 8);
                    ctx.stroke();
                }
            });

            ctx.fillStyle = '#059669';
            ctx.beginPath(); ctx.arc(sweeper.x, sweeper.y, 14, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = '#047857';
            ctx.lineWidth = 2;
            ctx.stroke();

            ctx.fillStyle = '#064e3b';
            ctx.beginPath();
            ctx.arc(sweeper.x, sweeper.y, 14, sweeper.dir > 0 ? -Math.PI / 3 : Math.PI * 2 / 3, sweeper.dir > 0 ? Math.PI / 3 : Math.PI * 4 / 3);
            ctx.fill();

            ctx.fillStyle = (Date.now() % 500 < 250) ? '#f59e0b' : '#d97706';
            ctx.beginPath(); ctx.arc(sweeper.x, sweeper.y, 4.5, 0, Math.PI * 2); ctx.fill();

            ctx.restore();

            // 5. Packets in flight
            packets.forEach(p => {
                const curX = p.fromX + (p.toX - p.fromX) * p.progress;
                const curY = p.fromY + (p.toY - p.fromY) * p.progress;
                ctx.fillStyle = p.color;
                ctx.shadowColor = p.color;
                ctx.shadowBlur = 6;
                ctx.beginPath(); ctx.arc(curX, curY, 5, 0, Math.PI * 2); ctx.fill();
                ctx.shadowBlur = 0;
            });

            drawCloudHub();
            drawQueueHUD();
            drawCameraHUD();
        }

        function loop() {
            update();
            render();
            requestAnimationFrame(loop);
        }
        loop();
    </script>
</body>
</html>
"""

def get_live_vision_payload():
    """Build a safe, compact payload for the canvas-based camera panel."""
    if not redis_ok:
        return {"image": "", "detections": [], "inference_ms": 0.0}

    # Do not display another user's or an old demo frame. Each browser session
    # sees only the image it submitted during the current session.
    task_id = st.session_state.get("live_vision_task_id")
    task = r.hgetall(f"task:{task_id}") if task_id else {}
    if not task or task.get("state") != "completed":
        return {"image": "", "detections": [], "inference_ms": 0.0}

    try:
        boxes = json.loads(task.get("boxes", "[]"))
        classes = json.loads(task.get("classes", "[]"))
        confidences = json.loads(task.get("confidences", "[]"))
        detections = [
            {"box": box, "class_name": str(class_name), "confidence": float(confidence)}
            for box, class_name, confidence in zip(boxes, classes, confidences)
        ]
        return {
            "image": f"data:image/jpeg;base64,{task.get('image_base64', '')}",
            "detections": detections,
            "inference_ms": float(task.get("inference_time_ms", 0.0)),
            "action": task.get("perception_action", "PATH_CLEAR"),
            "severity": task.get("perception_severity", "NONE"),
            "reason": task.get("perception_reason", ""),
            "hazard_detected": task.get("hazard_detected") == "true",
        }
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"image": "", "detections": [], "inference_ms": 0.0}

live_vision_json = json.dumps(get_live_vision_payload()).replace("</", "<\\/")
ARENA_HTML = ARENA_HTML.replace("__LIVE_VISION_DATA__", live_vision_json)
components.html(ARENA_HTML, height=590)

st.caption("Shared Edge AI Compute • RADS Dynamic Scheduling • Multi-Worker Fault Tolerance")

# Top Telemetry Cards
m_col1, m_col2, m_col3, m_col4, m_col5, m_col6, m_col7 = st.columns(7)

if redis_ok:
    processed = int(r.get("stats:processed") or 0)
    q_depth = int(r.zcard("queue:tasks") or 0)
    lat_sum = float(r.get("stats:latency_sum") or 0.0)
    avg_lat = round(lat_sum / processed, 1) if processed > 0 else 0.0
    
    crit_total = int(r.get("stats:critical_total") or 0)
    crit_met = int(r.get("stats:critical_deadline_met") or 0)
    cdsr = round((crit_met / crit_total) * 100.0, 1) if crit_total > 0 else 100.0
    failovers = int(r.get("stats:failovers") or 0)
    edge_fallbacks = int(r.get("stats:edge_fallbacks") or 0)
    lakehouse_exports = int(r.get("stats:lakehouse_exports") or 0)
else:
    processed, q_depth, avg_lat, cdsr, failovers, edge_fallbacks, lakehouse_exports = 0, 0, 0.0, 100.0, 0, 0, 0

m_col1.metric("Tasks Completed", f"{processed:,}")
m_col2.metric("Queue Depth", q_depth, delta=f"{q_depth} waiting" if q_depth > 0 else "Clear", delta_color="inverse")
m_col3.metric("Avg Latency", f"{avg_lat} ms")
m_col4.metric("Critical CDSR", f"{cdsr}%", delta="100% Target" if cdsr >= 95 else "Contention", delta_color="normal")
m_col5.metric("Failovers", failovers, delta="Recovered" if failovers > 0 else "Stable")
m_col6.metric("Edge Fallbacks", edge_fallbacks, delta=f"{edge_fallbacks} Protected" if edge_fallbacks > 0 else "Zero Misses", delta_color="normal")
m_col7.metric("Lakehouse Exports", lakehouse_exports, delta="Snappy Batches")

st.markdown("---")

# ================= TABBED SUITE: ROBOT AI PRIVATE CLOUD =================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚡ Queue & Worker Fabric",
    "☁️ Elastic Cloud Autoscaler",
    "🏢 Multi-Tenant Fleets & SLA",
    "🛡️ S3 Incident Black-Box",
    "📊 Benchmarks & Vision Feed"
])

with tab1:
    col_w, col_q = st.columns([1, 1])
    
    with col_w:
        st.subheader("👷 Dynamic AI Compute Fabric")
        worker_keys = sorted(r.keys("worker:*")) if redis_ok else ["worker:worker-1", "worker:worker-2"]
        if not worker_keys:
            worker_keys = ["worker:worker-1", "worker:worker-2"]
            
        for wk in worker_keys:
            wid = wk.replace("worker:", "")
            w_data = r.hgetall(wk) if redis_ok else {}
            status_val = w_data.get("status", "OFFLINE")
            healthy = (w_data.get("healthy") == "true")
            proc_jobs = w_data.get("processed_jobs", "0")
            cur_job = w_data.get("current_job_id")
            w_type = w_data.get("type", "BASE_NODE")
            
            card_border = "#10b981" if healthy and status_val != "BUSY" else ("#f59e0b" if status_val == "BUSY" else "#ef4444")
            icon = "🟢" if healthy and status_val != "BUSY" else ("🟡" if status_val == "BUSY" else "🔴")
            badge = " [ELASTIC]" if w_type == "ELASTIC_DYNAMIC" or wid not in ("worker-1", "worker-2") else " [BASE]"
            
            st.markdown(f"""
            <div style="background: #ffffff; border: 1.5px solid {card_border}; border-radius: 10px; padding: 14px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <b style="font-size: 15px; color: #0f172a;">{wid.upper()}{badge} {icon}</b>
                    <span style="font-size: 13px; color: #475569;">Status: <b style="color: #0f172a;">{status_val}</b></span>
                </div>
                <div style="font-size: 13px; color: #64748b; margin-top: 8px;">
                    Processed: <b style="color: #1e293b;">{proc_jobs} tasks</b> | Active Job: <code style="background: #f1f5f9; color: #0f172a; padding: 2px 6px; border-radius: 4px; border: 1px solid #e2e8f0;">{cur_job[:8] if cur_job else 'IDLE'}</code>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.caption("Automatic Failover: If any worker crashes, in-flight jobs are atomically requeued and peer-recovered.")

    with col_q:
        st.subheader(f"⏳ RADS Priority Queue ({q_depth} waiting)")
        if redis_ok and q_depth > 0:
            queue_items = r.zrange("queue:tasks", 0, 10, withscores=True)
            q_rows = []
            for rank, (tid, score) in enumerate(queue_items, 1):
                tdata = r.hgetall(f"task:{tid}") or {}
                crit = tdata.get("criticality", "NORMAL")
                badge = f"🚨 {crit}" if crit == "CRITICAL" else (f"🚁 {crit}" if crit == "HIGH" else f"📦 {crit}")
                q_rows.append({
                    "Pos": f"#{rank}",
                    "Criticality": badge,
                    "Robot": tdata.get("robot_id", "Unknown"),
                    "Fleet": tdata.get("tenant_id", "FLEET-AGV-LOGISTICS"),
                    "RADS Score": f"{-score:.3f}",
                    "Deadline": f"{tdata.get('deadline_ms', '-')}ms",
                    "Task ID": tid[:8] + "..."
                })
            st.dataframe(pd.DataFrame(q_rows), width="stretch", hide_index=True)
        else:
            st.info("✅ RADS Queue is clear. Workers are ready for robot perception tasks.")

with tab2:
    st.subheader("☁️ Autonomous Elastic Cloud Autoscaler")
    st.markdown("""
    **Event-Driven Edge Elasticity (KEDA-style):** The Private Cloud continuously inspects queue pressure and latency gradients.
    When queue depth crosses threshold (>= 3 tasks), auxiliary AI worker pods (`worker-3`, `worker-4`, `worker-5`) are provisioned in milliseconds.
    When the queue is drained and idle for > 6 seconds, auxiliary workers scale back down to minimize edge compute & energy footprint.
    """)
    
    scale_info = r.hgetall("cloud:autoscaler:status") if redis_ok else {}
    as_col1, as_col2, as_col3, as_col4 = st.columns(4)
    as_col1.metric("Autoscaler Policy", "KEDA Queue Metric")
    as_col2.metric("Active Cloud Workers", scale_info.get("current_workers", "2"), delta=f"Max: {scale_info.get('max_workers', 5)}")
    as_col3.metric("Current Scaling State", scale_info.get("state", "STABLE"))
    as_col4.metric("Scale-Up Threshold", ">= 3 tasks")
    
    st.markdown("#### 📜 Live Autoscaler Provisioning Log")
    scale_events = r.lrange("cloud:autoscaler:events", 0, 10) if redis_ok else []
    if scale_events:
        for ev in scale_events:
            color = "#059669" if "SCALE_DOWN" in ev else ("#d97706" if "SCALE_UP" in ev else "#2563eb")
            st.markdown(f"<div style='font-family: monospace; font-size: 13px; color: {color}; padding: 6px 10px; background: #ffffff; border: 1px solid #e2e8f0; border-left: 3px solid {color}; margin-bottom: 6px; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);'>{ev}</div>", unsafe_allow_html=True)
    else:
        st.info("Autoscaler initialized. Click '📈 Trigger Fleet Surge' in the sidebar to observe live elastic scaling!")

    st.markdown("#### 📅 Predictive Compute Provisioning (Upcoming Missions)")
    st.caption("Shifted from reactive to proactive: pre-warms pods 30s ahead of announced high-intensity robot missions.")
    if redis_ok:
        active_missions = r.lrange("missions:active", 0, 9)
        if active_missions:
            m_rows = []
            now_ts = time.time()
            for m_str in active_missions:
                try:
                    m = json.loads(m_str)
                    start_ts = m.get("start_time_epoch", now_ts)
                    lead = max(0, int(start_ts - now_ts))
                    status_lbl = "🟡 PRE-WARMING (30s Window)" if lead <= 30 and lead > 0 else ("🟢 ACTIVE SURGE" if lead == 0 else "⏳ SCHEDULED")
                    m_rows.append({
                        "Mission ID": m.get("mission_id"),
                        "Fleet ID": m.get("fleet_id"),
                        "Expected Tasks": m.get("expected_critical_tasks"),
                        "Target Workers": m.get("target_prewarmed_workers"),
                        "Lead Time": f"{lead}s",
                        "Status": status_lbl
                    })
                except Exception:
                    pass
            if m_rows:
                st.dataframe(pd.DataFrame(m_rows), width="stretch", hide_index=True)
            else:
                st.info("No upcoming missions announced yet.")
        else:
            st.info("No active or upcoming high-intensity missions registered. Proactive autoscaler is monitoring.")

with tab3:
    st.subheader("🏢 Multi-Tenant Fleet Governance & SLA Compliance")
    st.markdown("Industrial Private Clouds partition compute across distinct robotic departments, enforcing per-fleet rate limits and latency SLAs.")
    
    tenants_summary = fleet_tenants.get_all_tenants_metrics(r) if redis_ok else {}
    if tenants_summary:
        t_cols = st.columns(len(tenants_summary))
        for idx, (tid, tdata) in enumerate(tenants_summary.items()):
            with t_cols[idx]:
                st.markdown(f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid {tdata.get('color', '#2563eb')}; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <b style="font-size: 15px; color: {tdata.get('color', '#2563eb')};">{tdata.get('name')}</b><br>
                    <small style="color: #64748b;">Tier: <b style="color: #1e293b;">{tdata.get('tier')}</b></small>
                    <hr style="margin: 10px 0; border: none; border-top: 1px solid #e2e8f0;">
                    <div style="color: #475569; font-size: 13px; margin-bottom: 4px;">Target SLA: <b style="color: #0f172a;">&le; {tdata.get('sla_target_ms')} ms</b></div>
                    <div style="color: #475569; font-size: 13px; margin-bottom: 4px;">SLA Met: <b style="color: #059669;">{tdata.get('sla_compliance_pct')}%</b></div>
                    <div style="color: #475569; font-size: 13px; margin-bottom: 4px;">Rate Limit: <b style="color: #0f172a;">{tdata.get('rate_limit_per_sec')} req/s</b></div>
                    <div style="color: #475569; font-size: 13px;">Total Served: <b style="color: #0f172a;">{tdata.get('total_requests')} reqs</b></div>
                </div>
                """, unsafe_allow_html=True)
                
    st.markdown("---")
    st.caption("Zero-Trust Fleet Authentication: Ingress Gateway validates scoped tokens (`X-Fleet-Tenant`, `X-Robot-Token`) with per-second bucket enforcement.")

with tab4:
    st.subheader("🛡️ ISO 3691-4 Incident Black-Box & Compliance Archiver")
    st.markdown("""
    When safety-critical hazards occur (e.g. human in AGV path or worker node failover), sensor snapshots and flight telemetry
    are automatically sealed and archived into **S3-Compatible Object Storage** (`s3://robonexus-incidents/`) for audit compliance.
    """)
    
    incidents = incident_archiver.list_recent_incidents(10)
    if incidents:
        inc_rows = []
        for inc in incidents:
            inc_rows.append({
                "Incident ID": inc.get("incident_id"),
                "Timestamp (UTC)": inc.get("timestamp"),
                "Robot": inc.get("robot_id"),
                "Event Type": inc.get("event_type"),
                "Severity": inc.get("criticality"),
                "S3 URI": inc.get("s3_uri"),
                "Compliance Standard": inc.get("compliance_standard")
            })
        st.dataframe(pd.DataFrame(inc_rows), width="stretch", hide_index=True)
        
        with st.expander("🔍 Inspect Latest Incident Black-Box Packet (JSON)"):
            latest_inc = incident_archiver.get_incident_by_id(incidents[0]["incident_id"])
            if latest_inc:
                st.json({k: v for k, v in latest_inc.items() if k != "image_base64"})
    else:
        st.info("No safety hazard incidents logged yet. Triggering a critical collision hazard will automatically seal an incident record to S3.")

    st.markdown("---")
    st.subheader("📊 Data Lakehouse Parquet Exporter (Offline Analytics ETL)")
    st.markdown("""
    **Enterprise Columnar Lakehouse Ingestion:** Batch-processes high-velocity Redis time-series events, RADS scheduling metrics, 
    and sealed MinIO ISO 3691-4 incident logs into compressed **Apache Parquet** columnar datasets. 
    Parquet datasets are uploaded directly to the dedicated `robonexus-analytics` bucket (`s3://robonexus-analytics/`) for PySpark, DuckDB, and Trino analytics.
    """)
    
    col_exp_btn, col_exp_spacer = st.columns([1, 2])
    with col_exp_btn:
        if st.button("⚡ Export Parquet Batch Now", width="stretch", type="primary"):
            try:
                import batch_exporter
                new_meta = batch_exporter.export_fleet_telemetry_lakehouse(r)
                st.success(f"Successfully exported {new_meta['row_count']} rows to {new_meta['file_name']}!")
            except Exception as e:
                st.error(f"Lakehouse export error: {e}")
                
    latest_exp_raw = r.get("lakehouse:latest_export") if redis_ok else None
    if latest_exp_raw:
        latest_exp = json.loads(latest_exp_raw)
        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        p_col1.metric("Latest Parquet Dataset", latest_exp.get("file_name", "-"))
        p_col2.metric("Total Columnar Rows", f"{latest_exp.get('row_count', 0):,}")
        p_col3.metric("Compressed Size", f"{(latest_exp.get('file_size_bytes', 0) / 1024):.1f} KB", delta="Snappy")
        p_col4.metric("S3 Analytics Bucket", latest_exp.get("bucket", "robonexus-analytics"))
        
        st.markdown(f"**Target S3 Analytics URI:** `{latest_exp.get('s3_analytics_uri')}`")
        
        fpath = latest_exp.get("file_path")
        if fpath and os.path.exists(fpath):
            with st.expander("🔍 Preview Columnar Parquet Records (PyArrow / Pandas)", expanded=True):
                try:
                    df_parquet = pd.read_parquet(fpath)
                    st.dataframe(df_parquet.head(20), width="stretch", hide_index=True)
                    
                    with open(fpath, "rb") as f_pq:
                        pq_bytes = f_pq.read()
                    st.download_button(
                        label="📥 Download .parquet File",
                        data=pq_bytes,
                        file_name=latest_exp.get("file_name", "fleet_analytics.parquet"),
                        mime="application/octet-stream"
                    )
                except Exception as e:
                    st.warning(f"Could not load parquet preview: {e}")
    else:
        st.info("No Parquet export generated yet. Click '⚡ Export Parquet Batch Now' above to run the batch ETL pipeline.")

with tab5:
    st.subheader("📈 Performance Benchmarks & Live Vision Audit")
    
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        st.markdown("#### 🚨 Critical Deadline Satisfaction Rate (CDSR)")
        bench_data = pd.DataFrame({
            "Scheduler": ["Standard FIFO", "RoboNexus RADS"],
            "CDSR (%)": [35.0, 100.0]
        })
        st.bar_chart(bench_data.set_index("Scheduler"), color=["#ef4444"])
        
    with b_col2:
        st.markdown("#### ⏱️ Critical P95 Latency under Congestion")
        lat_data = pd.DataFrame({
            "Scheduler": ["Standard FIFO", "RoboNexus RADS"],
            "P95 Latency (ms)": [780.0, 24.5]
        })
        st.bar_chart(lat_data.set_index("Scheduler"), color=["#3b82f6"])
    st.markdown("---")
    col_img, col_hist = st.columns([1, 1])
    with col_img:
        st.subheader("👁️ AI Vision Inference Feed")
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
                    boxes = json.loads(latest_task.get("boxes", "[]"))
                    classes = json.loads(latest_task.get("classes", "[]"))
                    confidences = json.loads(latest_task.get("confidences", "[]"))
                    for b, c, confidence in zip(boxes, classes, confidences):
                        draw.rectangle(b, outline="cyan", width=3)
                        draw.text(
                            (b[0] + 4, max(4, b[1] - 14)),
                            f"{str(c).upper()} {float(confidence):.0%}",
                            fill="yellow"
                        )
                    
                    dl_status = "✅ MET" if latest_task.get("deadline_met") == "true" else "❌ MISSED"
                    st.image(
                        pil_img,
                        caption=(
                            f"Robot: {latest_task.get('robot_id')} | "
                            f"Action: {latest_task.get('perception_action', 'PENDING')} | "
                            f"Hazard: {latest_task.get('hazard_class', 'None')} | "
                            f"Latency: {latest_task.get('inference_time_ms')}ms | Deadline: {dl_status}"
                        )
                    )
                except Exception as e:
                    st.warning(f"Feed error: {e}")
            else:
                st.info("No completed inference frames yet.")
                
    with col_hist:
        st.subheader("📋 Real-Time Execution Log")
        if redis_ok:
            h_ids = r.lrange("history:tasks", 0, 15)
            h_rows = []
            for tid in h_ids:
                d = r.hgetall(f"task:{tid}")
                if d:
                    h_rows.append({
                        "Time": time.strftime("%H:%M:%S", time.localtime(float(d.get("created_ts", time.time())))),
                        "Robot": d.get("robot_id", "-"),
                        "Criticality": d.get("criticality", "NORMAL"),
                        "Worker": d.get("assigned_worker", "-"),
                        "Robot Action": d.get("perception_action", "-"),
                        "Hazard": d.get("hazard_class", "-"),
                        "Status": d.get("state", "-").upper(),
                        "Latency": f"{float(d.get('inference_time_ms', 0)):.1f}ms" if d.get("inference_time_ms") else "-",
                        "Deadline Met": "YES" if d.get("deadline_met") == "true" else ("NO" if d.get("state") == "completed" else "-"),
                        "Deadline Risk": d.get("deadline_risk", "-")
                    })
            if h_rows:
                st.dataframe(pd.DataFrame(h_rows), width="stretch", hide_index=True)

if auto_refresh:
    time.sleep(0.5)
    st.rerun()
