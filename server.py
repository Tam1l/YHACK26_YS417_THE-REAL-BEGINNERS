import os
import uuid
import base64
import time
from typing import Optional

import redis
from fastapi import FastAPI, HTTPException, Header, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

import rads

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_ALGORITHM = "HS256"

# Spec Section 29: Server-Side Robot Authorization Policies
ROBOT_POLICIES = {
    "robot-token-secret": {"robot_id": "AGV-01", "max_priority": 1, "max_criticality": "CRITICAL"},
    "agv-token": {"robot_id": "AGV-01", "max_priority": 1, "max_criticality": "CRITICAL"},
    "drone-token": {"robot_id": "DRONE-07", "max_priority": 2, "max_criticality": "HIGH"},
    "sweeper-token": {"robot_id": "SWEEPER-12", "max_priority": 5, "max_criticality": "NORMAL"},
}

raw_tokens = os.getenv("ROBOT_TOKENS", "robot-token-secret,agv-token,drone-token,sweeper-token")
PRE_SHARED_TOKENS = set(filter(None, [t.strip() for t in raw_tokens.split(",")])) | set(ROBOT_POLICIES)

redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
    protocol=2
)

try:
    redis_client.config_set('stop-writes-on-bgsave-error', 'no')
    redis_client.config_set('save', '')
except Exception:
    pass

