# RoboNexus — Top Features Implementation Roadmap

Repository: `Tam1l/YHACK26_YS417_THE-REAL-BEGINNERS`

Project: **RoboNexus — Robotics-Aware Private AI Cloud**

## Goal

The aim is to make RoboNexus look and behave like a **real private AI control plane for robot fleets**, not merely a YOLO inference API.

The strongest project story is:

> Multiple robot fleets compete for limited private AI compute. RoboNexus authenticates them, schedules requests according to mission criticality and deadlines, scales compute under load, preserves safety-critical jobs when workers fail, and shows the entire system live through a mission-control dashboard.

---

# Recommended Implementation Order

1. Criticality-Preserving Worker Failover
2. Production-Grade Robot/Fleet Authorization
3. RADS Scheduler Improvements + Dynamic Aging
4. Real YOLO Inference Mode Verification
5. SLA + Deadline Monitoring
6. Elastic Worker Autoscaling
7. Incident Black-Box Archive with MinIO
8. Mission-Control Dashboard Upgrade
9. Failure Injection / Chaos Demo Controls
10. Final End-to-End Demo Scenario

---

# 1. Criticality-Preserving Worker Failover

## Why this is the highest-priority feature

This directly addresses the challenge requirement:

> Maintain service availability when processing failures occur.

The ideal behavior:

```text
AGV-01 submits CRITICAL task
        ↓
RADS queues task at high priority
        ↓
Worker-1 starts processing
        ↓
Worker-1 crashes
        ↓
Health supervisor detects missed heartbeat
        ↓
Task is automatically recovered
        ↓
Original RADS priority is preserved
        ↓
Worker-2 receives task
        ↓
Task completes successfully
```

## Required behavior

- Every worker sends heartbeats.
- Gateway/supervisor tracks worker health.
- Every processing worker records its current in-flight task.
- A stale or dead worker is marked `DEAD`.
- Its in-flight job is automatically returned to the Redis sorted queue.
- The original RADS score must be preserved.
- Retry count must be tracked.
- Maximum retry count must prevent infinite retry loops.
- Recovery/failover events must be stored for the dashboard.
- Actual production failover logic must be tested.

## Codex Prompt

```text
You are working on the RoboNexus project:

Repository:
Tam1l/YHACK26_YS417_THE-REAL-BEGINNERS

RoboNexus is a private AI inference cloud for robot fleets.

Current architecture includes:
- FastAPI gateway in server.py
- Redis sorted-set scheduling queue
- worker.py worker pool
- RADS scheduler in rads.py
- Streamlit dashboard
- fleet tenancy/authentication
- worker heartbeat/failover concepts

TASK:
Implement production-grade criticality-preserving worker failover.

OBJECTIVE:
When a worker dies while processing an inference request, the system must automatically detect the failure and requeue the worker's in-flight task while preserving its original RADS priority.

IMPLEMENTATION REQUIREMENTS:

1. Inspect the complete current codebase before changing anything.

2. Refactor worker health monitoring so the actual production failover behavior can be called and tested through a deterministic method such as:

   HealthSupervisor.check_workers_once()

Do not place all logic only inside an infinite loop.

3. Every worker must maintain:
   - worker ID
   - heartbeat timestamp
   - current status
   - current task ID
   - current task RADS queue score where applicable

4. Define worker states:
   - IDLE
   - BUSY
   - DEAD

5. Detect a worker as dead when:
   - heartbeat is stale beyond the configured threshold, or
   - worker thread/process is no longer alive.

6. If a dead worker had an in-flight task:
   - retrieve the task safely
   - increment retry count
   - preserve the original Redis sorted-set score / RADS priority
   - requeue the task atomically where practical
   - clear the dead worker's task assignment
   - increment a global failover counter

7. Add a maximum retry count.
   Suggested default: 2 retries.

If retries exceed the threshold:
   - mark the task FAILED
   - store an explicit failure reason.

8. Record structured failover events in Redis.

Example event:

{
  "event": "TASK_FAILOVER",
  "task_id": "...",
  "failed_worker": "worker-1",
  "new_state": "REQUEUED",
  "retry_count": 1,
  "timestamp": "...",
  "criticality": "CRITICAL"
}

9. Preserve criticality and RADS score during failover.

A CRITICAL robot task must not lose priority merely because the worker processing it crashed.

10. Ensure race conditions cannot cause the same failed task to be simultaneously requeued multiple times.

11. Fix tests/test_failover.py.

Current tests must test the real worker/failover implementation rather than duplicating failover logic inside the test.

12. Add tests for:
   - stale heartbeat detection
   - busy worker failure
   - task requeue
   - RADS score preservation
   - retry count increment
   - maximum retry exhaustion
   - no duplicate recovery
   - idle worker death
   - healthy worker remains unchanged

13. Do not break existing APIs.

14. At the end:
   - run pytest
   - fix all regressions
   - provide a concise summary of changed files
   - explain exactly how to demonstrate worker failover live.

IMPORTANT:
Do not create a fake/simulated implementation that only updates dashboard text.
The Redis/task recovery must actually happen.
```

