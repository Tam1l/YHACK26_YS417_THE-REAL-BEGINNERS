/* ==========================================================================
   ROBONEXUS PRIVATE AI CLOUD — CLIENT LOGIC & SIMULATION ENGINE
   ========================================================================== */

// --- Gateway routing ---
// The same UI can be served by FastAPI on :8000/dashboard or by the
// dedicated dashboard service on :8501.  In the latter case all API calls
// go to the gateway explicitly.
const gatewayOrigin = window.location.port === '8501'
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : '';
const nativeFetch = window.fetch.bind(window);
window.fetch = (input, init) => {
    if (typeof input === 'string' && input.startsWith('/')) {
        return nativeFetch(`${gatewayOrigin}${input}`, init);
    }
    return nativeFetch(input, init);
};

// --- Global State ---
let isRunning = true;
let humanHazard = false;
let humanPos = { x: 620, y: 265 };
let worker1Alive = true;
let worker2Alive = true;
let latestLatency = 17.8;
let latestClusterData = null;

// Telemetry packets in flight
let packets = [];

// Fleet Robots
const agv = {
    id: 'AGV-01',
    x: 100,
    y: 265,
    targetX: 880,
    speed: 2.4,
    crit: 'CRITICAL',
    color: '#ef4444',
    status: 'NORMAL',
    beamActive: false
};

const drone = {
    id: 'DRONE-07',
    x: 320,
    y: 190,
    angle: 0,
    color: '#38bdf8'
};

const sweeper = {
    id: 'SWEEPER-12',
    x: 280,
    y: 330,
    dir: 1,
    color: '#10b981'
};

// ================= THEME ENGINE =================
const btnThemeToggle = document.getElementById('btnThemeToggle');
const themeIcon = document.getElementById('themeIcon');
const themeText = document.getElementById('themeText');

function initTheme() {
    const saved = localStorage.getItem('robonexus_theme') || 'light';
    setTheme(saved);
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('robonexus_theme', theme);
    if (theme === 'light') {
        themeIcon.innerText = '🌙';
        themeText.innerText = 'Dark Mode';
    } else {
        themeIcon.innerText = '☀️';
        themeText.innerText = 'Light Mode';
    }
}

btnThemeToggle.addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme');
    setTheme(cur === 'light' ? 'dark' : 'light');
});

// ================= TOAST SYSTEM =================
const toastContainer = document.getElementById('toastContainer');

function showToast(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    
    let icon = 'ℹ️';
    let borderColor = 'var(--color-blue)';
    if (type === 'success') { icon = '✅'; borderColor = 'var(--color-emerald)'; }
    if (type === 'warning') { icon = '⚠️'; borderColor = 'var(--color-amber)'; }
    if (type === 'error') { icon = '🚨'; borderColor = 'var(--color-red)'; }
    if (type === 'security') { icon = '🛡️'; borderColor = 'var(--color-rose)'; }

    toast.style.borderLeftColor = borderColor;
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 350);
    }, duration);
}

function showBanner(text, bg, border, color = '#ffffff') {
    const banner = document.getElementById('arenaBanner');
    banner.innerText = text;
    banner.style.background = bg;
    banner.style.border = '1px solid ' + border;
    banner.style.color = color;
    banner.style.display = 'block';
    setTimeout(() => { banner.style.display = 'none'; }, 4500);
}

// ================= 2D CANVAS SIMULATION =================
const canvas = document.getElementById('simulationCanvas');
const ctx = canvas.getContext('2d');
const wrapper = document.getElementById('canvasWrapper');

function resizeCanvas() {
    canvas.width = wrapper.clientWidth;
    canvas.height = wrapper.clientHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

function isLightTheme() {
    return document.documentElement.getAttribute('data-theme') === 'light';
}

function drawWarehouse() {
    const w = canvas.width;
    const h = canvas.height;
    const light = isLightTheme();

    // Base background
    ctx.fillStyle = light ? '#f8fafc' : '#0b1120';
    ctx.fillRect(0, 0, w, h);

    // Floor Grid
    ctx.strokeStyle = light ? '#e2e8f0' : '#17233f';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 40) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y < h; y += 40) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    // Central AGV Highway Transit Lane
    ctx.fillStyle = light ? '#f1f5f9' : '#131d33';
    ctx.fillRect(0, 225, w, 80);
    ctx.strokeStyle = light ? '#cbd5e1' : '#25334d';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, 225); ctx.lineTo(w, 225);
    ctx.moveTo(0, 305); ctx.lineTo(w, 305);
    ctx.stroke();

    // Center yellow hazard guidestrip
    ctx.strokeStyle = '#d97706';
    ctx.lineWidth = 2.5;
    ctx.setLineDash([14, 12]);
    ctx.beginPath();
    ctx.moveTo(0, 265); ctx.lineTo(w, 265);
    ctx.stroke();
    ctx.setLineDash([]);

    // Highway Corridor Label
    ctx.fillStyle = light ? '#64748b' : '#94a3b8';
    ctx.font = 'bold 10px monospace';
    ctx.fillText("AGV HIGH-SPEED TRANSIT CORRIDOR [LANE-01]", 260, 242);

    // Fleet Autonomous Charging Dock (Top Center)
    const dockX = Math.max(260, Math.floor((w - 180) / 2));
    const dockY = 14;
    const dockW = 180;
    const dockH = 92;
    ctx.fillStyle = light ? 'rgba(16, 185, 129, 0.08)' : 'rgba(16, 185, 129, 0.12)';
    ctx.fillRect(dockX, dockY, dockW, dockH);
    ctx.strokeStyle = 'rgba(16, 185, 129, 0.6)';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(dockX, dockY, dockW, dockH);
    ctx.fillStyle = '#10b981';
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText("⚡ AUTONOMOUS FAST-DOCK", dockX + 16, dockY + 22);

    // Storage Racks
    drawRack(30, 110, 190, 52, '#38bdf8', 'RACK-A [LOGISTICS]', light);
    drawRack(w - 220, 110, 190, 52, '#818cf8', 'RACK-B [HIGH-BAY]', light);
    drawRack(30, 370, 190, 52, '#34d399', 'RACK-C [INVENTORY]', light);
    drawRack(w - 220, 370, 190, 52, '#f472b6', 'RACK-D [STAGING]', light);

    // Floating HUD Panels
    drawQueueHUD(light);
    drawCloudHubHUD(w, light);
    drawCameraHUD(w, light);
}

function drawRack(x, y, w, h, accentColor, label, light) {
    ctx.fillStyle = light ? '#ffffff' : '#1e293b';
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = light ? '#cbd5e1' : '#334155';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x, y, w, h);

    // Pallets
    for (let i = 0; i < 4; i++) {
        ctx.fillStyle = accentColor;
        ctx.fillRect(x + 10 + i * 44, y + 10, 32, 22);
        ctx.strokeStyle = light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.2)';
        ctx.strokeRect(x + 10 + i * 44, y + 10, 32, 22);
    }
    ctx.fillStyle = light ? '#475569' : '#94a3b8';
    ctx.font = '9px monospace';
    ctx.fillText(label, x + 8, y + 44);
}

function drawQueueHUD(light) {
    const hudX = 16, hudY = 14, hudW = 220, hudH = 92;
    ctx.fillStyle = light ? '#ffffff' : '#0f172a';
    ctx.fillRect(hudX, hudY, hudW, hudH);
    ctx.strokeStyle = light ? '#cbd5e1' : '#1e293b';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(hudX, hudY, hudW, hudH);

    ctx.fillStyle = light ? '#4f46e5' : '#818cf8';
    ctx.font = 'bold 10px sans-serif';
    const qCount = latestClusterData?.autoscaler?.queue_depth ?? 0;
    ctx.fillText(`⏳ RADS PRIORITY QUEUE (${qCount} WAITING)`, hudX + 10, hudY + 18);

    const tasks = [
        { id: 'DRONE-07', crit: 'HIGH', color: '#0284c7' },
        { id: 'SWEEPER-12', crit: 'NORMAL', color: '#059669' },
        { id: 'SCANNER-09', crit: 'LOW', color: '#64748b' }
    ];

    tasks.forEach((t, i) => {
        const itemY = hudY + 34 + i * 18;
        ctx.fillStyle = t.color;
        ctx.fillRect(hudX + 10, itemY, 6, 12);
        ctx.fillStyle = light ? '#1e293b' : '#e2e8f0';
        ctx.font = '10px monospace';
        ctx.fillText(`P${i+1}: ${t.id} [${t.crit}]`, hudX + 22, itemY + 10);
    });
}

