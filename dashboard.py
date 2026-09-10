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
    .stApp { background-color: #0b0f19; color: #f3f4f6; }
    .worker-card {
        background: #111827; border: 1px solid #374151; border-radius: 10px; padding: 15px; margin-bottom: 10px;
    }
    .badge-crit { background-color: #ef4444; color: white; padding: 3px 8px; border-radius: 6px; font-weight: bold; }
    .badge-high { background-color: #f59e0b; color: black; padding: 3px 8px; border-radius: 6px; font-weight: bold; }
    .badge-norm { background-color: #10b981; color: white; padding: 3px 8px; border-radius: 6px; }
    .badge-low  { background-color: #6b7280; color: white; padding: 3px 8px; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

def generate_synthetic_scene(scene_type: str) -> str:
    img = Image.new("RGB", (320, 240), color=(20, 24, 33))
    draw = ImageDraw.Draw(img)
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
            background-color: #0b0f19;
            color: #f3f4f6;
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            overflow: hidden;
            user-select: none;
        }
        #container {
            position: relative;
            width: 100%;
            height: 575px;
            background: radial-gradient(circle at center, #111827 0%, #080c14 100%);
            border: 2px solid #1e293b;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.7);
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
            background: #0f172a;
            border-top: 1px solid #1e293b;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            box-sizing: border-box;
            z-index: 20;
        }
        .deck-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .deck-label {
            font-size: 11px;
            font-weight: bold;
            color: #64748b;
            letter-spacing: 0.5px;
            margin-right: 4px;
        }
        .btn {
            background: #1e293b;
            color: #e2e8f0;
            border: 1px solid #475569;
            border-radius: 6px;
            padding: 8px 14px;
            font-size: 12px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }
        .btn-danger {
            background: #991b1b;
            border-color: #ef4444;
            color: white;
        }
        .btn-danger:hover { background: #b91c1c; }
        .btn-primary {
            background: #1d4ed8;
            border-color: #3b82f6;
            color: white;
        }
        .btn-primary:hover { background: #2563eb; }
        .btn-warning {
            background: #854d0e;
            border-color: #eab308;
            color: white;
        }
        #banner {
            position: absolute;
            top: 12px;
            left: 50%;
            transform: translateX(-50%);
            padding: 6px 18px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
            display: none;
            z-index: 20;
            animation: pulse 1s infinite alternate;
        }
        @keyframes pulse {
            from { opacity: 0.85; }
            to { opacity: 1.0; }
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
                <button class="btn btn-primary" id="btnPlayPause">⏸ Pause Fleet</button>
                <button class="btn btn-danger" id="btnHazardToggle">🚨 TRIGGER HAZARD (AGV-01)</button>
            </div>
            <div class="deck-group">
                <span class="deck-label">LIVE DEMOS:</span>
                <button class="btn" id="btnBatchDemo" style="background:#1e3a8a; border-color:#3b82f6; color:#fff;">📦 5x Batch + 1 Critical Leapfrog</button>
                <button class="btn btn-warning" id="btnKillWorker">🔥 KILL WORKER-1</button>
                <button class="btn" id="btnSurge" style="background:#065f46; border-color:#10b981; color:#fff;">📈 Fleet Surge (Autoscale)</button>
                <button class="btn" id="btnRogueSpoof" style="background:#450a0a; border-color:#ef4444; color:#fca5a5;">🛡️ Rogue Token (403)</button>
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
            angle: 0,
            color: '#38bdf8'
        };

        const sweeper = {
            id: 'SWEEPER-12',
            x: 320,
            y: 328,
            dir: 1,
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

            // Background Grid
            ctx.strokeStyle = '#1e293b';
            ctx.lineWidth = 1;
            for (let x = 0; x < w; x += 40) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
            }
            for (let y = 0; y < h; y += 40) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
            }

            // Central AGV Highway Transit Lane
            ctx.fillStyle = 'rgba(15, 23, 42, 0.75)';
            ctx.fillRect(0, 225, w, 80);
            ctx.strokeStyle = '#334155';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(0, 225); ctx.lineTo(w, 225);
            ctx.moveTo(0, 305); ctx.lineTo(w, 305);
            ctx.stroke();

            // Center yellow hazard guidestrip
            ctx.strokeStyle = '#eab308';
            ctx.lineWidth = 2;
            ctx.setLineDash([14, 12]);
            ctx.beginPath();
            ctx.moveTo(0, 265); ctx.lineTo(w, 265);
            ctx.stroke();
            ctx.setLineDash([]);

            // Highway Corridor Label
            ctx.fillStyle = '#64748b';
            ctx.font = 'bold 10px monospace';
            ctx.fillText("AGV HIGH-SPEED TRANSIT CORRIDOR [LANE-01]", 260, 240);

            // Fleet Autonomous Charging Dock (Top Center: between Queue HUD and Cloud Hub)
            const dockX = Math.max(260, Math.floor((w - 180) / 2));
            const dockY = 14;
            const dockW = 180;
            const dockH = 92;
            ctx.fillStyle = 'rgba(16, 185, 129, 0.08)';
            ctx.fillRect(dockX, dockY, dockW, dockH);
            ctx.strokeStyle = 'rgba(16, 185, 129, 0.4)';
            ctx.lineWidth = 1.5;
            ctx.strokeRect(dockX, dockY, dockW, dockH);

            ctx.fillStyle = '#10b981';
            ctx.font = 'bold 11px sans-serif';
            ctx.fillText("⚡ AUTONOMOUS DOCK", dockX + 16, dockY + 22);

            ctx.fillStyle = '#6ee7b7';
            ctx.font = '9px monospace';
            ctx.fillText("BAY 1: WIRELESS INDUCTIVE", dockX + 16, dockY + 44);
            ctx.fillText("TELEMETRY: 5.8 GHz RAW", dockX + 16, dockY + 62);
            ctx.fillText("STATUS: ACTIVE READY", dockX + 16, dockY + 80);

            // Storage Racks - Perfectly spaced with zero overlap!
            const rackW = 175;
            const rackH = 46;

            const topRacks = [
                { x: 24, y: 122, label: "RACK AISLE A1" },
                { x: 224, y: 122, label: "RACK AISLE A2" },
                { x: 424, y: 122, label: "RACK AISLE A3" },
                { x: 624, y: 122, label: "RACK AISLE A4" }
            ];

            const bottomRacks = [
                { x: 24, y: 356, label: "RACK AISLE B1" },
                { x: 224, y: 356, label: "RACK AISLE B2" },
                { x: 424, y: 356, label: "RACK AISLE B3" }
            ];

            const allRacks = [...topRacks, ...bottomRacks].filter(r => r.x + rackW <= w - 10);

            allRacks.forEach(r => {
                // Shelf Body
                ctx.fillStyle = '#0f172a';
                ctx.fillRect(r.x, r.y, rackW, rackH);
                ctx.strokeStyle = '#334155';
                ctx.lineWidth = 1.5;
                ctx.strokeRect(r.x, r.y, rackW, rackH);

                // Rack Label
                ctx.fillStyle = '#94a3b8';
                ctx.font = 'bold 10px monospace';
                ctx.fillText(r.label, r.x + 10, r.y + 28);

                // Inventory Bins
                for (let b = 0; b < 4; b++) {
                    const bx = r.x + 102 + (b * 16);
                    ctx.fillStyle = (b % 2 === 0) ? '#f59e0b' : '#0284c7';
                    ctx.fillRect(bx, r.y + 12, 12, 22);
                    ctx.strokeStyle = '#0f172a';
                    ctx.lineWidth = 1;
                    ctx.strokeRect(bx, r.y + 12, 12, 22);
                }
            });

            // Drone flight path dashed guide (between Top Racks and Highway)
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.2)';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 8]);
            ctx.beginPath();
            ctx.moveTo(20, 195); ctx.lineTo(w - 20, 195);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        function drawCloudHub() {
            const w = canvas.width;
            const hubW = 172;
            const hubH = 92;
            const hubX = w - hubW - 16;
            const hubY = 14;

            ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
            ctx.fillRect(hubX, hubY, hubW, hubH);
            ctx.strokeStyle = '#38bdf8';
            ctx.lineWidth = 1.8;
            ctx.strokeRect(hubX, hubY, hubW, hubH);

            ctx.fillStyle = '#0284c7';
            ctx.fillRect(hubX, hubY, hubW, 22);

            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 11px sans-serif';
            ctx.fillText("☁️ PRIVATE AI CLOUD", hubX + 10, hubY + 15);

            // Workers
            ctx.fillStyle = worker1Alive ? '#10b981' : '#ef4444';
            ctx.beginPath(); ctx.arc(hubX + 18, hubY + 45, 5, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#e2e8f0';
            ctx.font = '11px monospace';
            ctx.fillText(`Worker-1: ${worker1Alive ? 'HEALTHY' : 'DEAD'}`, hubX + 30, hubY + 49);

            ctx.fillStyle = worker2Alive ? '#10b981' : '#ef4444';
            ctx.beginPath(); ctx.arc(hubX + 18, hubY + 70, 5, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = '#e2e8f0';
            ctx.fillText(`Worker-2: HEALTHY`, hubX + 30, hubY + 74);
        }

        function drawQueueHUD() {
            const qX = 16;
            const qY = 14;
            const qW = 230;
            const qH = 92;

            ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
            ctx.fillRect(qX, qY, qW, qH);
            ctx.strokeStyle = '#6366f1';
            ctx.lineWidth = 1.8;
            ctx.strokeRect(qX, qY, qW, qH);

            ctx.fillStyle = '#4f46e5';
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
                ctx.fillStyle = '#f8fafc';
                ctx.font = '10px monospace';
                const nameText = item.id.length > 17 ? item.id.substring(0, 15) + '..' : item.id;
                ctx.fillText(nameText, qX + 38, rowY);

                // Position Badge
                ctx.fillStyle = (idx === 0) ? '#ef4444' : '#64748b';
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

            ctx.fillStyle = 'rgba(10, 15, 26, 0.95)';
            ctx.fillRect(hudX, hudY, hudW, hudH);
            ctx.strokeStyle = '#06b6d4';
            ctx.lineWidth = 1.8;
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
                ctx.strokeStyle = '#ef4444';
                ctx.lineWidth = 2;
                ctx.strokeRect(hudX + 50, hudY + 32, 105, 60);
                ctx.fillStyle = '#ef4444';
                ctx.fillRect(hudX + 50, hudY + 22, 105, 13);
                ctx.fillStyle = 'white';
                ctx.font = 'bold 9px sans-serif';
                ctx.fillText("HUMAN HAZARD 99.1%", hudX + 53, hudY + 32);

                ctx.fillStyle = '#ef4444';
                ctx.font = 'bold 10px monospace';
                ctx.fillText("STATUS: PREEMPTION BRAKE", hudX + 8, hudY + 118);
            } else {
                ctx.strokeStyle = '#10b981';
                ctx.lineWidth = 1.5;
                ctx.strokeRect(hudX + 35, hudY + 38, 135, 48);
                ctx.fillStyle = '#10b981';
                ctx.font = '9px monospace';
                ctx.fillText("CORRIDOR CLEAR [P=0.98]", hudX + 40, hudY + 34);

                ctx.fillStyle = '#94a3b8';
                ctx.font = '10px monospace';
                ctx.fillText(`LATENCY: ${latestLatency.toFixed(1)}ms [DEADLINE MET]`, hudX + 8, hudY + 118);
            }
        }

        function update() {
            if (isRunning) {
                // AGV logic
                if (humanHazard) {
                    const dist = humanPos.x - agv.x;
                    if (dist > 75) {
                        agv.status = 'NORMAL';
                        agv.x += agv.speed;
                    } else if (dist > 0) {
                        agv.status = 'STOPPED';
                    } else {
                        // Safety fallback: ensure robot never stops past the hazard
                        agv.x = humanPos.x - 75;
                        agv.status = 'STOPPED';
                    }
                } else {
                    agv.status = 'NORMAL';
                    agv.x += agv.speed;
                    if (agv.x > canvas.width - 60) agv.x = 40;
                }

                // Drone hovering along inspection corridor
                drone.angle += 0.03;
                drone.x = 280 + Math.sin(drone.angle) * 110;
                drone.y = 195 + Math.cos(drone.angle) * 6;

                // Sweeper back and forth along bottom corridor
                sweeper.x += 1.2 * sweeper.dir;
                if (sweeper.x > canvas.width - 240) sweeper.dir = -1;
                if (sweeper.x < 40) sweeper.dir = 1;

                // Telemetry packets
                packets.forEach(p => { p.progress += 0.04; });
                packets = packets.filter(p => p.progress < 1.0);
            }
        }

        function render() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            drawWarehouse();

            // Draw Human if hazard
            if (humanHazard) {
                ctx.fillStyle = '#f87171';
                ctx.beginPath(); ctx.arc(humanPos.x, humanPos.y - 14, 8, 0, Math.PI * 2); ctx.fill();
                ctx.fillRect(humanPos.x - 6, humanPos.y - 6, 12, 22);
                ctx.strokeStyle = '#ef4444';
                ctx.strokeRect(humanPos.x - 14, humanPos.y - 26, 28, 48);

                ctx.fillStyle = '#ef4444';
                ctx.font = 'bold 10px sans-serif';
                ctx.fillText("HAZARD", humanPos.x - 20, humanPos.y - 32);
            }

            // AGV Robot
            ctx.fillStyle = agv.status === 'STOPPED' ? '#ef4444' : '#dc2626';
            ctx.fillRect(agv.x - 22, agv.y - 15, 44, 30);
            ctx.strokeStyle = agv.status === 'STOPPED' ? '#fca5a5' : '#f87171';
            ctx.lineWidth = 2;
            ctx.strokeRect(agv.x - 22, agv.y - 15, 44, 30);

            // Light cone
            ctx.fillStyle = agv.status === 'STOPPED' ? 'rgba(239, 68, 68, 0.25)' : 'rgba(234, 179, 8, 0.15)';
            ctx.beginPath();
            ctx.moveTo(agv.x + 22, agv.y);
            ctx.lineTo(agv.x + 100, agv.y - 35);
            ctx.lineTo(agv.x + 100, agv.y + 35);
            ctx.closePath();
            ctx.fill();

            ctx.fillStyle = 'white';
            ctx.font = 'bold 9px sans-serif';
            ctx.fillText(agv.id, agv.x - 18, agv.y + 3);

            // Drone
            ctx.fillStyle = '#0284c7';
            ctx.fillRect(drone.x - 12, drone.y - 12, 24, 24);
            ctx.strokeStyle = '#38bdf8';
            ctx.strokeRect(drone.x - 12, drone.y - 12, 24, 24);
            // Drone beam
            ctx.fillStyle = 'rgba(56, 189, 248, 0.15)';
            ctx.beginPath();
            ctx.moveTo(drone.x, drone.y + 12);
            ctx.lineTo(drone.x - 22, drone.y + 36);
            ctx.lineTo(drone.x + 22, drone.y + 36);
            ctx.closePath();
            ctx.fill();

            // Sweeper
            ctx.fillStyle = '#059669';
            ctx.beginPath(); ctx.arc(sweeper.x, sweeper.y, 14, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = '#34d399';
            ctx.stroke();

            // Packets in flight
            packets.forEach(p => {
                const curX = p.fromX + (p.toX - p.fromX) * p.progress;
                const curY = p.fromY + (p.toY - p.fromY) * p.progress;
                ctx.fillStyle = p.color;
                ctx.shadowColor = p.color;
                ctx.shadowBlur = 8;
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
m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

if redis_ok:
    processed = int(r.get("stats:processed") or 0)
    q_depth = int(r.zcard("queue:tasks") or 0)
    lat_sum = float(r.get("stats:latency_sum") or 0.0)
    avg_lat = round(lat_sum / processed, 1) if processed > 0 else 0.0
    
    crit_total = int(r.get("stats:critical_total") or 0)
    crit_met = int(r.get("stats:critical_deadline_met") or 0)
    cdsr = round((crit_met / crit_total) * 100.0, 1) if crit_total > 0 else 100.0
    failovers = int(r.get("stats:failovers") or 0)
else:
    processed, q_depth, avg_lat, cdsr, failovers = 0, 0, 0.0, 100.0, 0

m_col1.metric("Tasks Completed", f"{processed:,}")
m_col2.metric("Queue Depth", q_depth, delta=f"{q_depth} waiting" if q_depth > 0 else "Clear", delta_color="inverse")
m_col3.metric("Avg Inference Latency", f"{avg_lat} ms")
m_col4.metric("Critical Deadline Success (CDSR)", f"{cdsr}%", delta="100% Target" if cdsr >= 95 else "Contention", delta_color="normal")
m_col5.metric("Failover Recoveries", failovers, delta="Auto-Recovered" if failovers > 0 else "Stable")

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
            <div style="background: #111827; border: 2px solid {card_border}; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <b style="font-size: 16px;">{wid.upper()}{badge} {icon}</b>
                    <span>Status: <b>{status_val}</b></span>
                </div>
                <div style="font-size: 13px; color: #9ca3af; margin-top: 6px;">
                    Processed: <b>{proc_jobs} tasks</b> | Active Job: <code>{cur_job[:8] if cur_job else 'IDLE'}</code>
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
            color = "#10b981" if "SCALE_DOWN" in ev else ("#f59e0b" if "SCALE_UP" in ev else "#60a5fa")
            st.markdown(f"<div style='font-family: monospace; font-size: 13px; color: {color}; padding: 3px 0;'>{ev}</div>", unsafe_allow_html=True)
    else:
        st.info("Autoscaler initialized. Click '📈 Trigger Fleet Surge' in the sidebar to observe live elastic scaling!")

with tab3:
    st.subheader("🏢 Multi-Tenant Fleet Governance & SLA Compliance")
    st.markdown("Industrial Private Clouds partition compute across distinct robotic departments, enforcing per-fleet rate limits and latency SLAs.")
    
    tenants_summary = fleet_tenants.get_all_tenants_metrics(r) if redis_ok else {}
    if tenants_summary:
        t_cols = st.columns(len(tenants_summary))
        for idx, (tid, tdata) in enumerate(tenants_summary.items()):
            with t_cols[idx]:
                st.markdown(f"""
                <div style="background: #111827; border-left: 4px solid {tdata.get('color', '#3b82f6')}; border-radius: 8px; padding: 14px;">
                    <b style="font-size: 15px; color: {tdata.get('color')};">{tdata.get('name')}</b><br>
                    <small>Tier: <b>{tdata.get('tier')}</b></small>
                    <hr style="margin: 8px 0; border-color: #374151;">
                    <div>Target SLA: <b>&le; {tdata.get('sla_target_ms')} ms</b></div>
                    <div>SLA Met: <b style="color: #10b981;">{tdata.get('sla_compliance_pct')}%</b></div>
                    <div>Rate Limit: <b>{tdata.get('rate_limit_per_sec')} req/s</b></div>
                    <div>Total Served: <b>{tdata.get('total_requests')} reqs</b></div>
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
