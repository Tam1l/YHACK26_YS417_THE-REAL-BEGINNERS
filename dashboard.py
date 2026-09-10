import os
import time
import json
import redis
import pandas as pd
import streamlit as st

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

st.set_page_config(
    page_title="Private AI Cloud | Robotics Mission Control",
    page_icon="🤖",
    layout="wide",
)

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0b0f19 0%, #111827 100%);
        color: #f3f4f6;
    }
    .metric-card {
        background: rgba(31, 41, 55, 0.7);
        border: 1px solid rgba(75, 85, 99, 0.4);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    }
    .priority-badge-1 { color: #ef4444; font-weight: bold; }
    .priority-badge-2 { color: #f59e0b; font-weight: bold; }
    .priority-badge-5 { color: #10b981; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

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
    is_connected = True
except Exception as e:
    is_connected = False
    conn_error = str(e)

st.title("🤖 Private AI Cloud for Robotics")
st.caption("Live Mission Control & Priority Queue Execution Telemetry")

if not is_connected:
    st.error(f"Cannot connect to Redis at {REDIS_HOST}:{REDIS_PORT}. Error: {conn_error}")
    time.sleep(1)
    st.rerun()

processed = int(r.get("stats:processed") or 0)
depth = int(r.zcard("queue:tasks") or 0)
latency_sum = float(r.get("stats:latency_sum") or 0.0)
avg_latency = round(latency_sum / processed, 2) if processed > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Jobs Processed", f"{processed:,}")
col2.metric("Active Queue Depth", depth, delta=f"{depth} pending" if depth > 0 else "Idle", delta_color="inverse")
col3.metric("Avg Inference Latency", f"{avg_latency} ms")
col4.metric("Engine Health", "ONLINE 🟢" if is_connected else "OFFLINE 🔴")

st.markdown("---")

st.subheader("⚡ Real-Time Task Execution Log")

task_ids = r.lrange("history:tasks", 0, 25)
rows = []

for tid in task_ids:
    data = r.hgetall(f"task:{tid}")
    if data:
        p = int(data.get("priority", 9))
        p_label = "P1 [CRITICAL - AGV]" if p == 1 else ("P2 [DRONE]" if p == 2 else f"P{p} [STANDARD]")
        rows.append({
            "Task ID": tid[:8] + "...",
            "Robot ID": data.get("robot_id", "Unknown"),
            "Priority": p_label,
            "State": data.get("state", "queued").upper(),
            "Detections": data.get("detection_count", "-"),
            "Inference (ms)": data.get("inference_time_ms", "-"),
            "Created": time.strftime("%H:%M:%S", time.localtime(float(data.get("created_ts", time.time()))))
        })

if rows:
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No active tasks processed yet. Launch robot_simulator.py to generate live robot workloads.")

st.caption(f"Telemetry auto-updating. Active server: {REDIS_HOST}:{REDIS_PORT}")
time.sleep(0.5)
st.rerun()