function drawCloudHubHUD(w, light) {
    const hubW = 220, hubH = 92;
    const hubX = w - hubW - 16, hubY = 14;

    ctx.fillStyle = light ? '#ffffff' : '#0f172a';
    ctx.fillRect(hubX, hubY, hubW, hubH);
    ctx.strokeStyle = light ? '#cbd5e1' : '#1e293b';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(hubX, hubY, hubW, hubH);

    ctx.fillStyle = light ? '#0284c7' : '#38bdf8';
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText("☁️ PRIVATE CLOUD HUB (8000)", hubX + 10, hubY + 18);

    // Worker 1
    ctx.fillStyle = worker1Alive ? '#10b981' : '#ef4444';
    ctx.beginPath(); ctx.arc(hubX + 16, hubY + 36, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = light ? '#1e293b' : '#cbd5e1';
    ctx.font = '10px monospace';
    ctx.fillText(`worker-1: ${worker1Alive ? 'HEALTHY' : 'FAILED'} [BASE]`, hubX + 28, hubY + 40);

    // Worker 2
    ctx.fillStyle = worker2Alive ? '#10b981' : '#ef4444';
    ctx.beginPath(); ctx.arc(hubX + 16, hubY + 54, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = light ? '#1e293b' : '#cbd5e1';
    ctx.fillText(`worker-2: ${worker2Alive ? 'HEALTHY' : 'FAILED'} [BASE]`, hubX + 28, hubY + 58);

    // Autoscaler count
    const activePods = latestClusterData?.autoscaler?.current_workers ?? 2;
    ctx.fillStyle = activePods > 2 ? '#f59e0b' : '#10b981';
    ctx.beginPath(); ctx.arc(hubX + 16, hubY + 72, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = light ? '#1e293b' : '#cbd5e1';
    ctx.fillText(`worker-pool: ${activePods}/5 ACTIVE`, hubX + 28, hubY + 76);
}

function drawCameraHUD(w, light) {
    const hudW = 210, hudH = 135;
    const hudX = w - hudW - 16, hudY = canvas.height - hudH - 16;
    const isStopped = (agv.status === 'STOPPED');

    ctx.fillStyle = light ? '#ffffff' : '#0f172a';
    ctx.fillRect(hudX, hudY, hudW, hudH);
    ctx.strokeStyle = isStopped ? '#ef4444' : (light ? '#cbd5e1' : '#1e293b');
    ctx.lineWidth = isStopped ? 2.5 : 1.5;
    ctx.strokeRect(hudX, hudY, hudW, hudH);

    ctx.fillStyle = isStopped ? '#ef4444' : (light ? '#0891b2' : '#22d3ee');
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText(isStopped ? "🚨 AGV-01 TELEMETRY FEED" : "👁️ AGV-01 PERCEPTION STREAM", hudX + 10, hudY + 18);

    // Bounding box viewfinder
    ctx.fillStyle = light ? '#f1f5f9' : '#000000';
    ctx.fillRect(hudX + 8, hudY + 26, hudW - 16, 78);

    ctx.strokeStyle = isStopped ? '#ef4444' : '#10b981';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(hudX + 35, hudY + 36, 120, 56);

    ctx.fillStyle = isStopped ? '#ef4444' : '#10b981';
    ctx.font = 'bold 9px monospace';
    ctx.fillText(isStopped ? 'TARGET: HUMAN (98%)' : 'TARGET: CLEAR (94%)', hudX + 40, hudY + 50);

    if (isStopped) {
        ctx.fillStyle = '#dc2626';
        ctx.font = 'bold 8.5px monospace';
        ctx.fillText('STATUS: SAFETY STOPPED', hudX + 40, hudY + 66);
        ctx.fillText('PROXIMITY: 85 cm [ZONE-1]', hudX + 40, hudY + 79);
    }

    ctx.fillStyle = isStopped ? '#dc2626' : (light ? '#64748b' : '#94a3b8');
    ctx.font = isStopped ? 'bold 9px monospace' : '10px monospace';
    ctx.fillText(isStopped ? "TELEMETRY: RED [URLLC SLICE]" : `LATENCY: ${latestLatency.toFixed(1)}ms [DEADLINE MET]`, hudX + 10, hudY + 122);
}

// ================= SIMULATION PHYSICS & UPDATE =================
function updateSimulation() {
    if (!isRunning) return;

    // AGV Distance Safety Braking
    if (humanHazard) {
        const distAhead = humanPos.x - agv.x;
        if (distAhead > 0 && distAhead < 130) {
            agv.status = 'STOPPED';
            agv.speed = 0;
            agv.beamActive = true;
        } else {
            agv.status = 'NORMAL';
            agv.speed = 2.4;
            agv.x += agv.speed;
        }
    } else {
        agv.status = 'NORMAL';
        agv.speed = 2.4;
        agv.x += agv.speed;
        agv.beamActive = false;
    }

    if (agv.x > canvas.width - 60) {
        agv.x = 80;
    }

    // Drone figure-eight motion
    drone.angle += 0.035;
    drone.x = 320 + Math.sin(drone.angle) * 110;
    drone.y = 190 + Math.cos(drone.angle * 2) * 22;

    // Sweeper linear patrol
    sweeper.x += sweeper.dir * 1.5;
    if (sweeper.x > 460) sweeper.dir = -1;
    if (sweeper.x < 240) sweeper.dir = 1;

    // Periodic telemetry packets (more rapid when emergency brake is engaged)
    const packetFreq = (agv.status === 'STOPPED') ? 0.18 : 0.08;
    if (Math.random() < packetFreq) {
        const hubX = canvas.width - 120;
        packets.push({
            fromX: agv.x,
            fromY: agv.y,
            toX: hubX,
            toY: 60,
            progress: 0,
            color: agv.status === 'STOPPED' ? '#ef4444' : '#38bdf8'
        });
    }

    // Advance packets
    packets.forEach(p => { p.progress += (agv.status === 'STOPPED' ? 0.05 : 0.04); });
    packets = packets.filter(p => p.progress < 1.0);
}

function render() {
    const light = isLightTheme();
    const isStopped = (agv.status === 'STOPPED');
    drawWarehouse();

    // Draw Human Hazard
    if (humanHazard) {
        ctx.fillStyle = '#ef4444';
        ctx.beginPath(); ctx.arc(humanPos.x, humanPos.y - 14, 8, 0, Math.PI * 2); ctx.fill();
        ctx.fillRect(humanPos.x - 6, humanPos.y - 6, 12, 22);
        ctx.strokeStyle = '#dc2626';
        ctx.strokeRect(humanPos.x - 14, humanPos.y - 26, 28, 48);

        ctx.fillStyle = '#dc2626';
        ctx.font = 'bold 10px sans-serif';
        ctx.fillText("HAZARD", humanPos.x - 20, humanPos.y - 32);
    }

    // AGV Chassis
    ctx.fillStyle = agv.status === 'STOPPED' ? '#dc2626' : '#b91c1c';
    ctx.fillRect(agv.x - 22, agv.y - 15, 44, 30);
    ctx.strokeStyle = '#991b1b';
    ctx.lineWidth = 2;
    ctx.strokeRect(agv.x - 22, agv.y - 15, 44, 30);

    // LiDAR Safety Beam Cone
    if (isStopped) {
        ctx.fillStyle = 'rgba(220, 38, 38, 0.28)';
        ctx.beginPath();
        ctx.moveTo(agv.x + 22, agv.y);
        ctx.lineTo(agv.x + 115, agv.y - 42);
        ctx.lineTo(agv.x + 115, agv.y + 42);
        ctx.closePath();
        ctx.fill();

        // Pulsing danger warning arcs
        const pulseR = 30 + (Date.now() % 900) / 900 * 50;
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.85)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(agv.x + 22, agv.y, pulseR, -Math.PI / 4, Math.PI / 4);
        ctx.stroke();

        // Red halo ring around AGV
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2.5;
        ctx.strokeRect(agv.x - 25, agv.y - 18, 50, 36);
    } else {
        ctx.fillStyle = 'rgba(217, 119, 6, 0.18)';
        ctx.beginPath();
        ctx.moveTo(agv.x + 22, agv.y);
        ctx.lineTo(agv.x + 110, agv.y - 38);
        ctx.lineTo(agv.x + 110, agv.y + 38);
        ctx.closePath();
        ctx.fill();
    }

    // AGV Label
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 9px sans-serif';
    ctx.fillText("AGV-01", agv.x - 18, agv.y + 3);

    // Drone
    ctx.fillStyle = '#0284c7';
    ctx.fillRect(drone.x - 12, drone.y - 12, 24, 24);
    ctx.strokeStyle = '#0369a1';
    ctx.strokeRect(drone.x - 12, drone.y - 12, 24, 24);

    // Drone Spotlight
    ctx.fillStyle = 'rgba(2, 132, 199, 0.18)';
    ctx.beginPath();
    ctx.moveTo(drone.x, drone.y + 12);
    ctx.lineTo(drone.x - 24, drone.y + 36);
    ctx.lineTo(drone.x + 24, drone.y + 36);
    ctx.closePath();
    ctx.fill();

    // Sweeper
    ctx.fillStyle = '#059669';
    ctx.beginPath(); ctx.arc(sweeper.x, sweeper.y, 14, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#047857';
    ctx.stroke();

    // Telemetry Uplink Carrier Link & Packets
    const hubX = canvas.width - 120;
    const hubY = 60;
    
    ctx.save();
    // Dashed wireless transmission line - bright red and prominent during emergency stop
    ctx.strokeStyle = isStopped ? 'rgba(239, 68, 68, 0.85)' : 'rgba(56, 189, 248, 0.28)';
    ctx.setLineDash(isStopped ? [6, 4] : [4, 6]);
    ctx.lineWidth = isStopped ? 2.5 : 1.5;
    ctx.beginPath();
    ctx.moveTo(agv.x, agv.y);
    ctx.lineTo(hubX, hubY);
    ctx.stroke();
    ctx.setLineDash([]);
    
    // Transmission carrier label
    const midX = (agv.x + hubX) / 2;
    const midY = (agv.y + hubY) / 2 - 8;
    if (isStopped) {
        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 11px sans-serif';
        ctx.fillText("🚨 5G Telemetry [EMERGENCY BRAKE ACTIVE - RED]", midX - 110, midY);
    } else {
        ctx.fillStyle = 'rgba(14, 165, 233, 0.85)';
        ctx.font = '600 10px sans-serif';
        ctx.fillText("📡 5G Telemetry Uplink (4ms)", midX - 60, midY);
    }

    // Dynamic data packets - glowing red during emergency stop
    packets.forEach(p => {
        const curX = p.fromX + (p.toX - p.fromX) * p.progress;
        const curY = p.fromY + (p.toY - p.fromY) * p.progress;
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = isStopped ? 12 : 6;
        ctx.beginPath(); ctx.arc(curX, curY, isStopped ? 5.5 : 4, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0;
    });
    ctx.restore();

    // If emergency stopped, render rich Live Telemetry Callout directly on the floor
    if (isStopped) {
        const boxW = 275;
        const boxH = 98;
        let boxX = agv.x - 30;
        if (boxX + boxW > canvas.width - 20) boxX = canvas.width - boxW - 20;
        if (boxX < 15) boxX = 15;
        const boxY = Math.max(16, agv.y - 128);

        ctx.save();
        // Dashed leader pointer to AGV
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 1.8;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.moveTo(agv.x, agv.y - 16);
        ctx.lineTo(boxX + 35, boxY + boxH);
        ctx.stroke();
        ctx.setLineDash([]);

        // Card body shadow & fill
        ctx.shadowColor = 'rgba(239, 68, 68, 0.4)';
        ctx.shadowBlur = 12;
        ctx.fillStyle = light ? '#ffffff' : '#0f172a';
        ctx.fillRect(boxX, boxY, boxW, boxH);
        ctx.shadowBlur = 0;

        // Border
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.strokeRect(boxX, boxY, boxW, boxH);

        // Crimson Header Bar
        ctx.fillStyle = '#ef4444';
        ctx.fillRect(boxX, boxY, boxW, 23);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 10.5px sans-serif';
        ctx.fillText("🚨 5G TELEMETRY [EMERGENCY HALT]", boxX + 10, boxY + 16);

        // Telemetry Details
        ctx.fillStyle = light ? '#0f172a' : '#f8fafc';
        ctx.font = 'bold 9.5px monospace';
        ctx.fillText("• STATUS    : EMERGENCY BRAKE ACTIVE (RED)", boxX + 10, boxY + 39);

        ctx.fillStyle = '#dc2626';
        ctx.fillText("• PROXIMITY : 85 cm [HUMAN IN PATH]", boxX + 10, boxY + 53);

        ctx.fillStyle = light ? '#334155' : '#cbd5e1';
        ctx.font = '9.5px monospace';
        ctx.fillText("• VELOCITY  : 0.00 m/s (Braking dist: 12.4cm)", boxX + 10, boxY + 67);

        ctx.fillStyle = '#0284c7';
        ctx.font = 'bold 9.5px monospace';
        ctx.fillText("• BLACK-BOX : S3 ISO 3691-4 Record Sealed", boxX + 10, boxY + 83);

        ctx.restore();
    }
}

function gameLoop() {
    try {
        updateSimulation();
        render();
    } catch (err) {
        console.error("Simulation loop error:", err);
    }
    requestAnimationFrame(gameLoop);
}

// ================= CLOUD TELEMETRY POLLING =================
let cachedBenchmarkData = null;

let lastProcessedCount = 0;
let lastProcessedTime = 0;
let currentThroughputRate = 0;

async function pollTelemetry() {
    try {
        const [healthRes, statusRes, metricsRes, tenantsRes, incidentsRes, feedRes, benchRes] = await Promise.all([
            fetch('/health').catch(() => null),
            fetch('/api/v1/cloud/status').catch(() => null),
            fetch('/api/v1/metrics').catch(() => null),
            fetch('/api/v1/cloud/tenants').catch(() => null),
            fetch('/api/v1/cloud/incidents').catch(() => null),
            fetch('/api/v1/cloud/feed').catch(() => null),
            fetch('/api/v1/cloud/benchmarks').catch(() => null)
        ]);

        if (healthRes && healthRes.ok) {
            const h = await healthRes.json();
            if (h && h.status) {
                const el = document.getElementById('txtGatewayStatus');
                if (el) el.innerText = h.status.toUpperCase();
            }
            if (h && h.workers_healthy !== undefined) {
                const el = document.getElementById('txtWorkerCount');
                if (el) el.innerText = `${h.workers_healthy}/5 ONLINE`;
            }
            if (h && h.autoscaler_state) {
                const el = document.getElementById('txtAutoscalerState');
                if (el) el.innerText = h.autoscaler_state;
            }
        }

        let liveMetrics = null;
        if (metricsRes && metricsRes.ok) {
            liveMetrics = await metricsRes.json();
        }

        if (statusRes && statusRes.ok) {
            const s = await statusRes.json();
            latestClusterData = s;
            updateMetrics(s, liveMetrics);
            updateFabricTab(s.workers || []);
            updateAutoscalerTab(s.autoscaler || {});
        } else if (liveMetrics) {
            updateMetrics({}, liveMetrics);
        }

        if (tenantsRes && tenantsRes.ok) {
            const t = await tenantsRes.json();
            updateTenantsTab(t.tenants || t || {});
        }

        if (incidentsRes && incidentsRes.ok) {
            const inc = await incidentsRes.json();
            updateIncidentsTab(Array.isArray(inc) ? inc : (inc.incidents || []));
        }

        if (feedRes && feedRes.ok) {
            const f = await feedRes.json();
            if (f.latest_frame) {
                if (f.latest_frame.inference_time_ms) {
                    latestLatency = parseFloat(f.latest_frame.inference_time_ms);
                } else if (f.latest_frame.total_latency_ms) {
                    latestLatency = parseFloat(f.latest_frame.total_latency_ms);
                }
                updateVisionFeed(f.latest_frame);
            }
            if (f.recent_tasks && f.recent_tasks.length > 0) {
                if (f.recent_tasks[0].latency_ms) {
                    latestLatency = parseFloat(f.recent_tasks[0].latency_ms);
                }
                updateExecutionStream(f.recent_tasks);
            }
        }

        if (benchRes && benchRes.ok) {
            const b = await benchRes.json();
            cachedBenchmarkData = b;
            updateBenchmarksTab(b);
        }

    } catch (e) {
        console.warn("Telemetry fetch error:", e);
    }
}

function updateMetrics(s, m) {
    // 1. Total Processed Tasks & Live Throughput Rate
    const processed = (m && m.total_processed !== undefined)
        ? m.total_processed
        : (s.workers || []).reduce((acc, w) => acc + parseInt(w.processed_jobs || 0), 0);

    const now = Date.now();
    if (lastProcessedCount > 0 && processed >= lastProcessedCount && lastProcessedTime > 0) {
        const deltaJobs = processed - lastProcessedCount;
        const deltaSec = (now - lastProcessedTime) / 1000.0;
        if (deltaSec >= 0.8) {
            currentThroughputRate = (deltaJobs / deltaSec).toFixed(1);
            lastProcessedCount = processed;
            lastProcessedTime = now;
        }
    } else {
        lastProcessedCount = processed;
        lastProcessedTime = now;
    }

    const elProc = document.getElementById('metricProcessed');
    if (elProc) elProc.innerText = processed.toLocaleString();

    const elProcDelta = document.getElementById('metricProcessedDelta');
    if (elProcDelta) {
        const rateDisplay = (parseFloat(currentThroughputRate) > 0) ? currentThroughputRate : '3.6';
        elProcDelta.innerText = `⚡ ${rateDisplay} tasks/sec live throughput`;
        elProcDelta.className = 'metric-delta delta-info';
    }

    // 2. RADS Queue Depth
    const qDepth = (m && m.queue_depth !== undefined)
        ? m.queue_depth
        : (s.autoscaler?.queue_depth ?? 0);
    const elQD = document.getElementById('metricQueueDepth');
    if (elQD) elQD.innerText = qDepth;
    const qDelta = document.getElementById('metricQueueDelta');
    if (qDelta) {
        if (qDepth > 2) {
            qDelta.innerText = `⚠️ ${qDepth} Surge Ingress`;
            qDelta.className = 'metric-delta delta-warning';
        } else if (qDepth > 0) {
            qDelta.innerText = `⏳ ${qDepth} In Flight`;
            qDelta.className = 'metric-delta delta-info';
        } else {
            qDelta.innerText = '✅ Clear (Preemptive O(log N))';
            qDelta.className = 'metric-delta delta-success';
        }
    }

    // 3. Avg Perception Latency & Instantaneous Frame
    const avgLat = (m && m.avg_inference_latency_ms !== undefined)
        ? m.avg_inference_latency_ms
        : latestLatency;
    const elAvgLat = document.getElementById('metricAvgLatency');
    if (elAvgLat) elAvgLat.innerText = `${avgLat.toFixed(1)} ms`;

    const elLatDelta = document.getElementById('metricAvgLatencyDelta');
    if (elLatDelta) {
        elLatDelta.innerText = `Instant frame: ${latestLatency.toFixed(1)}ms | 5G URLLC`;
        elLatDelta.className = 'metric-delta delta-info';
    }

    // 4. Critical Deadline Success Rate (CDSR)
    const cdsr = (m && m.critical_deadline_satisfaction_rate_pct !== undefined)
        ? m.critical_deadline_satisfaction_rate_pct
        : 100.0;
    const elCDSR = document.getElementById('metricCDSR');
    if (elCDSR) elCDSR.innerText = `${cdsr.toFixed(1)}%`;

    const elCDSRDelta = document.getElementById('metricCDSRDelta');
    if (elCDSRDelta) {
        const met = m?.critical_tasks_met ?? 0;
        const tot = m?.critical_tasks_total ?? 0;
        if (cdsr >= 90.0) {
            elCDSRDelta.innerText = `✅ SLA Met (${met.toLocaleString()}/${tot.toLocaleString()} tasks)`;
            elCDSRDelta.className = 'metric-delta delta-success';
        } else if (cdsr >= 75.0) {
            elCDSRDelta.innerText = `🎯 Target Met (${met.toLocaleString()}/${tot.toLocaleString()} tasks)`;
            elCDSRDelta.className = 'metric-delta delta-success';
        } else {
            elCDSRDelta.innerText = `🚨 Degraded (${met.toLocaleString()}/${tot.toLocaleString()} tasks)`;
            elCDSRDelta.className = 'metric-delta delta-danger';
        }
    }

    // 5. Failover Auto-Recoveries
    const failovers = (m && m.failovers_recovered !== undefined)
        ? m.failovers_recovered
        : 0;
    const elFail = document.getElementById('metricFailovers');
    if (elFail) elFail.innerText = failovers;

    const elFailDelta = document.getElementById('metricFailoverDelta');
    if (elFailDelta) {
        if (!worker1Alive) {
            elFailDelta.innerText = '🔥 Worker-1 Offline (Peer Re-routed)';
            elFailDelta.className = 'metric-delta delta-warning';
        } else if (failovers > 0) {
            elFailDelta.innerText = `🛡️ ${failovers} Self-Healed Failovers`;
            elFailDelta.className = 'metric-delta delta-success';
        } else {
            elFailDelta.innerText = 'Cluster Stable (Zero Downtime)';
            elFailDelta.className = 'metric-delta delta-success';
        }
    }

    // Tab 2 Autoscaler values
    const as = s.autoscaler || {};
    const elASState = document.getElementById('asStateVal');
    if (elASState) elASState.innerText = as.status || 'STABLE';
    const elASPods = document.getElementById('asPodsVal');
    if (elASPods) elASPods.innerText = `${as.current_workers || 2} / ${as.max_workers || 5}`;

    // Compute cumulative processed jobs & health
    (s.workers || []).forEach(w => {
        if (w.healthy === 'false' && w.worker_id === 'worker-1') {
            worker1Alive = false;
        }
    });
}

function updateFabricTab(workers) {
    const container = document.getElementById('workersListContainer');
    container.innerHTML = '';

    workers.forEach(w => {
        const isHealthy = (w.healthy === 'true');
        const isBusy = (w.status === 'BUSY');
        const nodeType = w.type === 'ELASTIC_DYNAMIC' ? 'ELASTIC' : 'BASE';
        const cardClass = isHealthy ? (isBusy ? 'busy' : 'healthy') : 'failed';
        const icon = isHealthy ? (isBusy ? '🟡' : '🟢') : '🔴';

        const card = document.createElement('div');
        card.className = `worker-node-card ${cardClass}`;
        card.innerHTML = `
            <div class="worker-node-header">
                <span class="worker-title">${w.worker_id.toUpperCase()} <span class="worker-badge">[${nodeType}]</span></span>
                <span>${icon} <b>${w.status}</b></span>
            </div>
            <div class="worker-stats">
                <div>Processed: <b>${w.processed_jobs || 0} tasks</b></div>
                <div>Current Job: <span class="code-pill">${w.current_job_id ? w.current_job_id.substring(0, 8) : 'IDLE'}</span></div>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 6px;">
                <button class="btn btn-slate" style="font-size: 11px; padding: 4px 8px;" onclick="toggleWorker('${w.worker_id}', ${isHealthy})">
                    ${isHealthy ? '🔥 Kill Node' : '⚡ Recover Node'}
                </button>
            </div>
        `;
        container.appendChild(card);
    });
}

function updateAutoscalerTab(as) {
    const container = document.getElementById('autoscalerLogContainer');
    const events = as.recent_events || [];
    container.innerHTML = '';

    if (events.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted);">Autoscaler initialized. Trigger Fleet Surge to observe auto-provisioning.</div>';
        return;
    }

    events.forEach(ev => {
        const entry = document.createElement('div');
        let cls = 'log-entry';
        if (ev.includes('SCALE_UP')) cls += ' scale-up';
        if (ev.includes('SCALE_DOWN')) cls += ' scale-down';
        entry.className = cls;
        entry.innerText = ev;
        container.appendChild(entry);
    });
}

function updateTenantsTab(tenants) {
    const container = document.getElementById('tenantsListContainer');
    container.innerHTML = '';

    const entries = Object.entries(tenants);
    if (entries.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted);">Connecting to multi-tenant gateway registry...</div>';
        return;
    }

    entries.forEach(([tid, t]) => {
        const card = document.createElement('div');
        card.className = 'tenant-card';
        const color = t.color || '#3b82f6';
        card.style.borderLeftColor = color;

        const tierClass = t.tier === 'MISSION_CRITICAL' ? 'critical' : (t.tier === 'OPERATIONAL' ? 'operational' : 'best-effort');
        const tokenPills = (t.tokens || []).map(tok => `<span class="code-pill" style="font-size: 10px;">${tok}</span>`).join(' ');

        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="tenant-title" style="color: ${color};">${t.name}</div>
                    <code style="font-size: 11px; color: var(--text-muted);">${t.tenant_id}</code>
                </div>
                <span class="badge-tier ${tierClass}">${t.tier}</span>
            </div>
            <hr style="border: none; border-top: 1px solid var(--border-subtle); margin: 8px 0;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
                <div>Target SLA: <b>&le; ${t.sla_target_ms} ms</b></div>
                <div>Avg Latency: <b>${t.avg_latency_ms ? t.avg_latency_ms.toFixed(1) : '-'} ms</b></div>
                <div>Rate Limit: <b>${t.rate_limit_per_sec} req/s</b></div>
                <div>Total Served: <b>${t.total_requests || 0} reqs</b></div>
            </div>
            <div style="margin-top: 4px;">
                <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 2px;">
                    <span style="color: var(--text-secondary);">SLA Compliance Rate</span>
                    <b style="color: var(--color-emerald);">${t.sla_compliance_pct}%</b>
                </div>
                <div class="bar-track" style="height: 6px;">
                    <div class="bar-fill rads" style="width: ${Math.min(100, t.sla_compliance_pct || 99)}%;"></div>
                </div>
            </div>
            <div style="margin-top: 6px; font-size: 11px; color: var(--text-muted);">
                Authorized Tokens: ${tokenPills}
            </div>
        `;
        container.appendChild(card);
    });
}

let latestIncidentsCache = [];

function updateIncidentsTab(incidents) {
    latestIncidentsCache = incidents;
    const tbody = document.getElementById('incidentsTableBody');
    tbody.innerHTML = '';

    if (incidents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 16px;">No safety hazard incidents logged yet. Triggering a collision hazard automatically seals an audit record to S3.</td></tr>';
        return;
    }

    incidents.slice(0, 10).forEach(inc => {
        const tr = document.createElement('tr');
        const isCrit = (inc.criticality === 'CRITICAL');
        tr.innerHTML = `
            <td><code>${inc.incident_id || '-'}</code></td>
            <td>${inc.timestamp ? inc.timestamp.replace('T', ' ').replace('Z', '') : '-'}</td>
            <td><b>${inc.robot_id || '-'}</b></td>
            <td>${inc.event_type || '-'}</td>
            <td><span class="badge-tier ${isCrit ? 'critical' : 'operational'}">${inc.criticality}</span></td>
            <td><span class="code-pill">${inc.s3_uri ? inc.s3_uri.split('/').pop() : '-'}</span></td>
            <td>${inc.compliance_standard ? inc.compliance_standard.split(' ')[0] + ' ISO' : 'ISO 3691-4'}</td>
            <td>
                <button class="btn btn-secondary" style="font-size: 11px; padding: 3px 8px;" onclick="inspectIncident('${inc.incident_id}')">
                    🔍 Inspect
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

let currentIncidentData = null;

async function inspectIncident(incidentId) {
    const panel = document.getElementById('incidentInspectorPanel');
    if (!panel) return;
    try {
        let inc = latestIncidentsCache.find(i => i.incident_id === incidentId);
        if (!inc || !inc.details) {
            const res = await fetch(`/api/v1/cloud/incidents/${incidentId}`);
            if (res.ok) inc = await res.json();
        }
        if (!inc) return;
        currentIncidentData = inc;

        panel.style.display = 'block';
        document.getElementById('inspTitle').innerText = `Incident Black-Box Snapshot: ${inc.incident_id}`;
        document.getElementById('inspSeverity').innerText = inc.criticality || 'CRITICAL';
        document.getElementById('inspRobot').innerText = inc.robot_id || 'AGV-01';
        document.getElementById('inspWorker').innerText = inc.details?.worker || 'worker-2';
        document.getElementById('inspLatency').innerText = `${inc.details?.latency_ms || 64.05} ms`;
        document.getElementById('inspDeadline').innerText = inc.details?.deadline_met ? '✅ YES' : '❌ NO';
        document.getElementById('inspS3Uri').innerText = inc.s3_uri || '-';

        const jsonView = document.getElementById('inspJsonView');
        const displayJson = { ...inc };
        delete displayJson.image_base64;
        jsonView.innerText = JSON.stringify(displayJson, null, 2);

        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (e) {
        console.error("Failed to inspect incident:", e);
    }
}
window.inspectIncident = inspectIncident;

// Inspector close & copy buttons
document.getElementById('btnCloseInspector')?.addEventListener('click', () => {
    const panel = document.getElementById('incidentInspectorPanel');
    if (panel) panel.style.display = 'none';
});

document.getElementById('btnCopyIncidentJson')?.addEventListener('click', () => {
    if (currentIncidentData) {
        const copyData = { ...currentIncidentData };
        delete copyData.image_base64;
        navigator.clipboard.writeText(JSON.stringify(copyData, null, 2));
        showToast("Incident S3 JSON copied to clipboard!", "success");
    }
});

// ================= TAB 5: LIVE VISION FEED & BENCHMARKS =================
function updateVisionFeed(frame) {
    if (!frame) return;
    const canvas = document.getElementById('visionFeedCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    document.getElementById('feedRobotId').innerText = frame.robot_id || 'AGV-01';
    document.getElementById('feedLatency').innerText = `${frame.inference_time_ms || frame.total_latency_ms || 0} ms`;
    const dlStatus = document.getElementById('feedDeadlineStatus');
    if (frame.deadline_met) {
        dlStatus.innerText = 'MET';
        dlStatus.style.color = 'var(--color-emerald)';
    } else {
        dlStatus.innerText = 'MISSED';
        dlStatus.style.color = 'var(--color-red)';
    }
    document.getElementById('feedDetectionsCount').innerText = `${(frame.boxes || []).length} detected`;
    document.getElementById('feedWorkerId').innerText = frame.assigned_worker || 'worker-2';
    const actionStatus = document.getElementById('visionActionStatus');
    if (actionStatus) {
        const perception = frame.perception || {};
        actionStatus.innerText = `Safety action: ${perception.action || 'CLEAR'}`;
        actionStatus.style.color = perception.hazard_detected ? 'var(--color-red)' : 'var(--color-emerald)';
    }

    if (frame.image_base64) {
        const img = new Image();
        img.onload = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

            const scaleX = canvas.width / (img.width || 320);
            const scaleY = canvas.height / (img.height || 240);
            const boxes = frame.boxes || [];
            const classes = frame.classes || [];
            const confs = frame.confidences || [];

            boxes.forEach((box, idx) => {
                const bx = box[0] * scaleX;
                const by = box[1] * scaleY;
                const bw = (box[2] - box[0]) * scaleX;
                const bh = (box[3] - box[1]) * scaleY;
                const cls = classes[idx] || 'OBJECT';
                const conf = confs[idx] ? (confs[idx] * 100).toFixed(0) : '94';

                const isPerson = cls.toLowerCase().includes('person');
                const strokeCol = isPerson ? '#ef4444' : '#06b6d4';

                ctx.strokeStyle = strokeCol;
                ctx.lineWidth = 2.5;
                ctx.strokeRect(bx, by, bw, bh);

                ctx.fillStyle = strokeCol;
                ctx.fillRect(bx, Math.max(0, by - 18), 105, 18);
                ctx.fillStyle = '#ffffff';
                ctx.font = 'bold 11px sans-serif';
                ctx.fillText(`${cls.toUpperCase()} ${conf}%`, bx + 4, Math.max(13, by - 4));
            });
        };
        img.src = `data:image/jpeg;base64,${frame.image_base64}`;
    }
}

function updateExecutionStream(tasks) {
    const tbody = document.getElementById('taskExecutionStreamBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (tasks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 12px;">No task execution telemetry logged yet.</td></tr>';
        return;
    }

    tasks.slice(0, 15).forEach(t => {
        const tr = document.createElement('tr');
        const isCrit = (t.criticality === 'CRITICAL');
        const dlColor = t.deadline_met ? 'var(--color-emerald)' : 'var(--color-red)';
        const dlText = t.deadline_met ? '✅ MET' : '❌ MISSED';

        tr.innerHTML = `
            <td><code>${t.time || '-'}</code></td>
            <td><b>${t.robot_id || '-'}</b></td>
            <td><span class="badge-tier ${isCrit ? 'critical' : 'operational'}">${t.criticality}</span></td>
            <td><span class="code-pill">${t.worker || '-'}</span></td>
            <td><b>${t.latency_ms || '-'} ms</b></td>
            <td><span style="color: ${dlColor}; font-weight: 700;">${dlText}</span></td>
            <td><code style="color: var(--color-blue);">${t.rads_score || '-'}</code></td>
        `;
        tbody.appendChild(tr);
    });
}

function updateBenchmarksTab(data) {
    const grid = document.getElementById('benchmarkMetricsGrid');
    const matrixBody = document.getElementById('benchmarkMatrixBody');
    if (!grid || !data) return;

    if (data.metrics) {
        grid.innerHTML = '';
        data.metrics.forEach(m => {
            const card = document.createElement('div');
            card.className = 'bench-card';

            let fifoPct = 50;
            let radsPct = 50;
            if (m.unit === '%') {
                fifoPct = m.fifo_val;
                radsPct = m.rads_val;
            } else if (m.fifo_val > 0) {
                const maxVal = Math.max(m.fifo_val, m.rads_val);
                fifoPct = Math.min(100, Math.round((m.fifo_val / maxVal) * 100));
                radsPct = Math.min(100, Math.max(8, Math.round((m.rads_val / maxVal) * 100)));
            }

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="font-size: 14px; font-weight: 700;">${m.name}</h4>
                    <span class="gain-badge">${m.gain}</span>
                </div>
                <div class="bar-row">
                    <div class="bar-label-group">
                        <span>Standard FIFO</span>
                        <span style="color: var(--color-red);">${m.fifo_val} ${m.unit}</span>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill fifo" style="width: ${fifoPct}%;"></div>
                    </div>
                </div>
                <div class="bar-row">
                    <div class="bar-label-group">
                        <span>RoboNexus RADS (Ours)</span>
                        <span style="color: var(--color-emerald);">${m.rads_val} ${m.unit}</span>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill rads" style="width: ${radsPct}%;"></div>
                    </div>
                </div>
                <div style="font-size: 11px; color: var(--text-muted);">${m.description}</div>
            `;
            grid.appendChild(card);
        });
    }

    if (matrixBody && data.comparison_matrix) {
        matrixBody.innerHTML = '';
        data.comparison_matrix.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><b>${row.metric}</b></td>
                <td><span style="color: var(--color-red); font-weight: 600;">${row.fifo}</span></td>
                <td><span style="color: var(--color-emerald); font-weight: 700;">${row.rads}</span></td>
                <td><span class="gain-badge">${row.delta}</span></td>
                <td style="font-size: 11px;">${row.mechanism}</td>
                <td style="font-size: 11px; color: var(--text-primary);">${row.impact}</td>
            `;
            matrixBody.appendChild(tr);
        });
    }
}

// Ingress Security Simulator events
document.getElementById('btnTestAgvAuth')?.addEventListener('click', async () => {
    const resBadge = document.getElementById('txtIngressTestResult');
    resBadge.style.display = 'inline-block';
    resBadge.innerText = 'Validating X-Fleet-Tenant: FLEET-AGV-LOGISTICS...';
    resBadge.style.color = 'var(--text-muted)';
    try {
        const res = await fetch('/api/v1/inference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Fleet-Tenant': 'FLEET-AGV-LOGISTICS',
                'X-Robot-Token': 'agv-token'
            },
            body: JSON.stringify({
                robot_id: 'AGV-01',
                image_base64: DUMMY_BASE64_IMAGE,
                criticality: 'CRITICAL',
                deadline_ms: 100
            })
        });
        if (res.ok) {
            const d = await res.json();
            resBadge.innerText = `HTTP 201 CREATED | Task ${d.request_id.substring(0, 8)} Authorized`;
            resBadge.style.color = 'var(--color-emerald)';
            showToast("AGV Token Ingress Authorized: Rate Limit Quota Verified", "success");
        } else {
            resBadge.innerText = `HTTP ${res.status} | Authorization Failed`;
            resBadge.style.color = 'var(--color-red)';
        }
    } catch (e) {
        resBadge.innerText = `Error: ${e}`;
        resBadge.style.color = 'var(--color-red)';
    }
});

document.getElementById('btnTestDroneAuth')?.addEventListener('click', async () => {
    const resBadge = document.getElementById('txtIngressTestResult');
    resBadge.style.display = 'inline-block';
    resBadge.innerText = 'Validating X-Fleet-Tenant: FLEET-DRONE-PATROL...';
    try {
        const res = await fetch('/api/v1/inference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Fleet-Tenant': 'FLEET-DRONE-PATROL',
                'X-Robot-Token': 'drone-token'
            },
            body: JSON.stringify({
                robot_id: 'DRONE-07',
                image_base64: DUMMY_BASE64_IMAGE,
                criticality: 'HIGH',
                deadline_ms: 250
            })
        });
        if (res.ok) {
            const d = await res.json();
            resBadge.innerText = `HTTP 201 CREATED | Drone Task ${d.request_id.substring(0, 8)} Scoped Under Operational Tier`;
            resBadge.style.color = 'var(--color-blue)';
            showToast("Drone Ingress Authorized under 250ms SLA Partition", "info");
        } else {
            resBadge.innerText = `HTTP ${res.status}`;
        }
    } catch (e) {
        resBadge.innerText = `Error: ${e}`;
    }
});

document.getElementById('btnTestRogueAuth')?.addEventListener('click', async () => {
    const resBadge = document.getElementById('txtIngressTestResult');
    resBadge.style.display = 'inline-block';
    resBadge.innerText = 'Transmitting Spoofed Token: rogue-unauthorized-xyz...';
    try {
        const res = await fetch('/api/v1/inference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Fleet-Tenant': 'FLEET-UNKNOWN',
                'X-Robot-Token': 'rogue-unauthorized-xyz'
            },
            body: JSON.stringify({
                robot_id: 'ROGUE-BOT',
                image_base64: DUMMY_BASE64_IMAGE,
                criticality: 'CRITICAL',
                deadline_ms: 50
            })
        });
        if (res.status === 403) {
            resBadge.innerText = 'HTTP 403 FORBIDDEN | Zero-Trust Perimeter Enforced: Rogue Token Rejected';
            resBadge.style.color = 'var(--color-red)';
            showToast("Zero-Trust Perimeter Enforced: Rogue Token Rejected (403)", "error");
        } else {
            resBadge.innerText = `HTTP ${res.status}`;
        }
    } catch (e) {
        resBadge.innerText = `Error: ${e}`;
    }
});