---

# 2. Production-Grade Robot and Fleet Authorization

## Goal

Prevent robots from:
- impersonating another robot,
- switching tenants,
- claiming unauthorized CRITICAL priority,
- using unknown tokens.

A floor sweeper should never be able to submit:

```text
"I am an emergency AGV. Give me highest priority."
```

## Required authorization binding

```text
TOKEN
  ↓
FLEET
  ↓
AUTHORIZED ROBOTS
  ↓
MAXIMUM CRITICALITY
  ↓
SLA / RATE LIMIT POLICY
```

The client must not be trusted to define its own tenant or privilege level.

## Codex Prompt

```text
Continue working on RoboNexus.

TASK:
Harden robot authentication, tenant isolation, identity binding, and priority authorization.

FIRST:
Inspect:
- server.py
- fleet_tenants.py
- tests/test_authorization.py
- tests/test_gateway.py
- dashboard.py
- robot_simulator.py

PROBLEMS TO FIX:

1. Missing Authorization credentials must never silently receive a default privileged token.

Remove behavior equivalent to:

missing token -> robot-token-secret

unless explicitly guarded behind an opt-in DEV_MODE environment variable.

Default behavior must be secure.

2. Unknown tokens must return:

HTTP 401 Unauthorized

3. Bind authentication to:
   - fleet tenant
   - allowed robot IDs
   - maximum criticality
   - rate limit policy

4. Never trust fleet_tenant supplied in the request body.

The authenticated identity/policy must control the effective tenant.

If request tenant conflicts with authenticated tenant:
return 403.

5. Prevent robot impersonation.

Example:

agv-token submitting robot_id=DRONE-07
must return 403.

6. Prevent criticality/priority escalation.

Example:

sweeper-token requesting CRITICAL
must return 403 or be safely clamped according to a clearly defined policy.

Prefer rejection with a descriptive reason for hackathon visibility.

7. Apply the same security model consistently to:
   - /api/v1/inference
   - /predict

8. Keep backward compatibility where reasonable but security must take priority.

9. Add structured security events for:
   - unknown token
   - robot impersonation
   - fleet spoofing
   - criticality escalation
   - rate-limit violation

10. Update the dashboard so each robot preset uses the correct fleet token.

Do not submit every dashboard task with robot-token-secret.

11. Update robot_simulator.py to remain compatible.

12. Tests must verify:
   - valid AGV request accepted
   - missing token rejected
   - unknown token rejected
   - wrong robot rejected
   - wrong fleet rejected
   - criticality escalation rejected
   - valid drone accepted
   - valid sweeper accepted
   - rate limiting remains functional

13. Run pytest and fix all failures.

14. Document the authorization architecture in README.md.

At completion, summarize:
- security model
- files modified
- demo steps to prove anti-priority-spoofing to judges.
```

---

# 3. RADS Scheduler Improvements + Dynamic Aging

## Goal

Make RADS genuinely robotics-aware throughout queue lifetime.

Current concept:

```text
RADS =
Criticality
+ Deadline Urgency
+ Waiting/Aging
- Estimated Inference Cost
```

Aging should change while a task waits, rather than existing only mathematically during initial enqueue.

## Codex Prompt

