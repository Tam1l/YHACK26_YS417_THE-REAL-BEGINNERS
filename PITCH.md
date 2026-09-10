# 🤖 RoboNexus — Robotics-Aware Private AI Cloud
### *Hackathon Pitch Deck — YS417 THE REAL BEGINNERS*

---

## Slide 1 — The Problem

> **Every robot in a smart warehouse needs AI. But AI is expensive, slow, and dangerous when done wrong.**

Modern robot fleets — AGVs, drones, sweepers — increasingly rely on computer vision and AI for:

- 🚨 **Collision avoidance** (sub-100ms life-safety decisions)
- 📦 **Inventory scanning** (pallet detection, package recognition)
- 🚁 **Aerial navigation** (obstacle mapping, path planning)
- 🔧 **Defect inspection** (visual quality control)

**The status quo forces a painful tradeoff:**

| Option | Problem |
|---|---|
| Run AI on every robot | Expensive GPU hardware × entire fleet, high power, maintenance |
| Send to public cloud | WAN latency, internet dependency, sensitive data leaves facility |
| Do nothing | Blind robots, accidents, inefficiency |

**There is no good middle ground — until now.**

---

## Slide 2 — Our Solution

# RoboNexus
## *Shared, Private, Nearby AI Compute — With Robotics-Aware Intelligence*

**One AI compute cluster. Shared across your entire fleet. On your premises.**

```
     Robot Fleet                         RoboNexus Private Cloud
  +---------------------+          +----------------------------------+
  |  AGV-01   (P1)      |------>>  |  Secure Gateway (FastAPI)        |
  |  DRONE-04 (P2)      |------>>  |  RADS Priority Scheduler         |
  |  SWEEPER  (P5)      |------>>  |  Redis Sorted-Set Queue          |
  +---------------------+          |  YOLOv8 AI Workers (x5)         |
                                   |  Live Mission Control UI         |
                                   +----------------------------------+
```

**Key Promise:** The most safety-critical task **always** runs first — guaranteed, deterministically, in real time.

---

## Slide 3 — The Core Innovation: RADS

# RADS — Robotics-Aware Deadline Scheduler

> **The world's first scheduling algorithm designed specifically for mixed-criticality robot fleets.**

Standard queues treat all tasks equally. RADS does not.

### The RADS Scoring Formula

```
Score = 0.45 x Criticality  +  0.35 x Deadline Urgency  +  0.20 x Wait Time  -  0.10 x Inference Cost
```

| Weight | Factor | Why it matters |
|---|---|---|
| **45%** | Mission criticality (CRITICAL/HIGH/NORMAL/LOW) | Safety-critical tasks dominate |
| **35%** | Deadline urgency (time remaining) | Expiring deadlines jump the queue |
| **20%** | Aging / wait time | Prevents starvation of low-priority tasks |
| **-10%** | Estimated inference cost | Prefers cheaper tasks when tied |

### RADS vs FIFO vs Simple Priority

| Scheduler | Handles deadlines? | Anti-starvation? | Criticality-aware? | Dynamic re-scoring? |
|---|---|---|---|---|
| FIFO | No | Yes | No | No |
| Simple Priority | No | No | Yes | No |
| **RADS** | **Yes** | **Yes** | **Yes** | **Yes** |

---

## Slide 4 — System Architecture

```
+-------------------------------------------------------------------------+
|                    RoboNexus Edge Private Cloud                         |
|                                                                         |
|  +---------------------------------------+                              |
|  |     FastAPI Ingress Gateway           |  <- server.py               |
|  |  . JWT + Pre-shared token auth        |                              |
|  |  . Fleet RBAC per robot type          |                              |
|  |  . Rate limiting per tenant           |                              |
|  |  . RADS score computation             |                              |
|  |  . Edge fallback detection            |                              |
|  +--------------+------------------------+                              |
|                 |  ZADD (RADS score)                                    |
|  +--------------v------------------------+                              |
|  |     Redis Sorted-Set Priority Queue   |  <- Atomic ZPOPMIN          |
|  |     queue:tasks (up to 100 tasks)     |                              |
|  +--------------+------------------------+                              |
|                 |  ZPOPMIN (highest score first)                        |
|  +--------------v------------------------+                              |
|  |   AI Worker Pool (x5 concurrent)      |  <- worker.py               |
|  |  . YOLOv8 Nano vision inference       |                              |
|  |  . Perception policy engine           |                              |
|  |  . Incident archiving (ISO 3691-4)    |                              |
|  |  . Failover + crash recovery          |                              |
|  +--------------+------------------------+                              |
|                 |                                                        |
|  +--------------v------------------------+                              |
|  |  Elastic Autoscaler (background)      |  <- autoscaler.py           |
|  |  . Scale 2->5 workers on queue surge  |                              |
|  |  . Predictive pre-warming             |                              |
|  |  . Scale down after cooldown          |                              |
|  +---------------------------------------+                              |
|                                                                         |
|  +---------------------------------------+                              |
|  |  Mission Control Web UI               |  <- web/index.html          |
|  |  . Live arena canvas + robot tracks   |                              |
|  |  . YOLO camera feed                   |                              |
|  |  . Queue, latency, incident telemetry |                              |
|  |  . 8 one-click demo scenarios         |                              |
|  +---------------------------------------+                              |
+-------------------------------------------------------------------------+
```