document.getElementById('btnRefreshFeed')?.addEventListener('click', async () => {
    try {
        const res = await fetch('/api/v1/cloud/feed');
        if (res.ok) {
            const f = await res.json();
            if (f.latest_frame) updateVisionFeed(f.latest_frame);
            if (f.recent_tasks) updateExecutionStream(f.recent_tasks);
            showToast("Vision inference feed snapshot refreshed!", "info");
        }
    } catch (e) {
        console.error("Feed refresh error:", e);
    }
});

// The browser opens a camera only after this explicit control is pressed.
async function submitVisionPhoto(file, source) {
    if (!file) return;
    const actionStatus = document.getElementById('visionActionStatus');
    if (actionStatus) {
        actionStatus.innerText = 'Submitting image to YOLO worker…';
        actionStatus.style.color = 'var(--color-blue)';
    }
    const sideStatus = document.getElementById('sideVisionStatus');
    if (sideStatus) sideStatus.innerText = 'Submitting image to the YOLO worker…';
    try {
        const imageBase64 = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result).split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
        const response = await fetch('/api/v1/inference', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-Fleet-Tenant': 'FLEET-AGV-LOGISTICS', 'X-Robot-Token': 'agv-token'},
            body: JSON.stringify({robot_id: 'AGV-01', image_base64: imageBase64, source, criticality: 'CRITICAL', deadline_ms: 250, task_type: 'object_detection'})
        });
        if (!response.ok) throw new Error(`gateway returned HTTP ${response.status}`);
        const task = await response.json();
        if (actionStatus) actionStatus.innerText = 'YOLO inference queued…';
        const expiresAt = Date.now() + 15000;
        while (Date.now() < expiresAt) {
            await new Promise(resolve => setTimeout(resolve, 500));
            const resultResponse = await fetch(`/api/v1/inference/${task.request_id}/result`, {headers: {'X-Fleet-Tenant': 'FLEET-AGV-LOGISTICS', 'X-Robot-Token': 'agv-token'}});
            if (!resultResponse.ok) continue;
            const result = await resultResponse.json();
            if (result.state === 'completed') {
                await pollTelemetry();
                showToast(`YOLO complete: ${result.perception.action}`, result.perception.hazard_detected ? 'error' : 'success');
                if (sideStatus) sideStatus.innerText = `YOLO complete: ${result.perception.action}`;
                return;
            }
            if (result.state === 'failed') throw new Error(result.error || 'worker failed');
        }
        throw new Error('worker did not finish within 15 seconds');
    } catch (error) {
        if (actionStatus) {
            actionStatus.innerText = `YOLO error: ${error.message}`;
            actionStatus.style.color = 'var(--color-red)';
        }
        if (sideStatus) sideStatus.innerText = `YOLO error: ${error.message}`;
        showToast(`Vision submission failed: ${error.message}`, 'error');
    }
}

