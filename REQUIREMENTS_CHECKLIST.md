# Requirements checklist

## Runtime

- [x] Python 3.10 or newer
- [x] Redis 7 or newer on port 6379
- [x] FastAPI gateway on port 8000
- [x] Streamlit dashboard on port 8501
- [x] Two worker processes for the worker pool
- [x] YOLOv8 model download available on first worker startup

## Python packages

All Python package versions are pinned in `requirements.txt` for repeatable builds.

- [x] FastAPI and Uvicorn gateway
- [x] Redis client
- [x] Pydantic validation and JWT support
- [x] Ultralytics YOLO and PyTorch inference
- [x] Requests, Pillow, Pandas, and Streamlit
- [x] Pytest test runner

## Verification

- [x] `python -m pytest -q`
- [x] `docker compose config`
- [x] `docker compose up --build`
- [x] Open `http://localhost:8501`