def verify_token(
    authorization: Optional[str] = Header(None),
    x_robot_token: Optional[str] = Header(None, alias="X-Robot-Token"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    token = x_robot_token or x_api_key
    if authorization and authorization.startswith("Bearer "):
        jwt_raw = authorization.split(" ", 1)[1]
        if JWT_AVAILABLE:
            try:
                return jwt.decode(jwt_raw, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            except Exception:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT token")
        return {"token": jwt_raw}

    if token:
        if token in PRE_SHARED_TOKENS:
            policy = ROBOT_POLICIES.get(token, {"robot_token": token, "max_priority": 9, "max_criticality": "LOW"})
            return policy
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or unknown robot credentials")

    # In development, fallback only if no token is passed
    return {"auth": "default_dev_bypass"}

class InferenceSubmission(BaseModel):
    robot_id: str = Field(..., description="Unique identifier of the robot")
    task_type: str = Field("object_detection", description="Type of inference requested")
    criticality: str = Field("NORMAL", description="Mission Criticality: CRITICAL, HIGH, NORMAL, LOW")
    deadline_ms: float = Field(500.0, ge=10.0, le=30000.0, description="Execution deadline in milliseconds")
    image_base64: str = Field(..., description="Base64-encoded JPEG/PNG image")

    @field_validator("image_base64")
    @classmethod
    def validate_image_base64(cls, v: str) -> str:
        if not v:
            raise ValueError("image_base64 payload cannot be empty")
        return v

class PredictRequest(BaseModel):
    robot_id: str = Field(..., description="Unique identifier of the robot")
    priority: int = Field(..., ge=1, le=9, description="Priority: 1 is Highest, 9 is Lowest")
    image_base64: str = Field(..., description="Base64-encoded JPEG/PNG image")

    @field_validator("image_base64")
    @classmethod
    def validate_image_base64(cls, v: str) -> str:
        if not v:
            raise ValueError("image_base64 cannot be empty")
        return v

app = FastAPI(title="RoboNexus — Robotics-Aware Private AI Cloud", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/health")
def health():
    try:
        r_ping = redis_client.ping()
    except Exception:
        r_ping = False
    
    w1_ok = (redis_client.hget("worker:worker-1", "healthy") == "true")
    w2_ok = (redis_client.hget("worker:worker-2", "healthy") == "true")
    healthy_workers = sum([1 for ok in (w1_ok, w2_ok) if ok])
    
    return {
        "service": "RoboNexus Private AI Cloud Gateway",
        "status": "online" if r_ping else "degraded",
        "redis_connected": r_ping,
        "workers_healthy": healthy_workers,
        "workers_total": 2
    }

@app.post("/api/v1/inference", status_code=status.HTTP_201_CREATED)
def submit_inference(request: InferenceSubmission, auth=Depends(verify_token)):
    # Policy checks
    crit_str = request.criticality.upper()
    priority_num = 1 if crit_str == "CRITICAL" else (2 if crit_str == "HIGH" else (5 if crit_str == "NORMAL" else 9))
    
    if "max_priority" in auth and priority_num < auth["max_priority"]:
        raise HTTPException(status_code=403, detail="Requested priority exceeds robot policy")
    if auth.get("robot_id") and request.robot_id != auth["robot_id"]:
        raise HTTPException(status_code=403, detail="Robot ID does not match authenticated token")

    task_id = str(uuid.uuid4())
    task_key = f"task:{task_id}"
    now = time.time()
    
    rads_val = rads.compute_rads_score(
        criticality=crit_str,
        deadline_ms=request.deadline_ms,
        created_ts=now
    )
    queue_score = -rads_val
    
    redis_client.hset(task_key, mapping={
        "task_id": task_id,
        "robot_id": request.robot_id,
        "task_type": request.task_type,
        "criticality": crit_str,
        "deadline_ms": str(request.deadline_ms),
        "image_base64": request.image_base64,
        "state": "queued",
        "rads_score": str(rads_val),
        "queue_score": str(queue_score),
        "created_ts": str(now),
        "retry_count": "0"
    })
    
    redis_client.zadd("queue:tasks", {task_id: queue_score})
    redis_client.lpush("history:tasks", task_id)
    redis_client.ltrim("history:tasks", 0, 99)
    
    return {
        "request_id": task_id,
        "robot_id": request.robot_id,
        "criticality": crit_str,
        "rads_score": rads_val,
        "status": "QUEUED",
        "submitted_at": now
    }

@app.post("/predict", status_code=status.HTTP_201_CREATED)
def predict(request: PredictRequest, auth=Depends(verify_token)):
    try:
        # Policy enforcement
        if "max_priority" in auth and request.priority < auth["max_priority"]:
            raise HTTPException(status_code=403, detail="Requested priority exceeds robot policy")
        if auth.get("robot_id") and request.robot_id != auth["robot_id"]:
            raise HTTPException(status_code=403, detail="Robot ID does not match authenticated token")

        task_id = str(uuid.uuid4())
        task_key = f"task:{task_id}"
        now = time.time()
        
        crit_str = "CRITICAL" if request.priority == 1 else ("HIGH" if request.priority == 2 else ("NORMAL" if request.priority == 5 else "LOW"))
        deadline_val = 150.0 if request.priority == 1 else 500.0
        rads_val = rads.compute_rads_score(crit_str, deadline_val, now)
        queue_score = -rads_val
        
        redis_client.hset(task_key, mapping={
            "task_id": task_id,
            "robot_id": request.robot_id,
            "priority": str(request.priority),
            "criticality": crit_str,
            "deadline_ms": str(deadline_val),
            "image_base64": request.image_base64,
            "state": "queued",
            "rads_score": str(rads_val),
            "queue_score": str(queue_score),
            "created_ts": str(now),
            "retry_count": "0"
        })
        
        redis_client.zadd("queue:tasks", {task_id: queue_score})
        redis_client.lpush("history:tasks", task_id)
        redis_client.ltrim("history:tasks", 0, 99)
        
        return {
            "task_id": task_id,
            "robot_id": request.robot_id,
            "priority": request.priority,
            "rads_score": rads_val,
            "state": "queued",
            "submitted_at": now
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Queue Error: {str(e)}")

@app.get("/api/v1/inference/{request_id}/result")
@app.get("/result/{request_id}")
def get_result(request_id: str, auth=Depends(verify_token)):
    task_key = f"task:{request_id}"
    if not redis_client.exists(task_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task ID not found")
    
    data = redis_client.hgetall(task_key)
    state = data.get("state", "unknown")
    response = {
        "task_id": request_id,
        "request_id": request_id,
        "robot_id": data.get("robot_id"),
        "priority": int(data.get("priority", 5)),
        "criticality": data.get("criticality", "NORMAL"),
        "state": state,
        "status": state.upper(),
        "assigned_worker": data.get("assigned_worker", ""),
        "created_ts": data.get("created_ts"),
        "completed_ts": data.get("completed_ts"),
    }
    
    if state == "completed":
        response.update({
            "deadline_met": (data.get("deadline_met") == "true"),
            "inference_ms": float(data.get("inference_time_ms", 0.0)),
            "total_latency_ms": float(data.get("total_latency_ms", 0.0)),
            "result": {
                "boxes": data.get("boxes"),
                "classes": data.get("classes"),
                "confidences": data.get("confidences"),
                "detection_count": int(data.get("detection_count", 0)),
                "inference_time_ms": float(data.get("inference_time_ms", 0.0)),
            }
        })
    elif state == "failed":
        response["error"] = data.get("error_message", "Unknown worker processing error")
        
    return response

@app.get("/api/v1/metrics")
def get_system_metrics():
    processed = int(redis_client.get("stats:processed") or 0)
    lat_sum = float(redis_client.get("stats:latency_sum") or 0.0)
    avg_lat = round(lat_sum / processed, 2) if processed > 0 else 0.0
    
    crit_total = int(redis_client.get("stats:critical_total") or 0)
    crit_met = int(redis_client.get("stats:critical_deadline_met") or 0)
    cdsr = round((crit_met / crit_total) * 100.0, 1) if crit_total > 0 else 100.0
    
    failovers = int(redis_client.get("stats:failovers") or 0)
    queue_depth = int(redis_client.zcard("queue:tasks") or 0)
    
    return {
        "total_processed": processed,
        "queue_depth": queue_depth,
        "avg_inference_latency_ms": avg_lat,
        "critical_deadline_satisfaction_rate_pct": cdsr,
        "critical_tasks_total": crit_total,
        "critical_tasks_met": crit_met,
        "failovers_recovered": failovers
    }

@app.post("/api/v1/debug/workers/{worker_id}/fail")
def inject_worker_failure(worker_id: str):
    redis_client.set(f"debug:fail:{worker_id}", "1")
    return {"status": "injected", "worker_id": worker_id, "action": "worker killed"}

@app.post("/api/v1/debug/workers/{worker_id}/recover")
def recover_worker(worker_id: str):
    redis_client.delete(f"debug:fail:{worker_id}")
    redis_client.hset(f"worker:{worker_id}", "status", "IDLE")
    redis_client.hset(f"worker:{worker_id}", "healthy", "true")
    return {"status": "recovered", "worker_id": worker_id}