```text
Continue the RoboNexus implementation.

TASK:
Upgrade RADS — Robotics-Aware Deadline Scheduler — so waiting-time aging and deadline urgency can affect tasks while they remain queued.

Inspect:
- rads.py
- server.py
- worker.py
- Redis queue usage
- tests/test_rads.py
- tests/test_deadline_matrix.py

CURRENT MODEL:

RADS approximately combines:
- criticality
- deadline urgency
- waiting time
- estimated inference cost

The Redis queue stores negative RADS score so ZPOPMIN retrieves highest-priority work.

OBJECTIVE:
Make queue priorities evolve over time without making the implementation unstable or excessively expensive.

REQUIREMENTS:

1. Preserve the existing RADS conceptual model.

2. Create a clearly testable function:

calculate_rads(task, now=...)

It must support deterministic timestamps for tests.

3. Add a queue rescoring mechanism.

Choose a simple hackathon-safe design such as:
- periodic scheduler thread rescoring queued tasks every 100-500ms, or
- rescore a bounded set before worker dequeue.

Use whichever best matches the existing code.

4. Waiting tasks must gradually gain aging score.

5. Deadline urgency must increase as their remaining slack decreases.

6. CRITICAL jobs must retain strong preference.

7. Avoid starvation:
very old LOW/NORMAL jobs should eventually gain scheduling weight unless doing so would violate a safety-critical deadline.

8. Store enough scheduling information to explain why a task received its score.

For example:

{
  "criticality_component": 0.45,
  "deadline_component": 0.31,
  "waiting_component": 0.09,
  "inference_penalty": 0.02,
  "final_rads": 0.83
}

9. Add scheduling-decision events for dashboard visualization.

10. Add tests for:
   - CRITICAL > NORMAL under equal conditions
   - shorter deadline raises urgency
   - waiting increases score
   - queue rescoring changes ordering
   - starvation prevention
   - inference-cost penalty
   - negative Redis queue score convention remains correct

11. Ensure failover requeued tasks preserve or correctly recompute scheduling semantics without losing their original waiting history.

12. Avoid using an unbounded O(n) operation on every worker pop.

13. Document the RADS formula clearly.

14. Run pytest.

15. At completion explain how to demonstrate:

5 low-priority jobs queued
→ wait
→ inject CRITICAL 100ms AGV task
→ critical task immediately becomes queue position 1
→ old tasks still accumulate aging over time.
```

---

# 4. Real YOLO Inference Mode Verification

## Goal

Judges must be able to tell whether a result came from:
- actual YOLO inference, or
- synthetic infrastructure fallback.

Never accidentally present random detections as real AI inference.

## Codex Prompt

```text
Continue working on RoboNexus.

TASK:
Make inference execution transparent and guarantee a clean REAL YOLO vs SYNTHETIC FALLBACK distinction.

Inspect:
- worker.py
- Dockerfile
- requirements.txt
- requirements-cpu.txt
- dashboard.py
- server.py

REQUIREMENTS:

1. Add an explicit inference mode.

Suggested enum/string:

REAL_YOLO
SYNTHETIC_FALLBACK
UNAVAILABLE

2. If YOLOv8n loads successfully:
   inference_mode = REAL_YOLO

3. If the model cannot be loaded:
   do not pretend the fallback is another real vision engine.

Call it:
SYNTHETIC_FALLBACK

4. Every inference result should include:
   - inference_mode
   - model_name
   - model_loaded
   - inference_ms
   - worker_id

5. Correctly JSON-decode:
   - boxes
   - classes
   - confidences

before returning them through the API.

The API should return actual arrays, not JSON strings.

6. Add model health information to metrics.

Example:

{
  "model": "yolov8n.pt",
  "status": "READY",
  "mode": "REAL_YOLO"
}

7. Add visible dashboard status:

AI ENGINE ● YOLOv8n — REAL MODEL

or

AI ENGINE ⚠ SYNTHETIC FALLBACK

8. Preload/warm the YOLO model when workers start.

9. Perform a warmup inference if practical so the first live demo request is not misleadingly slow.

10. Ensure Docker deployment does not depend on an unexpected model download during the judging demo.

If legally/licensing-wise appropriate and practical:
document how to pre-cache the model.

11. Do not fabricate confidence scores for REAL_YOLO.

12. Add tests for:
   - response schema
   - valid arrays for boxes/classes/confidences
   - inference mode field
   - fallback mode clearly identified

13. Update README:
do not claim guaranteed sub-30ms inference.

Explain latency depends on:
- hardware
- model
- workload
- worker availability

14. Provide exact commands for verifying that the live system is using the real model.
```