---

## Slide 5 — Feature Deep-Dives

### Feature 1: Multi-Layer Security Gateway

**File:** `server.py`

- **JWT Bearer Token** authentication (HS256, configurable secret)
- **Pre-shared Robot Tokens** (`X-Robot-Token` header) per robot type
- **Robot Authorization Policies** — each token locked to max priority + criticality:
  - `agv-token` -> max priority 1, CRITICAL OK
  - `drone-token` -> max priority 2, HIGH OK
  - `sweeper-token` -> max priority 5, NORMAL only — **claims CRITICAL = HTTP 403**
- Rate limiting enforced per tenant via Redis atomic token-bucket counters

---

### Feature 2: RADS Priority Scheduler

**File:** `rads.py`

- Weighted multi-factor scoring (criticality 45%, deadline 35%, aging 20%, cost -10%)
- Redis `ZADD` with negative RADS score -> `ZPOPMIN` fetches highest-priority task atomically
- **Deadline Risk Prediction** — flags tasks whose predicted completion time will exceed deadline
- **Edge Fallback** — if predicted queue wait + inference + network > robot deadline: returns `EXECUTE_AT_EDGE`
- **5x Batch Leapfrog demo**: 5 low-priority tasks fill queue, 1 CRITICAL AGV task -> executes first

---

### Feature 3: Elastic Autoscaler

**File:** `autoscaler.py`

- Monitors Redis queue depth every 1 second
- **Reactive Scaling:** queue >= 3 tasks -> spawn additional workers (2 to up to 5 max)
- **Predictive Pre-warming:** `POST /announce-mission` registers high-load mission 15s ahead -> autoscaler pre-warms before load hits
- Scale-down with 6-second cooldown to prevent thrash
- All scaling events logged to Redis `cloud:autoscaler:events` stream for live UI telemetry

---

### Feature 4: Fleet RBAC and Multi-Tenancy

**File:** `fleet_tenants.py`

Three isolated tenant tiers:

| Tenant | Tier | SLA Target | Rate Limit | Priority |
|---|---|---|---|---|
| AGV Logistics | SAFETY_CRITICAL | 100ms | 50 req/s | 1 |
| Drone Navigation | OPERATIONAL | 250ms | 25 req/s | 2 |
| Sweeper Inventory | BEST_EFFORT | 800ms | 10 req/s | 5 |

- Token-resolved tenant lookup with full SLA enforcement
- Per-tenant Redis atomic rate limit counters
- Tenant context flows through all telemetry events

---

### Feature 5: YOLOv8 Real-Time Vision + Perception Policy

**Files:** `worker.py`, `perception_policy.py`, `docs/YOLO_MODEL_SETUP.md`

- **Model:** YOLOv8 Nano (`yolov8n.pt`, 6.5 MB) — CPU-optimized, no GPU required
- **Sub-30ms inference latency** — in-memory byte streaming, zero disk I/O
- **Perception Policy Engine** converts YOLO detections to robot action commands:

| Detection | Condition | Action |
|---|---|---|
| person in safety zone | High confidence | EMERGENCY_BRAKE |
| person outside zone | Any | SLOW_AND_MONITOR |
| car / truck / forklift | In corridor | CONTROLLED_STOP |
| pallet / agv | In path | REROUTE |
| Clear frame | — | PATH_CLEAR |

- AGV safety zone: center 25-75% width, lower 52% of frame
- Policy fully overridable via `ROBONEXUS_CLASS_POLICIES` env variable (JSON patch)

---

### Feature 6: S3 Incident Black-Box (ISO 3691-4 Compliant)

**File:** `incident_archiver.py`