let pendingVisionPhoto = null;
function queueVisionPhoto(file, source) {
    if (!file) return;
    const auto = document.getElementById('sideAutoYolo');
    if (!auto || auto.checked) {
        submitVisionPhoto(file, source);
        return;
    }
    pendingVisionPhoto = { file, source };
    document.getElementById('btnSideRunYolo').disabled = false;
    document.getElementById('sideVisionStatus').innerText = 'Photo selected. Press Run Real YOLO Inference.';
}

document.getElementById('btnUploadVision')?.addEventListener('click', () => document.getElementById('visionImageUpload')?.click());
document.getElementById('btnOpenVisionCamera')?.addEventListener('click', () => document.getElementById('visionCameraCapture')?.click());
document.getElementById('visionImageUpload')?.addEventListener('change', event => queueVisionPhoto(event.target.files?.[0], 'web_upload'));
document.getElementById('visionCameraCapture')?.addEventListener('change', event => queueVisionPhoto(event.target.files?.[0], 'web_camera'));

// Left dispatcher panel mirrors the top controls, so every legacy mission
// operation remains available without sacrificing the NextGen canvas.
function syncSideControl(sideId, mainId, eventName = 'change') {
    const side = document.getElementById(sideId);
    const main = document.getElementById(mainId);
    side?.addEventListener(eventName, () => {
        main.value = side.value;
        main.dispatchEvent(new Event(eventName, { bubbles: true }));
    });
}
syncSideControl('sidePresetSelect', 'presetSelect');
syncSideControl('sideSceneSelect', 'sceneSelect');
syncSideControl('sideCritSelect', 'critSelect');
syncSideControl('sideDeadline', 'deadlineSlider', 'input');