---

# 5. SLA + Deadline Monitoring

## Goal

Turn latency into a robotics metric:

> Did the robot receive the AI result before its control deadline?

For robotics, this is far more meaningful than only displaying inference milliseconds.

## Codex Prompt

```text
Continue RoboNexus.

TASK:
Implement complete end-to-end deadline and SLA monitoring per task, robot, and fleet.

Inspect:
- server.py
- worker.py
- rads.py
- fleet_tenants.py
- dashboard.py
- robot_simulator.py

OBJECTIVE:
Track whether AI requests complete before their declared robotics deadline.

For every task capture timestamps:
- received_at
- queued_at
- processing_started_at
- processing_completed_at

Calculate:
- queue_wait_ms
- inference_ms
- total_latency_ms
- deadline_ms
- deadline_slack_ms
- deadline_met

deadline_met =
total_latency_ms <= deadline_ms

REQUIREMENTS:

1. Add deadline status to each result.

Example:

{
  "deadline_ms": 100,
  "total_latency_ms": 82,
  "deadline_slack_ms": 18,
  "deadline_met": true
}

2. Maintain global metrics:
   - total requests
   - completed
   - failed
   - deadline met
   - deadline missed
   - deadline success percentage
   - average queue latency
   - average inference latency
   - average total latency

3. Maintain per-fleet metrics.

Example:

FLEET-AGV-LOGISTICS
Requests: 120
Deadline Compliance: 97.5%
Avg Total Latency: 74ms

4. Maintain per-criticality metrics.

5. Deadline misses for CRITICAL jobs should create a visible alert/event.

6. Ensure existing stats that represent only inference time are not mislabeled as end-to-end latency.

7. Add endpoints or extend /api/v1/metrics so dashboard can retrieve these values.

8. Add tests for:
   - deadline met
   - deadline missed
   - queue latency calculation
   - total latency
   - fleet SLA counters
   - failed tasks excluded/included appropriately

9. Dashboard should show:
   - SLA Compliance %
   - Avg Inference
   - Avg Total Latency
   - Deadline Misses
   - Critical Deadline Misses

10. Update README.

11. Explain how to intentionally create a deadline miss for a live demo.
```

---

# 6. Elastic Worker Autoscaling

## Goal

Show the system changing compute capacity based on demand:

```text
Normal load:
2 workers

Queue surge:
2 → 3 → 4 → 5

Queue clears:
5 → 4 → 3 → 2
```

## Codex Prompt

```text
Continue RoboNexus.

TASK:
Make local worker autoscaling reliable, observable, and safely demoable.

Inspect:
- autoscaler.py
- worker.py
- server.py
- docker-compose.yml
- k8s/robonexus-cloud.yaml
- dashboard.py

CURRENT TARGET:
MIN_WORKERS = 2
MAX_WORKERS = 5

REQUIREMENTS:

1. Keep a minimum worker pool of 2.

2. Scale upward based on queue pressure.

Use:
- queue depth
and optionally
- deadline risk / number of critical queued jobs

3. Avoid uncontrolled worker creation.

4. Add cooldown/hysteresis so workers do not rapidly scale up/down.

5. Scale back toward minimum capacity when queue remains empty.

6. Never terminate a worker while it has an in-flight task.

7. Store autoscaling events.

Example:

{
  "event": "SCALE_UP",
  "from": 2,
  "to": 3,
  "queue_depth": 7,
  "timestamp": "..."
}

8. Add autoscaler state to metrics:
   - active workers
   - minimum
   - maximum
   - last scaling action
   - reason

9. Dashboard must visibly show:

WORKERS: 2 → 4
Reason: QUEUE PRESSURE

10. Add a one-click queue surge generator in the dashboard later, but keep autoscaler itself independent of UI.

11. Tests:
   - queue below threshold -> no scale
   - queue high -> scale up
   - max respected
   - empty queue -> scale down
   - min respected
   - busy worker not killed
   - cooldown works

12. IMPORTANT Kubernetes issue:
The application queue is a Redis SORTED SET.

Inspect whether the current KEDA Redis trigger is configured for a Redis list.

Do not claim the KEDA configuration works if it cannot monitor a sorted set.

Either:
A. implement a valid KEDA-compatible metric/scaling mechanism,
or
B. document Kubernetes autoscaling as deployment scaffolding and keep the verified hackathon demo on the local autoscaler.

13. Run tests and document verified behavior.
```

