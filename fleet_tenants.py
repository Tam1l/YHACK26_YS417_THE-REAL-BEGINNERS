import time
from typing import Dict, Optional, Tuple

TENANTS: Dict[str, Dict] = {
    "FLEET-AGV-LOGISTICS": {
        "tenant_id": "FLEET-AGV-LOGISTICS",
        "name": "Warehouse AGV Transport Fleet",
        "tier": "MISSION_CRITICAL",
        "priority_level": 1,
        "sla_target_ms": 100.0,
        "rate_limit_per_sec": 100,
        "tokens": ["agv-token", "robot-token-secret", "dev-agv-master"],
        "color": "#ef4444"
    },
    "FLEET-DRONE-PATROL": {
        "tenant_id": "FLEET-DRONE-PATROL",
        "name": "Airborne Facility Drone Patrol",
        "tier": "OPERATIONAL",
        "priority_level": 2,
        "sla_target_ms": 250.0,
        "rate_limit_per_sec": 25,
        "tokens": ["drone-token", "dev-drone-master"],
        "color": "#3b82f6"
    },
    "FLEET-SWEEPER-INVENTORY": {
        "tenant_id": "FLEET-SWEEPER-INVENTORY",
        "name": "Facility Cleaning & Inventory Sweepers",
        "tier": "BEST_EFFORT",
        "priority_level": 5,
        "sla_target_ms": 800.0,
        "rate_limit_per_sec": 10,
        "tokens": ["sweeper-token", "dev-sweeper-master"],
        "color": "#10b981"
    }
}

DEFAULT_TENANT = TENANTS["FLEET-AGV-LOGISTICS"]

def resolve_tenant(token: Optional[str] = None, explicit_tenant_id: Optional[str] = None) -> Dict:
    """Resolves the tenant profile from either an explicit header or bearer/robot token."""
    if explicit_tenant_id and explicit_tenant_id in TENANTS:
        return TENANTS[explicit_tenant_id]
    
    if token:
        for t in TENANTS.values():
            if token in t["tokens"]:
                return t
                
    return DEFAULT_TENANT

def check_tenant_quota(tenant_id: str, redis_client) -> Tuple[bool, str]:
    """Enforces atomic token-bucket / fixed-window rate limits per tenant in Redis."""
    tenant = TENANTS.get(tenant_id, DEFAULT_TENANT)
    max_rate = tenant["rate_limit_per_sec"]
    current_sec = int(time.time())
    key = f"quota:{tenant_id}:{current_sec}"
    
    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 2)
        if count > max_rate:
            return False, f"Tenant {tenant_id} rate limit exceeded ({count}/{max_rate} req/s)"
        return True, "Quota OK"
    except Exception:
        # If Redis is unavailable, allow throughput in degraded mode
        return True, "Redis bypass"

def record_tenant_telemetry(tenant_id: str, latency_ms: float, deadline_met: bool, redis_client):
    """Updates per-tenant SLA and throughput metrics in Redis."""
    try:
        pipe = redis_client.pipeline()
        pipe.hincrby(f"tenant:{tenant_id}", "total_requests", 1)
        if deadline_met:
            pipe.hincrby(f"tenant:{tenant_id}", "sla_met_count", 1)
        pipe.hincrbyfloat(f"tenant:{tenant_id}", "total_latency_sum", float(latency_ms))
        pipe.execute()
    except Exception:
        pass

def get_all_tenants_metrics(redis_client) -> Dict[str, Dict]:
    """Gathers SLA and request statistics for all tenants."""
    res = {}
    for tid, cfg in TENANTS.items():
        try:
            data = redis_client.hgetall(f"tenant:{tid}") or {}
            total = int(data.get("total_requests", 0))
            met = int(data.get("sla_met_count", 0))
            lat_sum = float(data.get("total_latency_sum", 0.0))
            sla_pct = round((met / total) * 100.0, 1) if total > 0 else 100.0
            avg_lat = round(lat_sum / total, 2) if total > 0 else 0.0
        except Exception:
            total, met, sla_pct, avg_lat = 0, 0, 100.0, 0.0

        res[tid] = {
            **cfg,
            "total_requests": total,
            "sla_met_count": met,
            "sla_compliance_pct": sla_pct,
            "avg_latency_ms": avg_lat
        }
    return res