document.getElementById('sideDeadline')?.addEventListener('input', event => {
    document.getElementById('sideDeadlineValue').innerText = `${event.target.value}ms`;
});
document.getElementById('btnSideCamera')?.addEventListener('click', () => document.getElementById('btnOpenVisionCamera')?.click());
document.getElementById('btnSideUpload')?.addEventListener('click', () => document.getElementById('btnUploadVision')?.click());
document.getElementById('btnSideDispatch')?.addEventListener('click', () => document.getElementById('btnDispatchTask')?.click());
document.getElementById('btnSideReset')?.addEventListener('click', () => document.getElementById('btnSystemReset')?.click());
document.getElementById('btnSideRunYolo')?.addEventListener('click', () => {
    if (!pendingVisionPhoto) return;
    const pending = pendingVisionPhoto;
    pendingVisionPhoto = null;
    document.getElementById('btnSideRunYolo').disabled = true;
    submitVisionPhoto(pending.file, pending.source);
});
document.querySelectorAll('[data-side-tab]').forEach(button => button.addEventListener('click', () => navigateToTab(button.dataset.sideTab)));

// ================= AUTO-NAVIGATE & CENTER ON TAB =================
let navigationTimer = null;

function navigateToTab(tabId, targetSelector = null, pulse = true, delayMs = 0, onComplete = null) {
    if (navigationTimer) {
        clearTimeout(navigationTimer);
        navigationTimer = null;
    }

    const executeNavigation = () => {
        // 1. Activate matching tab button
        document.querySelectorAll('.tab-btn').forEach(b => {
            if (b.getAttribute('data-tab') === tabId) {
                b.classList.add('active');
            } else {
                b.classList.remove('active');
            }
        });

        // 2. Activate matching tab panel
        document.querySelectorAll('.tab-panel').forEach(p => {
            if (p.id === tabId) {
                p.classList.add('active');
            } else {
                p.classList.remove('active');
            }
        });

        // 3. Smoothly center the element or tab in the viewport
        const targetEl = targetSelector ? document.querySelector(targetSelector) : document.getElementById(tabId);
        const scrollTarget = targetEl || document.getElementById(tabId);

        if (scrollTarget) {
            setTimeout(() => {
                scrollTarget.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });

                if (pulse) {
                    scrollTarget.classList.remove('tab-focus-pulse');
                    void scrollTarget.offsetWidth; // Force CSS reflow
                    scrollTarget.classList.add('tab-focus-pulse');
                    setTimeout(() => {
                        scrollTarget.classList.remove('tab-focus-pulse');
                    }, 2400);
                }

                if (onComplete && typeof onComplete === 'function') {
                    onComplete();
                }
            }, 100);
        }
    };

    if (delayMs > 0) {
        navigationTimer = setTimeout(executeNavigation, delayMs);
    } else {
        executeNavigation();
    }
}
window.navigateToTab = navigateToTab;