---

# 7. Incident Black-Box Archive with Real MinIO Storage

## Goal

Every safety-critical event should leave an auditable record.

Think of it as a **robotics flight recorder**.

## Codex Prompt

```text
Continue RoboNexus.

TASK:
Convert the current incident archiver into a real MinIO/S3-backed robotics incident black box.

Inspect:
- incident_archiver.py
- docker-compose.yml
- worker.py
- server.py
- requirements files
- dashboard.py

CURRENT PROBLEM:
The project contains MinIO infrastructure and may generate s3:// URIs, but incident data is currently written only to the local filesystem.

Do not preserve any fake S3 behavior.

REQUIREMENTS:

1. Integrate the MinIO service already present in docker-compose.

2. Use a proper Python MinIO or S3 client.

3. Configure using environment variables:
   - endpoint
   - access key
   - secret key
   - bucket
   - secure flag

4. Automatically create the incidents bucket if it does not exist.

5. For critical incidents, store:
   - original/sensor image
   - metadata JSON

Metadata should contain:
   - incident ID
   - task ID
   - robot ID
   - fleet
   - criticality
   - detection information
   - model/inference mode
   - worker ID
   - received timestamp
   - completion timestamp
   - total latency
   - deadline
   - deadline met/missed
   - failover count if any

6. Store an actual object URI/path corresponding to uploaded data.

7. Add incident listing/retrieval functions.

8. Dashboard must display recent critical incidents.

9. Provide graceful degradation:
if MinIO is unavailable, the main inference pipeline should not crash.

Mark archive result explicitly:
ARCHIVE_FAILED

10. Add retry behavior for transient MinIO failures.

11. Never hard-code production credentials.

Use docker-compose development credentials only through environment variables.

12. Do NOT claim ISO compliance.

Change language to something like:

"Designed for industrial safety auditability."

13. Add tests using mocks where necessary:
   - successful archive
   - metadata correctness
   - MinIO unavailable
   - upload failure
   - critical-only archive policy

14. Update README architecture diagram and deployment instructions.

15. Explain how to show a real archived incident in MinIO during judging.
```

---

# 8. Mission-Control Dashboard Upgrade

## Goal

Make the dashboard explain the architecture without judges having to read terminal output.

## Essential top strip

```text
AI ENGINE      YOLOv8n — REAL
RADS           ACTIVE
WORKERS        4 / 5
ROBOTS         3 CONNECTED
QUEUE          7
SLA            96.8%
```

## Codex Prompt

```text
Continue RoboNexus.

TASK:
Upgrade dashboard.py into a clear robotics mission-control dashboard without changing the core backend architecture.

The dashboard must prioritize system behavior over decorative graphics.

REQUIREMENTS:

1. Add a top health/status row showing:
   - AI Engine Mode
   - RADS Status
   - Active Workers
   - Connected Robots
   - Queue Depth
   - Overall Deadline/SLA Compliance

2. Add Worker Health panel.

Show each worker:
   - ID
   - state: IDLE / BUSY / DEAD
   - last heartbeat
   - current task
   - completed task count

3. Add RADS Queue panel.

Columns:
   - Position
   - Task
   - Robot
   - Fleet
   - Criticality
   - Deadline
   - RADS score
   - Deadline risk
   - Waiting time

4. Add Fleet SLA panel.

Per fleet:
   - requests
   - avg total latency
   - deadline success %
   - rate-limit violations

5. Add Live Event Log.

Events:
   - TASK_RECEIVED
   - TASK_SCHEDULED
   - WORKER_STARTED
   - WORKER_FAILED
   - TASK_REQUEUED
   - SCALE_UP
   - SCALE_DOWN
   - AUTH_REJECTED
   - DEADLINE_MISSED
   - INCIDENT_ARCHIVED

6. Add Recent Incidents panel with MinIO archive information.

7. Add AI result visualization:
   - input frame
   - bounding boxes where feasible
   - detected class
   - confidence
   - inference mode

8. Clearly identify:
REAL_YOLO
versus
SYNTHETIC_FALLBACK

9. Keep the dashboard usable on a normal laptop screen.

Avoid excessive giant fonts, decorative cards, and unnecessary scrolling.

10. Existing functionality must remain usable.

11. Dashboard should only read metrics/events through defined interfaces where practical rather than directly rewriting core Redis state.

Treat it as an operator console, but reduce tight coupling.

12. Add a small legend explaining:
   CRITICAL
   HIGH
   NORMAL
   LOW

13. Add a clear "System Healthy / Degraded" state.

14. Ensure dashboard does not crash if a metric is temporarily absent.

15. Verify dashboard manually after backend tests pass.
```

