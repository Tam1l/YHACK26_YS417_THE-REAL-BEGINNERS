# =========================================================================
# RoboNexus Enterprise Robot AI Private Cloud - Universal Container Image
# CPU-first runtime: PyTorch CPU + YOLOv8 Nano (yolov8n.pt)
# See docs/YOLO_MODEL_SETUP.md for full details.
# =========================================================================
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    SERVER_URL=http://gateway:8000

# Install runtime dependencies for OpenCV/Pillow and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications
COPY requirements.txt .
COPY requirements-cpu.txt .
COPY requirements-yolo-cpu.txt .

# Install CPU-optimized base dependencies first
RUN pip install --no-cache-dir -r requirements-cpu.txt

# Install YOLOv8 CPU dependencies (CPU PyTorch + torchvision + ultralytics)
# as specified in docs/YOLO_MODEL_SETUP.md
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.7.1+cpu \
    torchvision==0.22.1+cpu \
    && pip install --no-cache-dir \
    "ultralytics>=8.3,<9" \
    opencv-python-headless==4.11.0.86 \
    "Pillow>=10.0" \
    "numpy>=1.26"

# Copy application source code and weights
COPY . /app

# Pre-download yolov8n.pt during build so workers start without network latency.
# If yolov8n.pt was already COPY'd in, Ultralytics skips the download.
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt'); print('[+] YOLOv8 Nano model ready')" 2>/dev/null \
    || python -c "from ultralytics import YOLO; m=YOLO('yolov8n.pt'); print('[+] YOLOv8 Nano downloaded:', m.model_name)"

EXPOSE 8000 8501

# Default entrypoint supports passing specific component: "gateway", "worker", "dashboard", "autoscaler"
CMD ["python", "worker.py"]