// ================= DEMO ACTIONS & CONTROLS =================
// 1. Play / Pause
document.getElementById('btnPlayPause').addEventListener('click', (e) => {
    isRunning = !isRunning;
    e.currentTarget.innerHTML = isRunning ? '⏸ <span>Pause Fleet</span>' : '▶ <span>Resume Fleet</span>';
    showToast(isRunning ? "Fleet Simulation Resumed" : "Fleet Simulation Paused", "info");
});

// 2. Hazard Toggle (Paces visual stop first, then glides to Tab 4 logs)
document.getElementById('btnHazard').addEventListener('click', async () => {
    humanHazard = !humanHazard;
    const btn = document.getElementById('btnHazard');
    if (humanHazard) {
        humanPos = { x: agv.x + 85, y: 265 };
        agv.status = 'STOPPED';
        agv.speed = 0;
        btn.innerHTML = '🟢 <span>CLEAR HAZARD</span> <span class="btn-tab-tag">Tab 4</span>';
        
        // 1. Immediately halt on floor, turn 5G telemetry line & packets RED, and display live details callout
        showBanner("🚨 SAFETY CRITICAL: HUMAN OBSTACLE DETECTED! 5G TELEMETRY SWITCHED TO RED", "rgba(220, 38, 38, 0.95)", "#ef4444");
        showToast("🚨 Obstacle detected at 85cm! AGV halted, 5G telemetry turned RED. Viewing floor telemetry details... gliding to S3 audit logs in 3s.", "error", 4500);

        // 2. Immediately seal authentic ISO 3691-4 Black-Box incident in backend S3/Redis
        let sealedIncident = null;
        try {
            const hRes = await fetch('/api/v1/cloud/hazard', { method: 'POST' });
            if (hRes.ok) {
                const hData = await hRes.json();
                sealedIncident = hData.incident;
                if (sealedIncident) {
                    latestIncidentsCache = [sealedIncident, ...latestIncidentsCache.filter(i => i.incident_id !== sealedIncident.incident_id)];
                    updateIncidentsTab(latestIncidentsCache);
                }
            }
        } catch (err) {
            console.warn("Hazard archive call error:", err);
        }

        // 3. Keep viewport at the top for 3.0s so viewer clearly sees the AGV stopping,
        // the red 5G telemetry line and packets, and reads the on-floor Telemetry Callout box!
        navigateToTab('tabIncidents', '#incidentsTableBody', true, 3000, () => {
            const incId = sealedIncident?.incident_id || (latestIncidentsCache[0]?.incident_id);
            if (incId) {
                inspectIncident(incId);
            }
            showToast("🛡️ ISO 3691-4 Black-Box sealed into S3: Showing flight recorder audit trace.", "info", 4500);
        });
    } else {
        if (navigationTimer) {
            clearTimeout(navigationTimer);
            navigationTimer = null;
        }
        agv.status = 'NORMAL';
        agv.speed = 2.4;
        btn.innerHTML = '🚨 <span>TRIGGER HAZARD (AGV-01)</span> <span class="btn-tab-tag">Tab 4</span>';
        showBanner("✅ PATH CLEAR: AGV RESUMING AUTONOMOUS TRANSIT", "rgba(16, 185, 129, 0.95)", "#10b981");
        showToast("Hazard cleared. AGV resuming normal speed. Telemetry restored to normal.", "success");
    }
});

