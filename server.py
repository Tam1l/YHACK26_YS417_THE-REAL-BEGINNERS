import os
import uuid
import base64
import time
from typing import Optional

import redis
from fastapi import FastAPI, HTTPException, Header, Depends, status
from pydantic import BaseModel, Field, field_validator

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

raw_tokens = os.getenv("ROBOT_TOKENS", "robot-token-secret,agv-token,drone-token")
PRE_SHARED_TOKENS = set(filter(None, [t.strip() for t in raw_tokens.split(",")]))

redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
    protocol=2,
    protocol=2,
)

def verify_token(
    authorization: Optional[str] = Header(None),
    x_robot_token: Optional[str] = Header(None, alias="X-Robot-Token"),
):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        if JWT_AVAILABLE:
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                return payload
            except Exception:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT token")
        else:
            return {"token": token}

    if x_robot_token and (x_robot_token in PRE_SHARED_TOKENS or not PRE_SHARED_TOKENS):
        return {"robot_token": x_robot_token}

    # Development fallback
    if not authorization and not x_robot_token:
        return {"auth": "default_dev_bypass"}

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authentication credentials")

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

app = FastAPI(title="Private AI Cloud - Robotics Gateway", version="1.0.0")

@app.get("/")
def root():
    try:
        r_ping = redis_client.ping()
    except Exception:
        r_ping = False
    return {"service": "Private AI Cloud Gateway", "status": "online", "redis_connected": r_ping}

@app.post("/predict", status_code=status.HTTP_201_CREATED)
def predict(request: PredictRequest, auth=Depends(verify_token)):
    try:
        task_id = str(uuid.uuid4())
        task_key = f"task:{task_id}"
        now = time.time()
        
        redis_client.hset(task_key, mapping={
            "task_id": task_id,
            "robot_id": request.robot_id,
            "priority": str(request.priority),
            "image_base64": request.image_base64,
            "state": "queued",
            "created_ts": str(now),
        })
        
        # Priority Queue: 1 is highest priority (lowest score popped first)
        redis_client.zadd("queue:tasks", {task_id: request.priority})
        redis_client.lpush("history:tasks", task_id)
        redis_client.ltrim("history:tasks", 0, 99)
        
        return {
            "task_id": task_id,
            "robot_id": request.robot_id,
            "priority": request.priority,
            "state": "queued",
            "submitted_at": now
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Queue Error: {str(e)}")

@app.get("/result/{task_id}")
def get_result(task_id: str, auth=Depends(verify_token)):
    task_key = f"task:{task_id}"
    if not redis_client.exists(task_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task ID not found")
    
    data = redis_client.hgetall(task_key)
    state = data.get("state", "unknown")
    response = {
        "task_id": task_id,
        "robot_id": data.get("robot_id"),
        "priority": int(data.get("priority", 9)),
        "state": state,
        "created_ts": data.get("created_ts"),
        "completed_ts": data.get("completed_ts"),
    }
    
    if state == "completed":
        response["result"] = {
            "boxes": data.get("boxes"),
            "classes": data.get("classes"),
            "confidences": data.get("confidences"),
            "detection_count": int(data.get("detection_count", 0)),
            "inference_time_ms": float(data.get("inference_time_ms", 0.0)),
        }
    elif state == "failed":
        response["error"] = data.get("error_message", "Unknown worker processing error")
        
    return response
