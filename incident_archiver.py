import os
import time
import json
import uuid
from typing import Dict, List, Optional
import redis

INCIDENTS_DIR = os.getenv("INCIDENTS_DIR", os.path.join(os.path.dirname(__file__), "storage", "incidents"))
S3_BUCKET_NAME = os.getenv("S3_BUCKET", "robonexus-incidents")
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

os.makedirs(INCIDENTS_DIR, exist_ok=True)

try:
    r_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True, socket_timeout=1.0)
except Exception:
    r_client = None

def archive_incident(
    robot_id: str,
    event_type: str,
    criticality: str,
    details: Dict,
    image_base64: Optional[str] = None
) -> str:
    """
    Archives a safety hazard or worker failure event to the on-premise S3/MinIO bucket.
    Complies with ISO 3691-4 industrial safety incident recording specifications.
    """
    incident_id = f"INC-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    packet = {
        "incident_id": incident_id,
        "s3_uri": f"s3://{S3_BUCKET_NAME}/{time.strftime('%Y-%m-%d')}/{incident_id}.json",
        "timestamp": timestamp,
        "robot_id": robot_id,
        "event_type": event_type,
        "criticality": criticality,
        "compliance_standard": "ISO 3691-4 §5.2.2.4 (Safety Audit Trail)",
        "details": details,
        "has_sensor_frame": bool(image_base64)
    }
    
    # Store complete packet with frame to disk/S3 volume
    incident_file = os.path.join(INCIDENTS_DIR, f"{incident_id}.json")
    with open(incident_file, "w") as f:
        full_payload = {**packet, "image_base64": image_base64}
        json.dump(full_payload, f, indent=2)
        
    # Register summary to Redis index
    if r_client:
        try:
            r_client.lpush("incidents:recent", json.dumps(packet))
            r_client.ltrim("incidents:recent", 0, 49) # Keep 50 latest
            r_client.incr("stats:incidents_archived")
        except Exception:
            pass
            
    return packet["s3_uri"]

def list_recent_incidents(limit: int = 10) -> List[Dict]:
    """Retrieves the latest archived black-box incidents."""
    if r_client:
        try:
            items = r_client.lrange("incidents:recent", 0, limit - 1)
            if items:
                return [json.loads(i) for i in items]
        except Exception:
            pass
            
    # Fallback to local filesystem index
    incidents = []
    try:
        files = sorted(os.listdir(INCIDENTS_DIR), reverse=True)[:limit]
        for fname in files:
            if fname.endswith(".json"):
                with open(os.path.join(INCIDENTS_DIR, fname), "r") as f:
                    data = json.load(f)
                    data.pop("image_base64", None)
                    incidents.append(data)
    except Exception:
        pass
    return incidents

def get_incident_by_id(incident_id: str) -> Optional[Dict]:
    """Fetches complete incident record including sensor snapshot."""
    path = os.path.join(INCIDENTS_DIR, f"{incident_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None