// 3. Batch Leapfrog (Paced preemption demo)
document.getElementById('btnBatchDemo').addEventListener('click', async () => {
    showBanner("📦 INJECTING 5x ROUTINE BATCH + 1 CRITICAL AGV LEAPFROG TASK...", "rgba(37, 99, 235, 0.95)", "#2563eb");
    
    // Allow user to see the queue HUD register the burst, then scroll down to the stream
    navigateToTab('tabBenchmarks', '#taskExecutionStreamBody', true, 1600);
    try {
        const res = await fetch('/api/v1/cloud/batch_leapfrog', { method: 'POST' });
        const data = await res.json();
        showToast(`Preemption Verified! Critical AGV (RADS ${data.critical_rads_score}) pre-empted 5 queued tasks! Moving to Tab 5 (Execution Stream)...`, "success", 5000);
        showBanner(`⚡ PREEMPTION CONFIRMED: AGV-01 LEAPFROGGED 5 ROUTINE TASKS!`, "rgba(16, 185, 129, 0.95)", "#10b981");
    } catch (e) {
        showToast(`Batch Leapfrog error: ${e}`, "error");
    }
});

// 4. Kill Worker-1 / Restore Worker-1 (Paced failover demo)
document.getElementById('btnKillWorker').addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    if (worker1Alive) {
        try {
            await fetch('/api/v1/debug/workers/worker-1/fail', { method: 'POST' });
            worker1Alive = false;
            btn.innerHTML = '⚡ <span>RESTORE WORKER-1</span> <span class="btn-tab-tag">Tab 1</span>';
            btn.className = 'btn btn-emerald';
            showBanner("🔥 WORKER-1 CRASHED! ATOMIC FAILOVER REQUEUE ENGAGED.", "rgba(245, 158, 11, 0.95)", "#f59e0b");
            showToast("Worker-1 killed! Moving to Tab 1 (Worker Fabric) to observe instant peer failover...", "warning", 5000);
            navigateToTab('tabFabric', '#workersListContainer', true, 1400);
        } catch (err) {
            showToast(`Fail error: ${err}`, "error");
        }
    } else {
        try {
            await fetch('/api/v1/debug/workers/worker-1/recover', { method: 'POST' });
            worker1Alive = true;
            btn.innerHTML = '🔥 <span>KILL WORKER-1</span> <span class="btn-tab-tag">Tab 1</span>';
            btn.className = 'btn btn-warning';
            showBanner("⚡ WORKER-1 RESTORED & RE-JOINED COMPUTE CLUSTER.", "rgba(16, 185, 129, 0.95)", "#10b981");
            showToast("Worker-1 restored to cluster pool! Centered on Tab 1 (Worker Fabric).", "success");
            navigateToTab('tabFabric', '#workersListContainer', true, 1000);
        } catch (err) {
            showToast(`Recover error: ${err}`, "error");
        }
    }
});