- Generates structured incident records with unique `INC-{timestamp}-{hex}` IDs
- Full JSON packet: robot ID, event type, criticality, sensor frame, compliance tag
- **ISO 3691-4 Section 5.2.2.4** — Industrial Safety Audit Trail compliance
- Writes to on-premise MinIO/S3 volume at `s3://robonexus-incidents/{date}/{incident_id}.json`
- Redis index of 50 most recent incidents for live dashboard
- Events archived: `TASK_FAILOVER`, `EMERGENCY_BRAKE`, `WORKER_CRASH`, `DEADLINE_MISSED`

---

### Feature 7: Data Lakehouse Parquet Export

**File:** `batch_exporter.py`

- **ETL Pipeline** — queries all Redis event streams, transforms to columnar schema
- Exports as **Apache Parquet with SNAPPY compression** for downstream analytics
- Events captured: `TASK_FAILOVER`, `SCALE_UP`, `DEADLINE_MISSED`, `PREDICTIVE_SCALE_UP`, `EDGE_FALLBACK`
- Uploads to `s3://robonexus-analytics/{date}/` bucket
- Triggered via CLI, cron schedule, or `POST /trigger-lakehouse-export` REST endpoint
- Ready for Tableau, Power BI, or Apache Spark consumption

---

### Feature 8: Worker Failover and Crash Recovery

**Files:** `worker.py`, `workers.py`, `autoscaler.py`

- Workers register heartbeats in Redis every 500ms
- Missed heartbeat -> automatic worker respawn
- Tasks from crashed workers re-queued atomically — **zero task loss**
- **Kill Worker-1 demo** — simulates crash, shows automatic recovery in real time
- Robot-side exponential backoff retry: 1s -> 2s -> 4s -> 8s (prevents thundering herd)

---

### Feature 9: Mission Control Web UI

**Files:** `web/index.html`, `web/style.css`, `web/app.js`

A premium, dual-theme (dark/light) real-time operations dashboard.

**Side Panel (Operator Controls):**
- Robot mission selector, scene feed, criticality, deadline slider
- Dispatch Perception Task — one-click submit to RADS queue
- Live YOLO camera — capture frame, run inference, display result inline
- Quick-nav to all dashboard tabs

**8 One-Click Demo Scenarios (2x4 color-coded grid):**

| Color | Button | Demonstrates |
|---|---|---|
| Sapphire | 5x Batch Leapfrog | RADS preemption — AGV jumps 5 batch tasks |
| Sapphire | Announce Mission | Predictive pre-warming 15s before load spike |
| Emerald | Parquet Export | Lakehouse ETL to Apache Parquet |
| Emerald | Fleet Surge | Autoscaler reactive scale-up |
| Amber | Kill Worker-1 | Crash + automatic failover recovery |
| Amber | Edge Fallback | Deadline miss -> EXECUTE_AT_EDGE |
| Ruby | Emergency Hazard (AGV-01) | EMERGENCY_BRAKE + ISO incident log |
| Ruby | Rogue Token | Zero-trust 403 token rejection |

**Dashboard Tabs:**
1. Live Worker Fabric — pool status, heartbeats, task assignments
2. Elastic Autoscaler — scaling events, queue depth graph
3. Fleet RBAC and Quotas — per-tenant usage, rate limit gauges
4. S3 Incident Archive — ISO-compliant log with severity colors
5. YOLO Vision Feed — bounding boxes, action commands live

---

### Feature 10: 125-Test Verified Quality

**Directory:** `tests/`

| Test Suite | Coverage |
|---|---|
| `test_rads.py` | RADS scoring formula, edge cases, batch scenarios |
| `test_deadline_matrix.py` | All criticality x deadline x aging combinations |
| `test_edge_fallback.py` | Latency budget exceeded -> fallback decision |
| `test_gateway.py` | Auth, priority injection, rate limiting, RADS integration |
| `test_failover.py` | Worker crash -> task requeue -> recovery |
| `test_authorization.py` | Token policies, priority clamping, 403 enforcement |
| `test_perception_policy.py` | YOLO -> action mapping, safety zone geometry |
| `test_predictive_provisioning.py` | Mission announcement -> pre-warm timing |
| `test_lakehouse_exporter.py` | Parquet schema, S3 upload, event extraction |

**Result: 125 / 125 passing**

---

## Slide 6 — Technical Stack

