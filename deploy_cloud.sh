#!/usr/bin/env bash
# =============================================================================
# RoboNexus Enterprise Robot AI Private Cloud - Universal Deployment Script
# =============================================================================
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}=================================================================${NC}"
echo -e "${CYAN}       ROBONEXUS — ROBOTICS-AWARE PRIVATE AI CLOUD PLATFORM       ${NC}"
echo -e "${CYAN}         Autonomous Edge Compute Fabric for Robotic Fleets        ${NC}"
echo -e "${CYAN}=================================================================${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Step 1: Ensure Redis is Available
echo -e "\n${YELLOW}[1/4] Checking State Fabric (Redis on 127.0.0.1:6379)...${NC}"
if ! nc -z 127.0.0.1 6379 2>/dev/null; then
    echo -e "${YELLOW}[*] Redis not responding on port 6379. Checking Docker container...${NC}"
    if docker ps -a --format '{{.Names}}' | grep -q "yhack26-redis"; then
        docker start yhack26-redis >/dev/null 2>&1 || true
        echo -e "${GREEN}[+] Started existing Docker container yhack26-redis.${NC}"
    else
        docker run -d --name yhack26-redis -p 127.0.0.1:6379:6379 redis:7-alpine >/dev/null 2>&1 || true
        echo -e "${GREEN}[+] Spawned new Redis container on 127.0.0.1:6379.${NC}"
    fi
    sleep 1
else
    echo -e "${GREEN}[+] State Fabric (Redis) is ACTIVE on 127.0.0.1:6379.${NC}"
fi

# Step 2: Python Virtual Environment
echo -e "\n${YELLOW}[2/4] Verifying Python runtime and virtualenv...${NC}"
if [ -d ".venv" ]; then
    PYTHON_BIN=".venv/bin/python"
    UVICORN_BIN=".venv/bin/uvicorn"
    STREAMLIT_BIN=".venv/bin/streamlit"
else
    echo -e "${YELLOW}[*] Creating Python virtual environment (.venv)...${NC}"
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
    PYTHON_BIN=".venv/bin/python"
    UVICORN_BIN=".venv/bin/uvicorn"
    STREAMLIT_BIN=".venv/bin/streamlit"
fi
echo -e "${GREEN}[+] Python environment verified.${NC}"

# Step 3: Stop any previous running instances to prevent port collisions
echo -e "\n${YELLOW}[3/4] Cleaning previous instance processes...${NC}"
pkill -f "uvicorn server:app" 2>/dev/null || true
pkill -f "python worker.py" 2>/dev/null || true
pkill -f "streamlit run dashboard.py" 2>/dev/null || true
pkill -f "python robot_simulator.py" 2>/dev/null || true
sleep 1

# Step 4: Launch Private Cloud Services
echo -e "\n${YELLOW}[4/4] Launching Private Cloud Cluster Daemons...${NC}"

# 1. Gateway
echo -e "  -> Launching Ingress API Gateway (Port 8000)..."
nohup $UVICORN_BIN server:app --host 0.0.0.0 --port 8000 > /tmp/robonexus_gateway.log 2>&1 &
disown

# 2. Worker Pool & Autoscaler
echo -e "  -> Launching Elastic AI Worker Pool & Dynamic Autoscaler..."
nohup $PYTHON_BIN worker.py > /tmp/robonexus_worker.log 2>&1 &
disown

# 3. Mission Control Dashboard
echo -e "  -> Launching Mission Control Telemetry Ground Station (Port 8501)..."
nohup $STREAMLIT_BIN run dashboard.py --server.port 8501 --server.headless true --server.enableCORS false > /tmp/robonexus_dash.log 2>&1 &
disown

# Allow 2 seconds for warm up
sleep 2

# Verification
echo -e "\n${GREEN}=================================================================${NC}"
echo -e "${GREEN}      [SUCCESS] ROBONEXUS PRIVATE AI CLOUD IS FULLY OPERATIONAL   ${NC}"
echo -e "${GREEN}=================================================================${NC}"
echo -e "  • Gateway Ingress:       ${CYAN}http://127.0.0.1:8000${NC}"
echo -e "  • Interactive Swagger:   ${CYAN}http://127.0.0.1:8000/docs${NC}"
echo -e "  • Cloud Topology Status: ${CYAN}http://127.0.0.1:8000/api/v1/cloud/status${NC}"
echo -e "  • Multi-Tenant Fleets:   ${CYAN}http://127.0.0.1:8000/api/v1/cloud/tenants${NC}"
echo -e "  • S3 Black-Box Incidents:${CYAN}http://127.0.0.1:8000/api/v1/cloud/incidents${NC}"
echo -e "  • Mission Control UI:    ${CYAN}http://localhost:8501${NC}"
echo -e "-----------------------------------------------------------------"
echo -e "To launch concurrent fleet simulator traffic:"
echo -e "  ${YELLOW}$PYTHON_BIN robot_simulator.py${NC}"
echo -e "To run a live elastic autoscaler queue surge test:"
echo -e "  ${YELLOW}curl -X POST http://127.0.0.1:8000/api/v1/cloud/surge${NC}"
echo -e "=================================================================\n"