---

# 9. Failure Injection / Chaos Demo Controls

## Why this is valuable

Judges are far more impressed by:

> "Watch what happens when I kill the worker."

than by hearing:

> "Our architecture supports fault tolerance."

## Codex Prompt

```text
Continue RoboNexus.

TASK:
Add safe, demo-only chaos engineering controls to prove RoboNexus reliability live.

These controls must be disabled by default outside demo/development mode.

Add environment variable:

ROBONEXUS_DEMO_MODE=true

Only when enabled may chaos actions be exposed.

DASHBOARD CONTROLS:

1. Kill Worker
   - select worker
   - intentionally stop that worker
   - allow real health supervisor to detect failure

Do NOT directly fake the DEAD state.

2. Generate Queue Surge
   - generate configurable low/normal priority jobs
   - useful for demonstrating autoscaling

3. Inject Critical AGV Task
   - submit a genuine CRITICAL 100ms job through the normal API path

4. Simulate Unauthorized Priority Escalation
   - send CRITICAL request using sweeper credentials
   - visibly show HTTP 403

5. Simulate Slow Processing
   - optional controlled artificial delay
   - useful for demonstrating deadline risk and deadline misses

6. Restore Worker / Restart Pool
   - clean recovery mechanism for repeated demonstrations

7. Reset Demo State
   - clear demo queues/events/stats safely
   - never accidentally delete unrelated infrastructure data

REQUIREMENTS:

- All chaos actions must invoke real production code paths.
- Do not fake metrics.
- Add confirmation for destructive actions such as worker kill/reset.
- Mark all buttons clearly as DEMO controls.
- Ensure they are unavailable when ROBONEXUS_DEMO_MODE is false.
- Document the exact live demonstration procedure.
```

---

# 10. Final End-to-End Winning Demo Scenario

Once all core features are integrated, create a deterministic demonstration flow.

## Target Story

```text
1. RoboNexus starts with 2 workers.

2. Three fleets are connected:
   AGV
   Drone
   Sweeper

3. Generate multiple LOW/NORMAL inventory tasks.

4. Queue begins growing.

5. Autoscaler increases worker capacity:
   2 → 3 → 4 workers.

6. Inject a CRITICAL AGV collision-avoidance request
   with a 100 ms deadline.

7. RADS immediately places it ahead of ordinary jobs.

8. Worker-1 begins the CRITICAL task.

9. Kill Worker-1.

10. Heartbeat expires.

11. Health supervisor marks Worker-1 DEAD.

12. Critical task is automatically requeued
    with its priority preserved.

13. Worker-2/3 takes over.

14. Task completes.

15. Dashboard displays:
    failover event
    latency
    deadline status
    worker reassignment.

16. Critical incident metadata/frame is archived.

17. Submit a fake CRITICAL request using sweeper-token.

18. RoboNexus rejects it with HTTP 403.

19. Queue clears.

20. Autoscaler returns worker pool toward 2.
```

## Codex Prompt

