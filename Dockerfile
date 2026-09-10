# =========================================================================
# RoboNexus Enterprise Robot AI Private Cloud - Universal Container Image
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

# Install CPU-optimized dependencies
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch==2.7.1+cpu \
    && pip install --no-cache-dir -r requirements-cpu.txt \
    && pip install --no-cache-dir --no-deps ultralytics==8.4.146

# Copy application source code and weights
COPY . /app

EXPOSE 8000 8501

# Default entrypoint supports passing specific component: "gateway", "worker", "dashboard", "autoscaler"
CMD ["python", "worker.py"]