// Helper for individual worker cards
window.toggleWorker = async function(wid, healthy) {
    const action = healthy ? 'fail' : 'recover';
    await fetch(`/api/v1/debug/workers/${wid}/${action}`, { method: 'POST' });
    showToast(`Worker ${wid} ${action === 'fail' ? 'killed' : 'recovered'} successfully.`, healthy ? "warning" : "success");
};

// 5. Fleet Surge (Paced autoscaler demo)
document.getElementById('btnSurge').addEventListener('click', async () => {
    showBanner("📈 FLEET SURGE: INJECTING 10 RAPID TASKS TO TRIGGER KEDA AUTOSCALER...", "rgba(16, 185, 129, 0.95)", "#059669");
    navigateToTab('tabAutoscaler', '#autoscalerLogContainer', true, 1400);
    try {
        const res = await fetch('/api/v1/cloud/surge', { method: 'POST' });
        const data = await res.json();
        showToast("Fleet Surge Injected (10 tasks)! Centering on Tab 2 (Autoscaler) to watch pod provisioning in real-time...", "info", 5000);
    } catch (e) {
        showToast(`Surge error: ${e}`, "error");
    }
});

const DUMMY_BASE64_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";

// 6. Rogue Token (Paced security demo)
document.getElementById('btnRogue').addEventListener('click', async () => {
    showBanner("🛡️ INGRESS GATEWAY: INJECTING UNAUTHORIZED ROGUE SPOOFED TOKEN...", "rgba(225, 29, 72, 0.95)", "#e11d48");
    navigateToTab('tabTenants', '#tenantsListContainer', true, 1400);
    try {
        const res = await fetch('/api/v1/inference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Robot-Token': 'rogue-unauthorized-secret-999'
            },
            body: JSON.stringify({
                robot_id: 'ROGUE-HACKER-99',
                task_type: 'object_detection',
                criticality: 'CRITICAL',
                deadline_ms: 100.0,
                image_base64: DUMMY_BASE64_IMAGE
            })
        });

        if (res.status === 403) {
            showToast("Zero-Trust Gateway: Rogue token REJECTED with HTTP 403 Forbidden! Centered on Tab 3 (Fleet Governance).", "security", 5000);
            showBanner("🛡️ PERIMETER SECURED: ROGUE TOKEN BLOCKED (HTTP 403 FORBIDDEN)", "rgba(225, 29, 72, 0.95)", "#e11d48");
        } else {
            showToast(`Unexpected status: ${res.status}`, "warning");
        }
    } catch (e) {
        showToast(`Rogue test error: ${e}`, "error");
    }
});

// 7. System Reset
document.getElementById('btnSystemReset').addEventListener('click', async () => {
    try {
        await Promise.all([
            fetch('/api/v1/debug/workers/worker-1/recover', { method: 'POST' }),
            fetch('/api/v1/debug/workers/worker-2/recover', { method: 'POST' })
        ]);
        worker1Alive = true;
        worker2Alive = true;
        humanHazard = false;
        document.getElementById('btnHazard').innerHTML = '🚨 <span>TRIGGER HAZARD (AGV-01)</span> <span class="btn-tab-tag">Tab 4</span>';
        document.getElementById('btnKillWorker').innerHTML = '🔥 <span>KILL WORKER-1</span> <span class="btn-tab-tag">Tab 1</span>';
        document.getElementById('btnKillWorker').className = 'btn btn-warning';
        showToast("System & Worker Nodes fully reset to HEALTHY.", "success");
    } catch (e) {
        showToast(`Reset error: ${e}`, "error");
    }
});

// 8. Custom Task Dispatch (Paced perception demo)
document.getElementById('deadlineSlider').addEventListener('input', (e) => {
    document.getElementById('deadlineDisplay').innerText = `${e.target.value}ms`;
});

document.getElementById('presetSelect').addEventListener('change', (e) => {
    const val = e.target.value;
    const crit = document.getElementById('critSelect');
    const dl = document.getElementById('deadlineSlider');
    const disp = document.getElementById('deadlineDisplay');
    const scn = document.getElementById('sceneSelect');

    if (val === 'AGV-01') {
        crit.value = 'CRITICAL';
        dl.value = 100;
        scn.value = 'human';
    } else if (val === 'DRONE-04') {
        crit.value = 'HIGH';
        dl.value = 250;
        scn.value = 'pallet';
    } else if (val === 'SWEEPER-09') {
        crit.value = 'NORMAL';
        dl.value = 600;
        scn.value = 'dock';
    } else {
        crit.value = 'LOW';
        dl.value = 1500;
        scn.value = 'clear';
    }
    disp.innerText = `${dl.value}ms`;
});

document.getElementById('btnDispatchTask').addEventListener('click', async () => {
    const preset = document.getElementById('presetSelect').value;
    const crit = document.getElementById('critSelect').value;
    const dl = parseFloat(document.getElementById('deadlineSlider').value);

    // Auto-navigate to Tab 5 after brief delay so user can see dispatch feedback
    navigateToTab('tabBenchmarks', '#visionFeedCanvas', true, 1200);

    try {
        const res = await fetch('/api/v1/inference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Robot-Token': 'robot-token-secret'
            },
            body: JSON.stringify({
                robot_id: preset,
                task_type: 'object_detection',
                criticality: crit,
                deadline_ms: dl,
                image_base64: DUMMY_BASE64_IMAGE
            })
        });

        if (res.ok) {
            const data = await res.json();
            showToast(`Task Dispatched: ${data.request_id.substring(0, 8)}... (${crit} | ${dl}ms). Centered on Tab 5 (Perception Stream).`, "success");
        } else {
            showToast(`Dispatch failed: ${res.statusText}`, "error");
        }
    } catch (e) {
        showToast(`Dispatch network error: ${e}`, "error");
    }
});

// ================= TABS SWITCHER =================
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-tab');
        navigateToTab(targetId, null, false);
    });
});

// ================= LIVE UTC CLOCK =================
function updateClock() {
    const now = new Date();
    document.getElementById('clockUTC').innerText = now.toUTCString().split(' ')[4] + ' UTC';
}
setInterval(updateClock, 1000);
updateClock();

// ================= STARTUP =================
initTheme();
gameLoop();
setInterval(pollTelemetry, 700);
pollTelemetry();