```text
Perform a final integration pass on the RoboNexus repository.

Do not introduce major new architecture.

Your objective is to make the following hackathon demonstration deterministic and reliable:

A. System starts with minimum worker pool.
B. Multiple low/normal tasks create queue pressure.
C. Autoscaler scales workers upward.
D. A CRITICAL AGV 100ms task arrives.
E. RADS moves it ahead of lower-priority requests.
F. A worker processing it is deliberately killed.
G. Health supervisor detects failure.
H. Task is automatically requeued with criticality/RADS priority preserved.
I. Another worker processes it.
J. Dashboard records the failover and deadline outcome.
K. Incident is archived if policy requires it.
L. A sweeper attempts CRITICAL priority escalation.
M. Request is rejected with 403.
N. Queue drains and worker pool scales down.

TASKS:

1. Inspect all integration points for inconsistent schemas.

2. Normalize task states:
   RECEIVED
   QUEUED
   PROCESSING
   COMPLETED
   REQUEUED
   FAILED

3. Ensure timestamps use a consistent format.

4. Ensure worker IDs are included in results and events.

5. Ensure RADS score is visible.

6. Ensure deadline and SLA data are available.

7. Ensure failover events appear on dashboard.

8. Ensure autoscaling events appear on dashboard.

9. Ensure authentication events appear on dashboard.

10. Ensure incident archive state is visible.

11. Remove misleading claims:
    - guaranteed sub-30ms latency
    - fake S3 storage
    - fake safety-standard compliance
    - dynamic aging if not actually active
    - gRPC support if only proto exists
    - verified Kubernetes autoscaling if not tested

12. Ensure REAL_YOLO and SYNTHETIC_FALLBACK are clearly distinguished.

13. Run the complete test suite.

14. Add an integration/demo test script where practical.

15. Update README with:
    - current verified architecture
    - setup
    - demo steps
    - feature list
    - known limitations

16. Create DEMO_RUNBOOK.md containing exact terminal commands and dashboard actions needed for the final judge presentation.

Do not rewrite functioning modules unnecessarily.

Prioritize stability and a repeatable live demo.
```

---

# Feature Priority Matrix

| Priority | Feature | Judge Impact | Technical Value | Demo Value |
|---|---|---:|---:|---:|
| P0 | Criticality-Preserving Failover | 10/10 | 10/10 | 10/10 |
| P0 | Fleet/Auth Security | 9/10 | 10/10 | 9/10 |
| P0 | RADS Improvements | 10/10 | 10/10 | 10/10 |
| P0 | Real YOLO Verification | 8/10 | 8/10 | 9/10 |
| P0 | SLA/Deadline Monitoring | 10/10 | 9/10 | 10/10 |
| P1 | Autoscaling | 9/10 | 9/10 | 10/10 |
| P1 | Mission-Control Dashboard | 10/10 | 7/10 | 10/10 |
| P1 | Incident Black Box | 8/10 | 9/10 | 8/10 |
| P1 | Chaos Demo Controls | 10/10 | 7/10 | 10/10 |
| P2 | gRPC Runtime | 7/10 | 9/10 | 6/10 |
| P2 | Full Kubernetes Deployment | 7/10 | 9/10 | 5/10 |

---

# What NOT to Spend Too Much Time On

For a 24-hour hackathon, do not prioritize these before the P0/P1 items work reliably:

- complex Kubernetes deployment
- service mesh
- sophisticated GPU orchestration
- custom object-detection model training
- elaborate frontend animations
- distributed Redis cluster
- production-grade PKI
- full gRPC runtime migration
- extremely complex ML models

They can be presented as future deployment extensions.

---

# Final Core Feature Set

If time becomes extremely limited, ensure these six work perfectly:

```text
1. RADS Scheduler
2. Criticality-Preserving Failover
3. Fleet Authorization / Anti-Priority-Spoofing
4. Real YOLO Inference
5. Deadline/SLA Monitoring
6. Mission-Control Dashboard
```

Then add:

```text
7. Autoscaling
8. Incident Black Box
9. Demo Failure Injection
```

---

# Final Pitch

> RoboNexus is a private robotics AI control plane that allows multiple robot fleets to share centralized AI compute safely. Unlike a normal inference server, it understands mission criticality and deadlines through RADS, prevents robots from escalating their own priority, dynamically allocates compute under load, automatically recovers in-flight safety-critical requests when workers fail, and continuously measures whether robot decisions are delivered within their required control deadlines.

---

# Most Important Rule During Implementation

Do not optimize the project around the number of features.

Optimize around proving this sequence:

```text
COMPETING ROBOTS
      ↓
LIMITED COMPUTE
      ↓
RADS MAKES SAFETY-AWARE DECISION
      ↓
SYSTEM SCALES
      ↓
WORKER FAILS
      ↓
CRITICAL JOB SURVIVES
      ↓
DEADLINE/SLA IS MEASURED
      ↓
EVERYTHING IS VISIBLE TO THE JUDGE
```

That is the strongest RoboNexus story.
