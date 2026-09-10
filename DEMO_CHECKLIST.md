# RoboNexus judge demo

1. Run `pytest -q`; show the passing RADS tests.
2. Open `http://localhost:8501`; confirm gateway and Redis are online.
3. Dispatch five P9 batch tasks, then one P1 AGV collision task.
4. Point out that the P1 task is selected first and its RADS score/deadline is visible.
5. Submit a P1 task using `sweeper-token`; show the server rejects it with 403.
6. Show processed-task latency, queue depth, and the camera feed.
7. Explain that the worker tests cover a simulated failover path before the live demonstration.
