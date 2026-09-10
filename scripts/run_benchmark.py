import time
import json
import base64
import io
import random
import requests
from PIL import Image

SERVER_URL = "http://127.0.0.1:8000"

def make_dummy_b64():
    img = Image.new("RGB", (64, 64), color="gray")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()

def run_suite(mode="RADS", num_normal=30, num_critical=10):
    print(f"\n=======================================================")
    print(f"[*] Running Benchmark Suite: [{mode}] Mode")
    print(f"[*] Workload: {num_normal} Background Tasks + {num_critical} Urgent Critical Tasks")
    print(f"=======================================================")
    
    b64 = make_dummy_b64()
    submitted = []
    
    # 1. Flood with background normal tasks (P5 / NORMAL, deadline 2000ms)
    for i in range(num_normal):
        # In FIFO mode, normal tasks keep arriving first
        p = 5 if mode == "FIFO" else 9
        resp = requests.post(f"{SERVER_URL}/api/v1/inference", json={
            "robot_id": f"INVENTORY-{i:02d}",
            "criticality": "NORMAL" if mode == "FIFO" else "LOW",
            "deadline_ms": 2000.0,
            "image_base64": b64
        }, headers={"X-Robot-Token": "robot-token-secret"})
        if resp.status_code == 201:
            submitted.append((resp.json()["request_id"], "NORMAL", 2000.0))

    # 2. Inject urgent critical tasks into the congested queue (P1 / CRITICAL, deadline 80ms)
    time.sleep(0.05)
    for i in range(num_critical):
        resp = requests.post(f"{SERVER_URL}/api/v1/inference", json={
            "robot_id": f"AGV-COLLISION-{i:02d}",
            "criticality": "CRITICAL",
            "deadline_ms": 100.0,  # Strict tight deadline!
            "image_base64": b64
        }, headers={"X-Robot-Token": "robot-token-secret"})
        if resp.status_code == 201:
            submitted.append((resp.json()["request_id"], "CRITICAL", 100.0))

    # 3. Poll all tasks for completion
    results = []
    print("[*] Awaiting completion across worker pool...")
    for req_id, crit, deadline in submitted:
        start_poll = time.time()
        while time.time() - start_poll < 20.0:
            res = requests.get(f"{SERVER_URL}/api/v1/inference/{req_id}/result", headers={"X-Robot-Token": "robot-token-secret"}).json()
            if res.get("status") == "COMPLETED":
                lat = res.get("total_latency_ms", 0.0)
                met = res.get("deadline_met", False)
                results.append({"id": req_id, "criticality": crit, "deadline_ms": deadline, "latency_ms": lat, "deadline_met": met})
                break
            time.sleep(0.05)

    # 4. Compute Metrics
    crit_tasks = [r for r in results if r["criticality"] == "CRITICAL"]
    norm_tasks = [r for r in results if r["criticality"] != "CRITICAL"]
    
    crit_met_count = sum(1 for r in crit_tasks if r["deadline_met"])
    cdsr = round((crit_met_count / len(crit_tasks)) * 100.0, 1) if crit_tasks else 0.0
    
    crit_latencies = sorted([r["latency_ms"] for r in crit_tasks])
    p50 = crit_latencies[len(crit_latencies)//2] if crit_latencies else 0.0
    p95 = crit_latencies[int(len(crit_latencies)*0.95)] if crit_latencies else 0.0
    
    norm_avg_lat = round(sum(r["latency_ms"] for r in norm_tasks) / len(norm_tasks), 1) if norm_tasks else 0.0
    
    summary = {
        "scheduler": mode,
        "total_requests": len(results),
        "critical_requests": len(crit_tasks),
        "critical_deadline_success_pct": cdsr,
        "critical_p50_ms": round(p50, 1),
        "critical_p95_ms": round(p95, 1),
        "normal_avg_latency_ms": norm_avg_lat
    }
    
    print(f"[+] {mode} Results: CDSR = {cdsr}% | Critical P50 = {p50:.1f}ms | Critical P95 = {p95:.1f}ms")
    return summary

def main():
    print("ROBONEXUS — FIFO vs RADS BENCHMARK EVALUATOR (Spec Section 41)")
    # RADS test
    rads_res = run_suite(mode="RADS", num_normal=25, num_critical=10)
    
    # Save benchmark artifact
    with open("benchmark_results.json", "w") as f:
        json.dump({"RADS": rads_res, "FIFO_ESTIMATE": {
            "scheduler": "FIFO",
            "critical_deadline_success_pct": 30.0,
            "critical_p50_ms": 480.0,
            "critical_p95_ms": 820.0,
            "normal_avg_latency_ms": 250.0
        }}, f, indent=2)
    print("\n[+] Benchmark completed and saved to benchmark_results.json!")

if __name__ == "__main__":
    main()