| Layer | Technology | Purpose |
|---|---|---|
| API Gateway | FastAPI + Uvicorn | Async HTTP, sub-ms overhead |
| Queue | Redis Sorted Sets | Atomic ZADD/ZPOPMIN, O(log N) |
| AI Engine | Ultralytics YOLOv8 Nano | CPU vision inference, 6.5MB |
| Security | PyJWT + Pre-shared tokens | Multi-scheme robot auth |
| Storage | MinIO / S3 compatible | On-premise incident archive |
| Analytics | PyArrow + Parquet | Columnar lakehouse export |
| Dashboard | Vanilla HTML/CSS/JS | Zero-dependency mission control |
| Telemetry | Streamlit | Real-time metrics dashboard |
| Container | Docker + docker-compose | One-command deployment |
| Tests | pytest | 125 tests, all green |

---

## Slide 7 — Key Differentiators

| Capability | Generic YOLO Server | RoboNexus |
|---|---|---|
| Safety-critical preemption | No | Yes — RADS algorithm |
| Deadline awareness | No | Yes — real-time urgency scoring |
| Edge fallback | No | Yes — automatic EXECUTE_AT_EDGE |
| Multi-tenant isolation | No | Yes — Fleet RBAC + rate limits |
| Elastic autoscaling | No | Yes — reactive + predictive |
| Incident compliance | No | Yes — ISO 3691-4 audit trail |
| Worker fault tolerance | No | Yes — auto-respawn + requeue |
| Analytics export | No | Yes — Apache Parquet lakehouse |
| Anti-starvation | No | Yes — RADS aging factor |

---

## Slide 8 — Live Demo (30 Seconds)

1. **Show the UI** — dark-mode mission control, robot arena, live queue depth
2. **5x Batch Leapfrog** — watch CRITICAL AGV task jump 5 batch tasks in real time
3. **Kill Worker-1** — crash + automatic requeue + respawn — zero data loss
4. **Emergency Hazard** — EMERGENCY_BRAKE + ISO 3691-4 incident archived
5. **Rogue Token** — HTTP 403 — sweeper token rejected from CRITICAL priority
6. **Upload photo** — live YOLO inference — bounding boxes + action command
7. **pytest** — `125 passed` in the terminal

---

## Slide 9 — Impact and Scalability

### Real-World Applications

- **Warehouses** — AGV fleets sharing one AI cluster instead of 50 GPUs
- **Manufacturing** — Arms, AGVs, inspection drones with different SLAs on one platform
- **Hospitals** — Delivery robots + UV disinfection bots with strict safety tiers
- **Ports and Logistics** — Crane automation + ground robots with millisecond coordination

### Scalability Path

```
Today (Demo)         ->  Production               ->  Enterprise
----------------------------------------------------------------------
5 workers, 1 node    ->  10-50 GPU workers         ->  Multi-cluster
Redis localhost      ->  Redis Cluster (HA)         ->  RedisEnterprise
MinIO local          ->  MinIO distributed          ->  AWS S3 / GCS
Python workers       ->  NVIDIA Triton              ->  Model registry + A/B
RADS v1              ->  RADS v2 + ML prediction    ->  Reinforcement learning
```

---

## Slide 10 — Team and Ask

### YS417 — The Real Beginners

> We built a production-grade robotics AI infrastructure platform in one hackathon weekend.

**Shipped in this hackathon:**
- 10 major features
- 125 unit tests — all passing
- Full Docker containerization with docker-compose
- ISO 3691-4 compliant incident archiving
- Real-time web dashboard with 8 live interactive demo scenarios
- YOLOv8 vision pipeline with perception policy engine
- Apache Parquet data lakehouse export
- Elastic autoscaler with predictive pre-warming

**What we are asking:**
- Recognition for solving a real industrial robotics infrastructure problem
- Feedback on the RADS algorithm design
- Opportunity to continue building RoboNexus beyond the hackathon

---

## Quick Reference — Key Numbers

| Metric | Value |
|---|---|
| Inference latency | < 30ms (CPU, in-memory) |
| Max concurrent workers | 5 |
| Min workers always-on | 2 |
| Queue capacity | 100 tasks |
| Autoscaler reaction time | < 1 second |
| Incident log (Redis) | 50 most recent |
| RADS criticality weight | 45% |
| RADS deadline weight | 35% |
| Test coverage | 125 / 125 passing |
| Model size | 6.5 MB (YOLOv8 Nano) |
| Auth schemes | JWT + Pre-shared token |
| Compliance standard | ISO 3691-4 Section 5.2.2.4 |

---

*RoboNexus — Built at YHack 2026 by YS417 THE REAL BEGINNERS*
